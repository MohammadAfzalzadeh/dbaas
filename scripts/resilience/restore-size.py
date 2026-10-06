#!/usr/bin/env python3
"""Bounded deterministic restore samples with append-only attempt evidence."""
import argparse,json,time,uuid,shutil
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
s=spec_from_file_location("investigation",Path(__file__).with_name("recovery-investigation.py"));m=module_from_spec(s);s.loader.exec_module(m)
from lab import Lab,ROOT,run,utc


def execute(lab, rows=100000):
    original=lab.evidence.root
    lab.evidence.root=m.attempt_directory(original,"restore-size")
    if shutil.disk_usage(ROOT).free < 15*1024**3:raise RuntimeError("Less than 15 GiB host disk headroom")
    if rows not in (100000,440000):raise ValueError("Only bounded 100k/440k row datasets are allowed")
    lab.runtime.expected=lab.state['expected']
    r=lab.runtime;r.wait(lab.stable)
    r.direct(f"CREATE TABLE restore_payload(id integer PRIMARY KEY,payload text NOT NULL); INSERT INTO restore_payload SELECT i,repeat(md5(i::text),32) FROM generate_series(1,{rows}) i;")
    size=int(r.direct("SELECT pg_total_relation_size('restore_payload');"));before=r.direct('SELECT pg_current_wal_lsn();')
    backup=r.backup('size-'+str(rows)+'-'+uuid.uuid4().hex[:6]);time.sleep(2)
    target=r.direct("SELECT to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS');")
    time.sleep(2);r.direct(f"INSERT INTO restore_payload VALUES ({rows+1},'after-target');");r.archive()
    wal=int(r.direct("SELECT pg_wal_lsn_diff(pg_current_wal_lsn(),'"+before+"');"))
    name='isolated-size-'+uuid.uuid4().hex[:6]
    policy=json.loads(run(['helm','get','values','lab-patroni','-n',lab.ns,'--all','-o','json']))['networkPolicy']
    policy=json.loads(json.dumps(policy).replace('lab-patroni',name));p=lab.directory/'size-network.json';p.write_text(json.dumps({'networkPolicy':policy}))
    start=time.monotonic()
    run(['python3',str(ROOT/'scripts/isolated-restore.py'),'--namespace',lab.ns,'--source-release','lab-patroni','--target-release',name,'--recovery-time',target,'--network-values',str(p),'--execute'],timeout=900)
    pod=name+'-patronimvp-0'
    verified=r.direct(f"SELECT count(*)={rows} AND max(id)={rows} AND bool_and(payload=repeat(md5(id::text),32)) FROM restore_payload;",pod)=='t'
    if not verified:raise RuntimeError('Restored deterministic payload mismatch')
    r.direct("INSERT INTO restore_payload VALUES(1000000,'writable');",pod)
    record=dict(classification='EXPERIMENTALLY MEASURED',timestamp=utc(),environment=json.loads((original/'environment.json').read_text()),dataset_bytes=size,concurrency=0,duration_seconds=time.monotonic()-start,restore_seconds=time.monotonic()-start,restore_includes_pitr_and_writable_check=True,pitr_replay_seconds=None,backup=backup,wal_bytes_after_backup_start=wal,rows=rows,payload='1024 bytes per row, repeated md5(id), compressible',target_utc=target,validated=verified)
    lab.evidence.save('result.json',record)
    lab.command('scale','statefulset/'+name+'-patronimvp','--replicas=0')
    r.direct('DROP TABLE restore_payload;')
    print(json.dumps(dict(rows=rows,dataset_bytes=size,restore_seconds=record['restore_seconds'],evidence=str(lab.evidence.root))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state-dir',required=True);p.add_argument('--rows',type=int,choices=[100000,440000],default=100000);args=p.parse_args();lab=Lab(args.state_dir);lab.assert_owned();execute(lab,args.rows)
