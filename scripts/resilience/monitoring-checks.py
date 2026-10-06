#!/usr/bin/env python3
"""Load repository dashboards/rules and record real Prometheus queries/alert transitions."""
import argparse,json,time
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from urllib.parse import urlencode
import yaml
from lab import Lab,ROOT,utc


def api(lab,path):
    code="import urllib.request;print(urllib.request.urlopen("+repr('http://obs-kube-prometheus-stack-prometheus:9090'+path)+",timeout=10).read().decode())"
    return json.loads(lab.command('exec','persistent-client','--','python3','-c',code,timeout=20))


def execute(lab):
    spec = spec_from_file_location('investigation', Path(__file__).with_name('recovery-investigation.py'))
    investigation = module_from_spec(spec)
    spec.loader.exec_module(investigation)
    lab.evidence.root = investigation.attempt_directory(lab.evidence.root, 'monitoring-checks')
    lab.evidence.status = {}
    try:
        execute_attempt(lab)
    except Exception as error:
        # Setup can fail before the fault rehearsal writes its richer result.
        if not (lab.evidence.root / 'result.json').exists():
            lab.evidence.save('result.json', {
                'classification': 'FAILED', 'stage': 'preparation',
                'failure_type': type(error).__name__, 'completed': utc(),
            })
        raise


def execute_attempt(lab):
    inventory=api(lab,'/api/v1/label/__name__/values')['data']
    definitions={
      'postgresql-overview':[('PostgreSQL process running','patroni_postgres_running'),('WAL replay position','patroni_xlog_replayed_location'),('Streaming replicas','patroni_postgres_streaming')],
      'patroni-ha':[('Primary by member','patroni_primary'),('Replica role','patroni_replica'),('DCS last seen (epoch seconds)','patroni_dcs_last_seen'),('Pending restart','patroni_pending_restart')],
      'pgcat-overview':[('Completed transactions per second','rate(pgcat_stats_total_xact_count[1m])'),('Queries per second','rate(pgcat_stats_total_query_count[1m])')],
      'backup-recovery':[('Backup Job completions (Kubernetes)','kube_job_status_succeeded{job_name=~"lab-backup-.*"}'),('Backup Job failures (Kubernetes)','kube_job_status_failed{job_name=~"lab-backup-.*"}')],
      'dbaas-control-plane':[('API deployment available replicas','kube_deployment_status_replicas_available{deployment="dbaas-backend"}'),('API desired replicas','kube_deployment_spec_replicas{deployment="dbaas-backend"}')]
    }
    root=ROOT/'monitoring/grafana/dashboards';root.mkdir(parents=True,exist_ok=True)
    results=[]
    for name,panels in definitions.items():
        output=[]
        for title,expr in panels:
            metric=expr.split('(')[-1].split('[')[0].split('{')[0]
            if metric not in inventory:raise RuntimeError('Metric absent: '+metric)
            query=api(lab,'/api/v1/query?'+urlencode({'query':expr}))
            results.append(dict(dashboard=name,title=title,query=expr,response=query))
            output.append(dict(id=len(output)+1,title=title,type='timeseries',datasource={'type':'prometheus','uid':'${DS_PROMETHEUS}'},gridPos=dict(x=(len(output)%2)*12,y=(len(output)//2)*8,w=12,h=8),targets=[dict(refId='A',expr=expr)]))
        output.insert(0,dict(id=99,type='text',title='Scope',gridPos=dict(x=0,y=24,w=24,h=3),options=dict(mode='markdown',content='Disposable lab metric scope. PostgreSQL panels use Patroni, not a SQL exporter. Backup panels show Job outcomes, not backup age or recoverability. API panels show replica readiness, not HTTP operation health.')))
        dashboard=dict(uid='dbaas-'+name,title='DBaaS / '+name,schemaVersion=39,version=1,tags=['dbaas','lab-evidence'],timezone='utc',time={'from':'now-1h','to':'now'},refresh='10s',templating={'list':[dict(name='DS_PROMETHEUS',type='datasource',query='prometheus',current={'text':'Prometheus','value':'prometheus'})]},panels=output)
        content=json.dumps(dashboard,indent=2)+'\n';(root/(name+'.json')).write_text(content)
        lab.apply(dict(apiVersion='v1',kind='ConfigMap',metadata=dict(name='dashboard-'+name,namespace=lab.ns,labels={'grafana_dashboard':'1'}),data={name+'.json':content}))
    lab.evidence.save('dashboard-queries.json',results)
    rules=yaml.safe_load((ROOT/'monitoring/prometheus/rules.yaml').read_text());rules['metadata']['namespace']=lab.ns;rules['metadata']['labels']['release']='obs';lab.apply(rules)
    rehearse_scrape_alert(lab)

def rehearse_scrape_alert(lab):
    """Preserve the original failure even when restoring the monitor also fails."""
    policy = json.loads(lab.command('get', 'servicemonitor', 'pgcat', '-o', 'json', timeout=20))
    original = policy['spec']
    snapshots = []
    result = {'classification': 'FAILED', 'restoration': 'NOT APPLICABLE'}
    fault_attempted = False
    failure = None
    phase = 'baseline'

    def sample():
        response = api(lab, '/api/v1/rules?type=alert')
        matches = [r for g in response['data']['groups'] for r in g['rules']
                   if r['name'] == 'PgCatMetricsUnavailable']
        state = matches[0]['state'] if matches else 'absent'
        snapshots.append({'timestamp': utc(), 'state': state, 'rules': matches})
        lab.evidence.save('alert-transitions.json', snapshots)
        return state

    def await_state(expected, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if sample() == expected:
                return
            time.sleep(5)
        raise RuntimeError('Alert did not reach ' + expected)

    def capture_targets(stage):
        try:
            targets = api(lab, '/api/v1/targets')['data']['activeTargets']
            # Retain only the affected scrape targets, not the Prometheus config.
            targets = [t for t in targets
                       if t.get('labels', {}).get('service') == 'lab-pgcat-proxy-service']
            lab.evidence.save('targets-' + stage + '.json', targets)
        except Exception as error:
            result.setdefault('diagnostic_errors', {})[stage] = type(error).__name__

    try:
        await_state('inactive', 90)
        capture_targets('before')
        changed = json.loads(json.dumps(original))
        changed['endpoints'][0]['scheme'] = 'https'
        # A timed-out PATCH can still have reached the server; always restore it.
        fault_attempted = True
        phase = 'inject_fault'
        lab.command('patch', 'servicemonitor', policy['metadata']['name'],
                    '--type=merge', '-p', json.dumps({'spec': changed}), timeout=20)
        phase = 'pending'
        await_state('pending', 90)
        phase = 'firing'
        await_state('firing', 180)
    except Exception as error:
        failure = error
        result['failure_type'] = type(error).__name__
        result['failure_stage'] = phase
        capture_targets('failure')
    finally:
        if fault_attempted:
            try:
                lab.command('patch', 'servicemonitor', policy['metadata']['name'],
                            '--type=json', '-p', json.dumps([
                                {'op': 'replace', 'path': '/spec', 'value': original}
                            ]), timeout=20)
                restored = json.loads(lab.command('get', 'servicemonitor', policy['metadata']['name'], '-o', 'json', timeout=20))['spec']
                if restored != original:
                    raise RuntimeError('ServiceMonitor differs after restoration')
                result['restoration'] = 'LIVE VALIDATED'
                await_state('inactive', 120)
                result['resolved'] = 'LIVE VALIDATED'
            except Exception as error:
                result['restoration_error_type'] = type(error).__name__
                if result['restoration'] != 'LIVE VALIDATED':
                    result['restoration'] = 'FAILED'
                if failure is None:
                    failure = error
                    result['failure_type'] = type(error).__name__
                    result['failure_stage'] = 'restoration_or_resolution'
        try:
            lab.evidence.save('prometheus-rules.json', api(lab, '/api/v1/rules?type=alert'))
        except Exception as error:
            result.setdefault('diagnostic_errors', {})['final_rules'] = type(error).__name__
        result['classification'] = 'LIVE VALIDATED' if failure is None else 'FAILED'
        result['completed'] = utc()
        lab.evidence.save('alert-transitions.json', snapshots)
        lab.evidence.save('result.json', result)
    if failure is not None:
        raise failure


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state-dir',required=True);args=p.parse_args();lab=Lab(args.state_dir);lab.assert_owned();execute(lab)
