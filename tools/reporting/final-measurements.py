#!/usr/bin/env python3
"""Derive final portfolio measurements and charts from preserved runtime artifacts."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]
R=Path('results/runtime/multinode/dbaas-phase5-bc4cacdf48')
B=Path('results/benchmarks/dbaas-phase5-bc4cacdf48/matrix/attempt-1')
def read(path):return json.loads((ROOT/path).read_text())
rows=read(B/'pgbench.json');impact=read(B/'backup-impact.json');windows=read(R/'failover-windows.json')
sizes=[read(p.relative_to(ROOT)) for p in sorted((ROOT/R/'restore-size').glob('attempt-*/result.json'))]
baseline=next(x for x in impact if not x['with_backup']);during=next(x for x in impact if x['with_backup'])
summary=dict(source_matrix=str(B/'pgbench.json'),sample_count=len(rows),failed_transactions=sum(x['failed_transactions'] for x in rows),backup_tps_percent_change=(during['tps']/baseline['tps']-1)*100,backup_latency_percent_change=(during['average_latency_ms']/baseline['average_latency_ms']-1)*100,backup_baseline_tps=baseline['tps'],backup_during_tps=during['tps'],restore_samples=[dict(bytes=x['dataset_bytes'],mib=x['dataset_bytes']/1024**2,seconds=x['restore_seconds']) for x in sizes])
(ROOT/'results/validation/phase6/measured-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
out=ROOT/'docs/images/results/final';out.mkdir(parents=True,exist_ok=True);manifest=[]
plt.rcParams.update({'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
def save(fig,name,source):
    fig.text(.015,.01,'Disposable kind lab on one host | individual samples | no production guarantee',fontsize=8)
    fig.tight_layout(rect=(0,.06,1,1))
    for suffix in ('svg','png'):fig.savefig(out/(name+'.'+suffix),dpi=200)
    plt.close(fig);manifest.append(dict(chart=name,sources=[str(s) for s in source]))
for field,unit,name in [('tps','Transactions / second','tps-vs-concurrency'),('average_latency_ms','Mean latency (ms)','latency-vs-concurrency')]:
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    for ax,profile in zip(axes,['read-heavy','write-heavy','mixed']):
        for route,color in [('direct','#2864a0'),('pgcat','#18866c')]:
            selected=[r for r in rows if r['profile']==profile and r['route']==route]
            ax.scatter([r['concurrency'] for r in selected],[r[field] for r in selected],label=route,color=color)
        ax.set(title=profile,xlabel='Concurrent clients',ylabel=unit,ylim=(0,None));ax.set_xticks([1,10,25,50]);ax.legend();ax.grid(alpha=.15)
    save(fig,name,[B/'pgbench.json'])
selected=[r for r in rows if r['profile']=='mixed' and r['concurrency']==10]
fig,ax=plt.subplots(figsize=(7,4));ax.bar([r['route'] for r in selected],[r['tps'] for r in selected],color=['#2864a0','#18866c']);ax.set(title='Mixed workload, ten clients',ylabel='Transactions / second');save(fig,'direct-vs-pgcat',[B/'pgbench.json'])
fig,ax=plt.subplots(figsize=(9,4));keys=list(windows);width=.24
for offset,field,label in [(-width,'server_promotion_observed_seconds','Promotion observed'),(0,'independent_sql_probe_seconds','Independent SQL probe'),(width,'first_acknowledged_write_after_observed_promotion_seconds','Client write after promotion')]:ax.bar([i+offset for i in range(len(keys))],[windows[k][field] for k in keys],width,label=label)
ax.set_xticks(range(len(keys)),[f'{k}\n{windows[k]["clients"]} client(s)' for k in keys]);ax.set(ylabel='Seconds after worker stop',title='Abrupt-loss observations');ax.legend(fontsize=8);save(fig,'failover-timeline',[R/'failover-windows.json'])
fig,ax=plt.subplots(figsize=(8,4))
for offset,field,label in [(-.18,'failed_transactions','Failed transactions'),(.18,'reconnects','Connection reconnects')]:ax.bar([i+offset for i in range(len(keys))],[windows[k][field] for k in keys],.36,label=label)
ax.set_xticks(range(len(keys)),[f'{k}\n{windows[k]["clients"]} client(s)' for k in keys]);ax.set(title='Persistent clients during abrupt worker loss',ylabel='Count');ax.legend();save(fig,'persistent-clients',[R/'failover-windows.json'])
fig,axes=plt.subplots(1,2,figsize=(8,4))
for ax,field,unit in [(axes[0],'tps','Transactions / second'),(axes[1],'average_latency_ms','Mean latency (ms)')]:ax.bar(['Baseline','During backup'],[baseline[field],during[field]],color=['#2864a0','#18866c']);ax.set(ylabel=unit)
fig.suptitle('Mixed workload, ten clients, paired 15-second samples');save(fig,'backup-impact',[B/'backup-impact.json'])
fig,axes=plt.subplots(1,2,figsize=(8,4));labels=[f'{x["dataset_bytes"]/1024**2:.1f} MiB' for x in sizes]
axes[0].bar(labels,[x['backup']['duration_seconds'] for x in sizes]);axes[0].set(ylabel='Seconds',title='Backup Job completion')
axes[1].bar(labels,[x['restore_seconds'] for x in sizes],color='#18866c');axes[1].set(ylabel='Seconds',title='Isolated PITR plus data checks');save(fig,'restore-duration',[R/'restore-size/attempt-1/result.json',R/'restore-size/attempt-2/result.json'])
# Separate contexts are named explicitly; these are not a speedup comparison.
fig,ax=plt.subplots(figsize=(8,4));ax.bar(labels,[x['wal_bytes_after_backup_start']/1024**2 for x in sizes],color='#ad6634');ax.set(title='PITR samples: WAL interval including forced switches',ylabel='WAL interval (MiB)',xlabel='Measured source relation size');save(fig,'pitr-recovery',[R/'restore-size/attempt-1/result.json',R/'restore-size/attempt-2/result.json'])
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
link=lambda path:'[raw evidence](../../'+str(path)+')'
text='''# Performance results

These are disposable single-host measurements, not capacity commitments, an SLA, or production recovery objectives. Historical failed/aborted attempts are excluded from successful sample counts and remain in the evidence tree.

## Environment and methodology

The final matrix used PostgreSQL 16.6, Patroni 4.0.4, PgCat 1.2.0, Kubernetes 1.30.0 and Calico 3.28.2; three database members and two proxies shared one Docker host with local-path storage. The recorded working tree was dirty, so the Git revision alone does not reproduce it. '''+link(R/'environment.json')+'''

PostgreSQL pgbench scale 1; ten seconds per point; one sample per route/profile/concurrency; at most four client threads. Read-heavy weights select-only:simple-update 9:1, write-heavy uses simple-update, and mixed uses tpcb-like. Logical balances are reset; caches are not cold-started. There is no dedicated warm-up, randomized route order or replica catch-up barrier. Direct traffic uses the primary, while PgCat enables query parsing and read/write splitting across role Services; the routes are not a pure measurement of proxy overhead. Both proxies use transaction pooling and a pool budget of 60; max_connections is 200 to accommodate idle pools, direct clients and operational headroom. This was a documented budget, not a tuning search. '''+link(B/'pgbench.json')+'''

## Direct PostgreSQL and PgCat matrix

| Profile | Clients | Direct TPS | PgCat TPS | Direct mean ms | PgCat mean ms | Failed transactions, direct / proxy |
|---|---:|---:|---:|---:|---:|---:|
'''
for profile in ['read-heavy','write-heavy','mixed']:
 for clients in [1,10,25,50]:
  d=next(r for r in rows if r['profile']==profile and r['concurrency']==clients and r['route']=='direct');g=next(r for r in rows if r['profile']==profile and r['concurrency']==clients and r['route']=='pgcat')
  text+=f"| {profile} | {clients} | {d['tps']:.3f} | {g['tps']:.3f} | {d['average_latency_ms']:.3f} | {g['average_latency_ms']:.3f} | {d['failed_transactions']} / {g['failed_transactions']} |\n"
text+='\nAll table values: '+link(B/'pgbench.json')+'. Reconnects and latency percentiles were not reported and remain null. There is no statistical significance claim. The proxy is evaluated as a connection/routing layer; these samples do not establish that it is faster.\n'
for name in ['tps-vs-concurrency','latency-vs-concurrency','direct-vs-pgcat']:text+=f'\n![{name}](../images/results/final/{name}.svg)\n'
x=windows['attempt-3'];text+=f'''\n## Failover under load

Four clients acknowledged {x['acknowledged_transactions']:,} writes, with {x['failed_transactions']} failed transactions, {x['reconnects']} reconnects, no replay retries and no missing acknowledged IDs. Promotion was observed at {x['server_promotion_observed_seconds']:.3f} seconds, the independent SQL probe at {x['independent_sql_probe_seconds']:.3f}, and the first client acknowledgement after observed promotion at {x['first_acknowledged_write_after_observed_promotion_seconds']:.3f}. '''+link(R/'failover-windows.json')+'\n\n'
text+='Before/during/after TPS: '+', '.join(f"{w['tps']:.3f}" for w in x['windows'])+'. The during window ends at the independent probe; the after window still includes client errors. Sequential startup affects the baseline. '+link(R/'failover-windows.json')+'\n\n![Failover](../images/results/final/failover-timeline.svg)\n\n![Persistent clients](../images/results/final/persistent-clients.svg)\n'
text+=f'''\n## Backup impact

Baseline {baseline['tps']:.3f} TPS versus {during['tps']:.3f} TPS during backup: **{summary['backup_tps_percent_change']:.2f}%** relative change, calculated from raw values by this reporting script. Mean latency changed from {baseline['average_latency_ms']:.3f} to {during['average_latency_ms']:.3f} ms. Backup Job completion took {during['backup'][0]['duration_seconds']:.3f} seconds. '''+link(B/'backup-impact.json')+'''

Retained container CPU and filesystem read/write counters are available, but short scrape windows do not isolate backup cost or PVC durability. '''+link(B/'backup-resource-metrics.json')+'''

![Backup impact](../images/results/final/backup-impact.svg)

## Restore and PITR measurements

| Relation size | Backup Job seconds | Restore and writable/data checks, seconds | WAL interval bytes |
|---|---:|---:|---:|
'''
for i,x in enumerate(sizes,1):text+=f"| [{x['dataset_bytes']/1024**2:.1f} MiB](../../{R}/restore-size/attempt-{i}/result.json) | {x['backup']['duration_seconds']:.3f} | {x['restore_seconds']:.3f} | {x['wal_bytes_after_backup_start']:,} |\n"
text+='''
Payloads repeat md5 strings and compress well. Restore time includes scheduling, bootstrap, PITR and assertions; replay alone is not timed. WAL intervals begin before backup and include forced switches, excluding payload-generation WAL. Backup catalog sizes describe the whole cluster. These observations do not define a scaling curve.

![Restore](../images/results/final/restore-duration.svg)

![PITR WAL](../images/results/final/pitr-recovery.svg)

## Historical context

The [earlier matrix](../../results/benchmarks/dbaas-phase5-8a3ad9f385/pgbench.json) remains separate. Its aborted session-pooling attempt is retained under that run's attempts directory. The final transaction-pooling results do not prove compatibility with every session-dependent SQL feature. No new live benchmark was run during packaging.
'''
(ROOT/'docs/report/performance-results.md').write_text(text)
print(json.dumps(summary))
