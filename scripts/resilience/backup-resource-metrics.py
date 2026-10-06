#!/usr/bin/env python3
"""Query retained real counters over the recorded backup-impact sample windows."""
import argparse,json
from pathlib import Path
from datetime import datetime,timedelta
from urllib.parse import urlencode
from importlib.util import spec_from_file_location,module_from_spec
from lab import Lab
s=spec_from_file_location('checks',Path(__file__).with_name('monitoring-checks.py'));m=module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('--state-dir',required=True);p.add_argument('--comparison',type=Path,required=True);a=p.parse_args();l=Lab(a.state_dir);l.assert_owned()
names=set(m.api(l,'/api/v1/label/__name__/values')['data']);records=[]
for row in json.loads(a.comparison.read_text()):
    end=datetime.fromisoformat(row['timestamp']);start=end-timedelta(seconds=row['wall_seconds']);queries={}
    for metric in ['container_cpu_usage_seconds_total','container_fs_reads_bytes_total','container_fs_writes_bytes_total']:
        if metric not in names:queries[metric]=dict(status='MISSING');continue
        expr=metric+'{namespace="resilience",pod=~"lab-patroni-.*|lab-minio-.*",container!="",container!="POD"}'
        response=m.api(l,'/api/v1/query_range?'+urlencode(dict(query=expr,start=start.timestamp(),end=end.timestamp(),step='5s')))
        queries[metric]=dict(status='AVAILABLE' if response['data']['result'] else 'MISSING',query=expr,response=response)
    records.append(dict(with_backup=row['with_backup'],start=start.isoformat(),end=end.isoformat(),queries=queries))
out=a.comparison.with_name('backup-resource-metrics.json');out.write_text(json.dumps(dict(classification='EXPERIMENTALLY MEASURED',samples=records,limitations='Retained scrape counters queried after the experiment; short 15-second windows. Repeated query points can reuse one scrape. CPU/I/O counters describe containers and do not isolate backup overhead or PVC durability.'),indent=2)+'\n')
print(json.dumps([dict(with_backup=r['with_backup'],metrics={k:v['status'] for k,v in r['queries'].items()}) for r in records]))
