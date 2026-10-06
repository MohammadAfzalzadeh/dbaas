#!/usr/bin/env python3
"""Phase 6.5 bounded review in a new owned kind cluster; private state stays outside Git."""
import argparse
import concurrent.futures
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
OUT = ROOT / 'results/validation/phase6-5/live'
IMAGES = ['dbaas/wal-g:3.0.7','dbaas/patroni:2.1.0','dbaas/pgcat-config-watcher:1.1.1',
          'dbaas/minio:RELEASE.2025-04-22T22-12-26Z','dbaas/mc:RELEASE.2025-04-16T18-13-26Z',
          'dbaas/kubectl:1.30.0','dbaas/backend:0.2.0']

class Review:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.state = json.loads((self.directory/'state.json').read_text())
        self.name = self.state['name']
        if not self.name.startswith('dbaas-review-'): raise ValueError('Invalid ownership prefix')
        self.ns = 'review'
        self.kube = ['kubectl','--kubeconfig',str(self.directory/'kubeconfig'),'-n',self.ns]
        self.env = dict(os.environ, KUBECONFIG=str(self.directory/'kubeconfig'))
        self.credentials = json.loads((self.directory/'credentials.json').read_text()) if (self.directory/'credentials.json').exists() else {}
        OUT.mkdir(parents=True, exist_ok=True)
    def clean(self, text):
        for value in self.credentials.values():
            if isinstance(value,str): text=text.replace(value,'[REDACTED]')
        return text
    def run(self, cmd, data=None, timeout=900):
        p=subprocess.run(cmd,input=data,capture_output=True,text=True,timeout=timeout,env=self.env)
        if p.returncode: raise RuntimeError(self.clean(' '.join(cmd[:3])+': '+p.stderr[-1500:]))
        return p.stdout
    def k(self,*args,**kw): return self.run(self.kube+list(args),**kw)
    def get(self,kind,*args): return json.loads(self.k('get',kind,*args,'-o','json'))
    def save(self,name,data):
        path=OUT/(name+'.json')
        if path.exists(): raise ValueError('Refusing to overwrite evidence '+name)
        path.write_text(self.clean(json.dumps(data,indent=2))+'\n')
    def save_state(self):
        p=self.directory/'state.json';p.write_text(json.dumps(self.state));p.chmod(0o600)
    def apply(self,obj): return self.k('apply','-f','-',data=yaml.safe_dump(obj))
    def owned(self):
        if self.get('namespace','kube-system')['metadata']['uid']!=self.state['uid']: raise ValueError('Cluster UID mismatch')
    def secret(self,name,values):
        self.apply(dict(apiVersion='v1',kind='Secret',metadata=dict(name=name,namespace=self.ns),stringData=values))
    def prepare(self,release):
        for key in ('postgres','replication','root','backup','pgadmin'):
            self.credentials[release+'-'+key]=secrets.token_urlsafe(36)
        p=self.directory/'credentials.json';p.write_text(json.dumps(self.credentials));p.chmod(0o600)
        c=lambda key:self.credentials[release+'-'+key]
        self.secret(release+'-patroni-postgres-credentials',{'superuser-username':'postgres','superuser-password':c('postgres'),'replication-username':'standby','replication-password':c('replication')})
        self.secret(release+'-minio-minio-credentials',{'root-user':'root','root-password':c('root'),'backup-user':'backup','backup-password':c('backup'),'backup-bucket':'backup'})
        walg=dict(PGHOST='localhost',PGPORT='5432',PGUSER='postgres',PGPASSWORD=c('postgres'),PGDATABASE='postgres',AWS_ACCESS_KEY_ID='backup',AWS_SECRET_ACCESS_KEY=c('backup'),WALG_S3_PREFIX='s3://backup',AWS_ENDPOINT=f'http://{release}-minio-minio:9000',AWS_REGION='us-east-1',AWS_S3_FORCE_PATH_STYLE='true',WALG_COMPRESSION_METHOD='brotli')
        self.secret(release+'-patroni-wal-g-credentials',{'.walg.env':'\n'.join(k+'='+json.dumps(v) for k,v in walg.items())+'\n'})
        config=yaml.safe_load((ROOT/'helmCharts/pgcat/values.yaml').read_text())['pgcatconfig']
        config['general']['PGCAT_SUPERUSER_PASSWORD']=c('postgres')
        db=config['DBS'][0];db.update(PRIMARY_READ=True,POOL_MODE='transaction')
        db['users'][0]['PASSWORD']=c('postgres')
        db['shards'][0].update(MASTER_HOST=f'patronimvp-master-{release}-patroni',REPLICA_HOST='',INCLUDE_REPLICA=False)
        self.secret(release+'-pgcat-pgcat-config',{'pgcat.yaml':yaml.safe_dump(config)})
        self.secret(release+'-pgcat-pgadmin',{'pgadmin-password':c('pgadmin')})
    def spec(self,release):
        return dict(namespace=self.ns,project=dict(releaseName=release,enableMinio=True,enablePgCat=True),postgresql=dict(pgReplicas=1,pgStorageCapacity=1),minio=dict(storageCapacity=1))
    def request(self,spec):
        code="""import os,json,time,urllib.request,urllib.error
spec=SPEC
started=time.monotonic()
r=urllib.request.Request('http://127.0.0.1:8000/api/deploy',data=json.dumps(spec).encode(),headers={'Authorization':'Bearer '+os.environ['DBAAS_API_TOKEN'],'Content-Type':'application/json'})
try:
 response=urllib.request.urlopen(r,timeout=1500);status=response.status;body=json.loads(response.read())
except urllib.error.HTTPError as e:status=e.code;body=json.loads(e.read())
print(json.dumps({'release':spec['project']['releaseName'],'status':status,'body':body,'seconds':time.monotonic()-started}))
""".replace('SPEC',repr(spec))
        return json.loads(self.k('exec','deployment/dbaas-backend','--','python','-c',code,timeout=1550))
    def sql(self,release,sql,proxy=False):
        host=release+'-pgcat-proxy-service' if proxy else 'localhost'
        code="import os,psycopg2,json; c=psycopg2.connect(host="+repr(host)+",user='postgres',dbname='postgres',password=os.environ['PATRONI_SUPERUSER_PASSWORD'],connect_timeout=5); c.autocommit=True; q=c.cursor(); q.execute("+repr(sql)+"); print(json.dumps(q.fetchall() if q.description else []))"
        return json.loads(self.k('exec',release+'-patroni-patronimvp-0','-c','patronimvp','--','python3','-c',code))
    def inventory(self):
        data={}
        for kind in ['statefulsets','deployments','services','persistentvolumeclaims','cronjobs','servicemonitors']:
            try:items=self.get(kind)['items']
            except RuntimeError:
                if kind=='servicemonitors':data[kind]='CRD absent; rendered review only';continue
                raise
            data[kind]=[{'name':i['metadata']['name'],'uid':i['metadata']['uid'],'labels':i['metadata'].get('labels',{}),'selector':i.get('spec',{}).get('selector'),'volume_claims':i.get('spec',{}).get('volumeClaimTemplates'),'replicas':i.get('spec',{}).get('replicas')} for i in items]
        data['secrets']=[{'name':i['metadata']['name'],'uid':i['metadata']['uid'],'keys':sorted(i.get('data',{}))} for i in self.get('secrets')['items']]
        return data
    def setup(self):
        if self.name in self.run(['kind','get','clusters']).splitlines():raise ValueError('Refusing existing cluster')
        self.state['inotify_before']=int(Path('/proc/sys/fs/inotify/max_user_instances').read_text());self.state['creation_started']=True;self.save_state()
        self.run(['docker','run','--rm','--privileged','--entrypoint','sysctl','kindest/node:v1.30.0','-w','fs.inotify.max_user_instances=1024'])
        cfg={'kind':'Cluster','apiVersion':'kind.x-k8s.io/v1alpha4','networking':{'disableDefaultCNI':True,'podSubnet':'192.168.0.0/16'},'nodes':[{'role':'control-plane'},{'role':'worker'},{'role':'worker'}]}
        p=self.directory/'kind.yaml';p.write_text(yaml.safe_dump(cfg))
        self.run(['kind','create','cluster','--name',self.name,'--image','kindest/node:v1.30.0','--kubeconfig',str(self.directory/'kubeconfig'),'--config',str(p)],timeout=480)
        (self.directory/'kubeconfig').chmod(0o600)
        self.state['uid']=self.get('namespace','kube-system')['metadata']['uid'];self.save_state()
        self.configure()
    def configure(self):
        self.owned()
        url='https://raw.githubusercontent.com/projectcalico/calico/v3.28.2/manifests/calico.yaml'
        manifest=urllib.request.urlopen(url,timeout=60).read()
        expected=json.loads((ROOT/'scripts/resilience/dependencies.json').read_text())['calico.yaml']['sha256']
        if hashlib.sha256(manifest).hexdigest()!=expected:raise ValueError('Calico checksum mismatch')
        self.run(self.kube[:3]+['apply','-f','-'],data=manifest.decode(),timeout=180)
        self.k('rollout','restart','daemonset/kube-proxy','-n','kube-system')
        self.k('rollout','status','daemonset/calico-node','-n','kube-system','--timeout=300s',timeout=320)
        self.k('wait','--for=condition=Ready','nodes','--all','--timeout=300s',timeout=320)
        self.k('rollout','status','deployment/coredns','-n','kube-system','--timeout=180s')
        self.run(['kind','load','docker-image','--name',self.name,*IMAGES],timeout=1200)
        self.k('create','namespace',self.ns)
        self.credentials['api']=secrets.token_urlsafe(36)
        self.prepare('cluster-a');self.prepare('cluster-b')
        self.secret('dbaas-api-auth',{'token':self.credentials['api']})
        for name in ['rbac.yaml','deploy.yaml']:
            for obj in yaml.safe_load_all((ROOT/'application/k8s'/name).read_text()):
                obj['metadata']['namespace']=self.ns
                for subject in obj.get('subjects',[]):subject['namespace']=self.ns
                if obj['kind']=='Deployment':
                    c=obj['spec']['template']['spec']['containers'][0];c['image']='dbaas/backend:0.2.0'
                    for var in c['env']:
                        if var['name']=='DBAAS_ALLOWED_NAMESPACES':var['value']=self.ns
                self.apply(obj)
        self.k('rollout','status','deployment/dbaas-backend','--timeout=180s')
        self.save('environment',{'cluster':self.name,'uid':self.state['uid'],'nodes':3,'physical_hosts':1,'cni':'Calico v3.28.2','credential_creation':'fresh generated outside repository','inotify_before':self.state['inotify_before'],'inotify_temporary':1024})
    def concurrent(self):
        self.owned();observations=[]
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            futures=[pool.submit(self.request,self.spec(r)) for r in ['cluster-a','cluster-b']]
            while not all(f.done() for f in futures):
                code="import glob,pathlib,yaml,json; print(json.dumps([{'directory':str(pathlib.Path(p).parent),'file':pathlib.Path(p).name,'mode':oct(pathlib.Path(p).stat().st_mode & 511),'values':yaml.safe_load(pathlib.Path(p).read_text())} for p in glob.glob('/tmp/dbaas-values-*/*.yaml')]))"
                observations.append(json.loads(self.k('exec','deployment/dbaas-backend','--','python','-c',code)))
                time.sleep(3)
            responses=[f.result() for f in futures]
        self.save('concurrent-different',{'responses':responses,'temporary_files':observations,'inventory':self.inventory()})
        if any(r['status']!=200 for r in responses):raise RuntimeError('Provisioning failure retained')
    def isolation(self):
        self.owned();rows={}
        for release,value in [('cluster-a','A'),('cluster-b','B')]:
            self.sql(release,"CREATE TABLE review_marker(value text PRIMARY KEY); INSERT INTO review_marker VALUES ('"+value+"');")
            rows[release]=[self.sql(release,'SELECT * FROM review_marker;',True) for _ in range(10)]
        self.save('isolation',{'proxy_reads':rows,'inventory':self.inventory()})
        assert all(r==[['A']] for r in rows['cluster-a']) and all(r==[['B']] for r in rows['cluster-b'])
    def duplicate(self):
        self.owned();before=self.inventory();serial=[self.request(self.spec('cluster-a')) for _ in range(2)]
        with concurrent.futures.ThreadPoolExecutor(2) as pool:parallel=list(pool.map(self.request,[self.spec('cluster-a')]*2))
        self.save('duplicate',{'serial':serial,'same_release_concurrent':parallel,'before':before,'after':self.inventory(),'data_a':self.sql('cluster-a','SELECT * FROM review_marker;',True),'data_b':self.sql('cluster-b','SELECT * FROM review_marker;',True)})
    def partial(self):
        self.owned();self.prepare('cluster-c');spec=self.spec('cluster-c');spec['existingSecrets']={'pgcat':'deliberately-missing-pgcat'}
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            failed=pool.submit(self.request,spec)
            independent=pool.submit(self.request,self.spec('cluster-b'))
            response=failed.result();other_response=independent.result()
        state=json.loads(self.run(['helm','list','-n',self.ns,'--all','-o','json']))
        self.save('partial-failure',{'response':response,'independent_cluster_b_response':other_response,'helm_releases':state,'inventory':self.inventory(),'postgres_query':self.sql('cluster-c','SELECT 1;')})
        result=self.request(self.spec('cluster-c'))
        self.save('partial-retry',{'response':result,'query':self.sql('cluster-c','SELECT 1;',True)})
    def catalog(self,release):
        return json.loads(self.k('exec',release+'-patroni-patronimvp-0','-c','patronimvp','--','/wal-g/wal-g','backup-list','--detail','--json','--config','/wal-g-credentials/.walg.env',timeout=60))
    def backup_job(self,case):
        cron=self.get('cronjob','cluster-a-patroni-exec-script-cronjob')
        import copy
        job={'apiVersion':'batch/v1','kind':'Job','metadata':{'name':'review-backup-'+case,'namespace':self.ns},'spec':copy.deepcopy(cron['spec']['jobTemplate']['spec'])}
        job['spec'].update(backoffLimit=0,activeDeadlineSeconds=90)
        pod=job['spec']['template']['spec'];pod['restartPolicy']='Never'
        script=self.get('configmap','cluster-a-patroni-my-script')['data']['script.sh']
        import re
        script=re.sub(r'--kill-after=60s \d+s','--kill-after=5s 20s',script)
        if case in ['unreachable','wrong-credential']:
            key='AWS_ENDPOINT' if case=='unreachable' else 'AWS_SECRET_ACCESS_KEY'
            value='http://127.0.0.1:1' if case=='unreachable' else 'synthetic-deliberately-invalid-key'
            edit="import pathlib,json; p=pathlib.Path('/wal-g-credentials/.walg.env'); lines=p.read_text().splitlines(); pathlib.Path('/tmp/review-negative-walg.env').write_text('\\n'.join("+repr(key+'='+json.dumps(value))+" if x.startswith("+repr(key+'=')+") else x for x in lines)+'\\n')"
            script=script.replace('exec timeout',"umask 077\npython3 -c "+__import__('shlex').quote(edit)+"\ntrap 'rm -f /tmp/review-negative-walg.env' EXIT\ntimeout").replace('--config /wal-g-credentials/.walg.env','--config /tmp/review-negative-walg.env')
        cm='review-backup-'+case+'-script'
        self.apply({'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':cm,'namespace':self.ns},'data':{'script.sh':script}})
        for volume in pod['volumes']:
            if volume['name']=='script-volume':volume['configMap']['name']=cm
        if case=='missing-target':
            for env in pod['containers'][0]['env']:
                if env['name']=='LABEL_SELECTOR':env['value']+=',review-missing=yes'
        self.apply(job);start=time.monotonic()
        while time.monotonic()-start<110:
            status=self.get('job',job['metadata']['name'])['status']
            if any(c['type'] in ['Complete','Failed'] and c['status']=='True' for c in status.get('conditions',[])):break
            time.sleep(2)
        else:raise RuntimeError('Backup Job did not terminate within bound')
        logs=self.k('logs','job/'+job['metadata']['name'],timeout=20)
        leaked=any(v in logs for v in self.credentials.values())
        return {'case':case,'status':status,'seconds':time.monotonic()-start,'logs':self.clean(logs),'known_generated_credential_leaked':leaked}
    def backup(self):
        self.owned();b_before=self.inventory();b_catalog=self.catalog('cluster-b');results=[]
        for case in ['baseline','missing-target','unreachable','wrong-credential','store-unavailable','recovered']:
            before=self.catalog('cluster-a')
            try:
                if case=='store-unavailable':
                    self.k('scale','statefulset/cluster-a-minio-minio-statefulset','--replicas=0')
                    self.k('wait','--for=delete','pod/cluster-a-minio-minio-statefulset-0','--timeout=120s')
                result=self.backup_job(case)
            finally:
                if case=='store-unavailable':
                    self.k('scale','statefulset/cluster-a-minio-minio-statefulset','--replicas=1')
                    self.k('wait','--for=condition=Ready','pod/cluster-a-minio-minio-statefulset-0','--timeout=180s')
            after=self.catalog('cluster-a');before_names={x['backup_name'] for x in before};new=[x['backup_name'] for x in after if x['backup_name'] not in before_names]
            result['new_backup_records']=new
            result['expected_success']=case in ['baseline','recovered']
            result['actual_success']=any(c['type']=='Complete' and c['status']=='True' for c in result['status'].get('conditions',[]))
            results.append(result);self.save('backup-'+case,result)
            assert result['actual_success']==result['expected_success']
            assert bool(new)==result['expected_success']
            assert not result['known_generated_credential_leaked']
            time.sleep(2)
        self.save('backup-isolation',{'b_catalog_before':b_catalog,'b_catalog_after':self.catalog('cluster-b'),'b_rows':self.sql('cluster-b','SELECT * FROM review_marker;',True),'before_inventory':b_before,'after_inventory':self.inventory(),'case_count':len(results)})
    def pitr(self):
        self.owned();from datetime import datetime,timezone,timedelta
        outputs=[]
        base=[sys.executable,str(ROOT/'scripts/recovery.py'),'--namespace',self.ns,'--patroni-releasename','cluster-a-patroni','--pgcat-releasename','cluster-a-pgcat']
        for name,target in [('invalid','invalid'),('before-backup','2020-01-01 00:00:00'),('future','2999-01-01 00:00:00')]:
            p=subprocess.run(base+['--recovery-time',target],capture_output=True,text=True,env=self.env)
            outputs.append({'case':name,'exit_code':p.returncode,'output':self.clean(p.stdout+p.stderr),'mode':'dry-run; no destructive invocation'})
        self.save('pitr-negative-live',{'cases':outputs,'source_query':self.sql('cluster-a','SELECT * FROM review_marker;',True),'inventory':self.inventory()})
        # A valid isolated clone gives a real source/clone policy test, without deleting source data.
        target=self.sql('cluster-a',"SELECT to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS');")[0][0]
        time.sleep(2);self.sql('cluster-a',"INSERT INTO review_marker VALUES ('A-after-target');")
        self.sql('cluster-a','SELECT pg_switch_wal();');time.sleep(3)
        cmd=[sys.executable,str(ROOT/'scripts/isolated-restore.py'),'--namespace',self.ns,'--source-release','cluster-a-patroni','--target-release','review-clone','--recovery-time',target,'--execute']
        output=self.run(cmd,timeout=900)
        # Source helper expects <project>-patroni naming; query clone explicitly.
        code="import os,psycopg2,json;c=psycopg2.connect(host='localhost',user='postgres',dbname='postgres',password=os.environ['PATRONI_SUPERUSER_PASSWORD']);q=c.cursor();q.execute('SELECT * FROM review_marker');print(json.dumps(q.fetchall()))"
        rows=json.loads(self.k('exec','review-clone-patronimvp-0','-c','patronimvp','--','python3','-c',code))
        self.save('clone',{'output':output,'rows':rows,'target':target,'source_rows':self.sql('cluster-a','SELECT * FROM review_marker;',True)})
        assert rows==[['A']]
    def network(self):
        self.owned()
        def peer(release):return {'podSelector':{'matchLabels':{'release-name':release}}}
        dns={'to':[{'namespaceSelector':{'matchLabels':{'kubernetes.io/metadata.name':'kube-system'}}}],'ports':[{'port':53,'protocol':p} for p in ['TCP','UDP']]}
        ips=[self.get('service','kubernetes','-n','default')['spec']['clusterIP']]+[a['address'] for n in self.get('nodes')['items'] for a in n['status']['addresses'] if a['type']=='InternalIP']
        api={'to':[{'ipBlock':{'cidr':ip+'/32'}} for ip in ips],'ports':[{'port':443},{'port':6443}]}
        for release in ['cluster-a','cluster-b']:
            pg=peer(release+'-patroni');pool=peer(release+'-pgcat');store=peer(release+'-minio')
            for component,ingress,egress in [
                ('patroni',[{'from':[pg,pool],'ports':[{'port':5432},{'port':8008}]}],[dns,api,{'to':[pool],'ports':[{'port':5432}]},{'to':[pg],'ports':[{'port':5432},{'port':8008}]},{'to':[store],'ports':[{'port':9000}]}]),
                ('pgcat',[{'from':[pg],'ports':[{'port':5432}]}],[dns,{'to':[pg],'ports':[{'port':5432}]}]),
                ('minio',[{'from':[pg,store,peer('review-clone')],'ports':[{'port':9000},{'port':9001}]}],[dns,api,{'to':[store],'ports':[{'port':9000}]}])]:
                self.apply({'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':release+'-'+component+'-review','namespace':self.ns},'spec':{'podSelector':peer(release+'-'+component)['podSelector'],'policyTypes':['Ingress','Egress'],'ingress':ingress,'egress':egress}})
        self.apply({'apiVersion':'v1','kind':'Pod','metadata':{'name':'unrelated-review-probe','namespace':self.ns},'spec':{'containers':[{'name':'probe','image':'dbaas/patroni:2.1.0','command':['sleep','infinity']}]}})
        self.k('wait','--for=condition=Ready','pod/unrelated-review-probe','--timeout=120s')
        def probe(pod,host,port,container=None):
            code="import socket,json;ip=socket.gethostbyname("+repr(host)+");s=socket.socket();s.settimeout(3)\ntry:s.connect((ip,"+str(port)+"));print(json.dumps({'resolved':True,'connected':True}))\nexcept OSError as e:print(json.dumps({'resolved':True,'connected':False,'error':type(e).__name__}))"
            args=['exec',pod]+(['-c',container] if container else [])+['--','python3','-c',code]
            return {'pod':pod,'host':host,'port':port,**json.loads(self.k(*args))}
        rows=[probe('unrelated-review-probe','patronimvp-master-cluster-a-patroni',5432),probe('unrelated-review-probe','cluster-a-minio-minio',9000),probe('review-clone-patronimvp-0','patronimvp-master-cluster-a-patroni',5432,'patronimvp')]
        proxy=self.get('pods','-l','app=proxy,release-name=cluster-a-pgcat')['items'][0]['metadata']['name']
        script="const net=require('net');const s=net.connect(5432,'patronimvp-master-cluster-b-patroni');s.setTimeout(3000);s.on('connect',()=>{console.log(JSON.stringify({connected:true}));s.destroy()});s.on('timeout',()=>{console.log(JSON.stringify({connected:false,error:'timeout'}));s.destroy()});s.on('error',e=>{console.log(JSON.stringify({connected:false,error:e.code}));});"
        rows.append({'pod':proxy,'host':'patronimvp-master-cluster-b-patroni',**json.loads(self.k('exec',proxy,'-c','pgcat-config-watcher','--','node','-e',script))})
        positive={r:self.sql(r,'SELECT * FROM review_marker;',True) for r in ['cluster-a','cluster-b']}
        api_output=self.k('exec','deployment/dbaas-backend','--','helm','list','-n',self.ns,'-q')
        self.save('network',{'denied_probes':rows,'positive_sql':positive,'api_to_kubernetes':bool(api_output),'policies':self.get('networkpolicy'),'scope':'explicit per-release policies in Calico; not tenant RBAC isolation'})
        assert all(not row['connected'] and row['error'] in ['TimeoutError','timeout'] for row in rows)

    def cleanup(self):
        if 'uid' in self.state:self.owned()
        if self.state.get('creation_started'):
            self.run(['kind','delete','cluster','--name',self.name])
            self.run(['docker','run','--rm','--privileged','--entrypoint','sysctl','kindest/node:v1.30.0','-w','fs.inotify.max_user_instances='+str(self.state['inotify_before'])])
        self.save('cleanup',{'deleted':self.name,'inotify_restored':self.state.get('inotify_before'),'remaining_clusters':self.run(['kind','get','clusters']).splitlines()})
        import shutil
        shutil.rmtree(self.directory)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['setup','configure','concurrent','isolation','duplicate','partial','backup','pitr','network','cleanup']);p.add_argument('--state-dir',required=True);a=p.parse_args()
    d=Path(a.state_dir)
    if a.stage=='setup':
        d.mkdir(mode=0o700,exist_ok=False)
        f=d/'state.json';f.write_text(json.dumps({'name':'dbaas-review-'+secrets.token_hex(4)}));f.chmod(0o600)
    review=Review(d)
    getattr(review,a.stage)()

if __name__=='__main__':main()
