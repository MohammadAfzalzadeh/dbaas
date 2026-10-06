"""Small pgbench matrix with raw output, environment and explicit missing measurements."""
import json
from pathlib import Path
import re
import time
import uuid
from importlib.util import spec_from_file_location,module_from_spec
from lab import ROOT, utc


def parse_pgbench(output):
    if 'Run was aborted' in output:raise ValueError('Aborted pgbench output is not a complete sample')
    patterns={'tps':r'^tps = ([0-9.]+)', 'average_latency_ms':r'^latency average = ([0-9.]+)',
              'failed_transactions':r'^number of failed transactions: (\d+)', 'transactions':r'^number of transactions actually processed: (\d+)'}
    result={name:float(m.group(1)) if name in ('tps','average_latency_ms') else int(m.group(1)) for name,pattern in patterns.items() if (m:=re.search(pattern,output,re.M))}
    if 'tps' not in result or 'average_latency_ms' not in result:raise ValueError('Missing pgbench result; do not report an aborted run as throughput')
    result.update(reconnects=None,p95_ms=None,p99_ms=None)
    return result


def pgbench(lab,host,profile,concurrency,duration=10):
    profiles={'read-heavy':['-b','select-only@9','-b','simple-update@1'],
              'write-heavy':['-b','simple-update'], 'mixed':['-b','tpcb-like']}
    cmd=['exec','persistent-client','--','pgbench','-h',host,'-U','postgres','-n','-c',str(concurrency),'-j',str(min(concurrency,4)),'-T',str(duration),'-r',*profiles[profile],'postgres']
    import subprocess
    start=time.monotonic();result=subprocess.run(lab.kube+cmd,capture_output=True,text=True,timeout=duration+60)
    output=lab.evidence.clean(result.stdout+result.stderr)
    if result.returncode:
        root=ROOT/'results/benchmarks'/lab.name/'attempts';root.mkdir(parents=True,exist_ok=True)
        (root/(profile+'-'+str(concurrency)+'-'+host+'-'+uuid.uuid4().hex[:8]+'-aborted.txt')).write_text(output)
        raise RuntimeError('pgbench aborted; sanitized output retained')
    return dict(timestamp=utc(),profile=profile,concurrency=concurrency,duration_seconds=duration,wall_seconds=round(time.monotonic()-start,3),host=host,**parse_pgbench(output)),output


def execute(lab):
    spec=spec_from_file_location('investigation',Path(__file__).with_name('recovery-investigation.py'));module=module_from_spec(spec);spec.loader.exec_module(module)
    root=module.attempt_directory(ROOT/'results/benchmarks'/lab.name,'matrix')
    env=json.loads((lab.evidence.root/'environment.json').read_text())
    env['current_proxy_images']=[dict(name=c['name'],image=c['image']) for c in lab.get('pods','-l','app=proxy')['items'][0]['spec']['containers']]
    env.update(max_connections=int(lab.runtime.direct('SHOW max_connections;')),pgcat_pool_size_per_proxy=60,pgcat_pool_mode='transaction',cni='Calico v3.28.2')
    lab.command('exec','persistent-client','--','pgbench','-h','patronimvp-master-lab-patroni','-U','postgres','-i','-s','1','postgres',timeout=180)
    size=int(lab.runtime.direct("SELECT sum(pg_total_relation_size(t::regclass)) FROM unnest(ARRAY['pgbench_accounts','pgbench_branches','pgbench_tellers','pgbench_history']) t;"))
    results=[]
    for profile in ('read-heavy','write-heavy','mixed'):
        for concurrency in (1,10,25,50):
            for route,host in [('direct','patronimvp-master-lab-patroni'),('pgcat','lab-pgcat-proxy-service')]:
                # Reset logical values before each sample; this is not a cold-cache experiment.
                lab.runtime.direct('UPDATE pgbench_accounts SET abalance=0; UPDATE pgbench_tellers SET tbalance=0; UPDATE pgbench_branches SET bbalance=0; TRUNCATE pgbench_history;')
                record,output=pgbench(lab,host,profile,concurrency)
                record.update(route=route,environment=env,dataset_size_bytes=size,scale_factor=1,replicates=1)
                results.append(record)
                (root/(profile+'-'+str(concurrency)+'-'+route+'.txt')).write_text(output)
                (root/'pgbench.json').write_text(json.dumps(results,indent=2)+'\n')
    lab.evidence.record('benchmarks','PASS',detail='24 pgbench samples; scale 1; three profiles; raw output retained; no percentile estimates')
    # Same workload and duration with and without an official base-backup Job.
    import threading
    comparison=[]
    for with_backup in (False,True):
        backup=[];errors=[]
        def job():
            try:backup.append(lab.runtime.backup('impact-'+uuid.uuid4().hex[:6]))
            except Exception as e:errors.append(type(e).__name__)
        worker=threading.Thread(target=job) if with_backup else None
        if worker:worker.start()
        record,output=pgbench(lab,'lab-pgcat-proxy-service','mixed',10,15)
        if worker:worker.join(timeout=180)
        if errors or (worker and worker.is_alive()):raise RuntimeError('Backup impact Job failed')
        record.update(with_backup=with_backup,environment=env,dataset_size_bytes=size,backup=backup)
        comparison.append(record);(root/('backup-impact-'+str(with_backup)+'.txt')).write_text(output)
    (root/'backup-impact.json').write_text(json.dumps(comparison,indent=2)+'\n')
    lab.evidence.record('backup_impact','PASS',detail='Paired short pgbench samples; backup completion; no CPU/I/O extrapolation')
