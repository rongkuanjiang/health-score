/* DOM interaction tests against the real local Python server; no rendering assertions.
   Optional dev dependency: npm install --prefix tmp/dashboard_dom_tests --no-save jsdom
   Run from the workspace root: node new_scoring_NHANES_inspired/test_dashboard_ui.cjs
   Set PYTHON_EXE if the workspace virtual environment is unavailable. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {spawn} = require('node:child_process');
const {JSDOM} = (() => { try { return require('jsdom'); } catch { return require('../tmp/dashboard_dom_tests/node_modules/jsdom'); } })();
const python = process.env.PYTHON_EXE || path.resolve(__dirname, '../.venv/Scripts/python.exe');
const server = spawn(python, ['-u', '-c', "from dashboard_server import Handler, ThreadingHTTPServer; s=ThreadingHTTPServer(('127.0.0.1',0),Handler); print(s.server_port,flush=True); s.serve_forever()"], {cwd: __dirname, stdio: ['ignore', 'pipe', 'inherit']});
let dom;
async function until(fn) {
  const end = Date.now() + 5000;
  while (!fn()) { if (Date.now() > end) throw Error('Timed out waiting for UI'); await new Promise(r => setTimeout(r, 10)); }
}
(async () => {
  const port = await new Promise((resolve, reject) => {server.stdout.once('data', data => resolve(Number(String(data).trim()))); server.once('error', reject); server.once('exit', code => reject(Error(`Server exited: ${code}`)));});
  const base = `http://127.0.0.1:${port}`;
  dom = new JSDOM(fs.readFileSync(path.join(__dirname, 'dashboard/index.html'), 'utf8'), {url: base, runScripts: 'dangerously'});
  const w = dom.window, d = w.document, errors = [], sent = [];
  w.addEventListener('error', event => errors.push(event.error));
  let hold = null;
  w.fetch = async (url, options) => {
    if (options?.body) sent.push({url, body: JSON.parse(options.body)});
    const response = await fetch(base + url, options);
    if (hold && ['/score/organ-stress', '/score/inflammation', '/score/system-stability', '/score/nutrition'].includes(url)) await hold;
    return response;
  };
  for (const file of ['details.js', 'app.js', 'organ.js', 'inflammation.js', 'stability.js', 'nutrition.js', 'domains.js', 'overview.js', 'wearables.js']) {
    const script = d.createElement('script'); script.textContent = fs.readFileSync(path.join(__dirname, 'dashboard', file), 'utf8'); d.body.append(script);
  }
  const get = id => d.getElementById(id), org = id => get(`organ-${id}`);
  const result = () => org('results').textContent;
  async function profile(name) { org('profile').value = name; org('load').click(); await until(() => !org('calculate').disabled); assert.equal(org('error').textContent, ''); }
  async function calculate() { org('form').requestSubmit(); await until(() => !org('calculate').disabled); assert.equal(org('error').textContent, ''); }
  const change = element => element.dispatchEvent(new w.Event('input', {bubbles:true}));
  assert.equal(get('onboarding').hidden, false);
  assert.equal(get('overview').hidden, true);
  assert.equal(get('biomarker-editor').hidden, true);
  assert.equal(get('onboarding-form').checkValidity(), false);
  assert.equal(get('wearable-data').closest('form'),get('onboarding-form'));
  assert.equal(get('domain-metabolism').contains(get('step-inputs')),false);
  const stepInput=()=>get('step-inputs').querySelector('input');
  stepInput().value='0';change(stepInput());
  assert.match(get('activity').textContent,/1\/7 days recorded/);
  get('person-age').value = '42'; get('person-sex').value = 'female'; get('person-pregnancy').value = 'not_pregnant';
  get('onboarding-form').requestSubmit();
  assert.equal(get('onboarding').hidden, true);
  assert.equal(get('overview').hidden, false);
  assert.equal(get('overview-cards').children.length, 5);
  assert.equal(get('domain-radar').querySelectorAll('.radar-grid').length, 5);
  assert.equal(get('domain-radar').querySelectorAll('.radar-point').length, 0);
  for (const id of ['age','organ-age','infl-age','nutr-age']) assert.equal(get(id).value, '42');
  assert.equal(get('pregnancy').value, 'no'); assert.equal(get('organ-pregnancy').value, 'not_pregnant');
  assert.equal(get('organ-sex').value, 'female');
  get('overview-metabolism').querySelector('button').click(); assert.equal(get('biomarker-editor').hidden, false);
  assert.equal(get('domain-nav').children.length, 5);
  assert.equal(get('domain-nav').querySelectorAll('button:disabled').length, 0);
  assert.equal(get('domain-organ-stress').hidden, false);
  get('nav-organ-stress').click();
  assert.equal(get('domain-metabolism').hidden, false);
  await profile('example'); assert.match(result(), /87\.5/); assert.match(result(), /85\.0/); assert.match(get('overview-organ-stress').textContent,/86\.3/); assert.equal(get('domain-radar').querySelectorAll('[data-domain="organ-stress"]').length,1);
  assert.match(result(), /ALT exceeds/);
  get('nav-metabolism').click();
  get('profile').value = 'example'; get('load').click(); await until(() => !get('calculate').disabled);
  assert.match(get('results').textContent, /85\.6/);
  assert.equal(get('domain-radar').querySelectorAll('.radar-profile').length,0);
  assert.equal(get('domain-radar').querySelectorAll('.radar-connection').length,1);
  assert.equal(get('results-view-metabolism').hidden,false);
  get('domain-metabolism').querySelector('[aria-controls="inputs-view-metabolism"]').click();
  assert.equal(get('inputs-view-metabolism').hidden,false);
  assert.equal(get('results-view-metabolism').hidden,true);
  assert.equal(get('hba1c').value,'5.5');
  get('edit-wearable').click();assert.equal(get('wearable-data').open,true);
  stepInput().value='7000';change(stepInput());get('onboarding-form').requestSubmit();
  assert.match(get('wearable-summary-text').textContent,/7,000 steps/);
  assert.match(get('overview-metabolism').textContent,/85\.6/);
  get('edit-wearable').click();get('step-source').value='watch';get('step-source').dispatchEvent(new w.Event('change'));
  assert.equal(stepInput().value,'');get('cancel-person').click();
  assert.equal(get('step-source').value,'manual');assert.equal(stepInput().value,'7000');
  get('reset').click();assert.equal(stepInput().value,'7000');
  get('profile').value='example';get('load').click();await until(()=>!get('calculate').disabled);
  get('nav-organ-stress').click(); assert.equal(org('egfr').value, '75'); assert.match(result(), /87\.5/);
  get('theme').value = 'midnight'; get('theme').dispatchEvent(new w.Event('change')); assert.equal(d.documentElement.dataset.theme, 'midnight');
  await profile('bound'); assert.match(result(), /Possible point range: 75–100/);
  assert.match(get('overview-organ-stress').textContent,/Unavailable/);
  assert.equal(get('domain-radar').querySelectorAll('[data-domain="organ-stress"]').length,0);
  await profile('plateau'); assert.match(result(), /100\.0/); assert.doesNotMatch(result(), /No exact score assigned/);
  await profile('missing'); assert.match(result(), /1\/2 observations supplied/);
  await profile('pregnant'); assert.equal(org('results').querySelectorAll('strong')[0].textContent, '—');
  await profile('creatinine'); assert.equal(sent.at(-1).body.observations.egfr, undefined); assert.match(result(), /eGFR:/);
  await profile('younger'); assert.match(result(), /eGFR:/); assert.match(result(), /Points are not defined below age 18/);
  await profile('example'); org('alt-applicable').checked = false; change(org('alt-applicable')); await calculate(); assert.match(result(), /Confirm that this reference interval/);
  await profile('example'); org('alp-report').value = 'different'; change(org('alp-report')); await calculate(); assert.match(result(), /report identifiers differ/);
  await profile('example'); org('egfr-date').value = ''; change(org('egfr-date')); await calculate(); assert.equal(org('results').querySelector('strong').textContent, '—');
  await profile('example'); org('uacr').value = '0'; org('uacr-unit').value = 'mg/g'; org('uacr-flag').value = '<img src=x onerror=alert(1)>'; change(org('uacr')); await calculate();
  assert.equal(sent.at(-1).body.optional_observations.uacr.value, 0); assert.match(result(), /<img src=x/); assert.equal(org('results').querySelector('img'), null);
  let release; hold = new Promise(resolve => {release = resolve;});
  org('form').requestSubmit(); assert.equal(org('calculate').disabled, true);
  org('alt').value = '90'; change(org('alt')); release(); hold = null;
  await until(() => !org('calculate').disabled); assert.match(result(), /Results will appear after calculation/);
  org('reset').click(); assert.equal(org('egfr').value, ''); assert.equal(get('hba1c').value, '5.5');
  const infl = id => get(`infl-${id}`), inflammationResult = () => infl('results').textContent;
  async function inflammationProfile(name) {infl('profile').value=name;infl('load').click();await until(()=>!infl('calculate').disabled);assert.equal(infl('error').textContent,'');}
  async function inflammationCalculate() {infl('form').requestSubmit();await until(()=>!infl('calculate').disabled);assert.equal(infl('error').textContent,'');}
  get('nav-inflammation').click(); assert.equal(get('domain-organ-stress').hidden,false);
  await inflammationProfile('example');assert.equal(infl('results').querySelector('strong').textContent,'82.2');assert.match(get('overview-inflammation').textContent,/82\.2/);assert.match(get('domain-radar').querySelector('[data-domain="inflammation"]').textContent,/82\.2/);assert.match(inflammationResult(),/High \(synthetic/);
  await inflammationProfile('low');assert.equal(infl('results').querySelector('strong').textContent,'98.2');assert.match(inflammationResult(),/High \(synthetic/);
  await inflammationProfile('bound');assert.equal(infl('results').querySelector('strong').textContent,'98.2');assert.match(inflammationResult(),/Points from a reported bound/);
  for (const name of ['high','uncertain-bound','cbc','standard','unknown','pregnant','younger']) {await inflammationProfile(name);assert.equal(infl('results').querySelector('strong').textContent,'—');}
  await inflammationProfile('example');infl('crp-unit').value='mg/dL';infl('crp').value='0.2';change(infl('crp'));await inflammationCalculate();assert.match(inflammationResult(),/80\.0 \/ 100/);
  infl('wbc').value='0';infl('wbc-flag').value='<img src=x onerror=alert(1)>';change(infl('wbc'));await inflammationCalculate();assert.equal(sent.at(-1).body.observations.wbc.value,0);assert.equal(infl('results').querySelector('img'),null);assert.match(inflammationResult(),/<img src=x/);
  infl('crp-date').value='';change(infl('crp-date'));await inflammationCalculate();assert.match(inflammationResult(),/Collection date is required/);assert.equal(infl('results').querySelector('strong').textContent,'—');
  await inflammationProfile('example');get('nav-metabolism').click();get('nav-inflammation').click();assert.match(inflammationResult(),/80\.0/);
  hold = new Promise(resolve=>{release=resolve;});infl('form').requestSubmit();infl('crp').value='3';change(infl('crp'));release();hold=null;await until(()=>!infl('calculate').disabled);assert.equal(inflammationResult(),'');
  infl('reset').click();assert.equal(infl('crp').value,'');assert.equal(get('hba1c').value,'5.5');
  await until(()=>infl('curve').querySelector('svg'));assert.equal(infl('curve').querySelectorAll('polyline').length,1);
  const stab=id=>get(`stab-${id}`), stabilityResult=()=>stab('results').textContent;
  async function stabilityProfile(name){stab('profile').value=name;stab('load').click();await until(()=>!stab('calculate').disabled);assert.equal(stab('error').textContent,'');}
  async function stabilityCalculate(){stab('form').requestSubmit();await until(()=>!stab('calculate').disabled);assert.equal(stab('error').textContent,'');}
  const stabilityJSON=()=>JSON.parse(stab('results').querySelector('pre').textContent);
  get('nav-system-stability').click();assert.equal(get('domain-inflammation').hidden,false);
  await stabilityProfile('example');assert.match(stab('state').textContent,/All four/);assert.match(stabilityResult(),/4\/4 reference-panel results interpretable/);assert.equal(stabilityJSON().domain_score,100);assert.equal(stab('results').querySelectorAll('svg').length,4);
  assert.equal(get('domain-radar').querySelectorAll('[data-domain="system-stability"][data-score="100"]').length,1);
  assert.match(get('overview-system-stability').textContent,/100.0 \/ 100/);
  stab('sodium').value='132.5';stab('potassium').value='5.5';change(stab('sodium'));await stabilityCalculate();assert.equal(stabilityJSON().domain_score,70);assert.match(get('overview-system-stability').textContent,/70.0 \/ 100/);
  assert.equal(get('domain-radar').querySelector('[data-domain="system-stability"]').getAttribute('data-score'),'70');
  for(const [name,status,count]of [['partial','partial',3],['abnormal','outside_reference',1],['critical','source_critical_flag',3],['conflict','source_flag_conflict',4],['bound','partial',3],['ranges','unavailable',0],['interference','partial',3],['calcium','all_within_reference',4]]){
    await stabilityProfile(name);const r=stabilityJSON();assert.equal(r.panel_status,status,name);assert.equal(r.coverage.interpretable_count,count,name);
    const plotted=get('domain-radar').querySelectorAll('[data-domain="system-stability"][data-score]');
    assert.equal(plotted.length,r.domain_score===null?0:1);
    if(plotted.length)assert.equal(Number(plotted[0].getAttribute('data-score')),r.domain_score);
    if(name==='critical'){assert.equal(sent.at(-1).body.observations.potassium.value,null);assert.match(stabilityResult(),/contact the reporting care team/);assert.match(get('overview-system-stability').textContent,/Laboratory critical flag present/);}
    if(name==='bound'){assert.match(stabilityResult(),/<= 3.5/);assert.equal(stab('results').querySelectorAll('svg').length,3);}
    if(name==='calcium')assert.match(stabilityResult(),/Total calcium: Critical flag/);
  }
  await stabilityProfile('example');stab('potassium-qualifier').value='<';stab('potassium').value='3.5';change(stab('potassium'));await stabilityCalculate();assert.equal(stabilityJSON().panel_status,'outside_reference');
  await stabilityProfile('example');stab('potassium-unit').value='mEq/L';change(stab('potassium-unit'));await stabilityCalculate();assert.equal(stabilityJSON().panel_status,'all_within_reference');
  stab('date').value='';change(stab('date'));await stabilityCalculate();assert.equal(stabilityJSON().coverage.interpretable_count,0);
  await stabilityProfile('example');stab('assay').value='blood_gas';change(stab('assay'));await stabilityCalculate();assert.equal(stabilityJSON().coverage.interpretable_count,3);
  stab('assay').value='chemistry_bicarbonate';stab('alias').checked=true;change(stab('alias'));await stabilityCalculate();assert.equal(stabilityJSON().coverage.interpretable_count,4);
  stab('potassium-flags').value='<img src=x onerror=alert(1)>';stab('potassium-instructions').value='<script>bad()</script>';change(stab('potassium-flags'));await stabilityCalculate();assert.equal(stabilityJSON().panel_status,'partial');assert.match(stabilityResult(),/<img src=x/);assert.equal(stab('results').querySelector('img,script'),null);
  await stabilityProfile('calcium');stab('total_calcium').value='10';stab('total_calcium-unit').value='mg/dL';stab('total_calcium-lower').value='8';stab('total_calcium-upper').value='11';stab('total_calcium-refunit').value='mg/dL';stab('total_calcium-flags').value='';change(stab('total_calcium'));await stabilityCalculate();assert.equal(stabilityJSON().context_observations[0].normalized_value,2.495);assert.equal(stabilityJSON().coverage.interpretable_count,4);
  get('nav-metabolism').click();get('nav-system-stability').click();assert.equal(stab('total_calcium').value,'10');
  hold=new Promise(resolve=>{release=resolve;});stab('form').requestSubmit();stab('sodium').value='150';change(stab('sodium'));release();hold=null;await until(()=>!stab('calculate').disabled);assert.equal(stabilityResult(),'');
  stab('reset').click();assert.equal(stab('sodium').value,'');assert.equal(get('hba1c').value,'5.5');
  assert.equal(get('domain-radar').querySelector('[data-domain="system-stability"]'),null);
  await stabilityCalculate();assert.equal(stabilityJSON().panel_status,'unavailable');assert.equal(stab('results').querySelectorAll('svg').length,0);
  const nutr = id => get(`nutr-${id}`), nutritionResult = () => nutr('results').textContent;
  async function nutritionProfile(name) {nutr('profile').value=name;nutr('load').click();await until(()=>!nutr('calculate').disabled);assert.equal(nutr('error').textContent,'');}
  async function nutritionCalculate() {nutr('form').requestSubmit();await until(()=>!nutr('calculate').disabled);assert.equal(nutr('error').textContent,'');}
  get('nav-nutrition').click();assert.equal(get('domain-system-stability').hidden,false);
  await nutritionProfile('example');assert.match(nutritionResult(),/75\.0 \/ 100/);assert.match(nutritionResult(),/Low \(synthetic/);
  assert.equal(JSON.parse(nutr('results').querySelector('pre').textContent).domain_score,75);
  assert.match(get('overview-nutrition').textContent,/75\.0/); assert.equal(get('domain-radar').querySelector('[data-domain="nutrition"]').getAttribute('data-score'),'75');
  await nutritionProfile('wrong-test');assert.equal(JSON.parse(nutr('results').querySelector('pre').textContent).domain_score,75);
  await nutritionProfile('optional');assert.ok(JSON.parse(nutr('results').querySelector('pre').textContent).domain_score>0);
  await nutritionProfile('plateau');assert.match(nutritionResult(),/100\.0 \/ 100/);assert.match(nutritionResult(),/Low \(synthetic/);
  await nutritionProfile('low');assert.match(nutritionResult(),/25\.0 \/ 100/);
  for (const name of ['high','bound','wide-bound','routine','missing-date','pregnant','younger']) {await nutritionProfile(name);assert.equal(nutr('results').querySelector('strong').textContent,'—');}
  await nutritionProfile('example');nutr('vitamin_d').value='16';nutr('vitamin_d-unit').value='ng/mL';change(nutr('vitamin_d'));await nutritionCalculate();assert.match(nutritionResult(),/75\.0 \/ 100/);
  nutr('albumin').value='0';nutr('albumin-flag').value='<img src=x onerror=alert(1)>';change(nutr('albumin'));await nutritionCalculate();assert.equal(sent.at(-1).body.observations.albumin.value,0);assert.equal(nutr('results').querySelector('img'),null);assert.match(nutritionResult(),/<img src=x/);
  for (const id of ['b12-date','b12-report','evaluation-date']) {await nutritionProfile('example');nutr(id).value='';change(nutr(id));await nutritionCalculate();assert.equal(nutr('results').querySelector('strong').textContent,'—');}
  await nutritionProfile('example');nutr('b12-specimen').value='unknown';change(nutr('b12-specimen'));await nutritionCalculate();assert.equal(nutr('results').querySelector('strong').textContent,'—');
  await nutritionProfile('example');nutr('b12-reliability').value='unreliable';change(nutr('b12-reliability'));await nutritionCalculate();assert.equal(nutr('results').querySelector('strong').textContent,'—');assert.match(nutritionResult(),/Low \(synthetic/);
  await nutritionProfile('example');get('nav-metabolism').click();get('nav-nutrition').click();assert.match(nutritionResult(),/75\.0/);
  hold = new Promise(resolve=>{release=resolve;});nutr('form').requestSubmit();nutr('vitamin_d').value='80';change(nutr('vitamin_d'));release();hold=null;await until(()=>!nutr('calculate').disabled);assert.equal(nutritionResult(),'');assert.equal(get('domain-radar').querySelector('[data-domain="nutrition"]'),null);
  nutr('reset').click();assert.equal(nutr('vitamin_d').value,'');assert.equal(nutr('evaluation-date').value,'');assert.equal(get('hba1c').value,'5.5');
  await until(()=>nutr('curve').querySelector('svg'));assert.equal(nutr('curve').querySelectorAll('polyline').length,1);assert.match(nutr('curve').textContent,/125/);
  get('load-all-demo').click();
  await until(()=>!get('load-all-demo').disabled);
  assert.equal(get('overview').hidden,false);
  assert.equal(get('biomarker-editor').hidden,true);
  assert.match(get('person-summary').textContent,/Demo: Alex, 42, male/);
  for(const prefix of ['', 'organ-', 'infl-', 'nutr-', 'stab-']){
    assert.equal(get(`${prefix}age`).value,'42');
    assert.equal(get(`${prefix}pregnancy`).value,'not_applicable');
    assert.equal(get(`${prefix}profile`).value,'demo');
    assert.match(get(`${prefix}profile-note`).textContent,/not population averages/);
  }
  assert.equal(get('sex').value,'male');assert.equal(org('sex').value,'male');
  assert.equal(org('albumin').value,nutr('albumin').value);
  assert.equal(nutr('calcium').value,stab('total_calcium').value);
  assert.equal(get('report').value,org('alt-report').value);
  assert.equal(org('alt-date').value,infl('wbc-date').value);
  assert.equal(infl('wbc-date').value,nutr('b12-date').value);
  assert.equal(nutr('b12-date').value,stab('date').value);
  assert.equal(infl('wbc-flag').value,'');assert.equal(nutr('albumin-flag').value,'');
  assert.equal(get('hba1c').value,'5.4');assert.equal(infl('wbc').value,'6.4');
  assert.equal(nutr('other_cbc').value,''); // Generic slots have no invented analyte.
  assert.equal(nutr('hemoglobin-specimen').value,'whole_blood');
  assert.equal(nutr('rbc_folate-specimen').value,'rbc');
  assert.equal(get('biomarker-editor').parentElement,get('overview'));
  assert.match(get('dashboard-progress').textContent,/5\/5 domains calculated/);
  for(const domain of ['metabolism','organ-stress','inflammation','nutrition','system-stability']){
    get(`nav-${domain}`).click();
    assert.equal(get(`entry-${domain}`).open,true);
    assert.equal(get(`domain-${domain}`).hidden,false);
    assert.equal(get('overview').hidden,false);
  }
  assert.equal(d.querySelectorAll('.unified-domain[open]').length,1);
  assert.equal(d.querySelectorAll('.unified-domain:not([hidden])').length,1);
  assert.equal(get('dashboard-home').hidden,true);
  get('back-overview').click();
  assert.equal(get('dashboard-home').hidden,false);
  assert.equal(get('biomarker-editor').hidden,true);
  assert.match(get('inline-metabolism').textContent,/86\.4/);
  assert.match(get('inline-nutrition').textContent,/100\.0/);
  assert.match(get('inline-inflammation').textContent,/90\.4/);
  assert.match(get('inline-organ-stress').textContent,/100\.0/);
  get('calculate-all').click();await until(()=>!get('calculate-all').disabled);
  assert.match(get('dashboard-progress').textContent,/5\/5 domains calculated/);
  assert.equal(get('domain-radar').querySelectorAll('.radar-point').length,5);
  assert.equal(get('domain-radar').querySelectorAll('.radar-profile').length,1);
  assert.equal(get('domain-radar').querySelector('.radar-profile').getAttribute('points').split(' ').length,5);
  assert.match(get('radar-status').textContent,/5 numerical points across 5 of 5 domains/);
  assert.equal(get('domain-radar').querySelector('[data-domain="system-stability"]').getAttribute('data-score'),'100');
  w.fetch = async () => {throw Error('Synthetic connection failure');};
  nutr('profile').value='example';nutr('load').click();await until(()=>!nutr('calculate').disabled);assert.match(nutr('error').textContent,/Synthetic connection failure/);
  stab('profile').value='example';stab('load').click();await until(()=>!stab('calculate').disabled);assert.match(stab('error').textContent,/Synthetic connection failure/);
  infl('profile').value='example';infl('load').click();await until(()=>!infl('calculate').disabled);assert.match(infl('error').textContent,/Synthetic connection failure/);
  await profile('example').catch(error => assert.match(error.message, /Synthetic connection failure/));
  assert.match(org('error').textContent, /Synthetic connection failure/);
  get('back-overview').click();assert.equal(get('overview').hidden,false);
  get('edit-person').click();get('person-age').value='51';get('person-pregnancy').value='pregnant';get('onboarding-form').requestSubmit();
  assert.equal(get('pregnancy').value,'yes');assert.equal(get('nutr-pregnancy').value,'pregnant');
  assert.equal(get('stab-age').value,'51');assert.equal(get('stab-pregnancy').value,'pregnant');
  assert.equal(get('domain-radar').querySelectorAll('.radar-point').length,0);
  assert.equal(get('domain-radar').querySelectorAll('.radar-profile,.radar-connection').length,0);
  get('edit-person').click();get('person-age').value='99';get('cancel-person').click();assert.equal(get('person-age').value,'51');
  // Wearable records never call scoring endpoints or replace laboratory results.
  assert.equal(get('wear-view-trends').hidden,false);
  assert.equal(get('wear-view-entry').hidden,true);
  assert.equal(get('wear-view-log').hidden,true);
  get('wear-view-entry-button').click();
  assert.equal(get('wear-view-trends').hidden,true);
  assert.equal(get('wear-view-entry').hidden,false);
  get('wear-source').value='Unsaved device';
  get('wear-view-log-button').click();
  assert.equal(get('wear-view-entry').hidden,true);
  assert.equal(get('wear-view-log').hidden,false);
  get('wear-view-entry-button').click();
  assert.equal(get('wear-source').value,'Unsaved device');
  const sentBefore=sent.length, radarBefore=get('domain-radar').innerHTML;
  get('wear-source').value='<watch>';get('wear-steps').value='0';get('wear-sleep').value='7.5';
  get('wear-ecg').value='Inconclusive';get('wear-time').value='09:15';get('wear-ecg-hr').value='68';
  get('wear-note').value='<img src=x onerror=alert(1)>';
  get('wear-form').requestSubmit();
  assert.match(get('wear-save-status').textContent,/saved/);
  assert.match(get('wear-log').textContent,/Inconclusive/);
  assert.equal(get('wear-log').querySelector('img'),null);
  assert.match(get('wear-cards').children[1].textContent,/7.5/);
  const savedLog=get('wear-log').textContent;
  get('wear-demo').click();assert.match(get('wear-mode').textContent,/Fictional/);
  assert.match(get('wear-coverage').textContent,/26\/30/);
  assert.equal(get('wear-chart').querySelectorAll('.wear-point').length,26);
  assert.equal(get('wear-chart').querySelectorAll('.wear-line').length,22);
  get('wear-demo').click();assert.equal(get('wear-log').textContent,savedLog);
  get('wear-metric').value='sleep';get('wear-metric').dispatchEvent(new w.Event('change'));
  assert.match(get('wear-coverage').textContent,/1\/30/);
  get('wear-sleep').value='25';assert.equal(get('wear-form').checkValidity(),false);
  get('wear-sleep').value='7.5';
  get('wear-delete').click();assert.doesNotMatch(get('wear-log').textContent,/Inconclusive/);
  assert.equal(sent.length,sentBefore);assert.equal(get('domain-radar').innerHTML,radarBefore);
  assert.deepEqual(errors, []);
  console.log('PASS: unified dashboard, inline domains, calculate-all, full demo, onboarding, shared details, five-domain overview, radar points and gaps, critical notices, navigation, profiles, bounds, safe text, stale responses, reset and connection errors.');
})().catch(error => {console.error(error); process.exitCode = 1;}).finally(() => {dom?.window.close(); server.kill();});
