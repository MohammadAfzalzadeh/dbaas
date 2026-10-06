#!/usr/bin/env python3
"""Staged experiments in a newly owned kind cluster; never uses a default context."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.request
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/smoke-test'))
from run import run, IMAGES, walg_environment
from evidence import Evidence
from lifecycle import Runtime, utc

class Lab:
    def __init__(self, directory):
        self.directory=Path(directory).resolve()
        self.state=json.loads((self.directory/'state.json').read_text())
        self.name=self.state['name']; self.ns='resilience'; self.release='lab'
        if not self.name.startswith('dbaas-phase5-'):raise ValueError('Not a Phase 5 owned cluster')
        os.environ['KUBECONFIG']=str(self.directory/'kubeconfig')
        self.kube=['kubectl','--kubeconfig',os.environ['KUBECONFIG'],'-n',self.ns]
        self.evidence=Evidence.__new__(Evidence)
        self.evidence.root=ROOT/'results/runtime/multinode'/self.name
        self.evidence.root.mkdir(parents=True,exist_ok=True)
        self.evidence.sensitive=[]
        if (self.directory/'credentials.json').exists():
            self.credentials=json.loads((self.directory/'credentials.json').read_text())
            self.evidence.sensitive=list(self.credentials.values())
        status=self.evidence.root/'status.json'
        self.evidence.status=json.loads(status.read_text()) if status.exists() else {}
        self.runtime=Runtime(self.kube,run,self.evidence,self.ns,self.release,self.directory)
        self.runtime.stable=self.stable
    def command(self,*args,**kwargs):return run(self.kube+list(args),**kwargs)
    def get(self,kind,*args):return json.loads(self.command('get',kind,*args,'-o','json'))
    def apply(self,obj):return self.command('apply','-f','-',data=yaml.safe_dump(obj))
    def save_state(self):
        p=self.directory/'state.json';p.write_text(json.dumps(self.state));p.chmod(0o600)
    def assert_owned(self):
        nodes=run(['kind','get','nodes','--name',self.name]).splitlines()
        if not nodes or any(not x.startswith(self.name+'-') for x in nodes):raise RuntimeError('Ownership check failed')
        actual=self.get('namespace','kube-system')['metadata']['uid']
        if actual!=self.state['kube_system_uid']:raise RuntimeError('Cluster identity changed')
    def stable(self):
        pods=self.runtime.pods()
        if len(pods)!=3:return False
        if not all(any(c['type']=='Ready' and c['status']=='True' for c in p.get('status',{}).get('conditions',[])) for p in pods):return False
        members=self.runtime.membership()['members']
        return len(members)==3 and sum(m['role'] in ('leader','primary') for m in members)==1 and all(m['state'] in ('running','streaming') for m in members)
    def topology(self,name):
        self.evidence.save(name+'.json',dict(timestamp=utc(),nodes=self.get('nodes'),pods=self.get('pods'),pdb=self.get('pdb'),pvcs=self.get('pvc'),members=self.runtime.membership()))
        (self.evidence.root/(name+'.txt')).write_text(self.command('get','pods','-o','wide')+self.command('get','nodes')+self.command('get','pdb'))
    def helm(self,release,component,values):
        p=self.directory/(release+'-values.json');p.write_text(json.dumps(values));p.chmod(0o600)
        run(['helm','upgrade','--install',release,str(ROOT/'helmCharts'/component),'-n',self.ns,'-f',str(p),'--wait','--wait-for-jobs','--timeout','10m'],timeout=660)
    def setup(self,calico,temporary_inotify):
        manifest=Path(calico).read_bytes()
        expected=json.loads((ROOT/'scripts/resilience/dependencies.json').read_text())['calico.yaml']['sha256']
        if hashlib.sha256(manifest).hexdigest()!=expected:raise ValueError('Calico manifest checksum mismatch')
        self.evidence.save('cni-source.json',dict(url='https://raw.githubusercontent.com/projectcalico/calico/v3.28.2/manifests/calico.yaml',sha256=hashlib.sha256(manifest).hexdigest()))
        if self.name in run(['kind','get','clusters']).splitlines():raise RuntimeError('Refusing to reuse cluster')
        self.state['creation_started']=True;self.save_state()
        if temporary_inotify:
            original=int(Path('/proc/sys/fs/inotify/max_user_instances').read_text())
            self.state['original_inotify']=original;self.save_state()
            run(['docker','run','--rm','--privileged','--entrypoint','sysctl','kindest/node:v1.30.0',
                 '-w','fs.inotify.max_user_instances='+str(temporary_inotify)])
        run(['kind','create','cluster','--name',self.name,'--kubeconfig',os.environ['KUBECONFIG'],'--image','kindest/node:v1.30.0','--config',str(ROOT/'kind/resilience.yaml')],timeout=480)
        Path(os.environ['KUBECONFIG']).chmod(0o600)
        self.state['kube_system_uid']=self.get('namespace','kube-system')['metadata']['uid'];self.save_state()
        run(['kubectl','--kubeconfig',os.environ['KUBECONFIG'],'apply','-f',str(Path(calico).resolve())],timeout=180)
        self.command('rollout','restart','daemonset/kube-proxy','-n','kube-system')
        self.command('rollout','status','daemonset/calico-node','-n','kube-system','--timeout=300s',timeout=320)
        self.command('wait','--for=condition=Ready','nodes','--all','--timeout=300s',timeout=320)
        self.command('rollout','status','deployment/coredns','-n','kube-system','--timeout=180s')
        self.provision()

    def provision(self):
        self.command('rollout','status','daemonset/calico-node','-n','kube-system','--timeout=300s',timeout=320)
        self.command('wait','--for=condition=Ready','nodes','--all','--timeout=300s',timeout=320)
        self.command('rollout','status','deployment/coredns','-n','kube-system','--timeout=180s')
        run(['kind','load','docker-image','--name',self.name,*IMAGES],timeout=1800)
        self.command('create','namespace',self.ns)
        creds={k:secrets.token_urlsafe(36) for k in ('postgres','replication','minio','backup','api','pgadmin')}
        self.credentials=creds;self.evidence.sensitive=list(creds.values())
        p=self.directory/'credentials.json';p.write_text(json.dumps(creds));p.chmod(0o600)
        def secret(name,values):self.apply(dict(apiVersion='v1',kind='Secret',metadata=dict(name=name,namespace=self.ns),stringData=values))
        secret('dbaas-api-auth',{'token':creds['api']})
        secret('lab-patroni-postgres-credentials',{'superuser-username':'postgres','superuser-password':creds['postgres'],'replication-username':'standby','replication-password':creds['replication']})
        secret('lab-minio-minio-credentials',{'root-user':'root','root-password':creds['minio'],'backup-user':'backup','backup-password':creds['backup'],'backup-bucket':'backup'})
        walg=dict(PGHOST='localhost',PGPORT='5432',PGUSER='postgres',PGPASSWORD=creds['postgres'],PGDATABASE='postgres',AWS_ACCESS_KEY_ID='backup',AWS_SECRET_ACCESS_KEY=creds['backup'],WALG_S3_PREFIX='s3://backup',AWS_ENDPOINT='http://lab-minio-minio:9000',AWS_REGION='us-east-1',AWS_S3_FORCE_PATH_STYLE='true',WALG_COMPRESSION_METHOD='brotli')
        secret('lab-patroni-wal-g-credentials',{'.walg.env':walg_environment(walg)})
        config=yaml.safe_load((ROOT/'helmCharts/pgcat/values.yaml').read_text())['pgcatconfig']
        config['general']['PGCAT_SUPERUSER_PASSWORD']=creds['postgres']
        db=config['DBS'][0];db['PRIMARY_READ']=True;db['POOL_MODE']='transaction';db['users'][0].update(PASSWORD=creds['postgres'],POOL_SIZE=60)
        db['shards'][0].update(MASTER_HOST='patronimvp-master-lab-patroni',REPLICA_HOST='patronimvp-replica-lab-patroni')
        secret('lab-pgcat-pgcat-config',{'pgcat.yaml':yaml.safe_dump(config)})
        secret('lab-pgcat-pgadmin',{'pgadmin-password':creds['pgadmin']})
        for filename in ('rbac.yaml','deploy.yaml'):
            for obj in yaml.safe_load_all((ROOT/'application/k8s'/filename).read_text()):
                obj['metadata']['namespace']=self.ns
                for subject in obj.get('subjects',[]):subject['namespace']=self.ns
                if obj['kind']=='Deployment':
                    spec=obj['spec']['template']['spec'];spec['nodeSelector']={'kubernetes.io/hostname':self.name+'-control-plane'}
                    spec['tolerations']=[dict(key='node-role.kubernetes.io/control-plane',operator='Exists',effect='NoSchedule')]
                    c=spec['containers'][0];c['image']='dbaas/backend:0.2.0'
                    for env in c['env']:
                        if env['name']=='DBAAS_ALLOWED_NAMESPACES':env['value']=self.ns
                self.apply(obj)
        self.command('rollout','status','deployment/dbaas-backend','--timeout=180s')
        # API-pod localhost request keeps the token out of argv, files and output.
        payload=dict(namespace=self.ns,project=dict(releaseName='lab',enableMinio=True,enablePgCat=True),postgresql=dict(pgReplicas=3,pgStorageCapacity=2),minio=dict(storageCapacity=2))
        code="import os,json,urllib.request; p="+repr(payload)+"; r=urllib.request.Request('http://127.0.0.1:8000/api/deploy',data=json.dumps(p).encode(),headers={'Authorization':'Bearer '+os.environ['DBAAS_API_TOKEN'],'Content-Type':'application/json'}); print(urllib.request.urlopen(r,timeout=1500).read().decode())"
        start=time.monotonic();result=self.command('exec','deployment/dbaas-backend','--','python','-c',code,timeout=1550)
        response=json.loads(result)
        if not response.get('ok'):raise RuntimeError('API provisioning failed')
        self.evidence.save('provisioning.json',dict(duration_seconds=round(time.monotonic()-start,3),response=response))
        spread=[dict(maxSkew=1,topologyKey='kubernetes.io/hostname',whenUnsatisfiable='DoNotSchedule')]
        self.helm('lab-patroni','patroni',dict(postgres=dict(replicaCount=3,storageCapacity='2Gi',explicitRetainPolicy=True,scheduling=dict(antiAffinity='required',nodeSelector={'dbaas-worker':'true'},topologySpreadConstraints=spread))))
        # OnDelete needs deliberate replacement for changed scheduling; all existing
        # pods are replaced one at a time, replicas before the current primary.
        for pod in sorted(self.runtime.pods(),key=lambda p:p['metadata']['labels'].get('role')=='primary'):
            name=pod['metadata']['name'];self.command('delete','pod',name,'--wait=true');self.runtime.wait(self.stable,240)
        self.helm('lab-pgcat','pgcat',dict(replicaCount=2,patroniReleaseName='lab-patroni',scheduling=dict(antiAffinity='required',nodeSelector={'dbaas-worker':'true'})))
        # Independent clients stay on the control plane during worker disruption.
        placement={'nodeSelector':{'kubernetes.io/hostname':self.name+'-control-plane'},
                   'tolerations':[dict(key='node-role.kubernetes.io/control-plane',operator='Exists',effect='NoSchedule')]}
        def client_run(cmd,data=None,timeout=900):
            if data and 'apply' in cmd:
                obj=json.loads(data)
                if obj.get('kind')=='Pod':
                    obj['spec'].update(placement)
                    obj['metadata']['labels']={'dbaas-client':'allowed'}
                    data=json.dumps(obj)
            return run(cmd,data,timeout)
        self.runtime.run=client_run
        self.runtime.clients()
        self.runtime.run=run
        password_env=dict(name='PGPASSWORD',valueFrom=dict(secretKeyRef=dict(name='lab-patroni-postgres-credentials',key='superuser-password')))
        client=dict(apiVersion='v1',kind='Pod',metadata=dict(name='persistent-client',namespace=self.ns,labels={'dbaas-client':'allowed','dbaas-monitor':'true'}),
                    spec={**placement,'containers':[dict(name='client',image='dbaas/patroni:2.1.0',command=['sleep','infinity'],env=[password_env])]})
        self.apply(client)
        self.command('wait','--for=condition=Ready','pod/persistent-client','--timeout=180s')
        self.runtime.wait(self.stable,240)
        pods=self.runtime.pods()
        if len({p['spec']['nodeName'] for p in pods})!=3:raise RuntimeError('Database members not spread across workers')
        self.topology('initial-topology')
        self.evidence.save('environment.json',dict(timestamp=utc(),git_revision=run(['git','rev-parse','HEAD']).strip(),dirty=bool(run(['git','status','--porcelain'])),kubernetes='v1.30.0',node_topology='1 control-plane + 3 workers',postgresql='16.6',patroni='4.0.4',pgcat='1.2.0',storage='kind local-path RWO; node-affine',docker=json.loads(run(['docker','info','--format','{"cpus":{{.NCPU}},"memory_bytes":{{.MemTotal}}}']))))
        self.evidence.record('multinode','PASS',detail='3 PostgreSQL workers; 2 PgCat replicas; real API provisioning')
    def cleanup(self):
        if self.state.get('creation_started'):
            nodes=run(['kind','get','nodes','--name',self.name]).splitlines()
            if nodes and 'kube_system_uid' in self.state:self.assert_owned()
            if 'original_inotify' in self.state:
                run(['docker','run','--rm','--privileged','--entrypoint','sysctl','kindest/node:v1.30.0','-w','fs.inotify.max_user_instances='+str(self.state['original_inotify'])])
            run(['kind','delete','cluster','--name',self.name])
        self.evidence.save('cleanup.json',dict(timestamp=utc(),deleted_cluster=self.name,restored_inotify=self.state.get('original_inotify')))
        for p in self.directory.iterdir():
            if p.is_file():p.unlink()
        self.directory.rmdir()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['setup','provision','baseline','network','disruptions','proxy_failure','restore','rotation','observability','benchmarks','cleanup'])
    parser.add_argument('--state-dir',required=True)
    parser.add_argument('--calico-manifest')
    parser.add_argument('--temporary-inotify-limit',type=int)
    args=parser.parse_args();directory=Path(args.state_dir)
    if args.stage=='setup':
        directory.mkdir(mode=0o700,parents=False,exist_ok=False)
        (directory/'state.json').write_text(json.dumps({'name':'dbaas-phase5-'+secrets.token_hex(5)}));(directory/'state.json').chmod(0o600)
    lab=Lab(directory)
    try:
        if args.stage=='setup':lab.setup(args.calico_manifest,args.temporary_inotify_limit)
        elif args.stage=='cleanup':lab.cleanup()
        else:
            lab.assert_owned()
            if args.stage=='provision':lab.provision()
            else:
                from experiments import execute
                execute(lab,args.stage)
        lab.evidence.record(args.stage,'PASS',detail='Stage completed; individual artifacts define the validation scope')
    except Exception as error:
        lab.evidence.record(args.stage,'FAIL',detail=lab.evidence.clean(type(error).__name__+': '+str(error)[:500]))
        print('Stage failed; private state retained. Exception type: '+type(error).__name__,file=sys.stderr)
        raise SystemExit(1)

if __name__=='__main__':main()
