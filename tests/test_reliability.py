"""Offline Phase 3 workload and failure regressions."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_phase1 import render, recovery, api

FAMILIES = ['helmCharts', 'application/helmCharts']
def kind(docs, name):
    return next(d for d in docs if d['kind'] == name)

class ReliabilityTests(unittest.TestCase):
    def test_pdb_replica_counts(self):
        for family in FAMILIES:
            for chart in ['patroni', 'pgcat']:
                for count in (1, 2, 3):
                    values = {'postgres': {'replicaCount': count}} if chart == 'patroni' else {'replicaCount': count}
                    docs = render(f'{family}/{chart}', values=values)
                    pdbs = [d for d in docs if d['kind'] == 'PodDisruptionBudget']
                    self.assertEqual(len(pdbs), int(count > 1))
                    if pdbs:
                        self.assertEqual(pdbs[0]['spec']['maxUnavailable'], 1)
                        self.assertEqual(pdbs[0]['spec']['selector']['matchLabels']['release-name'], 'alpha')

    def test_scoped_scheduling_and_overrides(self):
        for family in FAMILIES:
            for chart in ['patroni', 'pgcat', 'minio']:
                for mode in ['preferred', 'required']:
                    scheduling = dict(antiAffinity=mode, nodeSelector={'disk': 'fast'}, tolerations=[{'key': 'db', 'operator': 'Exists'}],
                        topologySpreadConstraints=[dict(maxSkew=1, topologyKey='topology.kubernetes.io/zone', whenUnsatisfiable='ScheduleAnyway', labelSelector={'matchLabels': {'bad': 'wide'}})])
                    settings = {'scheduling': scheduling}
                    values = {'postgres': settings} if chart == 'patroni' else {'minio': settings} if chart == 'minio' else settings
                    docs = render(f'{family}/{chart}', name='bravo', namespace='other-ns', values=values)
                    workload = kind(docs, 'Deployment' if chart == 'pgcat' else 'StatefulSet')
                    # PgAdmin may precede PgCat in Helm sorted output.
                    if chart == 'pgcat':
                        workload = next(d for d in docs if d['kind'] == 'Deployment' and d['metadata']['name'].endswith('proxy-deployment'))
                    spec = workload['spec']['template']['spec']
                    self.assertEqual(spec['nodeSelector'], {'disk': 'fast'})
                    self.assertEqual(spec['topologySpreadConstraints'][0]['labelSelector']['matchLabels']['release-name'], 'bravo')
                    self.assertNotIn('bad', spec['topologySpreadConstraints'][0]['labelSelector']['matchLabels'])
                    term = spec['affinity']['podAntiAffinity'][mode + 'DuringSchedulingIgnoredDuringExecution'][0]
                    if mode == 'preferred': term = term['podAffinityTerm']
                    self.assertEqual(term['labelSelector']['matchLabels']['release-name'], 'bravo')

    def test_patroni_probes_and_retention(self):
        for family in FAMILIES:
            docs = render(f'{family}/patroni', values={'postgres': {'explicitRetainPolicy': True, 'livenessProbe': {'enabled': True}}}, extra=['--kube-version', '1.30.0'])
            spec = kind(docs, 'StatefulSet')['spec']
            self.assertEqual(spec['updateStrategy']['type'], 'OnDelete')
            self.assertEqual(spec['persistentVolumeClaimRetentionPolicy'], {'whenDeleted': 'Retain', 'whenScaled': 'Retain'})
            container = spec['template']['spec']['containers'][0]
            self.assertEqual(container['startupProbe']['httpGet']['path'], '/health')
            self.assertEqual(container['readinessProbe']['httpGet']['path'], '/read-only')
            self.assertEqual(container['livenessProbe']['httpGet']['path'], '/liveness')
            self.assertEqual(container['startupProbe']['failureThreshold'], 360)
            self.assertNotIn('memory', container['resources']['limits'])
            with self.assertRaises(AssertionError):
                render(f'{family}/patroni', values={'postgres': {'explicitRetainPolicy': True}}, extra=['--kube-version', '1.26.0'])

    def test_all_containers_have_requests_and_resource_override(self):
        for family in FAMILIES:
            for chart in ['patroni', 'pgcat', 'minio']:
                docs = render(f'{family}/{chart}')
                for d in docs:
                    spec = d.get('spec', {})
                    if d['kind'] == 'CronJob': spec = spec['jobTemplate']['spec']
                    pod = spec.get('template', {}).get('spec', {})
                    for container in pod.get('containers', []) + pod.get('initContainers', []):
                        self.assertIn('memory', container['resources']['requests'])
                if chart == 'patroni':
                    spec = kind(render(f'{family}/{chart}', values={'postgres': {'resources': {'requests': {'memory': '2Gi'}}}}), 'StatefulSet')['spec']
                    self.assertEqual(spec['template']['spec']['containers'][0]['resources']['requests']['memory'], '2Gi')

    def test_backup_bounds(self):
        for family in FAMILIES:
            docs = render(f'{family}/patroni')
            cron = kind(docs, 'CronJob')['spec']
            self.assertEqual(cron['concurrencyPolicy'], 'Forbid')
            self.assertGreater(cron['jobTemplate']['spec']['activeDeadlineSeconds'], 21060)
            self.assertGreater(cron['startingDeadlineSeconds'], 0)
            script = next(d for d in docs if d['kind'] == 'ConfigMap' and 'script.sh' in d.get('data', {}))['data']['script.sh']
            self.assertIn('timeout --signal=TERM --kill-after=60s', script)
            with self.assertRaises(AssertionError):
                render(f'{family}/patroni', values={'backup': {'activeDeadlineSeconds': 20000}})

    def test_minio_single_instance_and_network_opt_in(self):
        for family in FAMILIES:
            with self.assertRaises(AssertionError):
                render(f'{family}/minio', values={'minio': {'replicaCount': 2}})
            for chart in ['patroni', 'pgcat', 'minio']:
                self.assertFalse(any(d['kind'] == 'NetworkPolicy' for d in render(f'{family}/{chart}')))
                with self.assertRaises(AssertionError):
                    render(f'{family}/{chart}', values={'networkPolicy': {'enabled': True}})
                docs = render(f'{family}/{chart}', values={'networkPolicy': {'enabled': True, 'ingress': [{}], 'egress': [{}]}})
                self.assertEqual(kind(docs, 'NetworkPolicy')['spec']['podSelector']['matchLabels']['release-name'], 'alpha')

    def test_pgcat_query_probe_and_grace(self):
        for family in FAMILIES:
            docs = render(f'{family}/pgcat')
            pod = next(d for d in docs if d['kind'] == 'Deployment' and d['metadata']['name'].endswith('proxy-deployment'))['spec']['template']['spec']
            self.assertGreater(pod['terminationGracePeriodSeconds'], 60)
            self.assertEqual(pod['containers'][1]['readinessProbe']['exec']['command'], ['node', 'pgcat-health.js'])
            self.assertIn('emptyDir', pod['volumes'][1])

    def test_readiness_dependency_failure(self):
        with patch.dict(os.environ, {'DBAAS_API_TOKEN': 'x' * 32}), patch('shutil.which', return_value=None):
            self.assertEqual(api.readyz().status_code, 503)
        with patch.dict(os.environ, {'DBAAS_API_TOKEN': 'x' * 32}), patch('shutil.which', return_value='/tool'):
            self.assertEqual(api.readyz().status_code, 200)

    def test_recovery_retains_private_failure_state(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'state'
            args = argparse.Namespace(state_dir=str(target))
            plan = dict(namespace='test-ns', release='alpha', pgcat='pool', backup='base_123')
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors), self.assertRaises(RuntimeError):
                with recovery.recovery_workspace(args, plan) as (workspace, stage):
                    stage('pvc-deletion-started')
                    raise RuntimeError('synthetic-secret-never-print')
            state = json.loads((target / 'state.json').read_text())
            self.assertEqual(state['stage'], 'failed-at-pvc-deletion-started')
            self.assertEqual(target.stat().st_mode & 0o777, 0o700)
            self.assertEqual((target / 'state.json').stat().st_mode & 0o777, 0o600)
            self.assertIn('helm upgrade --install alpha', errors.getvalue())
            self.assertIn('DATABASE DATA MAY ALREADY BE DELETED', errors.getvalue())
            self.assertNotIn('synthetic-secret', errors.getvalue())
            with self.assertRaises(FileExistsError):
                with recovery.recovery_workspace(args, plan): pass

    def test_recovery_temporary_cleanup_on_failure(self):
        plan = dict(namespace='ns', release='alpha', pgcat='pool', backup='base_123')
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(RuntimeError):
            with recovery.recovery_workspace(argparse.Namespace(), plan) as (workspace, stage):
                raise RuntimeError('failure')
        self.assertFalse(Path(workspace).exists())

    def test_patroni_explicit_signal(self):
        recipe = Path('patroni/Dockerfile').read_text()
        self.assertIn('STOPSIGNAL SIGTERM', recipe)
        self.assertIn('exec /usr/bin/python3', Path('patroni/entrypoint.sh').read_text())

    def test_smoke_failed_creation_cleans_only_owned_cluster(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('smoke', 'scripts/smoke-test/run.py')
        smoke = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(smoke)
        calls = []
        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[:3] == ['kind', 'get', 'clusters']:
                return 'existing-important-cluster\n'
            if cmd[:3] == ['kind', 'create', 'cluster']:
                self.assertNotEqual(os.environ['KUBECONFIG'], '/original')
                raise RuntimeError('creation failed')
            return ''
        with patch.object(smoke, 'Evidence'), patch.dict(os.environ, {'KUBECONFIG': '/original'}), patch.object(smoke.shutil, 'which', return_value='/tool'), patch.object(smoke, 'run', side_effect=fake_run):
            with self.assertRaises(RuntimeError): smoke.main()
            self.assertEqual(os.environ['KUBECONFIG'], '/original')
        created = next(cmd for cmd in calls if cmd[:3] == ['kind', 'create', 'cluster'])
        deleted = next(cmd for cmd in calls if cmd[:3] == ['kind', 'delete', 'cluster'])
        self.assertEqual(created[4], deleted[4])
        self.assertTrue(deleted[4].startswith('dbaas-smoke-'))
        self.assertNotIn('existing-important-cluster', deleted)

    def test_smoke_existing_name_is_never_deleted(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('smoke_collision', 'scripts/smoke-test/run.py')
        smoke = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(smoke)
        with patch.object(smoke, 'Evidence'), patch.object(smoke.shutil, 'which', return_value='/tool'), patch.object(smoke.secrets, 'token_hex', return_value='collision'), patch.object(smoke, 'run', return_value='dbaas-smoke-collision\n') as run:
            with self.assertRaisesRegex(RuntimeError, 'reuse'): smoke.main()
            self.assertEqual(run.call_count, 1)
