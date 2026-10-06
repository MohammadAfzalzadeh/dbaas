"""Offline regressions for defects demonstrated during Phase 4 runtime validation."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml
from test_phase1 import api
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/smoke-test'))
from evidence import Evidence

class RuntimeTests(unittest.TestCase):
    def test_recovery_rejects_automatic_pvc_deletion_before_shutdown(self):
        from test_phase1 import RecoveryTests, recovery
        for key in ('whenScaled','whenDeleted'):
            args,fake,calls,pvc,backup=RecoveryTests().fixture()
            def wrapped(cmd):
                result=fake(cmd)
                if 'get' in cmd and cmd[cmd.index('get')+1]=='statefulset':
                    sts=json.loads(result);sts['spec']['persistentVolumeClaimRetentionPolicy']={key:'Delete'}
                    return json.dumps(sts)
                return result
            with patch.object(recovery,'run',side_effect=wrapped),self.assertRaisesRegex(ValueError,'retained PVCs'):
                recovery.preflight(args)
            self.assertFalse(any('scale' in c or 'uninstall' in c or 'delete' in c for c in calls))

    def test_failed_promotion_releases_disposable_node_scheduling(self):
        from lifecycle import Runtime
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'RUNTIME_RESULTS_DIR':directory}):
            evidence=Evidence();calls=[]
            runtime=Runtime(['kubectl','-n','lab'],lambda cmd:calls.append(cmd) or '',evidence,'lab','test',directory)
            runtime.primary=lambda:'primary-0'
            runtime.pods=lambda role=None:[{'metadata':{'name':'replica-1'}}]
            runtime.get=lambda kind,name:{'spec':{'nodeName':'disposable-node'}} if kind=='pod' else {'spec':{}}
            runtime.query=lambda sql:'1'
            def timeout(*args):raise RuntimeError('promotion timeout')
            runtime.wait=timeout
            with self.assertRaisesRegex(RuntimeError,'promotion timeout'):runtime.failover('primary_failover')
            self.assertTrue(any('cordon' in c for c in calls))
            self.assertEqual(calls[-1][-2:],['uncordon','disposable-node'])
            self.assertEqual(evidence.status['primary_failover']['status'],'FAIL')

    def test_recovery_stops_patroni_before_removing_its_services(self):
        from test_phase1 import RecoveryTests, recovery
        args,fake,calls,pvc,backup=RecoveryTests().fixture();args.execute=True
        with patch.object(recovery,'run',side_effect=fake):recovery.recover(args)
        scale=next(i for i,c in enumerate(calls) if 'scale' in c)
        stopped=next(i for i,c in enumerate(calls) if '--for=delete' in c)
        uninstall=next(i for i,c in enumerate(calls) if c[:3]==['helm','uninstall','alpha'])
        self.assertLess(scale,stopped);self.assertLess(stopped,uninstall)

    def test_recovery_shutdown_failure_preserves_volumes(self):
        from test_phase1 import RecoveryTests, recovery
        args,fake,calls,pvc,backup=RecoveryTests().fixture();args.execute=True
        def fail(cmd):
            if '--for=delete' in cmd:raise RuntimeError('shutdown failed')
            return fake(cmd)
        with patch.object(recovery,'run',side_effect=fail),self.assertRaises(RuntimeError):recovery.recover(args)
        self.assertFalse(any('delete' in c or c[:3]==['helm','uninstall','alpha'] for c in calls))

    def test_api_waits_for_stateful_members_before_pool_install(self):
        calls=[]
        spec=api.DeploySpec(namespace='dbaas',project=dict(releaseName='runtime',enablePgCat=True),postgresql=dict(pgReplicas=2))
        with patch.object(api,'run',side_effect=lambda cmd:calls.append(cmd) or 'ok'):
            api.deploy(spec)
        wait=next(c for c in calls if c[:2]==['kubectl','wait'])
        self.assertIn('--for=jsonpath={.status.readyReplicas}=2',wait)
        self.assertIn('statefulset/runtime-patroni-patronimvp',wait)
        pool=next(c for c in calls if c[:4]==['helm','upgrade','--install','runtime-pgcat'])
        self.assertLess(calls.index(wait),calls.index(pool))

    def test_readiness_failure_stops_provisioning(self):
        calls=[]
        def run(cmd):
            calls.append(cmd)
            if cmd[:2]==['kubectl','wait']:raise api.HTTPException(504,'Timed out')
            return 'ok'
        spec=api.DeploySpec(namespace='dbaas',project=dict(releaseName='runtime',enablePgCat=True),postgresql=dict(pgReplicas=2))
        with patch.object(api,'run',side_effect=run),self.assertRaises(api.HTTPException):api.deploy(spec)
        self.assertFalse(any(c[:4]==['helm','upgrade','--install','runtime-pgcat'] for c in calls))

    def test_pgadmin_defaults_use_valid_email_domain(self):
        # Validate with pgAdmin's actual email-validator package in the image during live testing.
        for family in ['helmCharts','application/helmCharts']:
            email=yaml.safe_load(Path(family,'pgcat/values.yaml').read_text())['pgadmin']['email']
            self.assertEqual(email,'admin@example.com')

    def test_evidence_redacts_authentication_nonce_without_removing_log_context(self):
        e=Evidence.__new__(Evidence);e.sensitive=[]
        self.assertEqual(e.clean('LOG: authentication nonce: synthetic-nonce\nready'), 'LOG: authentication nonce: [REDACTED]\nready')

    def test_evidence_redacts_and_generates_explicit_statuses(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'RUNTIME_RESULTS_DIR':directory}):
            e=Evidence();e.sensitive=['synthetic-secret-value'];e.save('logs/test.json',{'line':'prefix synthetic-secret-value suffix'})
            self.assertNotIn('synthetic-secret-value',Path(directory,'logs/test.json').read_text())
            e.record('sql','PASS',duration_seconds=1.25)
            self.assertEqual(json.loads(Path(directory,'status.json').read_text())['pitr']['status'],'NOT RUN')
            self.assertIn('| sql | PASS |',Path(directory,'summary.md').read_text())
            with self.assertRaises(ValueError):e.record('sql','probably works')

    def test_recovery_ignores_validated_role_service_endpoints(self):
        from test_phase1 import RecoveryTests, recovery
        args,fake,calls,pvc,backup=RecoveryTests().fixture()
        def wrapped(cmd):
            result=fake(cmd)
            if 'get' in cmd and '-l' in cmd and cmd[cmd.index('get')+1]=='endpoints':
                return json.dumps({'items':[{'metadata':{'name':'patronimvp-master-alpha'}},{'metadata':{'name':'patronimvp-replica-alpha'}}]})
            return result
        with patch.object(recovery,'run',side_effect=wrapped):
            self.assertEqual(recovery.preflight(args)['dcs'],[])

    def test_recovery_still_rejects_unknown_dcs_object(self):
        from test_phase1 import RecoveryTests, recovery
        args,fake,calls,pvc,backup=RecoveryTests().fixture()
        def wrapped(cmd):
            result=fake(cmd)
            if 'get' in cmd and '-l' in cmd and cmd[cmd.index('get')+1]=='endpoints':
                return json.dumps({'items':[{'metadata':{'name':'unrelated-endpoint'}}]})
            return result
        with patch.object(recovery,'run',side_effect=wrapped),self.assertRaisesRegex(ValueError,'Unexpected DCS'):
            recovery.preflight(args)

    def test_backup_uses_authenticated_tcp(self):
        from test_phase1 import render
        for family in ['helmCharts','application/helmCharts']:
            docs=render(family+'/patroni')
            script=next(d['data']['script.sh'] for d in docs if d['kind']=='ConfigMap' and 'script.sh' in d.get('data',{}))
            self.assertIn('PGPASSWORD="$PATRONI_SUPERUSER_PASSWORD" psql -h 127.0.0.1',script)

    def test_minio_retry_logs_are_bounded_and_redacted(self):
        import subprocess
        from test_phase1 import render
        for family in ['helmCharts','application/helmCharts']:
            docs=render(family+'/minio')
            script=next(d['data']['init-minio.sh'] for d in docs if d['kind']=='ConfigMap' and 'init-minio.sh' in d.get('data',{}))
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)
                (path/'sleep').write_text('#!/bin/sh\nexit 0\n');(path/'sleep').chmod(0o700)
                (path/'mc').write_text('#!/bin/sh\nn=$(cat "$COUNTER" 2>/dev/null || echo 0)\nn=$((n+1));echo "$n" > "$COUNTER"\nif [ "$n" -le 2 ]; then echo synthetic-sensitive-diagnostic >&2; exit 1; fi\nexit 0\n');(path/'mc').chmod(0o700)
                env={**os.environ,'PATH':directory+os.pathsep+os.environ['PATH'],'COUNTER':str(path/'count'),'MINIO_ROOT_USER':'root','MINIO_ROOT_PASSWORD':'synthetic-password','MINIO_BACKUP_USER':'backup','MINIO_BACKUP_PASSWORD':'synthetic-password','MINIO_BACKUP_BUCKET':'backup'}
                result=subprocess.run(['sh','-c',script],env=env,capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,0)
                self.assertNotIn('synthetic-sensitive-diagnostic',result.stdout+result.stderr)
                self.assertIn('completed: alias',result.stdout)

    def test_evidence_archives_prior_run(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'RUNTIME_RESULTS_DIR':directory}):
            first=Evidence();first.record('pitr','PASS');first.save('pitr/result.json',{'proof':'old'})
            second=Evidence()
            self.assertEqual(second.status['pitr']['status'],'NOT RUN')
            self.assertFalse(Path(directory,'pitr/result.json').exists())
            self.assertEqual(len(list(Path(directory,'attempts').glob('*/pitr/result.json'))),1)

    def test_walg_secret_uses_dotenv_not_json(self):
        from run import walg_environment
        original={'PGHOST':'localhost','PGPASSWORD':'synthetic-quote-"-value','AWS_S3_FORCE_PATH_STYLE':'true'}
        text=walg_environment(original)
        self.assertFalse(text.lstrip().startswith('{'))
        self.assertEqual({key:json.loads(value) for key,value in (line.split('=',1) for line in text.splitlines())},original)
        with self.assertRaises(ValueError):walg_environment({'BAD\nKEY':'value'})
