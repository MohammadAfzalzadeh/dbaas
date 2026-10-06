"""Offline Phase 1 regressions. Run with application/.venv/bin/python -m unittest discover -s tests -v."""
import argparse
import base64
from datetime import datetime, timezone
import importlib.util
import json
import logging
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
import unittest
from unittest.mock import patch

import yaml
from application.app import main as api

logging.disable(logging.CRITICAL)
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('recovery', ROOT / 'scripts/recovery.py')
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


def render(chart, name='alpha', namespace='test-dbaas', values=None, extra=None):
    cmd = ['helm', 'template', name, str(ROOT / chart), '-n', namespace]
    defaults = {'security': {'allowInlineSecrets': True}, 'postgres': {'SUPERUSER_PASSWORD':'synthetic-admin','REPLICATION_PASSWORD':'synthetic-replica'}, 'minio':{'rootPassword':'synthetic-root'},'minioInit':{'backupPassword':'synthetic-backup'},'pgadmin':{'pass':'synthetic-pgadmin'}}
    if chart.endswith('pgcat'):
        defaults['pgcatconfig'] = yaml.safe_load((ROOT/chart/'values.yaml').read_text())['pgcatconfig']
        defaults['pgcatconfig']['general']['PGCAT_SUPERUSER_PASSWORD']='synthetic-admin'
        for db in defaults['pgcatconfig']['DBS']:
            for user in db['users']:user['PASSWORD']='synthetic-user'
    def merge(a,b):
        for k,v in b.items():
            if isinstance(v,dict) and isinstance(a.get(k),dict):merge(a[k],v)
            else:a[k]=v
    merge(defaults,values or {})
    values=defaults
    with tempfile.TemporaryDirectory() as directory:
        if values is not None:
            p = Path(directory) / 'values.json'
            p.write_text(json.dumps(values))
            cmd += ['-f', str(p)]
        result = subprocess.run(cmd + (extra or []), capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(result.stderr)
    return [d for d in yaml.safe_load_all(result.stdout) if d]


def config_toml(config):
    code = "const {generatePgcatConfig}=require('./pgcat/pgcat-config-watcher');const fs=require('fs');process.stdout.write(generatePgcatConfig(JSON.parse(fs.readFileSync(0,'utf8'))));"
    r = subprocess.run(['node', '-e', code], input=json.dumps(config), capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        raise AssertionError(r.stderr)
    return tomllib.loads(r.stdout)


class HelmTests(unittest.TestCase):
    def test_all_charts_namespaces_and_isolation(self):
        for family in ['helmCharts', 'application/helmCharts']:
            for component in ['patroni', 'pgcat', 'minio']:
                for ns in ['dbaas', 'test-dbaas']:
                    with self.subTest(family=family, component=component, namespace=ns):
                        a = render(f'{family}/{component}', namespace=ns)
                        b = render(f'{family}/{component}', name='beta', namespace=ns)
                        other_pods = [d['spec']['template']['metadata']['labels'] for d in b if d['kind'] in ['StatefulSet', 'Deployment']]
                        for d in a:
                            self.assertNotEqual(d['metadata'].get('namespace'), 'default')
                            for subject in d.get('subjects', []):
                                self.assertEqual(subject.get('namespace', ns), ns)
                            if d['kind'] == 'Service' and d['spec'].get('selector'):
                                selector = d['spec']['selector']
                                self.assertFalse(any(all(labels.get(k) == v for k, v in selector.items()) for labels in other_pods))
                            if d['kind'] in ['StatefulSet', 'Deployment']:
                                selector = d['spec']['selector']['matchLabels']
                                self.assertFalse(any(all(labels.get(k) == v for k, v in selector.items()) for labels in other_pods))
                        self.assertFalse(any(d['kind'] in ['ClusterRole', 'ClusterRoleBinding'] for d in a))

    def test_bypass_binding_namespace(self):
        for family in ['helmCharts', 'application/helmCharts']:
            docs = render(f'{family}/patroni', extra=['--set', 'kubernetes.bypassApiService=true'])
            binding = next(d for d in docs if d['kind'] == 'ClusterRoleBinding')
            self.assertEqual(binding['subjects'][0]['namespace'], 'test-dbaas')

    def test_routing_and_metrics(self):
        for family in ['helmCharts', 'application/helmCharts']:
            patroni = render(f'{family}/patroni', name='custom-patroni')
            services = {d['metadata']['name'] for d in patroni if d['kind'] == 'Service'}
            governing = next(d for d in patroni if d['kind'] == 'Service' and d['metadata']['name'] == 'custom-patroni-patronimvp')
            self.assertEqual(governing['spec']['clusterIP'], 'None')
            self.assertNotIn('selector', governing['spec'])
            docs = render(f'{family}/pgcat', values={'patroniReleaseName': 'custom-patroni'})
            secret = next(d for d in docs if d['kind'] == 'Secret' and 'pgcat.yaml' in d.get('stringData', {}))
            config = yaml.safe_load(secret['stringData']['pgcat.yaml'])
            toml = config_toml(config)
            servers = toml['pools']['postgres']['shards']['0']['servers']
            self.assertEqual(servers[0][2], 'primary')
            self.assertEqual(servers[1][2], 'replica')
            self.assertTrue(all(s[0] in services for s in servers))
            service = next(d for d in docs if d['kind'] == 'Service' and d['metadata']['name'].endswith('proxy-service'))
            port = next(p for p in service['spec']['ports'] if p['name'] == 'metrics')
            self.assertEqual(port['port'], toml['general']['prometheus_exporter_port'])
            self.assertEqual(port['targetPort'], 'metrics')
            monitor = yaml.safe_load((ROOT/'serviceMonitor/pgcat-service.yaml').read_text())
            self.assertTrue(all(service['metadata']['labels'].get(k) == v for k,v in monitor['spec']['selector']['matchLabels'].items()))
            self.assertEqual(monitor['spec']['endpoints'][0]['port'], 'metrics')
            deployment = next(d for d in docs if d['kind'] == 'Deployment' and d['metadata']['name'].endswith('proxy-deployment'))
            container = next(c for c in deployment['spec']['template']['spec']['containers'] if c['name'] == 'proxy')
            self.assertEqual(next(p['containerPort'] for p in container['ports'] if p['name'] == 'metrics'), port['port'])
            self.assertEqual(len(deployment['spec']['template']['spec']['initContainers']), 1)
            self.assertFalse(any(x in secret['stringData']['pgcat.yaml'] for x in ['_patroniRelease', '<no value>', 'undefined', 'null']))

    def test_custom_metrics_port_and_ingress(self):
        docs = render('helmCharts/pgcat', values={'pgcatconfig': {'general': {'PROMETHEUS_EXPORTER_PORT': 19930}}, 'pgadminIngress': {'enabled': True, 'host': 'admin.example.test'}})
        route = next(d for d in docs if d['kind'] == 'IngressRoute')
        self.assertEqual(route['spec']['routes'][0]['match'], 'Host(`admin.example.test`)')
        svc = next(d for d in docs if d['kind'] == 'Service' and d['metadata']['name'].endswith('proxy-service'))
        self.assertEqual(svc['spec']['ports'][1]['port'], 19930)

    def test_schedule_and_restore_script(self):
        for family in ['helmCharts', 'application/helmCharts']:
            docs = render(f'{family}/patroni', values={'backup': {'BACKUP_PERIOD': '*/5 * * * *'}})
            cron = next(d for d in docs if d['kind'] == 'CronJob')
            self.assertEqual(cron['spec']['schedule'], '*/5 * * * *')
            sts = next(d for d in docs if d['kind'] == 'StatefulSet')
            shell = sts['spec']['template']['spec']['initContainers'][0]['args'][0]
            self.assertIn("<<'EOF'", shell)
            self.assertIn('"$BASE_BACKUP_NAME"', shell)
            self.assertNotIn('set -x', shell)
            self.assertEqual(subprocess.run(['sh', '-n'], input=shell, text=True, capture_output=True).returncode, 0)

    def test_backend_role_covers_child_roles(self):
        roles = list(yaml.safe_load_all((ROOT / 'application/k8s/rbac.yaml').read_text()))
        permissions = set()
        for role in roles:
            if role['kind'] == 'Role':
                for r in role['rules']:
                    permissions.update((g, resource, verb) for g in r['apiGroups'] for resource in r['resources'] for verb in r['verbs'])
        for doc in render('application/helmCharts/patroni'):
            if doc['kind'] == 'Role':
                for rule in doc['rules']:
                    for g in rule['apiGroups']:
                        for resource in rule['resources']:
                            for verb in rule['verbs']:
                                self.assertIn((g, resource, verb), permissions)
        for resource in ['roles', 'rolebindings']:
            self.assertIn(('rbac.authorization.k8s.io', resource, 'create'), permissions)
        self.assertIn(('', 'serviceaccounts', 'create'), permissions)


class APITests(unittest.TestCase):
    def setUp(self):
        env=patch.dict(os.environ,{'DBAAS_ALLOW_INLINE_SECRETS':'true','DBAAS_ALLOWED_NAMESPACES':'dbaas,test-dbaas'})
        env.start();self.addCleanup(env.stop)

    def request(self, **kwargs):
        data = dict(project={'releaseName': 'sample', 'enableMinio': True, 'enablePgCat': True}, namespace='test-dbaas',
                    postgresql={'pgReplicas': 2, 'superuser': {'username': 'owner', 'password': 'synthetic-quote-"-test'}, 'replication':{'username':'replicator','password':'synthetic-replication'}},
                    minio={'storageCapacity': 5, 'rootUser': 'root', 'rootPassword': 'synthetic-root', 'backupUser': 'backup', 'backupPassword': 'synthetic-backup', 'backupBucket': 'backup'})
        if 'postgresql' in kwargs:
            kwargs['postgresql']={**data['postgresql'],**kwargs['postgresql']}
        data.update(kwargs)
        return api.DeploySpec(**data)

    def test_complete_commands_cleanup_and_preview_parity(self):
        req = self.request()
        generated = api.generated_values(req)
        paths, commands = [], []
        def fake(cmd):
            commands.append(cmd)
            if cmd[:2] == ['kubectl', 'wait']: return 'ready'
            path = Path(cmd[cmd.index('-f') + 1])
            paths.append(path)
            self.assertTrue(path.exists())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            values = yaml.safe_load(path.read_text())
            if path.stem == 'pgcat':
                self.assertEqual(values['patroniReleaseName'], 'sample-patroni')
                self.assertEqual(values['pgcatconfig']['DBS'][0]['shards'][0]['MASTER_HOST'], 'patronimvp-master-sample-patroni')
            return 'mock-success'
        with patch.object(api, 'run', side_effect=fake):
            result = api.deploy(req)
        self.assertTrue(result['ok'])
        installs = [c for c in commands if c[1] == 'upgrade']
        self.assertEqual([c[3] for c in installs], ['sample-minio', 'sample-patroni', 'sample-pgcat'])
        self.assertTrue(all(c[c.index('--namespace')+1] == 'test-dbaas' for c in installs))
        self.assertTrue(all('--create-namespace' not in c for c in installs))
        self.assertTrue(all(not p.exists() for p in paths))
        self.assertEqual(yaml.safe_load(generated['patroni'])['postgres']['SUPERUSER_PASSWORD'], 'synthetic-quote-"-test')
        self.assertIn('patronimvp-master-sample-patroni', api.preview(req))

    def test_partial_failure_and_cleanup(self):
        paths, installs = [], []
        def fake(cmd):
            if cmd[:2] == ['kubectl', 'wait']: return 'ready'
            paths.append(Path(cmd[cmd.index('-f') + 1]))
            if cmd[1] == 'upgrade':
                installs.append(cmd[3])
                if cmd[3] == 'sample-patroni':
                    raise api.HTTPException(400, 'synthetic failure')
            return 'ok'
        with patch.object(api, 'run', side_effect=fake), self.assertRaises(api.HTTPException) as caught:
            api.deploy(self.request())
        self.assertEqual(caught.exception.detail['completedReleases'], ['sample-minio'])
        self.assertEqual(installs, ['sample-minio', 'sample-patroni'])
        self.assertTrue(all(not p.exists() for p in paths))

    def test_subprocess_error(self):
        with patch.object(api.subprocess, 'run', return_value=subprocess.CompletedProcess([], 7, 'failed')), self.assertRaises(api.HTTPException):
            api.run(['helm', 'version'])

    def test_invalid_inputs(self):
        for change in [dict(project={'releaseName': '../escape'}), dict(namespace='Bad/NS'), dict(postgresql={'pgReplicas': 0}),
                       dict(walg={'backup': {'enablePITR': True}}), dict(walg={'backup': {'backupSchedule': '88 * * * *'}})]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.request(**change)

    def test_single_primary_config(self):
        req = self.request(postgresql={'pgReplicas': 1})
        values = yaml.safe_load(api.generated_values(req)['pgcat'])
        docs = render('application/helmCharts/pgcat', values=values)
        secret = next(d for d in docs if 'pgcat.yaml' in d.get('stringData', {}))
        toml = config_toml(yaml.safe_load(secret['stringData']['pgcat.yaml']))
        self.assertTrue(toml['pools']['postgres']['primary_reads_enabled'])
        self.assertEqual(len(toml['pools']['postgres']['shards']['0']['servers']), 1)


class BackupTests(unittest.TestCase):
    def test_shell_exit_semantics(self):
        for family in ['helmCharts', 'application/helmCharts']:
            docs = render(f'{family}/patroni')
            cron = next(d for d in docs if d['kind'] == 'CronJob')
            container = cron['spec']['jobTemplate']['spec']['template']['spec']['containers'][0]
            selector = next(v['value'] for v in container['env'] if v['name'] == 'LABEL_SELECTOR')
            self.assertIn('release-name=alpha', selector)
            self.assertNotIn('OnFailure', selector)
            inner = next(d['data']['script.sh'] for d in docs if d['kind'] == 'ConfigMap')
            with tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                for name, content in {'kubectl': '#!/bin/bash\nif [[ "$1" == get ]]; then\n case "$MODE" in empty) exit 0;; error) exit 9;; multiple) echo "one two";; *) echo primary;; esac\nelse\n bash -s\nfi\n',
                                      'psql': '#!/bin/bash\necho "${ROLE:-f}"\n',
                                      'wal-g': '#!/bin/bash\necho called > "$MARKER"\nexit "${BACKUP_EXIT:-0}"\n'}.items():
                    p = folder/name; p.write_text(content); p.chmod(0o700)
                script = folder/'script.sh';script.write_text(inner.replace('/wal-g/wal-g', str(folder/'wal-g')))
                outer = container['command'][2].replace('/scripts/script.sh', str(script))
                for mode, code, role, success in [('empty',0,'f',False),('error',0,'f',False),('multiple',0,'f',False),('single',9,'f',False),('single',0,'t',False),('single',0,'f',True)]:
                    env={**os.environ,'PATH': directory+os.pathsep+os.environ['PATH'],'MODE':mode,'BACKUP_EXIT':str(code),'ROLE':role,
                         'MARKER':str(folder/'called'),'LABEL_SELECTOR':selector,'POD_NAMESPACE':'test-dbaas','CONTAINER_NAME':'patronimvp','PATRONI_SUPERUSER_USERNAME':'postgres','PATRONI_SUPERUSER_PASSWORD':'synthetic-password'}
                    r=subprocess.run(['bash','-c',outer],env=env,capture_output=True,text=True)
                    self.assertEqual(r.returncode==0,success,(family,mode,code,role,r.stderr))
                self.assertTrue((folder/'called').exists())
                env.pop('LABEL_SELECTOR')
                r=subprocess.run(['bash','-c',outer],env=env,capture_output=True,text=True)
                self.assertNotEqual(r.returncode,0)
                self.assertIn('LABEL_SELECTOR is required',r.stderr)


class RecoveryTests(unittest.TestCase):
    def fixture(self):
        ns, release, cluster = 'test-dbaas', 'alpha', 'alpha-patronimvp'
        annotations = {'meta.helm.sh/release-name': release, 'meta.helm.sh/release-namespace': ns}
        labels={'application':'patroni','release-name':release,'cluster-name':cluster}
        pvc={'metadata':{'name':f'pgdata-{cluster}-0','namespace':ns,'uid':'pvc-1','labels':labels},'status':{'phase':'Bound'}}
        sts={'metadata':{'name':cluster,'namespace':ns,'uid':'sts-1','annotations':annotations},'spec':{'selector':{'matchLabels':labels},'volumeClaimTemplates':[{'metadata':{'name':'pgdata'}}]}}
        pod={'metadata':{'name':cluster+'-0','namespace':ns,'labels':{**labels,'role':'primary'},'ownerReferences':[{'uid':'sts-1','controller':True}]},'spec':{'volumes':[{'persistentVolumeClaim':{'claimName':pvc['metadata']['name']}}]},'status':{'conditions':[{'type':'Ready','status':'True'}]}}
        secret={'metadata':{'namespace':ns,'annotations':annotations},'data':{'.walg.env':base64.b64encode(b'AWS_ENDPOINT=http://test\nWALG_S3_PREFIX=s3://test\nAWS_ACCESS_KEY_ID=synthetic\nAWS_SECRET_ACCESS_KEY=synthetic\n').decode()}}
        proxy={'metadata':{'namespace':ns,'annotations':{**annotations,'meta.helm.sh/release-name':'pool'}}}
        proxy['data']={'pgcat.yaml':base64.b64encode(yaml.safe_dump({'DBS':[{'shards':[{'MASTER_HOST':'patronimvp-master-alpha','REPLICA_HOST':'patronimvp-replica-alpha'}]}]}).encode()).decode()}
        backup=[{'backup_name':'base_123','hostname':cluster+'-0','finish_time':'2025-01-01T00:00:00Z'}]
        calls=[]
        def fake(cmd):
            calls.append(cmd)
            if cmd[0]=='helm':
                if cmd[1]=='status':return json.dumps({'name':cmd[2],'namespace':ns,'info':{'status':'deployed'}})
                if cmd[1:3]==['get','values']:return json.dumps({'postgres':{'replicaCount':1},'patroniReleaseName':release,'walg':{'AWS_ENDPOINT':'http://test','WALG_S3_PREFIX':'s3://test','AWS_ACCESS_KEY_ID':'synthetic','AWS_SECRET_ACCESS_KEY':'synthetic'}})
                return ''
            if 'exec' in cmd:return json.dumps(backup)
            if 'get' in cmd:
                kind=cmd[cmd.index('get')+1]
                return json.dumps({'namespace':{'metadata':{'name':ns}},'service':{'metadata':{'namespace':ns,'annotations':annotations},'spec':{'selector':{**labels,'role':'primary' if 'master' in cmd[cmd.index('get')+2] else 'replica'}}},'statefulset':sts,'deployment':proxy,'secret':proxy if cmd[cmd.index('get')+2].endswith('pgcat-config') else secret,
                                   'pvc':pvc if len(cmd)>cmd.index('get')+4 and cmd[cmd.index('get')+2]!='-o' else {'items':[pvc]},'pods':{'items':[pod]},'endpoints':{'items':[]},'configmaps':{'items':[]}}[kind])
            return ''
        args=argparse.Namespace(namespace=ns,patroni_releasename=release,pgcat_releasename='pool',recovery_time='2025-02-01 00:00:00',backup_name=None,execute=False)
        return args,fake,calls,pvc,backup

    def test_invalid_timestamp(self):
        for value in ['wrong','2025-02-30 00:00:00','2025-01-01 24:00:00']:
            with self.assertRaises(ValueError):recovery.timestamp(value)

    def test_ambiguous_and_empty_pvcs(self):
        args,fake,calls,pvc,backup=self.fixture()
        with self.assertRaises(ValueError):recovery.select_pvcs([], 'alpha',args.namespace,'alpha-patronimvp')
        pvc['metadata']['labels']={**pvc['metadata']['labels'],'release-name':'other'}
        with self.assertRaises(ValueError):recovery.select_pvcs([pvc], 'alpha',args.namespace,'alpha-patronimvp')

    def test_backup_selection(self):
        args,fake,calls,pvc,backups=self.fixture()
        self.assertEqual(recovery.select_backup(backups,recovery.timestamp(args.recovery_time),'alpha-patronimvp'),'base_123')
        with self.assertRaises(ValueError):recovery.select_backup(backups,recovery.timestamp('2024-01-01 00:00:00'),'alpha-patronimvp')
        with self.assertRaises(ValueError):recovery.select_backup(backups,recovery.timestamp(args.recovery_time),'other-patronimvp')

    def test_dry_run_has_no_mutations(self):
        args,fake,calls,pvc,backup=self.fixture()
        with patch.object(recovery,'run',side_effect=fake):recovery.recover(args)
        self.assertFalse(any('uninstall' in c or 'delete' in c or 'upgrade' in c for c in calls))
        self.assertEqual(sum(c[:2]==['helm','template'] for c in calls),2)

    def test_execute_stops_on_failed_uninstall(self):
        args,fake,calls,pvc,backup=self.fixture();args.execute=True
        def fail(cmd):
            if 'uninstall' in cmd:
                calls.append(cmd);raise RuntimeError('mock uninstall failure')
            return fake(cmd)
        with patch.object(recovery,'run',side_effect=fail), self.assertRaises(RuntimeError):recovery.recover(args)
        self.assertFalse(any('delete' in c for c in calls))

    def test_execute_deletes_only_reviewed_claim_and_preserves_values(self):
        args,fake,calls,pvc,backup=self.fixture();args.execute=True
        restored={}
        def inspect(cmd):
            if cmd[:3]==['helm','upgrade','--install']:
                restored[cmd[3]]=json.loads(Path(cmd[cmd.index('-f')+1]).read_text())
            return fake(cmd)
        with patch.object(recovery,'run',side_effect=inspect):recovery.recover(args)
        deletes=[c for c in calls if 'delete' in c]
        self.assertEqual(len(deletes),1)
        self.assertEqual(deletes[0][3:6],['delete','pvc',pvc['metadata']['name']])
        self.assertNotIn('-l',deletes[0])
        self.assertEqual(restored['alpha']['postgres']['BASE_BACKUP_NAME'],'base_123')
        self.assertTrue(restored['alpha']['postgres']['BACKUP_ENABLE'])
        self.assertEqual(restored['pool']['patroniReleaseName'],'alpha')

    def test_foreign_pvc_blocks_execute_before_uninstall(self):
        args,fake,calls,pvc,backup=self.fixture();args.execute=True
        pvc['metadata']['labels']={**pvc['metadata']['labels'],'release-name':'other'}
        with patch.object(recovery,'run',side_effect=fake), self.assertRaises(ValueError):recovery.recover(args)
        self.assertFalse(any('uninstall' in c or 'delete' in c for c in calls))


if __name__ == '__main__':
    unittest.main()
