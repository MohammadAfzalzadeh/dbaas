#!/usr/bin/env python3
"""Render only captured measurements. Missing datasets are explicitly skipped."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','axes.titleweight':'bold','svg.fonttype':'none'})
COLORS={'direct':'#2864a0','pgcat':'#18866c'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--benchmarks',type=Path,required=True);parser.add_argument('--output',type=Path,default=Path('docs/images/results'));args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True);manifest={}
    def read(path):return json.loads(path.read_text()) if path.exists() else None
    def save(fig,name,source):
        fig.text(.01,.01,'Disposable kind lab • short samples • not production guarantees',fontsize=8,color='#536273')
        fig.tight_layout(rect=[0,.04,1,1])
        for extension in ('svg','png'):fig.savefig(args.output/(name+'.'+extension),dpi=170,bbox_inches='tight')
        plt.close(fig);manifest[name]=dict(status='EXPERIMENTALLY MEASURED',source=str(source))
    rows=read(args.benchmarks/'pgbench.json')
    if rows:
        for field,title,unit,name in [('tps','Transactions per second','TPS','tps-vs-concurrency'),('average_latency_ms','Average transaction latency','Milliseconds','latency-vs-concurrency')]:
            fig,axes=plt.subplots(1,3,figsize=(12,3.8))
            for ax,profile in zip(axes,('read-heavy','write-heavy','mixed')):
                for route in ('direct','pgcat'):
                    data=sorted((x for x in rows if x['profile']==profile and x['route']==route),key=lambda x:x['concurrency'])
                    ax.plot([x['concurrency'] for x in data],[x[field] for x in data],marker='o',label=route,color=COLORS[route])
                ax.set(title=profile,xlabel='Concurrent clients',ylabel=unit);ax.grid(alpha=.2);ax.legend()
            fig.suptitle(title+' — 10-second samples, pgbench scale 1');save(fig,name,args.benchmarks/'pgbench.json')
        fig,ax=plt.subplots(figsize=(7,4));data=[x for x in rows if x['profile']=='mixed' and x['concurrency']==10]
        ax.bar([x['route'] for x in data],[x['tps'] for x in data],color=[COLORS[x['route']] for x in data]);ax.set(title='Direct vs PgCat — mixed workload, 10 clients',ylabel='TPS');save(fig,'direct-vs-pgcat',args.benchmarks/'pgbench.json')
    else:
        for name in ('tps-vs-concurrency','latency-vs-concurrency','direct-vs-pgcat'):manifest[name]={'status':'NOT VALIDATED','reason':'No pgbench dataset'}
    impact=read(args.benchmarks/'backup-impact.json')
    if impact:
        fig,axes=plt.subplots(1,2,figsize=(8,4));labels=['With backup' if x['with_backup'] else 'Without backup' for x in impact]
        for ax,field,label in [(axes[0],'tps','TPS'),(axes[1],'average_latency_ms','Mean latency (ms)')]:
            ax.bar(labels,[x[field] for x in impact],color=['#2864a0','#18866c']);ax.set(ylabel=label)
        fig.suptitle('Backup impact — paired 15-second lab samples');save(fig,'backup-impact',args.benchmarks/'backup-impact.json')
    else:manifest['backup-impact']={'status':'NOT VALIDATED','reason':'No paired samples'}
    events=[]
    for name in ('drain-primary','node-loss'):
        d=read(args.runtime/(name+'.json'))
        if d:
            for field,label in [('promotion_observed_seconds','Promotion observed'),('sql_available_seconds','SQL available'),('stable_seconds','Membership stable')]:
                if field in d:events.append((name+' / '+label,d[field]))
    if events:
        fig,ax=plt.subplots(figsize=(9,4));ax.barh([x[0] for x in events],[x[1] for x in events],color='#2864a0');ax.invert_yaxis();ax.set(title='Observed milestones — drain polls follow command completion',xlabel='Seconds (command/polling observations)');save(fig,'failover-timeline',args.runtime)
    else:manifest['failover-timeline']={'status':'NOT VALIDATED','reason':'No measured disruption milestones'}
    restore=read(args.benchmarks/'restore-sizes.json')
    if restore:
        fig,ax=plt.subplots(figsize=(7,4))
        if len(restore)==1:
            value=restore[0];ax.bar([f"{value['dataset_bytes']/1024**2:.1f} MiB payload"],[value['restore_seconds']],color='#18866c');ax.set(title='One isolated PITR sample — no scaling curve',ylabel='Seconds to writable, data-checked target')
        else:
            ax.plot([x['dataset_bytes']/1024**2 for x in restore],[x['restore_seconds'] for x in restore],marker='o',color='#18866c');ax.set(title='Isolated target-time restore with data checks',xlabel='Measured relation size (MiB)',ylabel='Seconds')
        save(fig,'restore-duration',args.benchmarks/'restore-sizes.json')
    else:
        isolated=read(args.runtime/'isolated-restore.json')
        if isolated:
            fig,ax=plt.subplots(figsize=(6,4));ax.bar(['Baseline isolated restore'],[isolated['duration_seconds']],color='#18866c');ax.set(ylabel='Seconds',title='One observed isolated restore; not a scaling curve');save(fig,'restore-duration',args.runtime/'isolated-restore.json')
        else:manifest['restore-duration']={'status':'NOT VALIDATED','reason':'No restore measurement'}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':main()
