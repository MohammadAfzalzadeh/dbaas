"""Install an actual Operator/Prometheus lab stack and inventory real metric families."""
import json
import hashlib
from pathlib import Path
import secrets
import os
import time
from urllib.parse import urlencode
import yaml
from lab import ROOT, run, utc


def execute(lab):
    chart=Path(os.environ.get('PROMETHEUS_CHART','/tmp/kube-prometheus-stack-58.7.2.tgz'))
    expected=json.loads((ROOT/'scripts/resilience/dependencies.json').read_text())[chart.name]['sha256']
    if hashlib.sha256(chart.read_bytes()).hexdigest()!=expected:raise ValueError('Monitoring chart checksum mismatch')
    lab.command("label","pod","persistent-client","dbaas-monitor=true","--overwrite")
    admin=secrets.token_urlsafe(36);lab.evidence.sensitive.append(admin)
    if not lab.command('get','secret','obs-grafana-admin','--ignore-not-found','-o','name').strip():
        lab.apply(dict(apiVersion='v1',kind='Secret',metadata=dict(name='obs-grafana-admin',namespace=lab.ns),stringData={'admin-user':'admin','admin-password':admin}))
    placement=dict(nodeSelector={'kubernetes.io/hostname':lab.name+'-control-plane'},tolerations=[dict(key='node-role.kubernetes.io/control-plane',operator='Exists',effect='NoSchedule')])
    values=dict(defaultRules=dict(create=False),alertmanager=dict(enabled=False),nodeExporter=dict(enabled=False),
      grafana=dict(enabled=True,**placement,admin=dict(existingSecret='obs-grafana-admin',userKey='admin-user',passwordKey='admin-password'),image=dict(tag='12.4.0')),
      prometheusOperator=dict(**placement,tls=dict(enabled=True),admissionWebhooks=dict(enabled=True,failurePolicy="Fail",patch=dict(enabled=True,**placement))),
      prometheus=dict(prometheusSpec=dict(**placement,podMetadata=dict(labels={'dbaas-monitor':'true'}),scrapeInterval='5s',evaluationInterval='5s',retention='6h',resources=dict(requests=dict(memory='256Mi',cpu='100m')))),
      **{'kube-state-metrics':placement})
    path=lab.directory/'observability-values.yaml';path.write_text(yaml.safe_dump(values));path.chmod(0o600)
    run(['helm','upgrade','--install','obs',os.environ.get('PROMETHEUS_CHART','/tmp/kube-prometheus-stack-58.7.2.tgz'),'-n',lab.ns,'-f',str(path),'--wait','--timeout','10m'],timeout=660)
    for file in sorted((ROOT/'serviceMonitor').glob('*.yaml')):
        for obj in yaml.safe_load_all(file.read_text()):
            obj['metadata']['namespace']=lab.ns;obj['metadata']['labels']['release']='obs'
            obj['spec']['namespaceSelector']['matchNames']=[lab.ns]
            lab.apply(obj)
    lab.command('wait','--for=condition=Ready','pod','-l','app.kubernetes.io/name=prometheus','--timeout=180s')
    def api(path):
        code="import urllib.request;print(urllib.request.urlopen('http://obs-kube-prometheus-stack-prometheus:9090"+path+"',timeout=10).read().decode())"
        return json.loads(lab.command('exec','persistent-client','--','python3','-c',code))
    # Hold real Service connections and identify their peer IP in each proxy's
    # network namespace. This distinguishes load distribution from DB routing.
    import subprocess
    client_ip=lab.get('pod','persistent-client')['status']['podIP']
    remote_hex=''.join(f'{int(part):02X}' for part in client_ip.split('.')[::-1])
    code="import os,time,psycopg2; cs=[psycopg2.connect(host='lab-pgcat-proxy-service',dbname='postgres',user='postgres',password=os.environ['PGPASSWORD'],connect_timeout=3) for _ in range(20)];print('READY',flush=True);time.sleep(20);[c.close() for c in cs]"
    process=subprocess.Popen(lab.kube+['exec','persistent-client','--','python3','-u','-c',code],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
    distribution=[]
    try:
        if process.stdout.readline().strip()!='READY':raise RuntimeError('Connection distribution client failed')
        for pod in lab.get('pods','-l','app=proxy,release-name=lab-pgcat')['items']:
            if pod['metadata'].get('deletionTimestamp'):continue
            sockets=lab.command('exec',pod['metadata']['name'],'-c','pgcat-config-watcher','--','node','-e',"process.stdout.write(require('fs').readFileSync('/proc/net/tcp','utf8'))")
            count=sum(1 for line in sockets.splitlines()[1:] if len(line.split())>3 and line.split()[1].endswith(':1538') and line.split()[2].startswith(remote_hex+':') and line.split()[3]=='01')
            distribution.append(dict(pod=pod['metadata']['name'],client_connections=count))
        if len(distribution)!=2 or any(x['client_connections']==0 for x in distribution):raise RuntimeError('Service distribution did not reach both proxies')
    finally:process.wait(timeout=30)
    lab.evidence.save('service-distribution.json',dict(client_ip=client_ip,connections=20,proxy_sockets=distribution))
    time.sleep(20)
    targets=api('/api/v1/targets');lab.evidence.save('prometheus-targets.json',targets)
    families=api('/api/v1/label/__name__/values');lab.evidence.save('metric-families.json',families)
    lab.evidence.save('servicemonitors.json',lab.get('servicemonitors'))
    (lab.evidence.root/'metrics-patroni.txt').write_text(lab.command('exec','persistent-client','--','python3','-c',"import urllib.request;print(urllib.request.urlopen('http://patronimvp-master-lab-patroni:8008/metrics').read().decode())"))
    (lab.evidence.root/'metrics-pgcat.txt').write_text(lab.command('exec','persistent-client','--','python3','-c',"import urllib.request;print(urllib.request.urlopen('http://lab-pgcat-proxy-service:9930/metrics').read().decode())"))
    lab.evidence.record('observability','PASS',detail='Actual Prometheus Operator, ServiceMonitors, targets and metric inventory; inspect individual missing/broken families')
