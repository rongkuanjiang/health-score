/* System Stability DOM checks against the real API, isolated from concurrent domain redesigns. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawn}=require('node:child_process');
const {JSDOM}=(() => { try { return require('jsdom'); } catch { return require('../tmp/dashboard_dom_tests/node_modules/jsdom'); } })();
const server=spawn(process.env.PYTHON_EXE||'python',['-u','-c',"from dashboard_server import Handler, ThreadingHTTPServer; s=ThreadingHTTPServer(('127.0.0.1',0),Handler); print(s.server_port,flush=True); s.serve_forever()"],{cwd:__dirname,stdio:['ignore','pipe','inherit']});
let dom;
const until=async fn=>{const end=Date.now()+10000;while(!fn()){if(Date.now()>end)throw Error('Timed out');await new Promise(r=>setTimeout(r,10));}};
(async()=>{
  const port=await new Promise((resolve,reject)=>{server.stdout.once('data',d=>resolve(Number(String(d).trim())));server.once('error',reject);});
  const base=`http://127.0.0.1:${port}`;
  dom=new JSDOM(fs.readFileSync(path.join(__dirname,'dashboard/index.html'),'utf8'),{url:base,runScripts:'dangerously'});
  const w=dom.window,d=w.document,get=id=>d.getElementById(id),el=id=>get('stab-'+id),errors=[];
  w.addEventListener('error',e=>errors.push(e.error));w.fetch=(url,options)=>fetch(base+url,options);
  for(const file of ['details.js','app.js','organ.js','inflammation.js','stability.js','nutrition.js','domains.js','overview.js']){const script=d.createElement('script');script.textContent=fs.readFileSync(path.join(__dirname,'dashboard',file),'utf8');d.body.append(script);}
  get('person-age').value='42';get('person-pregnancy').value='not_pregnant';get('onboarding-form').requestSubmit();
  assert.equal(el('age').value,'42');assert.equal(el('pregnancy').value,'not_pregnant');
  const result=()=>JSON.parse(el('results').querySelector('pre').textContent);
  const change=id=>el(id).dispatchEvent(new w.Event('change',{bubbles:true}));
  const calc=async()=>{el('form').requestSubmit();await until(()=>!el('calculate').disabled);assert.equal(el('error').textContent,'');return result();};
  const profile=async name=>{el('profile').value=name;el('load').click();await until(()=>!el('calculate').disabled);assert.equal(el('error').textContent,'');return result();};
  const points=()=>get('domain-radar').querySelectorAll('[data-domain="system-stability"][data-score]');
  assert.equal((await profile('example')).domain_score,100);assert.equal(points().length,1);
  assert.match(get('overview-system-stability').textContent,/100.0 \/ 100/);
  el('sodium').value='132.5';el('potassium').value='5.5';change('sodium');assert.equal(points().length,0);
  assert.equal((await calc()).domain_score,70);assert.equal(points()[0].getAttribute('data-score'),'70');
  assert.match(el('results').textContent,/70.0 \/ 100/);assert.match(get('inline-system-stability').textContent,/70.0/);
  for(const name of ['partial','abnormal','critical','bound','ranges','interference']){
    assert.equal((await profile(name)).domain_score,null,name);assert.equal(points().length,0,name);
  }
  assert.equal((await profile('context')).domain_score,100);assert.equal(points().length,1);
  for(const name of ['conflict','calcium']){assert.equal((await profile(name)).domain_score,100);assert.match(get('overview-system-stability').textContent,/Flagged result: review markers/);}
  await profile('example');el('potassium-flags').value='critical_high';change('potassium-flags');await calc();
  assert.match(get('overview-system-stability').textContent,/Laboratory critical flag present/);assert.equal(points().length,1);
  el('pregnancy').value='pregnant';change('pregnancy');assert.equal((await calc()).domain_score,null);assert.equal(points().length,0);
  assert.equal(result().panel_status,'source_critical_flag');
  await profile('example');el('potassium-flags').value='<img src=x onerror=alert(1)>';change('potassium-flags');await calc();
  assert.equal(el('results').querySelector('img,script'),null);assert.match(el('results').textContent,/<img src=x/);
  const realFetch=w.fetch;let release;const hold=new Promise(r=>release=r);w.fetch=async(...args)=>{const response=await realFetch(...args);await hold;return response;};
  el('form').requestSubmit();el('sodium').value='150';change('sodium');release();await until(()=>!el('calculate').disabled);
  assert.equal(el('results').textContent,'');assert.equal(points().length,0);w.fetch=realFetch;
  get('hba1c').value='5.5';el('reset').click();assert.equal(el('sodium').value,'');assert.equal(get('hba1c').value,'5.5');
  assert.equal((await calc()).domain_score,null);assert.equal(points().length,0);assert.deepEqual(errors,[]);
  console.log('PASS: System Stability actual-API DOM checks, shared details, 100/70 totals, one radar point, missing/eligibility gaps, context independence, critical notices, safe text, stale responses and reset isolation.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>{dom?.window.close();server.kill();});
