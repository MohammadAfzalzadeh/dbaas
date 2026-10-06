#!/usr/bin/env python3
"""Summarize observed client windows, keeping injection-clock uncertainty explicit."""
import argparse,json
from pathlib import Path

def summarize(directory):
    data=json.loads((directory/'persistent-node-loss.json').read_text());rows=data['samples'];failed=[r for r in rows if not r['success']]
    first=failed[0]['elapsed_seconds'];last=failed[-1]['elapsed_seconds']+failed[-1]['latency_seconds'];end=rows[-1]['elapsed_seconds']+rows[-1]['latency_seconds']
    windows=[]
    for label,low,high in [('before_first_client_failure',0,first),('first_to_last_client_failure',first,last),('after_last_client_failure',last,end)]:
        selected=[r for r in rows if low<=r['elapsed_seconds']<high];seconds=high-low
        windows.append(dict(window=label,duration_seconds=seconds,successful_transactions=sum(r['success'] for r in selected),failed_transactions=sum(not r['success'] for r in selected),tps=sum(r['success'] for r in selected)/seconds if seconds>0 else None))
    return dict(environment=json.loads((directory/'environment.json').read_text()),timestamp=rows[0]['timestamp'],dataset='unique-ID resilience_ledger writes',dataset_size_bytes=None,concurrency=1,duration_seconds=end,windows=windows,transaction_retries=0,connection_reconnects=data['reconnects'],missing_acknowledged_ids=data['missing_acknowledged_ids'],failed_transactions=data['failed_transactions'],acknowledged_transactions=data['acknowledged_transactions'],longest_success_gap_seconds=data['longest_success_gap_seconds'],limitations='Observed client-failure windows, not precisely synchronized injection phases. Before window is short. One INSERT/commit per 0.1 seconds; failed transactions are not replayed. Automatic replica convergence failed.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(summarize(args.runtime),indent=2)+'\n')
