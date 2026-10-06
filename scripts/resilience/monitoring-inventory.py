#!/usr/bin/env python3
"""Capture actual metric names, scrape health, Grafana dashboards and explicit gaps."""
import argparse,base64,json
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
from lab import Lab
s=spec_from_file_location('checks',Path(__file__).with_name('monitoring-checks.py'));m=module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('--state-dir',required=True);a=p.parse_args();l=Lab(a.state_dir);l.assert_owned()
families=m.api(l,'/api/v1/label/__name__/values');targets=m.api(l,'/api/v1/targets');names=set(families['data']);l.evidence.save('final-metric-families.json',families);l.evidence.save('final-prometheus-targets.json',targets)
items=[]
for component,required in {
 'PostgreSQL process/WAL state':['patroni_postgres_running','patroni_xlog_replayed_location'],
 'Patroni member state':['patroni_primary','patroni_postgres_streaming','patroni_dcs_last_seen'],
 'PgCat transactions/queries':['pgcat_stats_total_xact_count','pgcat_stats_total_query_count'],
 'Backup Job outcomes':['kube_job_status_succeeded','kube_job_status_failed'],
 'FastAPI deployment readiness':['kube_deployment_status_replicas_available'],
 'Kubernetes workloads':['kube_pod_status_ready','kube_deployment_spec_replicas'],
 'MinIO requests/health':['minio_api_requests_total','minio_cluster_erasure_set_health'],
 'PVC byte usage':['kubelet_volume_stats_used_bytes']}.items():
 items.append(dict(component=component,status='AVAILABLE' if all(n in names for n in required) else 'MISSING',metrics=required,missing=[n for n in required if n not in names]))
for component in ['PostgreSQL SQL exporter','FastAPI HTTP operation metrics','Backup age/recoverability gauge','Loki/Fluent Bit delivery']:
 items.append(dict(component=component,status='NOT IMPLEMENTED'))
broken=[dict(labels=x['labels'],error=x['lastError']) for x in targets['data']['activeTargets'] if x['health']!='up']
items.append(dict(component='Unhealthy scrape targets',status='BROKEN' if broken else 'AVAILABLE',targets=broken));l.evidence.save('observability-inventory.json',items)
secret=l.get('secret','obs-grafana-admin')['data'];creds={k:base64.b64decode(v).decode() for k,v in secret.items()}
code="import sys,json,urllib.request,base64;v=json.load(sys.stdin);auth=base64.b64encode((v['admin-user']+':'+v['admin-password']).encode()).decode();r=urllib.request.Request('http://obs-grafana/api/search?query=DBaaS',headers={'Authorization':'Basic '+auth});print(urllib.request.urlopen(r,timeout=10).read().decode())"
x=json.loads(l.command('exec','-i','persistent-client','--','python3','-c',code,data=json.dumps(creds)));l.evidence.save('grafana-loaded-dashboards.json',[dict(uid=d['uid'],title=d['title']) for d in x]);print(json.dumps(dict(dashboards=len(x),metric_families=len(names),broken_targets=len(broken))))
