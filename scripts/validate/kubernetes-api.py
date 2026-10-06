import os,json,socket,ssl,urllib.request,urllib.error,subprocess
from pathlib import Path
p=Path('/var/run/secrets/kubernetes.io/serviceaccount');host=os.environ['KUBERNETES_SERVICE_HOST'];port=int(os.environ['KUBERNETES_SERVICE_PORT']);ns=(p/'namespace').read_text().strip()
result={'service_host':host,'service_port':port,'namespace':ns,'credentials':{x:{'exists':(p/x).exists(),'readable':os.access(p/x,os.R_OK)} for x in ['token','ca.crt','namespace']},'environment':{k:os.environ.get(k,'<unset>') if k.lower()=='no_proxy' else bool(os.getenv(k)) for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy','KUBECONFIG']}}
for name in ['kubernetes.default.svc','kubernetes.default.svc.cluster.local',host]:
 r={}
 try:r['dns']=socket.gethostbyname_ex(name)
 except Exception as e:r['dns_error']=str(e)
 try:
  with socket.create_connection((name,port),timeout=5) as s:
   r['tcp']='PASS'
   with ssl.create_default_context(cafile=str(p/'ca.crt')).wrap_socket(s,server_hostname=name) as tls:r['tls']=tls.version()
 except Exception as e:r['tls_error']=str(e)
 for mode in ['environment','direct']:
  try:
   handlers=[urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(p/'ca.crt')))]
   if mode=='direct':handlers.append(urllib.request.ProxyHandler({}))
   req=urllib.request.Request('https://'+name+':'+str(port)+'/version',headers={'Authorization':'Bearer '+(p/'token').read_text().strip()})
   with urllib.request.build_opener(*handlers).open(req,timeout=5) as resp:r[mode]={'status':resp.status,'version':json.load(resp).get('gitVersion')}
  except Exception as e:r[mode]={'error':str(e)}
 result[name]=r
for cmd in [['helm','version','--short'],['helm','list','-n',ns],['kubectl','get','namespace',ns],['kubectl','auth','can-i','create','statefulsets.apps','-n',ns],['helm','template','probe','/app/helmCharts/minio','-n',ns]]:
 try:
  proc=subprocess.run(cmd,text=True,capture_output=True,timeout=20); result[' '.join(cmd)]={'exit':proc.returncode,'stderr':proc.stderr[:1500],'stdout':proc.stdout[:1500] if cmd[1]!='template' else 'rendered manifests omitted'}
 except Exception as e:result[' '.join(cmd)]={'error':str(e)}
print(json.dumps(result,indent=2))
