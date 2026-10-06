#!/usr/bin/env python3
"""Rehearse the prior lab's 200-connection budget before a comparable matrix."""
import argparse,json
from lab import Lab
p=argparse.ArgumentParser();p.add_argument('--state-dir',required=True);a=p.parse_args();l=Lab(a.state_dir);l.assert_owned();l.runtime.expected=l.state['expected'];l.runtime.wait(l.stable)
before=int(l.runtime.direct('SHOW max_connections;'))
code="import json,urllib.request; r=urllib.request.Request('http://127.0.0.1:8008/config',data=json.dumps({'postgresql':{'parameters':{'max_connections':200}}}).encode(),method='PATCH');urllib.request.urlopen(r,timeout=5).read()"
l.command('exec',l.runtime.primary(),'-c','patronimvp','--','python3','-c',code)
for pod in sorted(l.runtime.pods(),key=lambda p:p['metadata']['labels'].get('role')=='primary'):
    l.command('delete','pod',pod['metadata']['name'],'--wait=true');l.runtime.wait(l.stable,240)
observed={p['metadata']['name']:int(l.runtime.direct('SHOW max_connections;',p['metadata']['name'])) for p in l.runtime.pods()}
assert all(v==200 for v in observed.values());l.runtime.assert_data()
l.evidence.save('benchmark-capacity.json',dict(classification='LIVE VALIDATED',before=before,after=observed,reason='Match prior matrix: two 60-connection pools plus 50 direct clients and operational headroom',restart_order='replicas first, then primary'))
print('Connection budget active on all three members; deterministic data retained')
