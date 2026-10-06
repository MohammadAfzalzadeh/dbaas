#!/usr/bin/env python3
"""Validate the real isolated-recovery helper's archive detachment and restarts."""
import argparse,importlib.util,json,time
from pathlib import Path
from lab import Lab,utc
spec=importlib.util.spec_from_file_location('investigation',Path(__file__).with_name('recovery-investigation.py'));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


def execute(lab):
    lab.evidence.root=mod.attempt_directory(lab.evidence.root,'isolated-durability');lab.evidence.status={}
    target=lab.state['restore_release'];pod=target+'-patronimvp-0';r=lab.runtime;r.expected=lab.state['expected']
    before=lab.get('statefulset','lab-patroni-patronimvp');events=[]
    def inspect(stage):
        rows=r.dataset(lambda sql:r.direct(sql,pod));settings=dict(restore_command=r.direct('SHOW restore_command;',pod),archive_mode=r.direct('SHOW archive_mode;',pod),in_recovery=r.direct('SELECT pg_is_in_recovery();',pod))
        if settings!=dict(restore_command='',archive_mode='off',in_recovery='f'):raise RuntimeError('Clone not detached from source recovery')
        expected=[dict(id=1,phase='baseline',value=100),dict(id=3,phase='isolated-write',value=300)]
        if rows!=expected:raise RuntimeError('Clone target-time or independent write mismatch')
        r.direct('CREATE TABLE IF NOT EXISTS durability_check(id integer PRIMARY KEY); INSERT INTO durability_check VALUES(1) ON CONFLICT DO NOTHING;',pod)
        data=json.loads(lab.command('exec',pod,'-c','patronimvp','--','python3','-c',mod.DIAGNOSTIC))
        lab.evidence.save(stage+'.json',dict(timestamp=utc(),rows=rows,settings=settings,diagnostic=data))
    inspect('before')
    row=dict(id=4,phase='future-source',value=400)
    r.direct("INSERT INTO validation_test(id,phase,value) VALUES(4,'future-source',400) ON CONFLICT(id) DO NOTHING;")
    if row not in r.expected:r.expected.append(row)
    lab.state['expected']=r.expected;lab.save_state();r.archive();r.assert_data()
    for mode in ('graceful','abrupt'):
        uid=lab.get('pod',pod)['metadata']['uid'];start=time.monotonic()
        args=['delete','pod',pod,'--wait=true'] if mode=='graceful' else ['delete','pod',pod,'--grace-period=0','--force','--wait=false']
        lab.command(*args)
        r.wait(lambda:lab.get('pod',pod)['metadata']['uid']!=uid,120)
        lab.command('wait','--for=condition=Ready','pod/'+pod,'--timeout=180s');inspect('after-'+mode)
        events.append(dict(restart=mode,duration_seconds=time.monotonic()-start,classification='LIVE VALIDATED'))
    after=lab.get('statefulset','lab-patroni-patronimvp')
    if before['metadata']['uid']!=after['metadata']['uid'] or before['spec']!=after['spec']:raise RuntimeError('Source StatefulSet changed')
    r.assert_data();result=dict(classification='LIVE VALIDATED',target=target,source_future_row_excluded=True,source_unchanged=True,archive_reads_disabled=True,archive_writes_disabled=True,restarts=events,replica_state='NOT APPLICABLE: one-member restore target',lifecycle=['bootstrap restore','reach target','promote','detach from source archive','independent operation'])
    lab.evidence.save('result.json',result);print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state-dir',required=True);a=p.parse_args();lab=Lab(a.state_dir);lab.assert_owned();execute(lab)
