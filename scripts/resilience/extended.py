"""Additional staged checks; kept separate from cluster creation and disruption."""
import json
import time
from lab import ROOT, run, utc
from experiments import Probe


def rotation(lab):
    # Rotate a disposable application role, separate from operator/replication roles.
    # Secret files are passed on stdin; no credential appears in argv or artifacts.
    import secrets,yaml
    old,new=secrets.token_urlsafe(36),secrets.token_urlsafe(36)
    lab.evidence.sensitive.extend([old,new])
    code="import os,sys,psycopg2; c=psycopg2.connect(host='patronimvp-master-lab-patroni',user='postgres',password=os.environ['PGPASSWORD'],dbname='postgres');c.autocommit=True;cur=c.cursor();cur.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',('rotation_app',));exists=cur.fetchone();cur.execute(('ALTER ROLE' if exists else 'CREATE ROLE')+' rotation_app LOGIN PASSWORD %s',(sys.stdin.read(),));cur.execute('GRANT CONNECT ON DATABASE postgres TO rotation_app')"
    lab.command('exec','-i','persistent-client','--','python3','-c',code,data=old)
    lab.apply(dict(apiVersion='v1',kind='Secret',metadata=dict(name='rotation-app',namespace=lab.ns),stringData={'password':old}))
    def auth(password):
        script="import sys,psycopg2; p=sys.stdin.read();\ntry:\n c=psycopg2.connect(host='patronimvp-master-lab-patroni',user='rotation_app',password=p,dbname='postgres',connect_timeout=3);c.close();print('PASS')\nexcept psycopg2.OperationalError:print('REJECTED')"
        return lab.command('exec','-i','persistent-client','--','python3','-c',script,data=password).strip()
    import base64
    secret=lab.get('secret','lab-pgcat-pgcat-config')
    config=yaml.safe_load(base64.b64decode(secret['data']['pgcat.yaml']))
    config['DBS'][0]['users']=[u for u in config['DBS'][0]['users'] if u['USER_NAME']!='rotation_app']
    config['DBS'][0]['users'].append(dict(USER_NAME='rotation_app',PASSWORD=old,POOL_SIZE=2,STATEMENT_TIMEOUT=0))
    def update_pool(password):
        config['DBS'][0]['users'][-1]['PASSWORD']=password
        lab.apply(dict(apiVersion='v1',kind='Secret',metadata=dict(name='lab-pgcat-pgcat-config',namespace=lab.ns),stringData={'pgcat.yaml':yaml.safe_dump(config)}))
        lab.command('rollout','restart','deployment/lab-pgcat-proxy-deployment')
        lab.command('rollout','status','deployment/lab-pgcat-proxy-deployment','--timeout=360s')
    def pool_auth(password):
        script="import sys,psycopg2; p=sys.stdin.read();\ntry:\n c=psycopg2.connect(host='lab-pgcat-proxy-service',user='rotation_app',password=p,dbname='postgres',connect_timeout=3);c.cursor().execute('SELECT 1');c.close();print('PASS')\nexcept psycopg2.OperationalError:print('REJECTED')"
        return lab.command('exec','-i','persistent-client','--','python3','-c',script,data=password).strip()
    update_pool(old)
    before=auth(old);pool_before=pool_auth(old)
    alter=code
    lab.command('exec','-i','persistent-client','--','python3','-c',alter,data=new)
    lab.apply(dict(apiVersion='v1',kind='Secret',metadata=dict(name='rotation-app',namespace=lab.ns),stringData={'password':new}))
    update_pool(new)
    after,invalid=auth(new),auth(old)
    pool_after,pool_invalid=pool_auth(new),pool_auth(old)
    if (pool_before,pool_after,pool_invalid)!=('PASS','PASS','REJECTED'):raise RuntimeError('PgCat coordinated credential rotation failed')
    if (before,after,invalid)!=('PASS','PASS','REJECTED'):raise RuntimeError('Application credential rotation failed')
    # Configuration revision rehearsal: OnDelete does not roll existing database pods.
    # A non-major configuration revision, sized so idle pool backends and the
    # 50-client direct benchmark can coexist without exhausting 100 connections.
    patch_config="import json,urllib.request; data=json.dumps({'postgresql':{'parameters':{'max_connections':200}}}).encode();r=urllib.request.Request('http://127.0.0.1:8008/config',data=data,method='PATCH',headers={'Content-Type':'application/json'});response=urllib.request.urlopen(r,timeout=10);print(response.status)"
    lab.command('exec',lab.runtime.primary(),'-c','patronimvp','--','python3','-c',patch_config)
    sts=lab.get('statefulset','lab-patroni-patronimvp');uids={p['metadata']['name']:p['metadata']['uid'] for p in lab.runtime.pods()}
    lab.command('patch','statefulset','lab-patroni-patronimvp','--type=merge','-p',json.dumps({'spec':{'template':{'metadata':{'annotations':{'dbaas.example/revision':'phase5'}}}}}))
    time.sleep(2)
    unchanged=uids=={p['metadata']['name']:p['metadata']['uid'] for p in lab.runtime.pods()}
    with Probe(lab,'revision-rollout'):
        for pod in sorted(lab.runtime.pods(),key=lambda p:p['metadata']['labels'].get('role')=='primary'):
            lab.command('delete','pod',pod['metadata']['name'],'--wait=true');lab.runtime.wait(lab.stable,240)
        lab.command('rollout','restart','deployment/lab-pgcat-proxy-deployment');lab.command('rollout','status','deployment/lab-pgcat-proxy-deployment','--timeout=360s')
        lab.command('rollout','restart','deployment/dbaas-backend');lab.command('rollout','status','deployment/dbaas-backend','--timeout=360s')
        lab.runtime.assert_data()
    lab.evidence.save('rotation.json',dict(timestamp=utc(),application_role=dict(old_before=before,new_after=after,old_after=invalid,secret_updated=True),replication='NOT VALIDATED',pgcat_credential=dict(before=pool_before,after=pool_after,old_after=pool_invalid,method='Secret update and coordinated rolling restart'),object_store='NOT VALIDATED'))
    connections=int(lab.runtime.direct('SHOW max_connections;'))
    if connections!=200:raise RuntimeError('Configuration revision not active after member restarts')
    lab.evidence.save('upgrades.json',dict(max_connections=connections,ondelete_kept_existing_uids=unchanged,replica_first_replacements=True,pgcat_rolling='PASS',api_single_replica_rolling='PASS',major_upgrade='NOT APPLICABLE'))
    lab.evidence.record('rotation','PASS',detail='Application SQL role and Secret changed; old login rejected; other credential classes not claimed')
    lab.evidence.record('upgrades','PASS',detail='OnDelete revision/manual replica-first restart; rolling PgCat and API')


def execute(lab,stage):
    if stage=='benchmarks':
        from benchmark import execute
        return execute(lab)
    if stage=='rotation':return rotation(lab)
    if stage=='observability':
        from observability import execute
        return execute(lab)
    raise ValueError('Unknown stage')
