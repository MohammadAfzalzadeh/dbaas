#!/usr/bin/env python3
"""Read-only checks; uses the caller's kubeconfig and explicit namespace/releases."""
import argparse
import json
import subprocess
import sys

def run(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise RuntimeError('Command failed: ' + ' '.join(args[:4]))
    return result.stdout

def check(namespace, release, component, pgcat_release=None):
    kube = ['kubectl', '-n', namespace]
    selector = 'application=patroni,release-name=' + release + ',cluster-name=' + release + '-patronimvp'
    pods = json.loads(run(kube + ['get', 'pods', '-l', selector, '-o', 'json']))['items']
    if not pods:
        raise RuntimeError('No Patroni members found')
    primaries = [p for p in pods if p['metadata']['labels'].get('role') == 'primary']
    if len(primaries) != 1:
        raise RuntimeError('Expected exactly one primary')
    primary = primaries[0]['metadata']['name']
    if component in ('cluster', 'patroni'):
        sts = json.loads(run(kube + ['get', 'sts', release + '-patronimvp', '-o', 'json']))
        if len(pods) != sts['spec']['replicas']:
            raise RuntimeError('Member count differs from desired replicas')
        membership = json.loads(run(kube + ['exec', primary, '-c', 'patronimvp', '--', 'python3', '-c',
            'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8008/cluster", timeout=5).read().decode())']))
        if {m['name'] for m in membership['members']} != {p['metadata']['name'] for p in pods}:
            raise RuntimeError('Patroni DCS membership differs from selected pods')
        for pod in pods:
            if not any(c['type'] == 'Ready' and c['status'] == 'True' for c in pod.get('status', {}).get('conditions', [])):
                raise RuntimeError('Unready member: ' + pod['metadata']['name'])
            expected = 'f' if pod['metadata']['name'] == primary else 't'
            actual = run(kube + ['exec', pod['metadata']['name'], '-c', 'patronimvp', '--', 'bash', '-c', 'PGPASSWORD="$PATRONI_SUPERUSER_PASSWORD" psql -h 127.0.0.1 -U "$PATRONI_SUPERUSER_USERNAME" -d postgres -Atqc "SELECT pg_is_in_recovery()"']).strip()
            if actual != expected:
                raise RuntimeError('SQL role disagrees with Patroni label')
    if component in ('cluster', 'pgcat'):
        if not pgcat_release:
            raise RuntimeError('--pgcat-release is required')
        proxies = json.loads(run(kube + ['get', 'pods', '-l', 'app=proxy,release-name=' + pgcat_release, '-o', 'json']))['items']
        if not proxies:
            raise RuntimeError('No PgCat pods')
        for pod in proxies:
            run(kube + ['exec', pod['metadata']['name'], '-c', 'pgcat-config-watcher', '--', 'node', 'pgcat-health.js'])
    if component in ('cluster', 'storage'):
        claims = json.loads(run(kube + ['get', 'pvc', '-o', 'json']))['items']
        names = {v['persistentVolumeClaim']['claimName'] for p in pods for v in p['spec']['volumes'] if 'persistentVolumeClaim' in v}
        selected = [c for c in claims if c['metadata']['name'] in names]
        if len(selected) != len(names) or not names or any(c['status']['phase'] != 'Bound' for c in selected):
            raise RuntimeError('Missing or unbound PostgreSQL PVC')
    if component in ('cluster', 'backup'):
        output = run(kube + ['exec', primary, '-c', 'patronimvp', '--', '/wal-g/wal-g', 'backup-list', '--detail', '--json', '--config', '/wal-g-credentials/.walg.env'])
        if not json.loads(output):
            raise RuntimeError('No remote WAL-G backup metadata found')
    print(component + ': PASS ' + namespace + '/' + release)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=['cluster', 'patroni', 'pgcat', 'backup', 'storage'])
    parser.add_argument('--namespace', required=True)
    parser.add_argument('--release', required=True, help='Patroni Helm release')
    parser.add_argument('--pgcat-release')
    args = parser.parse_args()
    try:
        check(args.namespace, args.release, args.component, args.pgcat_release)
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(1, 'Validation failed: ' + str(error) + '\n')

if __name__ == '__main__':
    main()
