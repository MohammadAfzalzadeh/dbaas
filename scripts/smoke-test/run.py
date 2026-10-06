#!/usr/bin/env python3
"""Disposable kind end-to-end smoke test; never uses the default kubeconfig."""
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import time
import urllib.request
import urllib.error
import yaml
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence import Evidence

ROOT = Path(__file__).resolve().parents[2]
IMAGES = ['dbaas/wal-g:3.0.7', 'dbaas/patroni:2.1.0', 'dbaas/pgcat-config-watcher:1.1.1',
          'dbaas/minio:RELEASE.2025-04-22T22-12-26Z', 'dbaas/mc:RELEASE.2025-04-16T18-13-26Z',
          'dbaas/kubectl:1.30.0', 'dbaas/backend:0.2.0']

def run(cmd, data=None, timeout=900):
    result = subprocess.run(cmd, input=data, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        # Output can contain Secrets. Only bounded command identity is reported.
        raise RuntimeError('Command failed: ' + ' '.join(cmd[:3]))
    return result.stdout

def walg_environment(config):
    """WAL-G selects dotenv parsing from the .env extension, not JSON."""
    import re
    if any(not re.fullmatch('[A-Z_][A-Z0-9_]*', key) for key in config):
        raise ValueError('Invalid WAL-G environment key')
    return '\n'.join(key+'='+json.dumps(str(value)) for key,value in config.items())+'\n'


def main():
    for command in ('docker', 'kind', 'kubectl', 'helm'):
        if not shutil.which(command):
            raise RuntimeError('Missing tool: ' + command)
    evidence = Evidence()
    name = 'dbaas-smoke-' + secrets.token_hex(5)
    if name in run(['kind', 'get', 'clusters']).splitlines():
        raise RuntimeError('Refusing to reuse a cluster')
    ns = os.getenv('SMOKE_NAMESPACE', 'dbaas-smoke')
    release = os.getenv('SMOKE_RELEASE', 'smoke')
    import re
    if any(not re.fullmatch('[a-z0-9]([-a-z0-9]*[a-z0-9])?', x) or len(x) > 35 for x in (ns, release)):
        raise RuntimeError('Invalid smoke namespace/release')
    pg, pool, storage = release + '-patroni', release + '-pgcat', release + '-minio'
    with tempfile.TemporaryDirectory(prefix='dbaas-smoke-') as directory:
        kubeconfig = str(Path(directory) / 'kubeconfig')
        previous = os.environ.get('KUBECONFIG')
        os.environ['KUBECONFIG'] = kubeconfig
        forward = None
        creation_started = False
        try:
            print('Creating isolated kind cluster ' + name, flush=True)
            creation_started = True
            run(['kind', 'create', 'cluster', '--name', name, '--kubeconfig', kubeconfig,
                 '--image', os.getenv('KIND_NODE_IMAGE', 'kindest/node:v1.30.0'), '--wait', '180s'], timeout=360)
            # Node Ready alone does not mean Service routing/DNS works.
            run(['kubectl', '--kubeconfig', kubeconfig, '-n', 'kube-system', 'rollout', 'status', 'daemonset/kube-proxy', '--timeout=90s'])
            run(['kubectl', '--kubeconfig', kubeconfig, '-n', 'kube-system', 'rollout', 'status', 'deployment/coredns', '--timeout=90s'])
            if os.getenv('SKIP_BUILD') != '1':
                run(['bash', str(ROOT / 'scripts/smoke-test/build-images.sh')], timeout=7200)
            run(['kind', 'load', 'docker-image', '--name', name, *IMAGES], timeout=1200)
            kube = ['kubectl', '--kubeconfig', kubeconfig, '-n', ns]
            run(kube + ['create', 'namespace', ns])
            def apply(obj):
                run(kube + ['apply', '-f', '-'], json.dumps(obj))
            def secret(secret_name, values):
                evidence.sensitive.extend(str(v) for k,v in values.items() if 'password' in k.lower() or k == 'token')
                apply(dict(apiVersion='v1', kind='Secret', metadata=dict(name=secret_name, namespace=ns), stringData=values))
            password, repl, rootpass, backpass, token = [secrets.token_urlsafe(36) for _ in range(5)]
            secret('dbaas-api-auth', {'token': token})
            secret(pg + '-postgres-credentials', {'superuser-username': 'postgres', 'superuser-password': password,
                   'replication-username': 'standby', 'replication-password': repl})
            secret(storage + '-minio-credentials', {'root-user': 'root', 'root-password': rootpass,
                   'backup-user': 'backup', 'backup-password': backpass, 'backup-bucket': 'backup'})
            walg = dict(PGHOST='localhost', PGPORT='5432', PGUSER='postgres', PGPASSWORD=password, PGDATABASE='postgres', AWS_ACCESS_KEY_ID='backup', AWS_SECRET_ACCESS_KEY=backpass, WALG_S3_PREFIX='s3://backup',
                        AWS_ENDPOINT='http://' + storage + '-minio:9000', AWS_REGION='us-east-1', AWS_S3_FORCE_PATH_STYLE='true', WALG_COMPRESSION_METHOD='brotli')
            secret(pg + '-wal-g-credentials', {'.walg.env': walg_environment(walg)})
            config = yaml.safe_load((ROOT / 'helmCharts/pgcat/values.yaml').read_text())['pgcatconfig']
            config['general']['PGCAT_SUPERUSER_PASSWORD'] = password
            db = config['DBS'][0]
            db['PRIMARY_READ'] = True
            db['users'][0]['PASSWORD'] = password
            db['shards'][0].update(MASTER_HOST='patronimvp-master-' + pg, REPLICA_HOST='patronimvp-replica-' + pg)
            secret(pool + '-pgcat-config', {'pgcat.yaml': yaml.safe_dump(config)})
            secret(pool + '-pgadmin', {'pgadmin-password': secrets.token_urlsafe(36)})
            for filename in ('rbac.yaml', 'deploy.yaml'):
                for obj in yaml.safe_load_all((ROOT / 'application/k8s' / filename).read_text()):
                    obj['metadata']['namespace'] = ns
                    for subject in obj.get('subjects', []):
                        subject['namespace'] = ns
                    if obj['kind'] == 'Deployment':
                        container = obj['spec']['template']['spec']['containers'][0]
                        container['image'] = 'dbaas/backend:0.2.0'
                        for env in container['env']:
                            if env['name'] == 'DBAAS_ALLOWED_NAMESPACES':
                                env['value'] = ns
                    apply(obj)
            run(kube + ['rollout', 'status', 'deployment/dbaas-backend', '--timeout=180s'])
            # Ask kubectl for a free localhost port; stderr is kept private.
            log = open(Path(directory) / 'port-forward.log', 'w+')
            forward = subprocess.Popen(kube + ['port-forward', 'service/dbaas-backend', ':80', '--address=127.0.0.1'], stdout=log, stderr=log)
            port = None
            for _ in range(100):
                log.flush(); log.seek(0)
                match = re.search(r'127\.0\.0\.1:(\d+)', log.read())
                if match:
                    port = int(match[1]); break
                time.sleep(.1)
            if port is None:
                raise RuntimeError('API port-forward failed')
            payload = dict(namespace=ns, project=dict(releaseName=release, enableMinio=True, enablePgCat=True),
                           postgresql=dict(pgReplicas=2, pgStorageCapacity=1), minio=dict(storageCapacity=1))
            request = urllib.request.Request('http://127.0.0.1:' + str(port) + '/api/deploy', data=json.dumps(payload).encode(),
                                            headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
            evidence.save('environment.json', dict(cluster=name, namespace=ns, release=release, kubernetes='kind v1.30.0', node_count=1, postgres_members=2, storage='kind local-path RWO', images=IMAGES,
                docker=json.loads(run(['docker', 'info', '--format', '{"cpus":{{.NCPU}},"memory_bytes":{{.MemTotal}}}']))))
            evidence.record('connectivity', 'PASS', detail='kube-proxy/CoreDNS available; API ready')
            print('Provisioning through FastAPI', flush=True)
            provisioning_started = time.monotonic()
            try:
                # Local port-forward must bypass ambient HTTP proxy settings.
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(request, timeout=1500) as response:
                    api_result = json.load(response)
                    if not api_result.get('ok'):
                        raise RuntimeError('Provisioning failed')
                    evidence.save('provisioning/api-response.json', api_result)
                    evidence.record('provisioning', 'PASS', duration_seconds=round(time.monotonic()-provisioning_started,3))
            except urllib.error.HTTPError as error:
                evidence.record('provisioning', 'FAIL', duration_seconds=round(time.monotonic()-provisioning_started,3), detail='HTTP '+str(error.code))
                # Print only the server's bounded structured progress field.
                try:
                    detail = json.loads(error.read()).get('detail', {})
                    completed = detail.get('completedReleases', []) if isinstance(detail, dict) else []
                    print('API completed releases: ' + ', '.join(x for x in completed if re.fullmatch('[a-z0-9-]+', x)), flush=True)
                except (ValueError, AttributeError):
                    pass
                diagnostic = subprocess.run(kube + ['exec', 'deployment/dbaas-backend', '--', 'helm', 'upgrade', '--install', storage,
                    '/app/helmCharts/minio', '-n', ns, '--dry-run=server'], capture_output=True, text=True, timeout=60)
                # This chart invocation uses external Secrets only. Do not print rendered manifests.
                print('Helm external-Secret dry-run diagnostic: ' + diagnostic.stderr[:2000], flush=True)
                for resource in ('pods', 'jobs'):
                    items = json.loads(run(kube + ['get', resource, '-o', 'json']))['items']
                    for item in items:
                        status = item.get('status', {})
                        reasons = [c.get('state', {}).get('waiting', {}).get('reason', '') for c in status.get('containerStatuses', [])]
                        print(resource + '/' + item['metadata']['name'] + ': ' + status.get('phase', '') + ' ' + ','.join(reasons), flush=True)
                raise
            releases=json.loads(run(['helm','--kubeconfig',kubeconfig,'list','-n',ns,'-o','json']))
            if {x['name'] for x in releases} != {pg,pool,storage} or any(x['status']!='deployed' for x in releases):
                raise RuntimeError('Unexpected Helm release inventory')
            evidence.save('provisioning/releases.json',releases)
            resources=json.loads(run(kube+['get','statefulsets,deployments,services,pvc,serviceaccounts,roles,rolebindings,cronjobs,pdb','-o','json']))['items']
            evidence.save('provisioning/resources.json',[dict(kind=x['kind'],name=x['metadata']['name'],namespace=x['metadata']['namespace'],uid=x['metadata']['uid'],labels=x['metadata'].get('labels',{})) for x in resources])
            evidence.save('provisioning/secret-names.json',run(kube+['get','secrets','-o','name']).splitlines())
            from lifecycle import Runtime
            Runtime(kube, run, evidence, ns, release, directory).execute()
            evidence.summary()
            print('Runtime lifecycle checks completed; see results/runtime/summary.md', flush=True)
        except Exception:
            if evidence.status['connectivity']['status'] != 'PASS':
                evidence.record('connectivity','FAIL',detail='Cluster/API preflight failed; inspect sanitized diagnostics')
            elif evidence.status['provisioning']['status'] != 'PASS':
                evidence.record('provisioning','FAIL',detail='Provisioning failed; partial resources may exist')
            raise
        finally:
            if forward:
                forward.terminate(); forward.wait(timeout=10)
            if creation_started and os.getenv('KEEP_FAILED_CLUSTER') == '1' and sys.exc_info()[0]:
                retained = Path('/tmp') / (name + '.kubeconfig')
                fd = os.open(retained, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'w') as output:
                    output.write(Path(kubeconfig).read_text())
                print('Failed disposable cluster retained for diagnosis: ' + name + '; private kubeconfig: ' + str(retained), flush=True)
            elif creation_started:
                # The random name was checked absent before creating it.
                run(['kind', 'delete', 'cluster', '--name', name], timeout=180)
            if previous is None:
                os.environ.pop('KUBECONFIG', None)
            else:
                os.environ['KUBECONFIG'] = previous

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Do not emit traceback, HTTP bodies, or subprocess output containing Secrets.
        print('NOT YET VALIDATED: smoke stopped (' + type(error).__name__ + '): ' + str(error).splitlines()[0])
        raise SystemExit(1)
