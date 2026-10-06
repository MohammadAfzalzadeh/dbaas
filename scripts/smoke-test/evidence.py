"""Small, explicit runtime evidence records; never accept Secrets/manifests here."""
from datetime import datetime, timezone
import json
from pathlib import Path
import os
import re

STEPS = ['connectivity', 'provisioning', 'postgresql', 'patroni', 'pgcat', 'sql', 'backup', 'wal', 'pitr', 'primary_failover', 'replica_failure', 'pgcat_restart', 'backup_during_writes', 'node_drain', 'network_policy']
class Evidence:
    def __init__(self):
        self.sensitive = []
        self.root = Path(os.getenv('RUNTIME_RESULTS_DIR', 'results/runtime'))
        self.root.mkdir(parents=True, exist_ok=True)
        # Keep prior runs separate; stale successes must not describe a new failed run.
        if (self.root/'status.json').exists():
            archive=self.root/'attempts'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            archive.mkdir(parents=True)
            for name in ['status.json','summary.md','environment.json','provisioning','patroni','sql','backup','pitr','failover']:
                path=self.root/name
                if path.exists():path.rename(archive/name)
        self.status = {step: {'status': 'NOT RUN'} for step in STEPS}
        self.save('status.json', self.status)
    def clean(self, value):
        if isinstance(value, dict): return {k:self.clean(v) for k,v in value.items()}
        if isinstance(value, list): return [self.clean(v) for v in value]
        if isinstance(value, str):
            value=re.sub(r'(authentication nonce:\s*)\S+', r'\1[REDACTED]', value)
            for secret in getattr(self, 'sensitive', []):
                if secret: value=value.replace(secret, '[REDACTED]')
        return value
    def save(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary=path.with_name('.'+path.name+'.tmp')
        temporary.write_text(json.dumps(self.clean(data), indent=2, sort_keys=True) + '\n')
        temporary.replace(path)
    def record(self, step, status, **data):
        if status not in ('PASS', 'FAIL', 'NOT RUN', 'NOT APPLICABLE'):
            raise ValueError('Invalid runtime status')
        self.status[step] = dict(status=status, timestamp=datetime.now(timezone.utc).isoformat(), **data)
        self.save('status.json', self.status)
        self.summary()
    def summary(self):
        lines = ['# Runtime validation summary', '', 'Disposable lab evidence only; no production guarantees.', '', '| Check | Status | Details |', '|---|---|---|']
        for name, result in self.status.items():
            detail = result.get('detail', '')
            if 'duration_seconds' in result: detail += ' Duration: ' + str(result['duration_seconds']) + ' seconds.'
            lines.append('| ' + name + ' | ' + result['status'] + ' | ' + str(detail).replace('|','/') + ' |')
        (self.root/'summary.md').write_text('\n'.join(lines)+'\n')

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--directory', default='results/runtime');args=parser.parse_args()
    obj=Evidence.__new__(Evidence);obj.root=Path(args.directory);obj.status=json.loads((obj.root/'status.json').read_text());obj.summary()
