"""Adversarial regressions discovered during the independent review."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml
from test_phase1 import render

ROOT=Path(__file__).resolve().parents[1]

class ChartInputReviewTests(unittest.TestCase):
    def rejected(self,chart,values):
        with tempfile.NamedTemporaryFile(mode='w',suffix='.yaml') as f:
            yaml.safe_dump(values,f);f.flush()
            p=subprocess.run(['helm','template','review',str(ROOT/chart),'-f',f.name],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('schema',p.stderr.lower())
        self.assertNotIn('nil pointer',p.stderr.lower())
    def test_negative_replicas_rejected_before_api_submission(self):
        for family in ['helmCharts','application/helmCharts']:
            self.rejected(family+'/patroni',{'postgres':{'replicaCount':-1}})
            self.rejected(family+'/pgcat',{'replicaCount':-1})
    def test_invalid_ports_rejected(self):
        for family in ['helmCharts','application/helmCharts']:
            for value in [0,70000]:
                self.rejected(family+'/patroni',{'postgres':{'pg_port':value}})
                self.rejected(family+'/minio',{'minio':{'adminPort':value}})
                self.rejected(family+'/pgcat',{'pgcatconfig':{'general':{'PGCAT_PORT':str(value)}}})
    def test_secret_reference_names_rejected(self):
        for family in ['helmCharts','application/helmCharts']:
            for name in ['BAD/secret','-bad','x'*64+'.name']:
                self.rejected(family+'/patroni',{'postgres':{'existingSecret':name}})
                self.rejected(family+'/pgcat',{'existingSecret':name})
                self.rejected(family+'/minio',{'minio':{'existingSecret':name}})
    def test_null_required_sections_fail_with_schema_message(self):
        for family in ['helmCharts','application/helmCharts']:
            self.rejected(family+'/patroni',{'postgres':None})
            self.rejected(family+'/pgcat',{'pgcatconfig':None})
    def test_valid_secret_names_ports_and_scale_zero_remain_supported(self):
        for family in ['helmCharts','application/helmCharts']:
            render(family+'/patroni',values={'postgres':{'replicaCount':0,'pg_port':6543,'existingSecret':'valid.secret'}})
            render(family+'/pgcat',values={'replicaCount':0,'existingSecret':'valid.secret','pgcatconfig':{'general':{'PGCAT_PORT':'65535'}}})

class RecoveryReviewTests(unittest.TestCase):
    def test_future_target_rejected_before_any_command(self):
        from unittest.mock import patch
        from test_phase1 import RecoveryTests, recovery
        args, _, _, _, _ = RecoveryTests().fixture()
        args.recovery_time = '2999-01-01 00:00:00'
        args.execute = True
        with patch.object(recovery, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'future'):
                recovery.recover(args)
            run.assert_not_called()

    def test_past_timestamp_still_requires_separate_wal_coverage_proof(self):
        from datetime import datetime, timezone
        from test_phase1 import recovery
        target = recovery.timestamp('2025-02-01 00:00:00')
        self.assertEqual(target, datetime(2025, 2, 1, tzinfo=timezone.utc))
        # Parsing validates time syntax, not availability of archived WAL.

if __name__=='__main__':unittest.main()
