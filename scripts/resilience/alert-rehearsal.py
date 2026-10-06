#!/usr/bin/env python3
"""Real workload faults and alert transitions, with bounded waits and restoration."""
import argparse,json,time,yaml
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
from lab import Lab,ROOT,utc
s=spec_from_file_location('checks',Path(__file__).with_name('monitoring-checks.py'));checks=module_from_spec(s);s.loader.exec_module(checks)
s=spec_from_file_location('investigation',Path(__file__).with_name('recovery-investigation.py'));m=module_from_spec(s);s.loader.exec_module(m)

def execute(lab, skip_proxy=False, only_backup=False):
    lab.evidence.root=m.attempt_directory(lab.evidence.root,'alert-rehearsal')
    rules=yaml.safe_load((ROOT/'monitoring/prometheus/rules.yaml').read_text());rules['metadata'].update(namespace=lab.ns,labels={'release':'obs'});lab.apply(rules)
    snapshots=[];results={}
    def wait(names,state,seconds=220):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            response=checks.api(lab,'/api/v1/rules?type=alert')
            found={r['name']:r for g in response['data']['groups'] for r in g['rules'] if r['name'] in names}
            snapshots.append(dict(timestamp=utc(),expected=state,rules=found));lab.evidence.save('transitions.json',snapshots)
            if len(found)==len(names) and all(r['state']==state for r in found.values()):return
            time.sleep(4)
        raise RuntimeError('Alerts did not reach '+state+': '+','.join(names))
    if not skip_proxy and not only_backup:
        names=['PgCatUnavailable']
        try:
            wait(names,'inactive');lab.command('scale','deployment/lab-pgcat-proxy-deployment','--replicas=0')
            wait(names,'pending');wait(names,'firing')
        finally:lab.command('scale','deployment/lab-pgcat-proxy-deployment','--replicas=2')
        wait(names,'inactive');results[names[0]]='LIVE VALIDATED';lab.evidence.save('result.json',results)
    if not only_backup:
        clone=lab.state['restore_release']+'-patronimvp-0'
        def patch(value):
            code="import urllib.request,json; r=urllib.request.Request('http://127.0.0.1:8008/config',data=json.dumps("+repr({'pause':value})+").encode(),method='PATCH');urllib.request.urlopen(r,timeout=5).read()"
            lab.command('exec',clone,'-c','patronimvp','--','python3','-c',code)
        names=['PostgreSQLProcessUnavailable','PatroniNoLeader']
        try:
            wait(names,'inactive');patch(True);time.sleep(12)
            lab.command('exec',clone,'-c','patronimvp','--','bash','-c','pg_ctl -D "$PATRONI_POSTGRESQL_DATA_DIR" -m fast -w stop',timeout=40)
            wait(names,'pending');wait(names,'firing')
        finally:patch(False)
        wait(names,'inactive');results.update({n:'LIVE VALIDATED' for n in names});lab.evidence.save('result.json',results)
    job='lab-backup-alert-'+lab.evidence.root.name
    template=lab.get('cronjob','lab-patroni-exec-script-cronjob')['spec']['jobTemplate']['spec']
    template['backoffLimit']=0;template['activeDeadlineSeconds']=60;template['template']['spec']['restartPolicy']='Never'
    for env in template['template']['spec']['containers'][0]['env']:
        if env['name']=='LABEL_SELECTOR':env['value']='release-name=deliberately-missing-backup-source'
    names=['BackupJobFailed']
    try:
        wait(names,'inactive');lab.apply(dict(apiVersion='batch/v1',kind='Job',metadata=dict(name=job,namespace=lab.ns),spec=template))
        wait(names,'pending');wait(names,'firing')
        lab.evidence.save('failed-backup-job.json',lab.get('job',job))
        (lab.evidence.root/'failed-backup.log').write_text(lab.evidence.clean(lab.command('logs','job/'+job)))
    finally:lab.command('delete','job',job,'--ignore-not-found')
    wait(names,'inactive');results[names[0]]='LIVE VALIDATED';lab.evidence.save('result.json',results)
    print(json.dumps(results))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state-dir',required=True);p.add_argument('--skip-proxy',action='store_true');p.add_argument('--only-backup',action='store_true');a=p.parse_args();l=Lab(a.state_dir);l.assert_owned();execute(l,a.skip_proxy,a.only_backup)
