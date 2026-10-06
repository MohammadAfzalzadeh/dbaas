"""Safety and data-integrity regressions for the Phase 5 operator tools."""
import importlib.util
from pathlib import Path
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/resilience'))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
restore=load('isolated_restore','scripts/isolated-restore.py')
storage=load('object_storage','scripts/object-storage.py')
investigation=load('recovery_investigation','scripts/resilience/recovery-investigation.py')
from benchmark import parse_pgbench
from test_phase1 import render

class Phase5Tests(unittest.TestCase):
    def test_isolated_restore_preserves_source_values_and_disables_archive_writes(self):
        source={'security':{'allowInlineSecrets':False},'postgres':{'existingSecret':'source-pg'},'walg':{'existingSecret':'source-walg','archiveEnabled':True},'backup':{'enabled':True},'networkPolicy':{'enabled':False}}
        value=restore.target_values(source,'base_example',datetime(2026,1,1,tzinfo=timezone.utc),1)
        self.assertTrue(source['walg']['archiveEnabled']);self.assertTrue(source['backup']['enabled'])
        self.assertFalse(value['walg']['restoreEnabled']);self.assertFalse(value['walg']['archiveEnabled']);self.assertFalse(value['backup']['enabled'])
        self.assertEqual(value['postgres']['BASE_BACKUP_NAME'],'base_example')
    def test_isolated_restore_rejects_inline_credentials(self):
        with self.assertRaises(ValueError):restore.target_values({'security':{'allowInlineSecrets':True}},'base',datetime.now(timezone.utc),1)
    def test_restore_rejects_source_target_collision_without_commands(self):
        import argparse
        args=argparse.Namespace(namespace='lab',source_release='same',target_release='same')
        with patch.object(restore,'run') as command,self.assertRaises(ValueError):restore.restore(args)
        command.assert_not_called()
    def test_restore_chart_omits_backup_and_disables_archiving(self):
        for family in ('helmCharts','application/helmCharts'):
            docs=render(family+'/patroni',extra=['--set','walg.archiveEnabled=false','--set','walg.restoreEnabled=false','--set','backup.enabled=false'])
            self.assertFalse(any(d['kind']=='CronJob' for d in docs))
            sts=next(d for d in docs if d['kind']=='StatefulSet')
            env=sts['spec']['template']['spec']['containers'][0]['env']
            self.assertIn("restore_command: ''",next(x['value'] for x in env if x['name']=='PATRONI_POSTGRESQL_PARAMETERS'))
            self.assertIn('archive_mode: off',next(x['value'] for x in env if x['name']=='PATRONI_POSTGRESQL_PARAMETERS'))
    def test_external_s3_requires_tls_by_default(self):
        with self.assertRaises(ValueError):storage.storage_config('http://store.example','backup','us-east-1',True)
        self.assertEqual(storage.storage_config('https://store.example','backup','region-a',False)['AWS_S3_FORCE_PATH_STYLE'],'false')
    def test_external_s3_rejects_credential_bearing_urls(self):
        for endpoint in ('https://user:password@example.com','https://example.com?token=hidden','file:///tmp/store'):
            with self.assertRaises(ValueError):storage.storage_config(endpoint,'backup','region',True)
    def test_pgbench_parser_rejects_aborted_run(self):
        with self.assertRaises(ValueError):parse_pgbench('connection lost\n')
    def test_pgbench_rejects_incomplete_output_with_tps(self):
        with self.assertRaises(ValueError):parse_pgbench('tps = 100.0\nlatency average = 1.0\nRun was aborted; the above results are incomplete.')
    def test_pgbench_does_not_invent_percentiles_or_reconnects(self):
        result=parse_pgbench('tps = 12.50 (without initial connection time)\nlatency average = 80.0 ms\nnumber of failed transactions: 2 (1%)\n')
        self.assertEqual(result['failed_transactions'],2);self.assertIsNone(result['p99_ms']);self.assertIsNone(result['reconnects'])

class ContinuationTests(unittest.TestCase):
    def test_attempts_never_replace_prior_evidence(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            first=investigation.attempt_directory(root,'node-loss')
            (first/'result.json').write_text('{"status":"FAILED"}')
            second=investigation.attempt_directory(root,'node-loss')
            self.assertEqual(first.name,'attempt-1')
            self.assertEqual(second.name,'attempt-2')
            self.assertEqual((first/'result.json').read_text(),'{"status":"FAILED"}')
    def test_isolated_restore_disables_future_source_archive_reads(self):
        source={'postgres':{'existingSecret':'pg'},'walg':{'existingSecret':'wal','restoreEnabled':True},'backup':{'enabled':True}}
        target=restore.target_values(source,'base',datetime.now(timezone.utc),2)
        self.assertTrue(source['walg']['restoreEnabled'])
        self.assertFalse(target['walg']['restoreEnabled'])
        self.assertFalse(target['walg']['archiveEnabled'])
        self.assertEqual(target['postgres']['replicaCount'],2)

    def test_member_metrics_survive_sql_readiness_loss_without_exposing_sql(self):
        for family in ('helmCharts','application/helmCharts'):
            docs=render(family+'/patroni')
            service=next(d for d in docs if d['kind']=='Service' and d['metadata']['name'].startswith('pgmetrics-'))
            self.assertTrue(service['spec']['publishNotReadyAddresses'])
            self.assertEqual([p['port'] for p in service['spec']['ports']],[8008])
            self.assertNotIn('role',service['spec']['selector'])

    def test_proxy_replacement_requires_both_ready_containers(self):
        probe=load('proxy_shutdown','scripts/resilience/proxy-shutdown.py')
        self.assertFalse(probe.ready({'metadata':{},'status':{}}))
        self.assertFalse(probe.ready({'metadata':{},'status':{'containerStatuses':[{'ready':True}]}}))
        self.assertFalse(probe.ready({'metadata':{'deletionTimestamp':'now'},'status':{'containerStatuses':[{'ready':True},{'ready':True}]}}))
        self.assertTrue(probe.ready({'metadata':{},'status':{'containerStatuses':[{'ready':True},{'ready':True}]}}))
