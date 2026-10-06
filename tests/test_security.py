"""Offline security contract tests, including the real ASGI middleware stack."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import yaml
from application.app import main as api

ROOT=Path(__file__).resolve().parents[1]
TOKEN='synthetic-token-for-offline-tests-only-32'

async def request(path, token=None, body=None):
    messages=[];sent=False
    data=json.dumps(body or {}).encode()
    async def receive():
        nonlocal sent
        if not sent:
            sent=True
            return {'type':'http.request','body':data,'more_body':False}
        await asyncio.sleep(10)
        return {'type':'http.disconnect'}
    async def send(message):messages.append(message)
    headers=[(b'content-type',b'application/json')]
    if token:headers.append((b'authorization',('Bearer '+token).encode()))
    scope={'type':'http','asgi':{'version':'3.0','spec_version':'2.4'},'http_version':'1.1','scheme':'https','method':'POST',
           'path':path,'raw_path':path.encode(),'query_string':b'','root_path':'','headers':headers,'client':('test',1),'server':('test',443)}
    # Keep a bounded event-loop tick for sandboxed threadpool wakeups.
    async def tick():
        while True:await asyncio.sleep(0.01)
    timer=asyncio.create_task(tick())
    try:
        await asyncio.wait_for(api.app(scope,receive,send),10)
    finally:
        timer.cancel()
    status=next(m['status'] for m in messages if m['type']=='http.response.start')
    content=b''.join(m.get('body',b'') for m in messages if m['type']=='http.response.body')
    return status,content

class SecurityTests(unittest.TestCase):
    def setUp(self):
        env=patch.dict(os.environ,{'DBAAS_API_TOKEN':TOKEN,'DBAAS_ALLOWED_NAMESPACES':'dbaas','DBAAS_ALLOW_INLINE_SECRETS':'false'})
        env.start();self.addCleanup(env.stop)
    def spec(self):return {'project':{'releaseName':'demo'},'postgresql':{}}
    def test_all_api_paths_require_auth(self):
        for path in ['/api/deploy','/api/values/preview','/api/recovery','/api/delete','/api/backup']:
            for token in [None,'wrong']:
                status,body=asyncio.run(request(path,token,self.spec()))
                self.assertEqual(status,401)
                self.assertNotIn(TOKEN.encode(),body)
    def test_missing_auth_configuration_fails_closed(self):
        with patch.dict(os.environ,{'DBAAS_API_TOKEN':''}):
            self.assertEqual(asyncio.run(request('/api/deploy',TOKEN,self.spec()))[0],503)
    def test_valid_auth_and_safe_commands(self):
        calls=[]
        def run(cmd):calls.append(cmd);return 'safe summary'
        with patch.object(api,'run',side_effect=run):
            status,body=asyncio.run(request('/api/deploy',TOKEN,self.spec()))
        self.assertEqual(status,200,body)
        cmd=next(c for c in calls if c[:2]==['helm','upgrade']);self.assertEqual(cmd[:4],['helm','upgrade','--install','demo-patroni'])
        self.assertEqual(cmd[cmd.index('--namespace')+1],'dbaas')
        self.assertNotIn(TOKEN,' '.join(cmd))
    def test_invalid_input_never_echoes_secret(self):
        body=self.spec();body['postgresql']={'superuser':{'username':'u','password':{'secret':'sensitive-marker'}}}
        status,result=asyncio.run(request('/api/deploy',TOKEN,body))
        self.assertEqual(status,422);self.assertNotIn(b'sensitive-marker',result)
        for key,value in [('namespace','../../escape'),('namespace','other')]:
            body=self.spec();body[key]=value
            self.assertIn(asyncio.run(request('/api/deploy',TOKEN,body))[0],[403,422])
    def test_external_secret_values_and_inline_rejection(self):
        body=self.spec();body['project']['enablePgCat']=True;body['existingSecrets']={'postgres':'db-auth','pgcat':'pool-auth'}
        values=api.generated_values(api.DeploySpec(**body))
        self.assertEqual(yaml.safe_load(values['patroni'])['postgres']['existingSecret'],'db-auth')
        self.assertNotIn('PASSWORD', ''.join(values.values()))
        body['postgresql']['superuser']={'username':'u','password':'sensitive-marker'}
        with self.assertRaises(api.HTTPException):api.generated_values(api.DeploySpec(**body))
    def test_unhandled_errors_do_not_escape_to_server_logs(self):
        with patch.object(api,'generated_values',side_effect=RuntimeError('sensitive-exception-marker')):
            status,body=asyncio.run(request('/api/deploy',TOKEN,self.spec()))
        self.assertEqual(status,500)
        self.assertNotIn(b'sensitive-exception-marker',body)

    def test_subprocess_timeout_and_output_redaction(self):
        with patch.object(api.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'sensitive-marker')):
            with self.assertRaises(api.HTTPException) as caught:api.run(['helm','version'])
            self.assertNotIn('sensitive-marker',str(caught.exception.detail))
        with patch.object(api.subprocess,'run',side_effect=subprocess.TimeoutExpired('helm',660)):
            with self.assertRaises(api.HTTPException) as caught:api.run(['helm','version'])
            self.assertEqual(caught.exception.status_code,504)
    def test_tempfiles_unique_private_and_cleaned(self):
        paths=[]
        def run(cmd):
            if cmd[:2]==['kubectl','wait']:return 'ready'
            path=Path(cmd[cmd.index('-f')+1]);paths.append(path)
            self.assertEqual(path.stat().st_mode&0o777,0o600)
            self.assertEqual(path.parent.stat().st_mode&0o777,0o700)
            return 'safe'
        with patch.object(api,'run',side_effect=run):
            api.deploy(api.DeploySpec(**self.spec()));api.deploy(api.DeploySpec(**self.spec()))
        self.assertEqual(len({p.parent for p in paths}),2)
        self.assertTrue(all(not p.exists() for p in paths))
    def test_chart_defaults_reference_external_secrets(self):
        for family in ['helmCharts','application/helmCharts']:
            for chart in ['patroni','minio','pgcat']:
                output=subprocess.check_output(['helm','template','demo',str(ROOT/family/chart),'-n','test-dbaas'],text=True)
                docs=[x for x in yaml.safe_load_all(output) if x]
                self.assertFalse(any(x['kind']=='Secret' for x in docs))
                self.assertIn('secretKeyRef' if chart!='pgcat' else 'secretName',output)
    def test_inline_configmaps_do_not_contain_runtime_credentials(self):
        from test_phase1 import render
        for family in ['helmCharts','application/helmCharts']:
            for component in ['patroni','pgcat','minio']:
                for d in render(f'{family}/{component}'):
                    if d['kind']=='ConfigMap':self.assertNotIn('synthetic-',json.dumps(d))
    def test_recovery_external_secrets_are_checked_before_mutation(self):
        from test_phase1 import RecoveryTests,recovery
        args,fake,calls,pvc,backup=RecoveryTests().fixture()
        def external(cmd):
            output=fake(cmd)
            if cmd[:3]==['helm','get','values']:
                data=json.loads(output);data['security']={'allowInlineSecrets':False};return json.dumps(data)
            if 'get' in cmd and cmd[cmd.index('get')+1]=='statefulset':
                data=json.loads(output)
                data['spec']['template']={'spec':{'volumes':[{'secret':{'secretName':'alpha-wal-g-credentials'}}], 'containers':[{'env':[{'valueFrom':{'secretKeyRef':{'name':'alpha-postgres-credentials'}}}]}]}}
                return json.dumps(data)
            if 'get' in cmd and cmd[cmd.index('get')+1]=='deployment':
                data=json.loads(output);data['spec']={'template':{'spec':{'volumes':[{'secret':{'secretName':'pool-pgcat-config'}}]}}};return json.dumps(data)
            if 'get' in cmd and cmd[cmd.index('get')+1]=='secret':
                name=cmd[cmd.index('get')+2]
                if name in ['alpha-postgres-credentials','pool-pgadmin']:
                    keys=['superuser-username','superuser-password','replication-username','replication-password'] if name.startswith('alpha') else ['pgadmin-password']
                    return json.dumps({'metadata':{'namespace':args.namespace},'data':{k:'c3ludGhldGlj' for k in keys}})
            return output
        with patch.object(recovery,'run',side_effect=external):recovery.recover(args)
        self.assertFalse(any('uninstall' in c or 'delete' in c for c in calls))
        def missing(cmd):
            if 'alpha-postgres-credentials' in cmd:raise RuntimeError('missing Secret')
            return external(cmd)
        args.execute=True;calls.clear()
        with patch.object(recovery,'run',side_effect=missing),self.assertRaises(RuntimeError):recovery.recover(args)
        self.assertFalse(any('uninstall' in c or 'delete' in c for c in calls))

    def test_dockerfile_instruction_and_shell_syntax(self):
        import re
        files=list(ROOT.glob('*/Dockerfile'))+[ROOT/'minio/mc.Dockerfile',ROOT/'tools/kubectl/Dockerfile']
        for path in files:
            text=path.read_text().replace('\\\n',' ')
            for line in text.splitlines():
                if not line.strip() or line.lstrip().startswith('#'):continue
                command,_,value=line.partition(' ')
                self.assertIn(command,{'FROM','RUN','ARG','ENV','WORKDIR','COPY','EXPOSE','ENTRYPOINT','CMD','USER','LABEL','STOPSIGNAL'},str(path))
                if command in {'CMD','ENTRYPOINT'}:self.assertIsInstance(json.loads(value),list)
                if command=='RUN':
                    result=subprocess.run(['sh','-n'],input=value,text=True,capture_output=True)
                    self.assertEqual(result.returncode,0,(str(path),result.stderr))
                if command=='FROM':self.assertIn(':',value.split()[0])
        self.assertNotIn('package-lock.json',(ROOT/'pgcat/.dockerignore').read_text())

    def test_lock_matches_manifest(self):
        package=json.loads((ROOT/'pgcat/package.json').read_text());lock=json.loads((ROOT/'pgcat/package-lock.json').read_text())
        self.assertEqual(package['dependencies'],lock['packages']['']['dependencies'])
        self.assertTrue(all(not v.startswith(('^','~')) for v in package['dependencies'].values()))
        self.assertTrue(all('integrity' in v for k,v in lock['packages'].items() if k))
    def test_preview_redacts_nested_credentials(self):
        from test_phase1 import APITests
        with patch.dict(os.environ,{'DBAAS_ALLOW_INLINE_SECRETS':'true','DBAAS_ALLOWED_NAMESPACES':'test-dbaas'}):
            text=api.preview(APITests().request())
        self.assertNotIn('synthetic-',text)
        self.assertIn('REDACTED',text)

if __name__=='__main__':unittest.main()
