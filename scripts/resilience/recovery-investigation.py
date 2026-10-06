#!/usr/bin/env python3
"""Append-only, instrumented abrupt-loss investigation in an owned disposable lab."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import time
from datetime import datetime, timezone
from lab import Lab, run, utc
from experiments import Probe

# Executed inside a database container. Passwords never leave its environment.
DIAGNOSTIC = r'''
import os,json,urllib.request,yaml
from pathlib import Path
import psycopg2
from psycopg2.extensions import parse_dsn

def scrub(v):
 if isinstance(v,dict):return {k:('[REDACTED]' if any(s in k.lower() for s in ('password','secret','token')) else scrub(x)) for k,x in v.items()}
 if isinstance(v,list):return [scrub(x) for x in v]
 return v
p=Path(os.environ['PATRONI_POSTGRESQL_DATA_DIR']);out={}
for endpoint in ('patroni','config','cluster'):
 try:out[endpoint]=scrub(json.load(urllib.request.urlopen('http://127.0.0.1:8008/'+endpoint,timeout=3)))
 except Exception as e:out[endpoint]={'error':type(e).__name__}
out['local_patroni_configuration']=scrub(yaml.safe_load(Path('/home/postgres/patroni.yml').read_text()))
out['signals']={f:(p/f).exists() for f in ('recovery.signal','standby.signal')}
out['timeline_history']={f.name:f.read_text() for f in (p/'pg_wal').glob('*.history')}
out['wal_files']=sorted(f.name for f in (p/'pg_wal').iterdir() if f.is_file())
try:
 c=psycopg2.connect(host='127.0.0.1',dbname='postgres',user=os.environ['PATRONI_SUPERUSER_USERNAME'],password=os.environ['PATRONI_SUPERUSER_PASSWORD'],connect_timeout=3,options='-c statement_timeout=3000')
 q=c.cursor()
 queries={
 'replication':'SELECT application_name,client_addr,state,sync_state,sent_lsn,write_lsn,flush_lsn,replay_lsn FROM pg_stat_replication',
 'slots':'SELECT slot_name,slot_type,active,restart_lsn,wal_status FROM pg_replication_slots',
 'wal_receiver':'SELECT status,receive_start_lsn,receive_start_tli,received_tli,written_lsn,flushed_lsn,latest_end_lsn,slot_name,sender_host FROM pg_stat_wal_receiver',
 'checkpoint':'SELECT * FROM pg_control_checkpoint()',
 'system':'SELECT * FROM pg_control_system()',
 'replay':"SELECT pg_is_in_recovery(),pg_last_wal_receive_lsn(),pg_last_wal_replay_lsn(),pg_last_xact_replay_timestamp()",
 'archiver':'SELECT * FROM pg_stat_archiver',
 'settings':"SELECT name,setting,source,sourcefile,sourceline FROM pg_settings WHERE name IN ('archive_mode','archive_command','restore_command','wal_log_hints','data_checksums','wal_level','wal_keep_size','max_slot_wal_keep_size','recovery_target_time','recovery_target_timeline','recovery_target_action')"
 }
 for name,sql in queries.items():
  q.execute(sql);out[name]=[dict(zip([x[0] for x in q.description],row)) for row in q.fetchall()]
 q.execute("SHOW primary_conninfo");conn=q.fetchone()[0];out['primary_conninfo']={k:v for k,v in parse_dsn(conn).items() if k in ('host','port','user','dbname','application_name','sslmode','passfile')}
 c.close()
except Exception as e:out['sql_error']=type(e).__name__
print(json.dumps(out,default=str))
'''


def attempt_directory(root, scenario):
    parent=Path(root)/scenario;parent.mkdir(parents=True,exist_ok=True)
    for n in range(1,10000):
        target=parent/f'attempt-{n}'
        try:target.mkdir();return target
        except FileExistsError:continue
    raise RuntimeError('Attempt limit reached')


def snapshot(lab, name):
    root=lab.evidence.root/name;root.mkdir()
    lab.evidence.save(name+'/placement.json',dict(timestamp=utc(),pods=lab.get('pods'),pvcs=lab.get('pvc'),statefulsets=lab.get('statefulsets')))
    for pod in lab.runtime.pods():
        namepod=pod['metadata']['name']
        try:result=subprocess.run(lab.kube+['exec',namepod,'-c','patronimvp','--','python3','-c',DIAGNOSTIC],capture_output=True,text=True,timeout=25)
        except subprocess.TimeoutExpired:
            lab.evidence.save(name+'/'+namepod+'.json',dict(error='Pod diagnostic timed out'));continue
        if result.returncode==0:
            lab.evidence.save(name+'/'+namepod+'.json',json.loads(result.stdout))
        else:lab.evidence.save(name+'/'+namepod+'.json',dict(error='Pod diagnostic unavailable',returncode=result.returncode))
        logs=subprocess.run(lab.kube+['logs',namepod,'-c','patronimvp','--tail=1500'],capture_output=True,text=True,timeout=20)
        (root/(namepod+'.log')).write_text(lab.evidence.clean(logs.stdout))


def execute(lab, clients=1, interval=.1):
    original=lab.evidence.root;lab.evidence.root=attempt_directory(original,'abrupt-recovery');lab.evidence.status={}
    lab.runtime.expected=lab.state['expected'];r=lab.runtime;r.wait(lab.stable,120);r.assert_data();snapshot(lab,'before')
    p=r.pods('primary')[0];node=p['spec']['nodeName'];old=p['metadata']['name'];events=dict(old_primary=old,node=node,initial='LIVE VALIDATED',automatic_reinitialize=False,clients=clients,configured_interval_seconds=interval)
    start=None
    try:
        with ExitStack() as stack:
            probes=[stack.enter_context(Probe(lab,'node-loss' if clients==1 else 'node-loss-'+str(i+1),interval)) for i in range(clients)]
            time.sleep(8);events['acknowledged_before_failure']=sum(x['success'] for probe in probes for x in probe.rows)
            events['injected']=utc();start=time.monotonic();run(['docker','stop','--time','0',node],timeout=30)
            new=r.wait(lambda:next((x['metadata']['name'] for x in r.pods('primary') if x['metadata']['name']!=old),None),180)
            events.update(new_primary=new,promotion_observed_seconds=time.monotonic()-start)
            r.wait(lambda:r.query('SELECT 1;')=='1',120);events['sql_probe_seconds']=time.monotonic()-start
            # The stopped pod cannot answer; collect survivors only without waiting on exec.
            for pod in r.pods():
                if pod['metadata']['name']!=old:
                    name=pod['metadata']['name'];data=lab.command('exec',name,'-c','patronimvp','--','python3','-c',DIAGNOSTIC,timeout=25)
                    lab.evidence.save('during-'+name+'.json',json.loads(data))
            events['node_returned']=utc();run(['docker','start',node]);events['node_return_seconds']=time.monotonic()-start
            try:r.wait(lab.stable,240);events['stable_seconds']=time.monotonic()-start;events['automatic_recovery']='LIVE VALIDATED'
            except RuntimeError:events['automatic_recovery']='FAILED'
            snapshot(lab,'after');time.sleep(15)
            r.assert_data()
        events['acknowledged_write_check']='LIVE VALIDATED'
    except Exception as error:
        events['error']=type(error).__name__;events.setdefault('automatic_recovery','FAILED')
        raise
    finally:
        run(['docker','start',node]);events['completed']=utc();lab.evidence.save('result.json',events)
        print(str(lab.evidence.root));print(json.dumps(events))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state-dir',required=True);p.add_argument('--clients',type=int,choices=[1,4],default=1);p.add_argument('--interval',type=float,choices=[.1,.01],default=.1);args=p.parse_args();lab=Lab(args.state_dir);lab.assert_owned();execute(lab,args.clients,args.interval)
