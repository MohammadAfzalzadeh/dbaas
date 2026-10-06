"""Offline parsers/lint for tracked and non-ignored source; run from repository root."""
import ast
import json
from pathlib import Path
import re
import subprocess
import tomllib
import yaml

root=Path(__file__).resolve().parents[1]
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=root,text=True).splitlines()
counts=dict(yaml=0,json=0,python=0,shell=0,javascript=0,toml=0)
for name in sorted(set(paths)):
    p=root/name
    if not p.is_file():continue
    if p.suffix in {'.yaml','.yml'} and 'templates' not in p.parts:
        list(yaml.safe_load_all(p.read_text()));counts['yaml']+=1
    if p.suffix=='.json':json.loads(p.read_text());counts['json']+=1
    if p.suffix=='.toml':tomllib.loads(p.read_text());counts['toml']+=1
    if p.suffix=='.py':ast.parse(p.read_text(),filename=name);counts['python']+=1
    if p.suffix in {'.sh','.bash'}:
        subprocess.run(['bash','-n',str(p)],check=True);counts['shell']+=1
    if p.suffix=='.js':
        subprocess.run(['node','--check',str(p)],check=True);counts['javascript']+=1
for script in re.findall(r'<script[^>]*>(.*?)</script>',(root/'application/static/index.html').read_text(),re.S):
    subprocess.run(['node','--check'],input=script,text=True,check=True);counts['javascript']+=1
for family in ['helmCharts','application/helmCharts']:
    for chart in ['minio','patroni','pgcat']:
        result=subprocess.run(['helm','lint',str(root/family/chart)],capture_output=True,text=True)
        if result.returncode:raise RuntimeError(f'Helm lint failed: {family}/{chart}')
        print(f'PASS helm lint {family}/{chart}')
subprocess.run(['git','diff','--check'],cwd=root,check=True)
print('PASS static parsers:',counts)
