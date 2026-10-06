#!/usr/bin/env python3
"""Download reviewed lab dependencies and verify their recorded SHA-256 hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);a=p.parse_args();a.directory.mkdir(parents=True,exist_ok=True)
for name,meta in json.loads(Path(__file__).with_name('dependencies.json').read_text()).items():
    dest=a.directory/name
    data=dest.read_bytes() if dest.exists() else urllib.request.urlopen(meta['url'],timeout=90).read()
    if hashlib.sha256(data).hexdigest()!=meta['sha256']:raise SystemExit('Checksum mismatch: '+name)
    dest.write_bytes(data);print('Checksum OK: '+name)
