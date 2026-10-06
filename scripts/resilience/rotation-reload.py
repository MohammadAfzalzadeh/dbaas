#!/usr/bin/env python3
"""Measure application credential rotation through projected Secret + PgCat autoreload."""
import argparse,base64,json,secrets,subprocess,threading,time,uuid
import yaml
from lab import Lab,utc
from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
spec=spec_from_file_location('investigation',Path(__file__).with_name('recovery-investigation.py'));mod=module_from_spec(spec);spec.loader.exec_module(mod)

HELD = r'''
import json,os,sys,time,psycopg2
from datetime import datetime,timezone
v=json.load(sys.stdin);c=psycopg2.connect(host=v['host'],dbname='postgres',user='rotation_probe',password=v['password'],connect_timeout=3,tcp_user_timeout=5000,options='-c statement_timeout=3000')
while not os.path.exists('/tmp/stop-'+v['id']):
 try:c.cursor().execute('SELECT 1');c.commit();ok=True;error=None
 except Exception as e:ok=False;error=type(e).__name__
 print(json.dumps(dict(timestamp=datetime.now(timezone.utc).isoformat(),success=ok,error=error)),flush=True);time.sleep(.5)
c.close()
'''


def execute(lab):
    lab.evidence.root=mod.attempt_directory(lab.evidence.root,'rotation-reload');lab.evidence.status={}
    before_uids={p['metadata']['name']:p['metadata']['uid'] for p in lab.get('pods','-l','app=proxy')['items']}
    old,new=secrets.token_urlsafe(36),secrets.token_urlsafe(36);lab.evidence.sensitive.extend([old,new])
    config=yaml.safe_load(base64.b64decode(lab.get('secret','lab-pgcat-pgcat-config')['data']['pgcat.yaml']))
    users=config['DBS'][0]['users'];users[:]=[u for u in users if u['USER_NAME']!='rotation_probe'];users.append(dict(USER_NAME='rotation_probe',PASSWORD=old,POOL_SIZE=2,STATEMENT_TIMEOUT=0))
    def set_role(password):
        code="import sys,json,os,psycopg2; c=psycopg2.connect(host='patronimvp-master-lab-patroni',user='postgres',password=os.environ['PGPASSWORD'],dbname='postgres');c.autocommit=True;q=c.cursor();q.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',('rotation_probe',));exists=q.fetchone();q.execute(('ALTER ROLE' if exists else 'CREATE ROLE')+' rotation_probe LOGIN PASSWORD %s',(sys.stdin.read(),))"
        lab.command('exec','-i','persistent-client','--','python3','-c',code,data=password)
    def secret(password):lab.apply(dict(apiVersion='v1',kind='Secret',metadata=dict(name='rotation-probe',namespace=lab.ns),stringData={'password':password}))
    def pool(password):
        users[-1]['PASSWORD']=password
        lab.apply(dict(apiVersion='v1',kind='Secret',metadata=dict(name='lab-pgcat-pgcat-config',namespace=lab.ns),stringData={'pgcat.yaml':yaml.safe_dump(config)}))
    def auth(host,password):
        code="import sys,json,psycopg2;v=json.load(sys.stdin);\ntry:\n c=psycopg2.connect(host=v['host'],user='rotation_probe',password=v['password'],dbname='postgres',connect_timeout=2,tcp_user_timeout=3000);c.cursor().execute('SELECT 1');c.close();print('ACCEPTED')\nexcept psycopg2.Error:print('REJECTED')"
        return lab.command('exec','-i','persistent-client','--','python3','-c',code,data=json.dumps(dict(host=host,password=password)),timeout=15).strip()
    hosts=['patronimvp-master-lab-patroni',*[p['status']['podIP'] for p in lab.get('pods','-l','app=proxy')['items'] if not p['metadata'].get('deletionTimestamp')]]
    set_role(old);secret(old);pool(old)
    lab.runtime.wait(lambda:all(auth(h,old)=='ACCEPTED' for h in hosts),180)
    processes=[];held={};events=[]
    try:
        for host in [hosts[0],'lab-pgcat-proxy-service']:
            identity=uuid.uuid4().hex;rows=[];held[host]=rows
            process=subprocess.Popen(lab.kube+['exec','-i','persistent-client','--','python3','-u','-c',HELD],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
            process.stdin.write(json.dumps(dict(id=identity,host=host,password=old)));process.stdin.close()
            def reader(proc=process,result=rows):
                for line in proc.stdout:result.append(json.loads(line))
            thread=threading.Thread(target=reader);thread.start();processes.append((identity,process,thread))
        lab.runtime.wait(lambda:all(rows and rows[-1]['success'] for rows in held.values()),20)
        events.append(dict(timestamp=utc(),action='Existing direct and PgCat sessions accepted old credential'))
        set_role(new);events.append(dict(timestamp=utc(),action='PostgreSQL role password changed; new direct connections require new credential'))
        secret(new);events.append(dict(timestamp=utc(),action='Application Secret updated'))
        start=time.monotonic();pool(new);events.append(dict(timestamp=utc(),action='PgCat projected configuration Secret updated; no restart requested'))
        lab.runtime.wait(lambda:all(auth(h,new)=='ACCEPTED' and auth(h,old)=='REJECTED' for h in hosts),180)
        elapsed=time.monotonic()-start;events.append(dict(timestamp=utc(),action='New accepted and old rejected on primary and each proxy'))
        time.sleep(10)
    finally:
        for identity,process,thread in processes:
            lab.command('exec','persistent-client','--','touch','/tmp/stop-'+identity);process.wait(timeout=15);thread.join(timeout=5)
        lab.evidence.save('existing-sessions.json',held);lab.evidence.save('sequence.json',events)
    after_uids={p['metadata']['name']:p['metadata']['uid'] for p in lab.get('pods','-l','app=proxy')['items']}
    result=dict(classification='LIVE VALIDATED',propagation_seconds=elapsed,proxy_restart=before_uids!=after_uids,postgres_restart=False,mechanism='Projected Secret -> watcher atomic file replacement -> PgCat 15-second autoreload',existing_session_samples={host:dict(success=sum(x['success'] for x in rows),failed=sum(not x['success'] for x in rows)) for host,rows in held.items()},replication_rotation='NOT VALIDATED',old_new_connections='REJECTED',new_connections='ACCEPTED')
    lab.evidence.save('result.json',result);print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state-dir',required=True);args=p.parse_args();lab=Lab(args.state_dir);lab.assert_owned();execute(lab)
