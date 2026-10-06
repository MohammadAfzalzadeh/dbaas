#!/usr/bin/env python3
"""Integration entry point for a NEW release in a fresh cluster using external WAL-G storage.

Requires precreated credential/config Secrets. No source-cluster access or cutover.
A ready target is not proof of recovered data; supply the source's expected dataset
and compare it after restore as described in docs/operations/restore-cutover.md.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import yaml
from recovery import identifier, timestamp, run, read_json, ROOT
spec=importlib.util.spec_from_file_location('isolated_restore',Path(__file__).with_name('isolated-restore.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('kubeconfig','namespace','target-release','postgres-secret','walg-secret','backup-name','recovery-time'):p.add_argument('--'+arg,required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    os.environ['KUBECONFIG']=str(Path(a.kubeconfig).resolve(strict=True))
    ns=identifier(a.namespace,63);release=identifier(a.target_release);when=timestamp(a.recovery_time)
    if not re.fullmatch(r'base_[A-Za-z0-9_]+',a.backup_name):raise ValueError('Explicit WAL-G backup identifier required')
    if any(x['name']==release for x in read_json(['helm','list','-n',ns,'--all','-o','json'])):raise ValueError('Target release exists')
    resources=read_json(['kubectl','-n',ns,'get','pvc,statefulsets,services,endpoints,configmaps','-o','json'])['items']
    if any(x['metadata']['name'].startswith((release+'-','pgdata-'+release+'-','patronimvp-master-'+release,'patronimvp-replica-'+release)) for x in resources):raise ValueError('Target resources already exist')
    for secret in (a.postgres_secret,a.walg_secret):
        # Metadata only; values are mounted by Kubernetes, never copied to the CLI.
        run(['kubectl','-n',ns,'get','secret',secret,'-o','name'])
    values=yaml.safe_load((ROOT/'helmCharts/patroni/values.yaml').read_text())
    values['postgres']['existingSecret']=a.postgres_secret;values['walg']['existingSecret']=a.walg_secret
    values=module.target_values(values,a.backup_name,when,1)
    with tempfile.TemporaryDirectory(prefix='dbaas-offsite-') as directory:
        file=Path(directory)/'values.json';file.write_text(json.dumps(values));file.chmod(0o600)
        run(['helm','template',release,str(ROOT/'helmCharts/patroni'),'-n',ns,'-f',str(file)])
        if a.execute:
            run(['helm','install',release,str(ROOT/'helmCharts/patroni'),'-n',ns,'-f',str(file),'--wait','--timeout','10m'])
            run(['kubectl','-n',ns,'wait','--for=jsonpath={.status.readyReplicas}=1','statefulset/'+release+'-patronimvp','--timeout=600s'])
        print('Target '+('ready; compare recovered data before cutover' if a.execute else 'rendered; dry run only'))

if __name__=='__main__':
    try:main()
    except Exception as exc:raise SystemExit('Off-site restore stopped: '+type(exc).__name__)
