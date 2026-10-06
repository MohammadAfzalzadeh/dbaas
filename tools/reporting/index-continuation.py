#!/usr/bin/env python3
"""Index actual continuation artifacts and verify the preserved historical evidence."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('runtime',type=Path);a=p.parse_args()
manifest=Path('results/runtime/phase5-continuation/previous-evidence-sha256.json')
previous=json.loads(manifest.read_text())
changed=[x['path'] for x in previous if not Path(x['path']).exists() or hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()!=x['sha256']]
if changed:raise RuntimeError('Historical evidence changed: '+', '.join(changed))
rows=[]
for path in sorted(a.runtime.rglob('*')):
    if path.is_file() and path.name!='evidence-index.json':
        rows.append(dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(a.runtime/'evidence-index.json').write_text(json.dumps(dict(prior_files_verified=len(previous),historical_evidence_unchanged=True,files=rows),indent=2)+'\n')
lines=['# Phase 5 continuation evidence','','All entries below exist on disk. The original 80 runtime artifacts were verified against the saved SHA-256 manifest. Successful reruns do not change historical failed outcomes.','','[Report](../audit/phase5-continuation-report.md) · [Machine index](../../'+str(a.runtime/'evidence-index.json')+')','','## Scenario results','']
for path in sorted(a.runtime.rglob('result.json')):
    data=json.loads(path.read_text());status=data.get('classification',data.get('automatic_recovery','See scoped outcomes'))
    lines.append('- ['+str(path.relative_to(a.runtime))+'](../../'+str(path)+'): '+status+'.')
lines+=['','## Supporting evidence','']
for name in ['environment.json','admission-validation.json','observability-inventory.json','grafana-loaded-dashboards.json','failover-windows.json','benchmark-capacity.json','cleanup.json','validation/summary.json']:
    path=a.runtime/name
    if path.exists():lines.append('- ['+name+'](../../'+str(path)+')')
lines+=['','## Benchmark matrix and backup impact','']
for path in sorted((Path('results/benchmarks')/a.runtime.name).rglob('*.json')):
    lines.append('- ['+str(path.relative_to(Path('results/benchmarks')/a.runtime.name))+'](../../'+str(path)+')')
Path('docs/evidence/phase5-continuation.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(indexed_files=len(rows),prior_files_verified=len(previous))))
