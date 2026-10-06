#!/usr/bin/env python3
"""Render measured continuation milestones and restore samples without interpolation."""
import argparse,json,hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('runtime',type=Path);p.add_argument('--output',type=Path,default=Path('docs/images/results/continuation'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
manifest=[]
def save(fig,name,sources):
    fig.text(.02,.015,'Single-host kind lab; individual measurements, not production guarantees',fontsize=8)
    fig.tight_layout(rect=(0,.055,1,1))
    for suffix in ('svg','png'):fig.savefig(a.output/(name+'.'+suffix),dpi=160)
    plt.close(fig);manifest.append(dict(chart=name,sources=[dict(path=str(s),sha256=hashlib.sha256(s.read_bytes()).hexdigest()) for s in sources]))
source=a.runtime/'failover-windows.json';data=json.loads(source.read_text());labels=list(data)
fig,ax=plt.subplots(figsize=(9,4));x=list(range(len(labels)));width=.24
for offset,key,title,color in [(-width,'server_promotion_observed_seconds','Promotion observed','#2864a0'),(0,'independent_sql_probe_seconds','Independent SQL probe','#18866c'),(width,'first_acknowledged_write_after_observed_promotion_seconds','First client write after promotion','#ad6634')]:
    ax.bar([v+offset for v in x],[data[k][key] for k in labels],width,label=title,color=color)
ax.set_xticks(x,[f'{k}\n{data[k]["clients"]} client(s)' for k in labels]);ax.set(ylabel='Seconds since worker stop',title='Abrupt primary-worker loss: server and client observations');ax.legend(fontsize=8);save(fig,'failover-reruns',[source])
sources=sorted((a.runtime/'restore-size').glob('attempt-*/result.json'))
if sources:
    rows=[json.loads(s.read_text()) for s in sources];fig,axes=plt.subplots(1,2,figsize=(8,4));labels=[f'{r["dataset_bytes"]/1024**2:.1f} MiB' for r in rows]
    axes[0].bar(labels,[r['backup']['duration_seconds'] for r in rows],color='#2864a0');axes[0].set(title='Base-backup Job completion',ylabel='Seconds')
    axes[1].bar(labels,[r['restore_seconds'] for r in rows],color='#18866c');axes[1].set(title='PITR + data/writable checks',ylabel='Seconds')
    save(fig,'restore-samples',sources)
(a.output/'continuation-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
