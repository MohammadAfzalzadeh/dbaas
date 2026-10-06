#!/usr/bin/env python3
"""Measure graceful deletion and persistent SQL while the peer remains available."""
import argparse,json,time
from lab import Lab,run,utc
from experiments import Probe
from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
s=spec_from_file_location('investigation',Path(__file__).with_name('recovery-investigation.py'));m=module_from_spec(s);s.loader.exec_module(m)

def ready(pod):
    statuses=pod.get("status",{}).get("containerStatuses",[])
    return not pod["metadata"].get("deletionTimestamp") and len(statuses)==2 and all(c["ready"] for c in statuses)

def execute(lab):
    lab.evidence.root=m.attempt_directory(lab.evidence.root,'proxy-shutdown')
    pods=[p for p in lab.get('pods','-l','app=proxy')['items'] if not p['metadata'].get('deletionTimestamp')]
    assert len(pods)==2 and all(all(c['ready'] for c in p['status']['containerStatuses']) for p in pods)
    pod=pods[0];name=pod['metadata']['name'];peer=pods[1]['metadata']['name'];node=pod['spec']['nodeName']
    ids={c['name']:c['containerID'].split('://')[1] for c in pod['status']['containerStatuses']}
    samples=[];endpoint_samples=[]
    with Probe(lab,'graceful-proxy'):
        started=utc();start=time.monotonic();lab.command('delete','pod',name,'--wait=false')
        while time.monotonic()-start<105:
            states={}
            for container,identity in ids.items():
                try:
                    x=json.loads(run(['docker','exec',node,'crictl','inspect',identity],timeout=10))['status']
                    states[container]={k:x.get(k) for k in ('state','exitCode','reason','finishedAt')}
                except RuntimeError:states[container]={'state':'removed'}
            samples.append(dict(seconds=time.monotonic()-start,containers=states))
            endpoints=lab.get('endpoints','lab-pgcat-proxy-service')
            names=[a.get('targetRef',{}).get('name') for x in endpoints.get('subsets',[]) for a in x.get('addresses',[])]
            endpoint_samples.append(dict(seconds=time.monotonic()-start,ready=names))
            assert peer in names,'Peer proxy became unavailable'
            if all(v['state'] in ('CONTAINER_EXITED','removed') for v in states.values()):break
            time.sleep(.25)
        terminated=time.monotonic()-start
        assert terminated<30,'Watcher shutdown exceeded expected bounded shutdown'
        lab.runtime.wait(lambda:len([p for p in lab.get('pods','-l','app=proxy')['items'] if ready(p)])==2,120)
        ready_seconds=time.monotonic()-start;time.sleep(5)
    lab.evidence.save('process-states.json',samples);lab.evidence.save('endpoints.json',endpoint_samples)
    result=dict(classification='LIVE VALIDATED',started=started,termination_seconds=terminated,replacement_ready_seconds=ready_seconds,peer_continuously_ready=True,termination_grace_seconds=pod['spec']['terminationGracePeriodSeconds'],containers=[dict(name=c['name'],image=c['image']) for c in pod['spec']['containers']])
    lab.evidence.save('result.json',result);print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state-dir',required=True);a=p.parse_args();l=Lab(a.state_dir);l.assert_owned();execute(l)
