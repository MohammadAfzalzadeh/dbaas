#!/usr/bin/env python3
"""Run repository rule tests with the owned lab's matching Prometheus binary."""
import argparse,subprocess,yaml
from pathlib import Path
from lab import Lab,ROOT
from importlib.util import spec_from_file_location,module_from_spec
s=spec_from_file_location('investigation',Path(__file__).with_name('recovery-investigation.py'));m=module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('--state-dir',required=True);a=p.parse_args();l=Lab(a.state_dir);l.assert_owned()
l.evidence.root=m.attempt_directory(l.evidence.root,'promtool')
pod=l.get('pods','-l','app.kubernetes.io/name=prometheus')['items'][0]['metadata']['name']
try:
    for path,data in [('/prometheus/dbaas-rules.yaml',yaml.safe_dump(yaml.safe_load((ROOT/'monitoring/prometheus/rules.yaml').read_text())['spec'])),('/prometheus/dbaas-rules-test.yaml',(ROOT/'tests/prometheus_rules_test.yaml').read_text().replace('/tmp/dbaas-rules.yaml','/prometheus/dbaas-rules.yaml'))]:
        l.command('exec','-i',pod,'-c','prometheus','--','sh','-c','cat > "$1"','sh',path,data=data)
    r=subprocess.run(l.kube+['exec',pod,'-c','prometheus','--','env','TMPDIR=/prometheus','promtool','test','rules','/prometheus/dbaas-rules-test.yaml'],capture_output=True,text=True)
    l.evidence.save('result.json',dict(classification='FAILED' if r.returncode else 'STATICALLY VALIDATED',output=r.stdout+r.stderr));print(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError('Rule regression failed')
finally:l.command('exec',pod,'-c','prometheus','--','rm','-f','/prometheus/dbaas-rules.yaml','/prometheus/dbaas-rules-test.yaml')
