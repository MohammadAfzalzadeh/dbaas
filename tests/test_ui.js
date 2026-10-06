const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const {generatePgcatConfig} = require('../pgcat/pgcat-config-watcher');

function page(response = {ok: true, release: 'demo', namespace: 'dbaas'}, httpOK = true) {
  const html = fs.readFileSync('application/static/index.html', 'utf8');
  const scripts = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(x => x[1]);
  const elements = new Map(), domListeners = [], calls = [];
  const fields = [ ['releaseName','demo'],['namespace','test-dbaas'],['pgReplicas','2'],['pgStorageCapacity','5'],
    ['superuserUsername','owner'],['superuserPassword','synthetic-admin'],['replicationUsername','replicator'],['replicationPassword','synthetic-replica'],
    ['enableMinio','true'],['enablePgCat','true'],['minioRootUser','root'],['minioRootPassword','synthetic-root'],
    ['minioStorageCapacity','5'],['minioBackupUser','backup'],['minioBackupPassword','synthetic-backup'],['minioBackupBucket','archive'],
    ['enablePITR','false'],['backupSchedule','*/5 * * * *'],['enableLogMonitoring','false'] ];
  const make = id => ({id, value: fields.find(x=>x[0]===id)?.[1] || '', textContent:'',dataset:{}, style:{}, listeners:[],
    classList:{add(){},remove(){},toggle(){}},addEventListener(type,fn){this.listeners.push([type,fn]);},
    getAttribute(){return null;},setAttribute(){},removeAttribute(){},hasAttribute(){return false;},
    querySelectorAll(){return [];},querySelector(){return null;},scrollIntoView(){}});
  const document = {getElementById(id){if(!elements.has(id))elements.set(id,make(id));return elements.get(id);},
    querySelectorAll(){return [];},addEventListener(type,fn){domListeners.push([type,fn]);}};
  const context = vm.createContext({document, URL, console:{log(){},error(){}},
    FormData:class{entries(){return fields.values();}},fetch:async (url,opts)=>{calls.push([url,JSON.parse(opts.body)]);return {ok:httpOK,statusText:'failure',headers:{get:()=> 'application/json'},json:async()=>response};}});
  scripts.forEach(s=>vm.runInContext(s,context));
  document.getElementById('apiToken').value='synthetic-test-token';
  document.getElementById('inlineSecretsMode');
  for(const [type,fn] of domListeners)if(type==='DOMContentLoaded')fn();
  return {elements,calls,context,form:document.getElementById('postgresqlConfigForm')};
}

test('UI initializes once and sends administrative credentials and MinIO values', async ()=>{
  const p=page();p.elements.get('inlineSecretsMode').checked=true;const submit=p.form.listeners.filter(([type])=>type==='submit');assert.equal(submit.length,1);
  await submit[0][1]({preventDefault(){},currentTarget:p.form});
  assert.equal(p.calls.length,1);assert.equal(p.calls[0][0],'/api/deploy');
  const payload=p.calls[0][1];
  assert.equal(payload.postgresql.superuser.username,'owner');
  assert.equal(payload.postgresql.superuser.password,'synthetic-admin');
  assert.equal(payload.postgresql.replication.password,'synthetic-replica');
  assert.equal(payload.minio.backupBucket,'archive');assert.equal(payload.namespace,'test-dbaas');
  assert.match(p.elements.get('output').textContent,/created\/updated/);
});

test('UI shows failure for HTTP errors, explicit failed responses and malformed successes',async()=>{
  for(const [body,httpOK] of [[{detail:{message:'Recovery/provisioning failed',completedReleases:['one']}},false],[{ok:false,detail:'operation failed'},true],['unexpected HTML',true]]){
    const p=page(body,httpOK);await p.context.handleSubmit({preventDefault(){},currentTarget:p.form});
    assert.match(p.elements.get('output').textContent,/❌/);assert.doesNotMatch(p.elements.get('output').textContent,/created\/updated/);
    assert.equal(p.form.dataset.submitting,'false');
  }
});

test('UI waits for response and blocks duplicate pending submits',async()=>{
  const p=page();let resolve;
  p.context.fetch=()=>new Promise(r=>{resolve=r;});
  const pending=p.context.handleSubmit({preventDefault(){},currentTarget:p.form});
  assert.equal(p.elements.get('output').textContent,'Deploying…');
  await p.context.handleSubmit({preventDefault(){},currentTarget:p.form});
  resolve({ok:true,headers:{get:()=> 'application/json'},json:async()=>({ok:true})});
  await pending;assert.match(p.elements.get('output').textContent,/created\/updated/);
});

test('PgCat generator quotes identifiers and credentials and rejects invalid configuration',()=>{
  const input={general:{PGCAT_PORT:5432,PROMETHEUS_EXPORTER_PORT:9930,PGCAT_SUPERUSER_USERNAME:'admin',PGCAT_SUPERUSER_PASSWORD:'synthetic-"-password'},DBS:[{NAME:'db.with.dots',users:[{USER_NAME:'one',PASSWORD:'synthetic',POOL_SIZE:2}],shards:[{MASTER_HOST:'master',MASTER_PORT:5432,INCLUDE_REPLICA:false}]}]};
  const config=generatePgcatConfig(input);assert.match(config,/\[pools\."db.with.dots"\]/);assert.ok(config.includes('synthetic-\\"-password'));
  assert.throws(()=>generatePgcatConfig({...input,DBS:[]}));
  assert.throws(()=>generatePgcatConfig({...input,general:{...input.general,PROMETHEUS_EXPORTER_PORT:'undefined'}}));
});

test('UI default uses Secret references and requires a token',async()=>{
  const p=page();p.elements.get('apiToken').value='';
  await p.context.handleSubmit({preventDefault(){},currentTarget:p.form});
  assert.equal(p.calls.length,0);assert.match(p.elements.get('output').textContent,/token/);
  p.elements.get('apiToken').value='synthetic-token';
  let headers;
  p.context.fetch=async(url,opts)=>{headers=opts.headers;p.calls.push([url,JSON.parse(opts.body)]);return {ok:false,status:401};};
  await p.context.handleSubmit({preventDefault(){},currentTarget:p.form});
  assert.equal(headers.Authorization,'Bearer synthetic-token');
  assert.equal(p.calls[0][1].postgresql.superuser,null);
  assert.deepEqual(Array.from(p.calls[0][1].users),[]);
  assert.match(p.elements.get('output').textContent,/Authentication failed/);
  assert.doesNotMatch(p.elements.get('output').textContent,/synthetic-token/);
});

test('watcher --once writes private TOML and never prints malformed YAML secrets',()=>{
  const os=require('node:os'),path=require('node:path'),cp=require('node:child_process');
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'pgcat-security-'));
  try {
    const input={general:{PGCAT_PORT:5432,PROMETHEUS_EXPORTER_PORT:9930,PGCAT_SUPERUSER_USERNAME:'admin',PGCAT_SUPERUSER_PASSWORD:'synthetic-private'},DBS:[{NAME:'postgres',users:[{USER_NAME:'u',PASSWORD:'synthetic-private',POOL_SIZE:1}],shards:[{MASTER_HOST:'primary',MASTER_PORT:5432,INCLUDE_REPLICA:false}]}]};
    const source=path.join(dir,'config.yaml'),dest=path.join(dir,'pgcat.toml');fs.writeFileSync(source,JSON.stringify(input));
    const env={...process.env,PGCAT_CONFIG_SOURCE:source,PGCAT_CONFIG_DEST:dest,LOG_PATH:dir};
    const run=()=>cp.spawnSync(process.execPath,['pgcat/pgcat-config-watcher.js','--once'],{env,encoding:'utf8'});
    let r=run();assert.equal(r.status,0,r.stderr);assert.equal(fs.statSync(dest).mode&0o777,0o600);
    assert.ok(!r.stdout.includes('synthetic-private'));
    fs.writeFileSync(source,'PASSWORD: [synthetic-private\n');r=run();assert.notEqual(r.status,0);
    assert.ok(!(r.stdout+r.stderr).includes('synthetic-private'));
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
});


test('watcher exits cleanly on SIGTERM and retains a complete configuration', async () => {
  const os = require('node:os'), path = require('node:path');
  const {spawn} = require('node:child_process');
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'watcher-stop-'));
  const source = path.join(root, 'source.yaml'), dest = path.join(root, 'pgcat.toml');
  const input = {general:{PGCAT_PORT:5432,PGCAT_SUPERUSER_USERNAME:'admin',PGCAT_SUPERUSER_PASSWORD:'test-only',ENABLE_PROMETHEUS:true,PROMETHEUS_EXPORTER_PORT:9930},DBS:[{NAME:'postgres',users:[{USER_NAME:'app',PASSWORD:'test-only',POOL_SIZE:2}],shards:[{MASTER_HOST:'primary',MASTER_PORT:5432,INCLUDE_REPLICA:false}]}]};
  fs.writeFileSync(source, JSON.stringify(input));
  const child = spawn(process.execPath, ['pgcat/pgcat-config-watcher.js'], {env:{...process.env,PGCAT_CONFIG_SOURCE:source,PGCAT_CONFIG_DEST:dest,LOG_PATH:root},stdio:'ignore'});
  try {
    await new Promise((resolve,reject) => {
      const deadline=Date.now()+5000;
      const timer=setInterval(() => { if(fs.existsSync(dest)){clearInterval(timer);resolve();} else if(Date.now()>deadline){clearInterval(timer);reject(new Error('watcher not ready'));}},20);
    });
    await new Promise(resolve => setTimeout(resolve,100));
    const exited=new Promise((resolve,reject) => {
      const timer=setTimeout(() => reject(new Error('watcher shutdown timed out')),2000);
      child.once('exit',(code,signal)=>{clearTimeout(timer);resolve({code,signal});});
    });
    child.kill('SIGTERM');
    assert.deepEqual(await exited,{code:0,signal:null});
    assert.equal(fs.readFileSync(dest,'utf8'),generatePgcatConfig(input));
  } finally {child.kill('SIGKILL');fs.rmSync(root,{recursive:true,force:true});}
});
