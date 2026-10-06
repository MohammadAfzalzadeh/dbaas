#!/usr/bin/env python3
"""Restore into a NEW release/PVC set; never mutates the source release or cuts over."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import time
from recovery import identifier, timestamp, select_backup, run, read_json, ROOT


def target_values(source_values, backup, target_time, replicas):
    values=deepcopy(source_values)
    if values.get('security',{}).get('allowInlineSecrets',False):
        raise ValueError('Isolated restore requires existing credential Secrets')
    if not values.get('postgres',{}).get('existingSecret') or not values.get('walg',{}).get('existingSecret'):
        raise ValueError('Explicit existing PostgreSQL and WAL-G Secrets are required')
    values['postgres'].update(replicaCount=replicas,BACKUP_ENABLE=True,BASE_BACKUP_NAME=backup,
                              RECOVERY_TARGET_TIME=target_time.isoformat(sep=' '),explicitRetainPolicy=True)
    # A writable clone must never archive a new timeline into its source prefix.
    # Configure an independent writable archive destination before cutover.
    values['walg']['archiveEnabled']=False
    # Bootstrap has its own restore_command; subsequent restarts must use the
    # clone's local WAL, never diverged WAL from the source archive prefix.
    values['walg']['restoreEnabled']=False
    values['backup']['enabled']=False
    return values


def restore(args):
    ns=identifier(args.namespace,63);source=identifier(args.source_release);target=identifier(args.target_release)
    if source==target:raise ValueError('Source and target releases must differ')
    when=timestamp(args.recovery_time)
    kube=['kubectl','-n',ns]
    releases=read_json(['helm','list','-n',ns,'--all','-o','json'])
    if any(x['name']==target for x in releases):raise ValueError('Target Helm release already exists')
    # Check names even when Helm metadata is missing; install must never adopt data.
    resources=read_json(kube+['get','statefulsets,pvc,services,endpoints,configmaps','-o','json'])['items']
    prefixes=(target+'-', 'pgdata-'+target+'-', 'patronimvp-master-'+target,'patronimvp-replica-'+target)
    if any(x['metadata']['name'].startswith(prefixes) for x in resources):raise ValueError('Target resource/PVC name already exists')
    source_status=read_json(['helm','status',source,'-n',ns,'-o','json'])
    if source_status['info']['status']!='deployed':raise ValueError('Source release is not deployed')
    values=read_json(['helm','get','values',source,'-n',ns,'--all','-o','json'])
    pods=read_json(kube+['get','pods','-l','application=patroni,release-name='+source+',role=primary','-o','json'])['items']
    if len(pods)!=1:raise ValueError('Source must have exactly one primary')
    backups=read_json(kube+['exec',pods[0]['metadata']['name'],'-c','patronimvp','--','/wal-g/wal-g','backup-list','--detail','--json','--config','/wal-g-credentials/.walg.env'])
    selected=select_backup(backups,when,source+'-patronimvp',args.backup_name)
    # Defaults may resolve names from the source release; make references explicit.
    values['postgres']['existingSecret']=values['postgres'].get('existingSecret') or source+'-postgres-credentials'
    values['walg']['existingSecret']=values['walg'].get('existingSecret') or source+'-wal-g-credentials'
    if args.network_values:
        import yaml
        values['networkPolicy']=yaml.safe_load(Path(args.network_values).read_text())['networkPolicy']
    elif values.get('networkPolicy',{}).get('enabled'):
        raise ValueError('Supply reviewed --network-values for an isolated target when source policies are enabled')
    new=target_values(values,selected,when,args.replicas)
    with tempfile.TemporaryDirectory(prefix='dbaas-isolated-restore-') as directory:
        path=Path(directory)/'values.json';path.write_text(json.dumps(new));path.chmod(0o600)
        run(['helm','template',target,str(ROOT/'helmCharts/patroni'),'-n',ns,'-f',str(path)])
        print(json.dumps(dict(source=source,target=target,namespace=ns,backup=selected,target_utc=when.isoformat(),source_mutations=False,target_archiving=False,execute=args.execute)))
        if args.execute:
            run(['helm','install',target,str(ROOT/'helmCharts/patroni'),'-n',ns,'-f',str(path),'--wait','--timeout','10m'])
            run(kube+['wait',f'--for=jsonpath={{.status.readyReplicas}}={args.replicas}','statefulset/'+target+'-patronimvp','--timeout=600s'])
            # Patroni can retain bootstrap recovery settings for a control loop.
            # Do not declare the clone safe until the running primary has stopped
            # reading and writing the source archive on subsequent recovery.
            deadline=time.monotonic()+120
            restarted=False
            while time.monotonic()<deadline:
                members=read_json(kube+['get','pods','-l','application=patroni,release-name='+target+',role=primary','-o','json'])['items']
                if len(members)==1:
                    output=run(kube+['exec',members[0]['metadata']['name'],'-c','patronimvp','--','bash','-c',
                        'PGPASSWORD="$PATRONI_SUPERUSER_PASSWORD" psql -h 127.0.0.1 -U "$PATRONI_SUPERUSER_USERNAME" -d postgres -Atqc "$1"','restore-check',
                        "SELECT current_setting('archive_mode'), current_setting('restore_command');"])
                    if output.strip()=='off|':break
                    if not restarted:
                        # Restart only the newly created clone after completed PITR.
                        # This makes Patroni apply normal recovery settings instead
                        # of retaining its custom-bootstrap restore_command.
                        run(kube+['exec',members[0]['metadata']['name'],'-c','patronimvp','--','python3','-c',
                            "import urllib.request; r=urllib.request.Request('http://127.0.0.1:8008/restart',data=b'{}',headers={'Content-Type':'application/json'});urllib.request.urlopen(r,timeout=60).read()"])
                        restarted=True
                time.sleep(2)
            else:raise RuntimeError('Clone still has source archive recovery configuration')
            print('Target ready with source archive reads/writes disabled. Data verification and cutover remain separate operator actions.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--namespace',required=True);p.add_argument('--source-release',required=True);p.add_argument('--target-release',required=True)
    p.add_argument('--recovery-time',required=True);p.add_argument('--backup-name');p.add_argument('--replicas',type=int,choices=[1,2,3],default=1)
    p.add_argument('--network-values',help='Reviewed target NetworkPolicy values file; never silently disables source policy intent')
    p.add_argument('--execute',action='store_true');args=p.parse_args()
    try:restore(args)
    except Exception as exc:p.exit(1,'Isolated restore stopped: '+type(exc).__name__+'; inspect target metadata with operator tools.\n')
