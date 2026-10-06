"""Measured database lifecycle checks, restricted to a caller-owned disposable cluster."""
from datetime import datetime, timezone
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
def utc(): return datetime.now(timezone.utc).isoformat()

class Runtime:
    def __init__(self, kube, run, evidence, ns, release, directory):
        self.kube, self.run, self.evidence = kube, run, evidence
        self.ns, self.release, self.directory = ns, release, Path(directory)
        self.pg, self.pool, self.storage = (release+'-'+x for x in ('patroni','pgcat','minio'))
        self.expected = [{'id':1,'phase':'baseline','value':100}]
    def get(self, resource, *args):
        return json.loads(self.run(self.kube+['get',resource,*args,'-o','json']))
    def pods(self, role=None):
        selector='application=patroni,release-name='+self.pg+',cluster-name='+self.pg+'-patronimvp'
        if role:selector+=',role='+role
        return self.get('pods','-l',selector)['items']
    def primary(self):
        pods=self.pods('primary')
        if len(pods)!=1:raise RuntimeError('Expected exactly one primary')
        return pods[0]['metadata']['name']
    def direct(self, sql, pod=None):
        return self.run(self.kube+['exec',pod or self.primary(),'-c','patronimvp','--','bash','-c',
            'PGPASSWORD="$PATRONI_SUPERUSER_PASSWORD" psql -h 127.0.0.1 -X -U "$PATRONI_SUPERUSER_USERNAME" -d postgres -v ON_ERROR_STOP=1 -Atqc "$1"','runtime',sql],timeout=20).strip()
    def query(self, sql):
        # Client is independent of PgCat: a restart does not kill the probe executor.
        code="const fs=require('fs'),y=require('js-yaml'),c=y.load(fs.readFileSync('/config/pgcat.yaml','utf8')),u=c.DBS[0].users[0];const r=require('child_process').spawnSync('psql',['-X','-w','-h',process.argv[1],'-p','5432','-U',u.USER_NAME,'-d',c.DBS[0].NAME,'-Atq','-v','ON_ERROR_STOP=1','-c',process.argv[2]],{env:{...process.env,PGPASSWORD:u.PASSWORD,PGCONNECT_TIMEOUT:'2',PGOPTIONS:'-c statement_timeout=3000'},encoding:'utf8',timeout:6000});if(r.status!==0)process.exit(1);process.stdout.write(r.stdout);"
        return self.run(self.kube+['exec',self.release+'-sql-client','--','node','-e',code,self.pool+'-proxy-service',sql],timeout=10).strip()
    def wait(self, callback, timeout=180):
        start=time.monotonic();last=None
        while time.monotonic()-start<timeout:
            try:
                result=callback()
                if result:return result
            except (RuntimeError, ValueError, KeyError, subprocess.TimeoutExpired) as error:last=type(error).__name__
            time.sleep(1)
        raise RuntimeError('Condition not met within '+str(timeout)+'s; last failure='+str(last))
    def membership(self):
        return json.loads(self.run(self.kube+['exec',self.primary(),'-c','patronimvp','--','python3','-c',
            'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8008/cluster",timeout=5).read().decode())'],timeout=15))
    def stable(self):
        pods=self.pods()
        if len(pods)!=2:return False
        if not all(any(c['type']=='Ready' and c['status']=='True' for c in p.get('status',{}).get('conditions',[])) for p in pods):return False
        members=self.membership()['members']
        if len(members)!=2:return False
        return (sum(m['role'] in ('leader','primary') for m in members)==1 and
                all(m['state'] in ('running','streaming') for m in members))
    def dataset(self, query):
        return json.loads(query("SELECT COALESCE(json_agg(t ORDER BY id),'[]'::json) FROM (SELECT id,phase,value FROM validation_test) t;"))
    def assert_data(self):
        self.wait(lambda:self.dataset(self.query)==self.expected)
        if self.dataset(self.direct)!=self.expected:raise RuntimeError('Primary dataset mismatch')
        for pod in self.pods('replica'):
            self.wait(lambda:self.dataset(lambda sql:self.direct(sql,pod['metadata']['name']))==self.expected)
    def backup_list(self):
        return json.loads(self.run(self.kube+['exec',self.primary(),'-c','patronimvp','--','/wal-g/wal-g','backup-list','--detail','--json','--config','/wal-g-credentials/.walg.env'],timeout=60))
    def backup(self, suffix):
        name=self.release+'-backup-'+suffix;start=time.monotonic();started=utc()
        self.run(self.kube+['create','job',name,'--from=cronjob/'+self.pg+'-exec-script-cronjob'])
        self.run(self.kube+['wait','--for=condition=complete','job/'+name,'--timeout=600s'],timeout=620)
        backups=self.backup_list()
        if not backups:raise RuntimeError('No backup metadata in object storage')
        result=dict(started=started,completed=utc(),duration_seconds=round(time.monotonic()-start,3),job=name,backups=backups)
        self.evidence.save('backup/'+suffix+'.json',result)
        # Job log contains command status and WAL-G progress, never Secret manifests.
        log=self.run(self.kube+['logs','job/'+name],timeout=20)
        (self.evidence.root/'backup'/(suffix+'-job.txt')).write_text(self.evidence.clean(log))
        return result
    def objects(self):
        # mc runs in an independent client pod with credentials mounted via Secret refs.
        output=self.run(self.kube+['exec',self.release+'-object-client','--','sh','-ec',
            'mc alias set store "$ENDPOINT" "$ACCESS" "$PASSWORD" >/dev/null 2>&1; mc ls --recursive --json store/backup'],timeout=60)
        return [json.loads(line) for line in output.splitlines() if line.strip()]
    def archive(self):
        segment=self.direct('SELECT pg_walfile_name(pg_current_wal_lsn());')
        import re
        if not re.fullmatch('[0-9A-F]{24}',segment):raise RuntimeError('Invalid WAL segment')
        self.direct('SELECT pg_switch_wal();')
        self.wait(lambda:self.direct("SELECT COALESCE(last_archived_wal >= '"+segment+"',false) FROM pg_stat_archiver;")=='t',180)
        objects=self.objects()
        if not any(segment in x.get('key','') and 'wal_' in x.get('key','') for x in objects):raise RuntimeError('Archived WAL object absent')
        result=dict(segment=segment,observed=utc(),archiver=json.loads(self.direct('SELECT row_to_json(s) FROM pg_stat_archiver s;')),objects=objects)
        self.evidence.save('backup/wal.json',result)
        self.evidence.record('wal','PASS',detail='Switched segment observed in pg_stat_archiver and object storage')
    def clients(self):
        def apply(pod):self.run(self.kube+['apply','-f','-'],json.dumps(pod))
        apply(dict(apiVersion='v1',kind='Pod',metadata=dict(name=self.release+'-sql-client',namespace=self.ns),spec=dict(restartPolicy='Never',containers=[dict(name='client',image='dbaas/pgcat-config-watcher:1.1.1',command=['sleep','infinity'],resources=dict(requests=dict(cpu='25m',memory='64Mi')),volumeMounts=[dict(name='config',mountPath='/config',readOnly=True)])],volumes=[dict(name='config',secret=dict(secretName=self.pool+'-pgcat-config'))])))
        apply(dict(apiVersion='v1',kind='Pod',metadata=dict(name=self.release+'-object-client',namespace=self.ns),spec=dict(restartPolicy='Never',containers=[dict(name='client',image='dbaas/mc:RELEASE.2025-04-16T18-13-26Z',command=['sleep','infinity'],resources=dict(requests=dict(cpu='25m',memory='64Mi')),env=[dict(name='ENDPOINT',value='http://'+self.storage+'-minio:9000'),dict(name='ACCESS',valueFrom=dict(secretKeyRef=dict(name=self.storage+'-minio-credentials',key='backup-user'))),dict(name='PASSWORD',valueFrom=dict(secretKeyRef=dict(name=self.storage+'-minio-credentials',key='backup-password')))])])))
        for kind in ['sql','object']:self.run(self.kube+['wait','--for=condition=Ready','pod/'+self.release+'-'+kind+'-client','--timeout=120s'])
    def failover(self, action):
        before=self.primary();pods=self.pods('replica');samples=[];stop=threading.Event();ready=threading.Event();acknowledged=[]
        def probe():
            counter=0
            while not stop.is_set():
                start=time.monotonic();at=utc();identity=action+'-'+str(counter);counter+=1
                try:
                    success=self.query("INSERT INTO validation_probe(id) VALUES ('"+identity+"') RETURNING 1;")=='1'
                    if success:acknowledged.append(identity);ready.set()
                except Exception:success=False
                samples.append(dict(timestamp=at,monotonic=start,success=success,latency_seconds=round(time.monotonic()-start,3)))
                stop.wait(.5)
        injected=time.monotonic();thread=threading.Thread(target=probe);thread.start();ready.wait(10);injected=time.monotonic();started=utc()
        result=dict(injected_at=started,old_primary=before,sampling_interval_seconds=.5,action=action)
        held_node=None
        try:
            if not ready.is_set():raise RuntimeError('Continuous write probe could not establish baseline')
            if action=='primary_failover':
                # In this single-node disposable profile a replacement can restart
                # before the leader lease expires. Hold new scheduling so the
                # existing replica must promote; this does not evict that replica.
                node=self.get('pod',before)['spec']['nodeName']
                if self.get('node',node).get('spec',{}).get('unschedulable'):
                    raise RuntimeError('Failure test requires an initially schedulable node')
                held_node=node
                self.run(self.kube+['cordon',node])
                result['replacement_scheduling_held_on']=node
                injected=time.monotonic();started=utc();result['injected_at']=started
                self.run(self.kube+['delete','pod',before,'--grace-period=0','--force','--wait=false'])
                new=self.wait(lambda:self.primary() if self.primary()!=before else None,180)
                result['promotion_observed_seconds']=round(time.monotonic()-injected,3);result['new_primary']=new
                self.run(self.kube+['uncordon',held_node]);held_node=None
                result['replacement_scheduling_released_at']=utc()
            elif action=='replica_failure':
                if len(pods)!=1:raise RuntimeError('Expected one replica target')
                self.run(self.kube+['delete','pod',pods[0]['metadata']['name'],'--grace-period=0','--force','--wait=false'])
            else:
                proxies=self.get('pods','-l','app=proxy,release-name='+self.pool)['items']
                proxies=[p for p in proxies if not p['metadata'].get('deletionTimestamp')]
                if len(proxies)!=1:raise RuntimeError('This failure profile expects exactly one PgCat pod')
                result['deleted_proxy']=proxies[0]['metadata']['name']
                self.run(self.kube+['delete','pod',result['deleted_proxy'],'--grace-period=0','--force','--wait=false'])
            self.wait(lambda:self.query('SELECT 1;')=='1',180)
            result['sql_available_observed_seconds']=round(time.monotonic()-injected,3)
            self.wait(self.stable,240)
            result['stable_observed_seconds']=round(time.monotonic()-injected,3)
            if action=='replica_failure' and self.primary()!=before:raise RuntimeError('Primary changed during replica failure')
            self.assert_data()
            # Stop and verify acknowledged probe commits, separately from uncertain failures.
            stop.set();thread.join(timeout=15)
            persisted=json.loads(self.direct("SELECT COALESCE(json_agg(id),'[]'::json) FROM validation_probe;"))
            missing=sorted(set(acknowledged)-set(persisted))
            result['acknowledged_probe_writes']=len(acknowledged)
            result['missing_acknowledged_probe_ids']=missing
            if missing:raise RuntimeError('Acknowledged probe writes missing after failure')
            row=dict(id={'primary_failover':10,'replica_failure':11,'pgcat_restart':12}[action],phase=action,value=200)
            self.query("INSERT INTO validation_test(id,phase,value) VALUES ("+str(row['id'])+",'"+row['phase']+"',200);")
            self.expected.append(row);self.expected.sort(key=lambda x:x['id']);self.assert_data()
            self.evidence.record(action,'PASS',duration_seconds=round(time.monotonic()-injected,3),detail='Prior committed test rows verified; new write and stable membership verified')
        except Exception:
            self.evidence.record(action,'FAIL');raise
        finally:
            if held_node:
                self.run(self.kube+['uncordon',held_node])
            stop.set();thread.join(timeout=15)
            for sample in samples:sample['elapsed']=round(sample.pop('monotonic')-injected,3)
            result['sql_samples']=samples
            result['failed_samples']=sum(not x['success'] for x in samples)
            failed=[x for x in samples if not x['success']]
            result['observed_failure_span_seconds']=None
            result['first_success_after_failure_seconds']=None
            if failed:
                result['observed_failure_span_seconds']=round(failed[-1]['elapsed']+failed[-1]['latency_seconds']-failed[0]['elapsed'],3)
                recovered=next((x for x in samples if x['success'] and x['elapsed']>failed[-1]['elapsed']),None)
                if recovered:result['first_success_after_failure_seconds']=round(recovered['elapsed']+recovered['latency_seconds'],3)
            if action=='primary_failover' and result.get('new_primary'):
                try:
                    logs=self.run(self.kube+['logs',result['new_primary'],'-c','patronimvp','--since-time='+started,'--timestamps'],timeout=15)
                    result['patroni_events']=[self.evidence.clean(line) for line in logs.splitlines() if any(marker in line.lower() for marker in ['promot','leader lock','lock owner','demot'])]
                except Exception:result['patroni_events']=[]
            result['patroni_detection_time']='NOT OBSERVED separately; promotion polling is an upper-bound observation'
            self.evidence.save('failover/'+action+'.json',result)
            output=io.StringIO();writer=csv.DictWriter(output,fieldnames=['timestamp','elapsed','success','latency_seconds']);writer.writeheader();writer.writerows(samples)
            (self.evidence.root/'failover'/(action+'.csv')).write_text(output.getvalue())
    def execute(self):
        current='postgresql'
        try:
            started=time.monotonic();self.wait(self.stable,240)
            self.evidence.record('postgresql','PASS',duration_seconds=round(time.monotonic()-started,3),detail='Readiness observation after API completion; not total bootstrap time')
            current='patroni'
            membership=self.membership();self.evidence.save('patroni/members.json',membership)
            pods=self.pods();readiness=[]
            for pod in pods:
                created=datetime.fromisoformat(pod['metadata']['creationTimestamp'].replace('Z','+00:00'))
                ready=next(c['lastTransitionTime'] for c in pod['status']['conditions'] if c['type']=='Ready' and c['status']=='True')
                readiness.append(dict(name=pod['metadata']['name'],created=created.isoformat(),ready=ready,duration_seconds=(datetime.fromisoformat(ready.replace('Z','+00:00'))-created).total_seconds(),uid=pod['metadata']['uid']))
            self.evidence.save('patroni/readiness.json',readiness)
            self.evidence.save('patroni/replication.json',json.loads(self.direct('SELECT COALESCE(json_agg(t),\'[]\'::json) FROM (SELECT application_name,state,sync_state,sent_lsn,replay_lsn FROM pg_stat_replication) t;')))
            for role in ['primary','replica']:
                expected={p['status']['podIP'] for p in self.pods(role)}
                service='patronimvp-'+('master' if role=='primary' else 'replica')+'-'+self.pg
                endpoints=self.get('endpoints',service)
                actual={a['ip'] for s in endpoints.get('subsets',[]) for a in s.get('addresses',[])}
                if actual!=expected:raise RuntimeError('Service endpoints do not match intended role')
                self.evidence.save('patroni/'+role+'-endpoints.json',endpoints)
            self.evidence.record('patroni','PASS',detail='Exactly one primary and one streaming replica; role endpoints match')
            current='pgcat';self.clients();self.wait(lambda:self.query('SELECT 1;')=='1')
            observations=[self.query('SELECT inet_server_addr(),pg_is_in_recovery();') for _ in range(8)]
            self.evidence.save('sql/routing.json',dict(client_pod=self.release+'-sql-client',host=self.pool+'-proxy-service',port=5432,backend_observations=observations))
            self.evidence.record('pgcat','PASS',detail='Independent client authenticated through PgCat Service; backend observations recorded')
            current='sql';self.query('CREATE TABLE validation_test(id integer PRIMARY KEY,phase text NOT NULL,value integer NOT NULL,created_at timestamptz DEFAULT clock_timestamp()); INSERT INTO validation_test(id,phase,value) VALUES (1,\'baseline\',100);')
            self.query('CREATE TABLE validation_probe(id text PRIMARY KEY);');self.assert_data();self.evidence.save('sql/expected-baseline.json',self.expected);self.evidence.record('sql','PASS',detail='Baseline row matches through PgCat, primary and replica')
            current='backup';backup=self.backup('baseline');objects=self.objects()
            if not any('backup_stop_sentinel.json' in x.get('key','') for x in objects):raise RuntimeError('Backup sentinel absent')
            self.evidence.save('backup/objects.json',objects);self.evidence.record('backup','PASS',duration_seconds=backup['duration_seconds'],detail='Official CronJob-derived Job, WAL-G listing and S3 objects verified')
            current='wal';time.sleep(2);target=self.direct("SELECT to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS');")
            time.sleep(2);self.query("INSERT INTO validation_test(id,phase,value) VALUES (2,'after-target',200);");self.expected.append(dict(id=2,phase='after-target',value=200));self.assert_data();self.archive()
            if os.getenv('RUN_PITR_TEST')=='1':
                current='pitr';start=time.monotonic();before=list(self.expected)
                self.evidence.save('pitr/attempt.json',dict(target_utc=target,before=before,started=utc(),rows_with_timestamps=json.loads(self.direct('SELECT json_agg(t ORDER BY id) FROM validation_test t;'))))
                command=['python3',str(ROOT/'scripts/recovery.py'),'--namespace',self.ns,'--patroni-releasename',self.pg,'--pgcat-releasename',self.pool,'--recovery-time',target,'--state-dir',str(self.directory/'recovery'),'--execute']
                recovery=subprocess.run(command,capture_output=True,text=True,timeout=1800)
                self.evidence.save('pitr/command.json',dict(exit_code=recovery.returncode,stdout=recovery.stdout,stderr=recovery.stderr))
                if recovery.returncode:raise RuntimeError('Recovery failed; sanitized stage diagnostics saved')
                self.wait(self.stable,240);self.expected=[dict(id=1,phase='baseline',value=100)];self.assert_data()
                self.query("INSERT INTO validation_test(id,phase,value) VALUES (3,'after-recovery',300);");self.expected.append(dict(id=3,phase='after-recovery',value=300));self.assert_data()
                result=dict(target_utc=target,before=before,after=self.expected,completed=utc(),duration_seconds=round(time.monotonic()-start,3),members=self.membership())
                self.evidence.save('pitr/result.json',result);self.evidence.record('pitr','PASS',duration_seconds=result['duration_seconds'],detail='A present, B absent, new C write verified on primary/replica/PgCat')
            if os.getenv('RUN_FAILURE_TEST')=='1':
                for current in ['primary_failover','replica_failure','pgcat_restart']:self.failover(current)
                current='backup_during_writes';written=[];errors=[];stop=threading.Event()
                def writer():
                    row_id=100
                    while not stop.is_set():
                        try:self.query("INSERT INTO validation_test(id,phase,value) VALUES ("+str(row_id)+",'backup-write',400);");written.append(dict(id=row_id,phase='backup-write',value=400));row_id+=1
                        except Exception:errors.append(utc())
                        stop.wait(.25)
                thread=threading.Thread(target=writer);thread.start()
                try:concurrent=self.backup('during-writes')
                finally:stop.set();thread.join(timeout=15)
                self.expected.extend(written);self.expected.sort(key=lambda x:x['id']);self.assert_data()
                if not written or errors:raise RuntimeError('Writes failed or absent during backup')
                self.evidence.save('backup/concurrent-writes.json',dict(rows=written,errors=errors,backup=concurrent))
                self.evidence.record('backup_during_writes','PASS',detail='Concurrent writes and backup completion verified; restore of this second backup NOT RUN')
            validation=self.run(['python3',str(ROOT/'scripts/validate/health.py'),'cluster','--namespace',self.ns,'--release',self.pg,'--pgcat-release',self.pool],timeout=180)
            self.evidence.save('logs/live-validator.json',dict(status='PASS',output=validation))
            self.evidence.save('sql/expected-final.json',self.expected)
            self.evidence.record('node_drain','NOT APPLICABLE',detail='Single-node kind; no multi-worker drain model')
            self.evidence.record('network_policy','NOT APPLICABLE',detail='Default kind CNI does not enforce policy; policies remain disabled')
        except Exception:
            self.evidence.record(current,'FAIL');raise
