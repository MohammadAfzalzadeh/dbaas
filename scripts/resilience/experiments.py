"""Bounded experiments against the identity-checked disposable Lab."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import uuid
from lab import ROOT, run, utc

class Probe:
    def __init__(self,lab,name,interval=.1):
        self.lab=lab;self.name=name;self.identity=uuid.uuid4().hex;self.rows=[];self.ready=threading.Event();self.interval=interval
    def __enter__(self):
        self.started=time.monotonic()
        self.process=subprocess.Popen(self.lab.kube+['exec','-i','persistent-client','--','python3','-u','-',self.identity,'lab-pgcat-proxy-service','600',str(self.interval)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
        self.process.stdin.write((ROOT/'scripts/resilience/persistent-client.py').read_text());self.process.stdin.close()
        def read():
            for line in self.process.stdout:
                row=json.loads(line);self.rows.append(row)
                if row.get('success'):self.ready.set()
        self.reader=threading.Thread(target=read);self.reader.start()
        if not self.ready.wait(20):
            self.lab.command('exec','persistent-client','--','touch','/tmp/stop-'+self.identity)
            self.process.wait(timeout=30);self.reader.join(timeout=5)
            raise RuntimeError('Persistent probe did not establish a healthy baseline')
        time.sleep(2)
        return self
    def __exit__(self,*exception):
        self.lab.command('exec','persistent-client','--','touch','/tmp/stop-'+self.identity)
        self.process.wait(timeout=30);self.reader.join(timeout=5)
        acknowledged=[r['id'] for r in self.rows if r['success']]
        persisted=json.loads(self.lab.runtime.direct("SELECT COALESCE(json_agg(id),'[]'::json) FROM resilience_ledger WHERE id LIKE '"+self.identity+"-%';"))
        missing=sorted(set(acknowledged)-set(persisted))
        successes=[r['elapsed_seconds']+r['latency_seconds'] for r in self.rows if r['success']]
        failed=[r for r in self.rows if not r['success']]
        result=dict(samples=self.rows,acknowledged_transactions=len(acknowledged),failed_transactions=len(failed),reconnects=max(0,max((r['connections'] for r in self.rows),default=0)-1),
                    longest_success_gap_seconds=round(max((b-a for a,b in zip(successes,successes[1:])),default=0),6),missing_acknowledged_ids=missing,interval_seconds=self.interval)
        self.lab.evidence.save('persistent-'+self.name+'.json',result)
        if missing:raise RuntimeError('Acknowledged writes missing after disruption')


def baseline(lab):
    r=lab.runtime;r.wait(lab.stable)
    r.query('CREATE TABLE validation_test(id integer PRIMARY KEY,phase text NOT NULL,value integer NOT NULL,created_at timestamptz DEFAULT clock_timestamp()); INSERT INTO validation_test VALUES (1,\'baseline\',100); CREATE TABLE resilience_ledger(id text PRIMARY KEY);')
    r.assert_data();r.backup('baseline');time.sleep(2)
    target=r.direct("SELECT to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS');")
    time.sleep(2);r.query("INSERT INTO validation_test(id,phase,value) VALUES (2,'after-target',200);")
    r.expected.append(dict(id=2,phase='after-target',value=200));r.assert_data();r.archive()
    lab.state.update(expected=r.expected,target=target);lab.save_state()
    lab.evidence.save('baseline.json',dict(expected=r.expected,target_utc=target,membership=r.membership()))
    lab.evidence.record('baseline','PASS',detail='SQL through PgCat, primary and two replicas; backup objects and WAL')


def network(lab):
    def peer(labels):return {'podSelector':{'matchLabels':labels}}
    dns={'to':[{'namespaceSelector':{'matchLabels':{'kubernetes.io/metadata.name':'kube-system'}}}], 'ports':[{'protocol':p,'port':53} for p in ('TCP','UDP')]}
    api=lab.get('service','kubernetes','-n','default')['spec']['clusterIP']
    nodeips=[a['address'] for n in lab.get('nodes')['items'] for a in n['status']['addresses'] if a['type']=='InternalIP']
    api_rule={'to':[{'ipBlock':{'cidr':ip+'/32'}} for ip in [api,*nodeips]],'ports':[{'port':443},{'port':6443}]}
    db=peer({'release-name':'lab-patroni'});pool=peer({'release-name':'lab-pgcat'});store=peer({'release-name':'lab-minio'});client=peer({'dbaas-client':'allowed'});monitor=peer({'dbaas-monitor':'true'})
    rules={
      'lab-patroni':dict(ingress=[{'from':[db,pool,client,monitor],'ports':[{'port':5432},{'port':8008}]}],egress=[dns,api_rule,{'to':[db],'ports':[{'port':5432},{'port':8008}]},{'to':[store],'ports':[{'port':9000}]}]),
      'lab-pgcat':dict(ingress=[{'from':[client],'ports':[{'port':5432}]},{'from':[monitor],'ports':[{'port':9930}]}],egress=[dns,{'to':[db],'ports':[{'port':5432}]}]),
      'lab-minio':dict(ingress=[{'from':[peer({'application':'patroni'}),store,client,monitor],'ports':[{'port':9000},{'port':9001}]}],egress=[dns,api_rule,{'to':[store],'ports':[{'port':9000}]}])}
    if lab.state.get('restore_release'):
        target=lab.state['restore_release']
        rules[target]=json.loads(json.dumps(rules['lab-patroni']).replace('lab-patroni',target))
    for release,settings in rules.items():
        values=json.loads(run(['helm','get','values',release,'-n',lab.ns,'--all','-o','json']))
        values['networkPolicy']={'enabled':True,**settings}
        lab.helm(release,('patroni' if release.startswith('isolated-') else release.split('-')[-1]),values)
    # Connectivity probes use a fresh pod with no allow label. Timeout must be
    # observed as a failed TCP connect, not a missing binary or failed pod startup.
    lab.apply(dict(apiVersion='v1',kind='Pod',metadata=dict(name='unrelated-probe',namespace=lab.ns),spec=dict(containers=[dict(name='probe',image='dbaas/patroni:2.1.0',command=['sleep','infinity'])])))
    lab.command('wait','--for=condition=Ready','pod/unrelated-probe','--timeout=180s')
    outcomes=[]
    for pod,expected in [('persistent-client',True),('unrelated-probe',False)]:
        for host,port in [('patronimvp-master-lab-patroni',5432),('lab-minio-minio',9000)]:
            script="import socket,json; s=socket.socket();s.settimeout(3);\ntry:s.connect(("+repr(host)+","+str(port)+"));print(json.dumps({'connected':True}))\nexcept OSError as e:print(json.dumps({'connected':False,'error':type(e).__name__}))"
            result=json.loads(lab.command('exec',pod,'--','python3','-c',script))
            outcomes.append(dict(pod=pod,host=host,port=port,expected=expected,**result))
            if result['connected']!=expected:raise RuntimeError('NetworkPolicy outcome disagrees with expected flow')
    if lab.state.get('restore_release'):
        target=lab.state['restore_release']+'-patronimvp-0'
        script="import socket,json; s=socket.socket();s.settimeout(3);\ntry:s.connect(('patronimvp-master-lab-patroni',5432));print('CONNECTED')\nexcept OSError:print('DENIED')"
        outcome=lab.command('exec',target,'-c','patronimvp','--','python3','-c',script).strip()
        outcomes.append(dict(pod=target,host='patronimvp-master-lab-patroni',outcome=outcome))
        if outcome!='DENIED':raise RuntimeError('Cross-release database access unexpectedly allowed')
    # Exercise actual flows after enforcement, not just an open socket.
    lab.runtime.assert_data();lab.runtime.backup('network');lab.runtime.archive()
    lab.command('exec','deployment/dbaas-backend','--','helm','list','-n',lab.ns)
    lab.evidence.save('network-policy.json',dict(cni='Calico v3.28.2',probes=outcomes,policies=lab.get('networkpolicy'),members=lab.runtime.membership(),api_to_kubernetes='PASS',replication='PASS',walg_to_minio='PASS',logging='NOT IMPLEMENTED'))
    lab.command('delete','pod','unrelated-probe','--wait=true')
    lab.evidence.record('network_policy','PASS',detail='Allowed SQL/replication/backup/API flows and denied unrelated TCP probes')


def disruptions(lab):
    r=lab.runtime
    # PgCat Service and independent per-pod configuration volumes.
    proxies=lab.get('pods','-l','app=proxy,release-name=lab-pgcat')['items']
    if len(proxies)!=2 or len({p['spec']['nodeName'] for p in proxies})!=2:raise RuntimeError('PgCat not spread')
    config=[]
    for p in proxies:
        pod=p['metadata']['name']
        digest=lab.command('exec',pod,'-c','pgcat-config-watcher','--','node','-e',"const f=require('fs'),c=require('crypto');console.log(c.createHash('sha256').update(f.readFileSync('/etc/pgcat/pgcat.toml')).digest('hex'))").strip()
        config.append(dict(pod=pod,node=p['spec']['nodeName'],config_sha256=digest,empty_dirs=[v['name'] for v in p['spec']['volumes'] if 'emptyDir' in v]))
    with Probe(lab,'pgcat-delete'):
        start=time.monotonic();lab.command('delete','pod',proxies[0]['metadata']['name'],'--wait=false')
        r.wait(lambda:r.query('SELECT 1;')=='1');sql=time.monotonic()-start
        lab.command('rollout','status','deployment/lab-pgcat-proxy-deployment','--timeout=180s')
        time.sleep(3)
    lab.evidence.save('pgcat-ha.json',dict(config=config,sql_available_seconds=sql,endpoints=lab.get('endpoints','lab-pgcat-proxy-service')))
    lab.evidence.record('pgcat_ha','PASS',detail='Two spread proxies; persistent client through pod deletion')
    for role in ('replica','primary'):
        pod=r.pods(role)[0];node=pod['spec']['nodeName'];old=r.primary();start=time.monotonic()
        events=dict(node=node,role=role,old_primary=old,drain_initiated=utc(),before_pdb=lab.get('pdb'))
        lab.topology('before-drain-'+role)
        try:
            with Probe(lab,'drain-'+role):
                result=subprocess.run(lab.kube+['drain',node,'--ignore-daemonsets','--delete-emptydir-data','--timeout=240s'],capture_output=True,text=True,timeout=260)
                events.update(drain_exit_code=result.returncode,drain_output=lab.evidence.clean(result.stdout+result.stderr),drain_completed_seconds=time.monotonic()-start)
                if result.returncode:raise RuntimeError('Drain failed; no eviction bypass used')
                if role=='primary':
                    new=r.wait(lambda:r.primary() if r.primary()!=old else None,180);events.update(new_primary=new,promotion_observed_seconds=time.monotonic()-start)
                elif r.primary()!=old:raise RuntimeError('Primary changed during replica drain')
                r.wait(lambda:r.query('SELECT 1;')=='1');events['sql_available_seconds']=time.monotonic()-start
                events['during_pdb']=lab.get('pdb');events['during_pods']=lab.get('pods');events['scheduling_events']=lab.get('events','--field-selector','reason=FailedScheduling')
                lab.command('uncordon',node)
                r.wait(lab.stable,240);r.assert_data();events['stable_seconds']=time.monotonic()-start
                time.sleep(3)
        finally:
            lab.command('uncordon',node);lab.evidence.save('drain-'+role+'.json',events)
        lab.evidence.record('drain_'+role,'PASS',duration_seconds=round(time.monotonic()-start,3),detail='Eviction respected; local PVC member rejoined on original node after uncordon')
    # Abrupt node loss is a separate experiment, never a renamed drain.
    primary=r.pods('primary')[0];node=primary['spec']['nodeName'];start=time.monotonic();events=dict(node=node,old_primary=primary['metadata']['name'],injected=utc())
    try:
        with Probe(lab,'node-loss'):
            run(['docker','stop','--time','0',node],timeout=30)
            new=r.wait(lambda:next((p['metadata']['name'] for p in r.pods('primary') if p['metadata']['name']!=events['old_primary']),None),180)
            events.update(new_primary=new,promotion_observed_seconds=time.monotonic()-start)
            r.wait(lambda:r.query('SELECT 1;')=='1',180);events['sql_available_seconds']=time.monotonic()-start
            events['nodes_during_loss']=lab.get('nodes');events['pdb_during_loss']=lab.get('pdb')
            run(['docker','start',node]);r.wait(lab.stable,240);r.assert_data();events['stable_seconds']=time.monotonic()-start;time.sleep(3)
    finally:
        run(['docker','start',node]);lab.evidence.save('node-loss.json',events)
    lab.evidence.record('node_loss','PASS',detail='Worker container stopped abruptly; source data and acknowledged ledger checked')


def proxy_failure(lab):
    proxies=[p for p in lab.get('pods','-l','app=proxy,release-name='+lab.runtime.pool)['items'] if not p['metadata'].get('deletionTimestamp')]
    if len(proxies)!=2:raise RuntimeError('Expected two proxies')
    before=lab.get('endpoints','lab-pgcat-proxy-service');start=time.monotonic()
    with Probe(lab,'pgcat-abrupt'):
        # Select the proxy holding the persistent client's TCP session. Run this
        # stage without other persistent-client workloads to avoid ambiguity.
        ip=lab.get('pod','persistent-client')['status']['podIP']
        remote=''.join(f'{int(part):02X}' for part in ip.split('.')[::-1])
        selected=[]
        for proxy in proxies:
            sockets=lab.command('exec',proxy['metadata']['name'],'-c','pgcat-config-watcher','--','node','-e',"process.stdout.write(require('fs').readFileSync('/proc/net/tcp','utf8'))")
            if any(len(line.split())>3 and line.split()[1].endswith(':1538') and line.split()[2].startswith(remote+':') and line.split()[3]=='01' for line in sockets.splitlines()[1:]):selected.append(proxy)
        if len(selected)!=1:raise RuntimeError('Expected exactly one proxy holding the probe session')
        proxies=selected
        injected=utc();start=time.monotonic()
        # Match the Phase 4 abrupt proxy-pod experiment. This is never used for drain.
        lab.command('delete','pod',proxies[0]['metadata']['name'],'--grace-period=0','--force','--wait=false')
        lab.runtime.wait(lambda:lab.runtime.query('SELECT 1;')=='1')
        sql=time.monotonic()-start
        lab.command('rollout','status','deployment/lab-pgcat-proxy-deployment','--timeout=180s')
        time.sleep(5)
    lab.evidence.save('pgcat-abrupt.json',dict(affected_client_session_selected=True,injected=injected,deleted_pod=proxies[0]['metadata']['name'],before_endpoints=before,after_endpoints=lab.get('endpoints','lab-pgcat-proxy-service'),sql_available_seconds=sql,duration_seconds=time.monotonic()-start,comparison='Phase 4 also used force deletion; different topology/CNI and one sample each'))
    lab.evidence.record('pgcat_abrupt','PASS',detail='Two replicas during abrupt deletion; persistent client outcomes retained')


def restore(lab):
    before=lab.get('statefulset','lab-patroni-patronimvp');pvcs=lab.get('pvc')
    target='isolated-'+uuid.uuid4().hex[:6];start=time.monotonic()
    policy=json.loads(run(['helm','get','values','lab-patroni','-n',lab.ns,'--all','-o','json']))['networkPolicy']
    policy=json.loads(json.dumps(policy).replace('lab-patroni',target))
    policy_path=lab.directory/'restore-network.json';policy_path.write_text(json.dumps({'networkPolicy':policy}))
    result=run(['python3',str(ROOT/'scripts/isolated-restore.py'),'--namespace',lab.ns,'--source-release','lab-patroni','--target-release',target,'--recovery-time',lab.state['target'],'--network-values',str(policy_path),'--execute'],timeout=900)
    pod=target+'-patronimvp-0'
    rows=lab.runtime.dataset(lambda sql:lab.runtime.direct(sql,pod))
    if rows!=[dict(id=1,phase='baseline',value=100)]:raise RuntimeError('Isolated restore target data mismatch')
    lab.runtime.direct("INSERT INTO validation_test(id,phase,value) VALUES (3,'isolated-write',300);",pod)
    lab.runtime.assert_data()
    after=lab.get('statefulset','lab-patroni-patronimvp')
    if before['metadata']['uid']!=after['metadata']['uid'] or before['spec']!=after['spec']:raise RuntimeError('Source changed during isolated restore')
    source_claims={x['metadata']['uid'] for x in pvcs['items']}
    restored_claims=[x for x in lab.get('pvc')['items'] if x['metadata']['name'].startswith('pgdata-'+target+'-')]
    if not restored_claims or any(x['metadata']['uid'] in source_claims for x in restored_claims):raise RuntimeError('PVC isolation failed')
    lab.evidence.save('isolated-restore.json',dict(target=target,target_utc=lab.state['target'],duration_seconds=round(time.monotonic()-start,3),restored_rows=rows,writable=True,source_unchanged=True,target_pvcs=restored_claims,output=result,archive_mode=lab.runtime.direct('SHOW archive_mode;',pod)))
    lab.state['restore_release']=target;lab.save_state()
    lab.evidence.record('isolated_restore','PASS',detail='A present/B absent, target writable; source StatefulSet/PVC identities preserved')


def execute(lab,stage):
    if 'expected' in lab.state:lab.runtime.expected=lab.state['expected']
    function=globals().get(stage)
    if function is None:
        from extended import execute as extended
        return extended(lab,stage)
    function(lab)
