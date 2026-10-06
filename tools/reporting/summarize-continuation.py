#!/usr/bin/env python3
"""Derive synchronized transaction windows from recorded injection/client timestamps."""
import argparse,json
from datetime import datetime,timedelta
from pathlib import Path

def summarize(attempt):
    result=json.loads((attempt/'result.json').read_text())
    probes=[json.loads(p.read_text()) for p in sorted(attempt.glob('persistent-node-loss*.json'))]
    injected=datetime.fromisoformat(result['injected'])
    sql=injected+timedelta(seconds=result['sql_probe_seconds'])
    samples=[dict(row,completed=datetime.fromisoformat(row['timestamp'])+timedelta(seconds=row['latency_seconds'])) for p in probes for row in p['samples']]
    start=min(datetime.fromisoformat(x['timestamp']) for x in samples);end=max(x['completed'] for x in samples)
    windows=[]
    for name,left,right in [('before',start,injected),('during',injected,sql),('after',sql,end)]:
        rows=[x for x in samples if left<=x['completed']<right or (name=='after' and x['completed']==right)];seconds=(right-left).total_seconds()
        windows.append(dict(name=name,start=left.isoformat(),end=right.isoformat(),seconds=seconds,acknowledged=sum(x['success'] for x in rows),failed=sum(not x['success'] for x in rows),tps=sum(x['success'] for x in rows)/seconds if seconds>0 else None))
    promotion=injected+timedelta(seconds=result['promotion_observed_seconds'])
    successful=[x['completed'] for x in samples if x['success'] and x['completed']>=promotion]
    return dict(classification='EXPERIMENTALLY MEASURED',clients=len(probes),configured_interval_seconds=probes[0]['interval_seconds'],windows=windows,server_promotion_observed_seconds=result['promotion_observed_seconds'],independent_sql_probe_seconds=result['sql_probe_seconds'],first_acknowledged_write_after_observed_promotion_seconds=(min(successful)-injected).total_seconds() if successful else None,failed_transactions=sum(p['failed_transactions'] for p in probes),reconnects=sum(p['reconnects'] for p in probes),transaction_retries=0,acknowledged_transactions=sum(p['acknowledged_transactions'] for p in probes),missing_acknowledged_ids=[x for p in probes for x in p['missing_acknowledged_ids']],longest_per_client_success_gap_seconds=max(p['longest_success_gap_seconds'] for p in probes),automatic_recovery=result['automatic_recovery'],limitations='One host; UTC completion inferred from client start timestamp plus measured latency. During window ends at independent SQL probe, not exact outage end. Failed operations may have committed and are not retried.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('runtime',type=Path);a=p.parse_args()
    rows={x.name:summarize(x) for x in sorted((a.runtime/'abrupt-recovery').glob('attempt-*')) if (x/'result.json').exists() and 'sql_probe_seconds' in json.loads((x/'result.json').read_text())}
    (a.runtime/'failover-windows.json').write_text(json.dumps(rows,indent=2)+'\n')
