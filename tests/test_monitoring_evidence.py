"""Failure paths must preserve evidence and restore the actual scrape configuration."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/resilience'))
spec = importlib.util.spec_from_file_location('monitoring_checks', 'scripts/resilience/monitoring-checks.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
from evidence import Evidence


class FakeLab:
    def __init__(self, root, fault_error=None, cleanup_error=None):
        self.evidence = Evidence.__new__(Evidence)
        self.evidence.root = Path(root)
        self.evidence.sensitive = []
        self.policy = {'metadata': {'name': 'pgcat'}, 'spec': {'endpoints': [{'port': 'metrics'}]}}
        self.original = copy.deepcopy(self.policy)
        self.fault_error = fault_error
        self.cleanup_error = cleanup_error
        self.patches = []

    def get(self, *args):
        return copy.deepcopy(self.policy)

    def command(self, *args, **kwargs):
        if args[0] == 'get':
            return json.dumps(self.policy)
        self.patches.append(args)
        if '--type=merge' in args:
            self.policy['spec'] = json.loads(args[-1])['spec']
            if self.fault_error:
                raise self.fault_error
        else:
            if self.cleanup_error:
                raise self.cleanup_error
            self.policy['spec'] = json.loads(args[-1])[0]['value']
        return ''


def responses(states):
    states = iter(states)

    def call(lab, path):
        if path == '/api/v1/targets':
            return {'data': {'activeTargets': [
                {'labels': {'service': 'lab-pgcat-proxy-service'}, 'health': 'down'},
                {'labels': {'service': 'unrelated'}, 'health': 'up'},
            ]}}
        state = next(states)
        if isinstance(state, Exception):
            raise state
        return {'data': {'groups': [{'rules': [{'name': 'PgCatMetricsUnavailable', 'state': state}]}]}}
    return call


class MonitoringEvidenceTests(unittest.TestCase):
    def test_success_requires_restoration_and_resolution(self):
        with tempfile.TemporaryDirectory() as root:
            lab = FakeLab(root)
            with patch.object(checks, 'api', side_effect=responses(['inactive', 'pending', 'firing', 'inactive', 'inactive'])):
                checks.rehearse_scrape_alert(lab)
            self.assertEqual(lab.policy, lab.original)
            result = json.loads((Path(root) / 'result.json').read_text())
            self.assertEqual(result['classification'], 'LIVE VALIDATED')
            self.assertEqual(result['resolved'], 'LIVE VALIDATED')

    def test_cleanup_failure_does_not_mask_original_failure_or_erase_samples(self):
        with tempfile.TemporaryDirectory() as root:
            lab = FakeLab(root, cleanup_error=ValueError('private cleanup diagnostic'))
            failure = RuntimeError('private original diagnostic')
            with patch.object(checks, 'api', side_effect=responses(['inactive', failure])):
                with self.assertRaises(RuntimeError) as raised:
                    checks.rehearse_scrape_alert(lab)
            self.assertIs(raised.exception, failure)
            text = (Path(root) / 'result.json').read_text()
            result = json.loads(text)
            self.assertEqual(result['classification'], 'FAILED')
            self.assertEqual(result['restoration'], 'FAILED')
            self.assertEqual(result['restoration_error_type'], 'ValueError')
            self.assertEqual(result['failure_stage'], 'pending')
            self.assertNotIn('private', text)
            self.assertTrue(json.loads((Path(root) / 'alert-transitions.json').read_text()))
            targets = json.loads((Path(root) / 'targets-failure.json').read_text())
            self.assertEqual(len(targets), 1)

    def test_timed_out_patch_is_restored_and_stays_failed(self):
        with tempfile.TemporaryDirectory() as root:
            lab = FakeLab(root, fault_error=TimeoutError('request may have reached server'))
            with patch.object(checks, 'api', side_effect=responses(['inactive', 'inactive'])):
                with self.assertRaises(TimeoutError):
                    checks.rehearse_scrape_alert(lab)
            result = json.loads((Path(root) / 'result.json').read_text())
            self.assertEqual(lab.policy, lab.original)
            self.assertEqual(result['classification'], 'FAILED')
            self.assertEqual(result['restoration'], 'LIVE VALIDATED')
            self.assertEqual(result['resolved'], 'LIVE VALIDATED')

    def test_baseline_failure_does_not_patch_monitor(self):
        with tempfile.TemporaryDirectory() as root:
            lab = FakeLab(root)
            with patch.object(checks, 'api', side_effect=responses([RuntimeError('unavailable')])):
                with self.assertRaises(RuntimeError):
                    checks.rehearse_scrape_alert(lab)
            self.assertEqual(lab.patches, [])
            self.assertEqual(json.loads((Path(root) / 'result.json').read_text())['restoration'], 'NOT APPLICABLE')

    def test_repeated_runs_allocate_separate_attempts_even_if_inventory_fails(self):
        with tempfile.TemporaryDirectory() as root:
            for _ in range(2):
                lab = FakeLab(root)
                with patch.object(checks, 'api', side_effect=RuntimeError('no API')):
                    with self.assertRaises(RuntimeError):
                        checks.execute(lab)
            results = list((Path(root) / 'monitoring-checks').glob('*/result.json'))
            self.assertEqual(len(results), 2)
            for result in results:
                self.assertEqual(json.loads(result.read_text())['classification'], 'FAILED')
            self.assertEqual(sorted(p.name for p in (Path(root) / 'monitoring-checks').iterdir()), ['attempt-1', 'attempt-2'])
