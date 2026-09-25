'use strict';
(() => {
  const root = document.getElementById('domain-nutrition');
  const el = id => document.getElementById(`nutr-${id}`);
  const human = x => String(x).replaceAll('_', ' ');
  const node = (tag, text, cls) => {const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n;};
  const input = (id, label, type = 'number') => `<label>${label}<input id="nutr-${id}" type="${type}" ${type === 'number' ? 'step="any" min="0"' : ''}></label>`;
  const select = (id, label, options) => `<label>${label}<select id="nutr-${id}">${options.map(([v,t]) => `<option value="${v}">${t}</option>`).join('')}</select></label>`;
  const states = [['unknown','Not sure'],['absent','No'],['present','Yes']];
  const markers = [['vitamin_d','Vitamin D'],['b12','Total vitamin B12'],['serum_folate','Serum folate'],['rbc_folate','RBC folate'],['ferritin','Ferritin'],['iron','Iron'],['transferrin','Transferrin'],['tibc','TIBC'],['transferrin_saturation','Transferrin saturation'],['albumin','Albumin'],['prealbumin','Prealbumin'],['total_protein','Total protein'],['hemoglobin','Hemoglobin'],['mcv','MCV'],['rdw','RDW'],['other_cbc','Other CBC result'],['calcium','Calcium'],['magnesium','Magnesium'],['other_chemistry','Other chemistry result']];
  const qualifiers = [['=','Exact (=)'],['<','Less than (<)'],['<=','At most (≤)'],['>','Greater than (>)'],['>=','At least (≥)']];
  const specimens = [['unknown','Not stated'],['serum','Serum'],['plasma','Plasma'],['whole_blood','Whole blood'],['rbc','Red blood cells'],['other','Other']];
  const profiles = [['blank','Manual entry'],['example','Worked example · 75 points + albumin flag'],['plateau','Plateau · 100 points + albumin flag'],['low','Low B12 · 62.5 total'],['high','High ferritin · total withheld'],['bound','Bounded ferritin · total withheld'],['wide-bound','Bounded B12 · total withheld'],['routine','Routine bloodwork only'],['optional','B12 and ferritin only'],['wrong-test','Different vitamin D test'],['missing-date','Missing collection date'],['pregnant','Pregnancy · withheld'],['younger','Age 16 · observations only']];
  const fields = markers.map(([id,label]) => `<fieldset class="organ-measurement"><legend>${label}</legend><div class="grid">${input(id,'Reported value')}${id === 'vitamin_d' ? select(`${id}-unit`,'Unit',[['nmol/L','nmol/L'],['ng/mL','ng/mL']]) : input(`${id}-unit`,'Unit exactly as reported','text')}${select(`${id}-qualifier`,'Result qualifier',qualifiers)}${input(`${id}-report`,'Report identifier','text')}${input(`${id}-date`,'Collection date','date')}${input(`${id}-flag`,'Laboratory flag (optional)','text')}${select(`${id}-specimen`,'Specimen stated on report',specimens)}</div><details><summary>Reference limits and report metadata</summary><p>Copy limits in the same unit as this result. Leave unknown information blank.</p><div class="grid">${input(`${id}-lower`,'Lower reference limit')}${input(`${id}-upper`,'Upper reference limit')}${select(`${id}-reliability`,'Reliability stated by laboratory',[['unknown','Not stated'],['valid','Valid'],['unreliable','Unreliable']])}${input(`${id}-analyte-name`,'Analyte name as reported (optional)','text')}</div><label class="check"><input id="nutr-${id}-applicable" type="checkbox">The report identifies this reference range as applicable to this result.</label></details></fieldset>`);
  root.innerHTML = `<div class="section-head domain-intro"><div><h2>Nutrition markers</h2><p>B12 and iron-marker profile: one provisional score out of 100. Vitamin D is optional.</p></div></div>
    <div class="toolbar">${select('profile','Try a synthetic profile',profiles)}<button id="nutr-load" type="button">Load nutrition profile</button><button id="nutr-reset" class="secondary" type="button">Clear nutrition</button></div><p id="nutr-profile-note">Manual entry. Leave unavailable tests blank.</p>
    <form id="nutr-form"><section class="panel"><h3>Context at collection</h3><div class="grid">${input('age','Age at collection (years)')}${select('pregnancy','Pregnancy status',[['unknown','Not sure / not answered'],['not_pregnant','Not pregnant'],['not_applicable','Not applicable'],['pregnant','Pregnant']])}${input('evaluation-date','Evaluation date','date')}${select('supplementation','Taking vitamin D supplements at collection?',states)}${select('treatment','Receiving vitamin D treatment at collection?',states)}${select('conditions','Known conditions affecting vitamin D interpretation?',states)}${select('iron-confounders','Known inflammation, infection, liver/kidney disease or malignancy affecting ferritin?',states)}${select('iron-treatment','Recent iron treatment or transfusion?',states)}${select('b12-treatment','B12 supplements or treatment at collection?',states)}</div><p>Evaluation date is the date against which collection dates are checked. Points describe the result at collection, not necessarily your health today. This prototype assigns points only to eligible adults; no fasting information is needed.</p></section>
    <section class="panel"><h3>Required B12 and ferritin results</h3><p>Each contributes 50%. Use results from the same report, collection date and specimen type. Confirm applicable laboratory ranges, including upper limits. Missing or uninterpretable core results leave a gap; weights are never redistributed.</p>${fields[1]}${fields[4]}</section><section class="panel"><h3>Optional vitamin D result</h3><p>Enter one chosen result. Keep its own report and collection date; do not average results or add D2 and D3 fractions.</p>${select('analyte','Vitamin D test name on report',[['unknown','Not sure / not stated'],['total_25_hydroxyvitamin_d','Total 25-hydroxyvitamin D · 25(OH)D'],['1_25_dihydroxyvitamin_d','1,25-dihydroxyvitamin D'],['vitamin_d_fraction','D2 or D3 fraction']])}${fields[0]}</section>
    <section class="panel"><details><summary>Other available laboratory results · optional context</summary><p>Enter only results you already have. These observations do not add points or establish nutrient adequacy. No additional testing is implied. Context units are preserved without conversion.</p>${fields.filter((_,i)=>![0,1,4].includes(i)).join('')}</details></section>
    <button id="nutr-calculate" type="submit">Calculate Nutrition score</button><p id="nutr-error" role="alert"></p></form>
    <section class="panel"><h3>Nutrition-marker snapshot</h3><p id="nutr-state" role="status">Add bloodwork or load a synthetic profile.</p><div id="nutr-results"></div></section>
    <section class="panel"><details class="education"><summary>Understand these markers and points</summary><p>Nutrition = 50% B12 points + 50% ferritin points. This experimental laboratory profile does not measure diet quality or overall nutrient adequacy. Both core results must be usable. Values above the applicable lab upper limit are retained for review without points. Known iron confounders or recent iron treatment/transfusion withhold ferritin points. Unknown context remains unknown; missing CRP does not exclude inflammation.</p><h4>Total 25-hydroxyvitamin D</h4><p>This is the vitamin D measurement used by this prototype. Other vitamin D tests are not interchangeable. The point curve is an unvalidated design choice, not a clinical scale or supplementation target. A score of 100 does not establish optimal nutrition.</p><div id="nutr-curve"></div><p>Exact results above 125 nmol/L and all results reported with a bound receive no points. Their results and notices remain visible. Zero is not a valid vitamin D measurement for this curve.</p><h4>Other results</h4><p>B12 and ferritin form the fixed core; folate and other iron-related measurements remain context only. Albumin, prealbumin and blood-cell findings are not converted into nutrition points. Supplied laboratory flags remain visible even when the vitamin D component is unavailable.</p><p>Reference information: <a href="https://ods.od.nih.gov/factsheets/VitaminD-HealthProfessional/" target="_blank" rel="noopener noreferrer">NIH vitamin D fact sheet</a> · <a href="https://www.endocrine.org/clinical-practice-guidelines/vitamin-d-for-prevention-of-disease" target="_blank" rel="noopener noreferrer">Endocrine Society prevention guideline</a>. These sources do not validate this point curve.</p></details></section>`;
  const number = id => el(id).value.trim() === '' ? null : Number(el(id).value);
  let revision = 0;
  function invalidate() {
    window.dispatchEvent(new CustomEvent('scorer-result', {detail: {domain: 'nutrition', result: null}}));revision++; el('results').replaceChildren(); el('state').textContent = 'Inputs changed. Calculate to see current results.'; el('error').textContent = '';}
  function request() {
    const r = {evaluation_date:el('evaluation-date').value,person:{age:number('age'),pregnancy_status:el('pregnancy').value},context:{vitamin_d_supplementation:el('supplementation').value,vitamin_d_treatment:el('treatment').value,relevant_conditions:el('conditions').value,iron_confounders:el('iron-confounders').value,recent_iron_treatment_or_transfusion:el('iron-treatment').value,b12_supplementation_or_treatment:el('b12-treatment').value},observations:{}};
    for (const [id] of markers) {
      if (number(id) === null) continue;
      const o = {value:number(id),unit:el(`${id}-unit`).value.trim(),qualifier:el(`${id}-qualifier`).value,report_id:el(`${id}-report`).value.trim(),reliability:el(`${id}-reliability`).value,observation_id:`manual-nutrition-${id}`,specimen_type:el(`${id}-specimen`).value};
      if (el(`${id}-date`).value) o.specimen_date = el(`${id}-date`).value;
      if (el(`${id}-flag`).value) o.lab_flag = el(`${id}-flag`).value;
      if (el(`${id}-analyte-name`).value) o.analyte_name = el(`${id}-analyte-name`).value;
      if (id === 'vitamin_d') o.analyte = el('analyte').value;
      if (id === 'b12') o.analyte = 'total_vitamin_b12';
      if (id === 'ferritin') o.analyte = 'ferritin';
      for (const [field,suffix] of [['lower_limit','lower'],['upper_limit','upper']]) if (number(`${id}-${suffix}`) !== null) o[field] = number(`${id}-${suffix}`);
      o.reference_range_applicable = el(`${id}-applicable`).checked;
      r.observations[id] = o;
    }
    return r;
  }
  const reasons = {missing_vitamin_d:'No vitamin D result was supplied.',invalid_age:'Enter a valid age at collection.',pediatric_points_not_defined:'Points are not defined below age 18.',pregnancy_outside_scope:'Points are not defined during pregnancy.',pregnancy_status_unknown:'Pregnancy eligibility is unknown.',specimen_date_required:'Collection date is required.',invalid_specimen_date:'Check the collection date.',future_specimen_date:'Collection date is after the evaluation date.',invalid_evaluation_date:'Enter a valid evaluation date.',evaluation_date_required:'Evaluation date is required.',report_id_required:'A report identifier is required.',unsupported_analyte:'Confirm the supported analyte for this marker: total B12, ferritin, or total 25-hydroxyvitamin D.',unsupported_or_unknown_specimen_type:'Serum or plasma must be identified on the selected report.',above_scoring_range:'This result is above the scoring range; it remains visible below.',bounded_result:'Bounded results do not receive exact numerical points.',unreliable_result:'The laboratory marked this result unreliable.'};
  const reasonText = code => reasons[code] || human(code);
  function notices(parent, list) {for (const n of list) parent.append(node('p',typeof n.text === 'string' ? n.text : JSON.stringify(n.text),'notice'));}
  function render(r) {
    window.dispatchEvent(new CustomEvent('scorer-result', {detail: {domain: 'nutrition', result: r}}));
    const out = el('results'), c = r.components.vitamin_d; out.replaceChildren();
    el('state').textContent = `${human(r.status)} · ${r.model_version}`;
    out.append(domainScoreHeader('Nutrition', r.display_score));
    for (const reason of r.reasons) out.append(node('p',human(reason),'notice'));
    for (const marker of ['b12','ferritin']) {const part=r.components[marker];out.append(node('h4',human(marker)),node('p',part.score===null?'Unavailable':`${part.display_score} / 100; 50% weight; ${part.weighted_contribution.toFixed(2)} points contributed`));notices(out,part.notices);}
    out.append(node('h4','Optional vitamin D component'),node('p',c.display_score===null?'Unavailable':`${c.display_score} / 100; excluded from the Nutrition total`));
    if (r.domain_score === null) out.append(node('p','Insufficient information for a nutrition marker score within this prototype’s scope. Available laboratory results are shown below.'));
    for (const reason of c.reasons) out.append(node('p',reasonText(reason),'notice'));
    notices(out,r.notices); notices(out,c.notices);
    out.append(node('h4','Coverage'),node('p',`${r.coverage.scored_component_count} of ${r.coverage.defined_component_count} implemented components scored. This is not a percentage of nutrition measured or a confidence estimate. Both core markers are required for the total.`));
    for (const [key,label] of [['available','Available observations'],['unusable','Observations unavailable for component use'],['missing','Missing component inputs']]) {
      out.append(node('p',`${label}: ${r.coverage[key].map(o => `${human(o.marker)}${o.reasons.length ? ' ('+o.reasons.map(reasonText).join('; ')+')' : ''}`).join(', ') || 'none'}`));
    }
    for (const o of r.observations) {
      const raw = o.observation, card = node('section','', 'component');
      card.append(node('h4',human(o.marker)),node('p',`Reported: ${raw.qualifier || '='} ${raw.value} ${raw.unit}`),node('p',`Test: ${raw.analyte_name || human(raw.analyte || o.marker)} · Specimen: ${human(raw.specimen_type || 'unknown')}`),node('p',`Collection: ${raw.specimen_date || 'unknown'}${o.specimen_age_days === null ? '' : ` (${o.specimen_age_days} days before evaluation)`} · Report: ${raw.report_id || 'unknown'}`));
      if (o.normalized_value !== null) card.append(node('p',`Normalized: ${o.qualifier} ${o.normalized_value} ${o.normalized_unit}`));
      card.append(node('p',`Laboratory comparison: ${human(o.reference_status)}`));
      for (const reason of [...o.errors,...o.metadata_reasons,...o.reliability_reasons]) card.append(node('p',reasonText(reason),'notice'));
      notices(card,o.notices); out.append(card);
    }
    const details = node('details',''); details.append(node('summary','Result JSON'),node('pre',JSON.stringify(r,null,2))); out.append(details);
  }
  let pending = 0;
  async function calculate() {
    const token = ++revision; pending++; el('calculate').disabled = true; el('error').textContent = ''; el('results').replaceChildren(); el('state').textContent = 'Calculating…';
    try {const response = await fetch('/score/nutrition',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request())}); const result = await response.json(); if (!response.ok) throw Error(result.error || 'Calculation failed.'); if (token === revision) render(result);}
    catch (error) {if (token === revision) {el('error').textContent = error.message; el('state').textContent = 'Calculation unavailable. Check the local server and try again.';}}
    finally {pending--; el('calculate').disabled = pending > 0;}
  }
  el('form').addEventListener('submit',event => {event.preventDefault(); calculate();});
  el('form').addEventListener('input',invalidate); el('form').addEventListener('change',invalidate);
  function reset() {el('form').reset(); invalidate(); el('profile-note').textContent = 'Manual entry. Leave unavailable tests blank.';}
  el('reset').addEventListener('click',()=>{reset();el('profile').value='blank';});
  el('load').addEventListener('click',()=>{
    const p = el('profile').value; reset(); if (p === 'blank') return;
    const set = (id,value) => {el(id).value=value;};
    const now = new Date(), today = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
    set('evaluation-date',today); set('age',p === 'younger' ? 16 : 40); set('pregnancy',p === 'pregnant' ? 'pregnant' : 'not_pregnant');
    for (const id of ['supplementation','treatment','conditions','iron-confounders','iron-treatment','b12-treatment']) set(id,'absent');
    set('analyte',p === 'wrong-test' ? '1_25_dihydroxyvitamin_d' : 'total_25_hydroxyvitamin_d');
    if (!['routine','optional'].includes(p)) set('vitamin_d',({plateau:75,low:15,high:126,bound:30,'wide-bound':50})[p] || 40);
    if (p === 'bound') set('vitamin_d-qualifier','<');
    if (p === 'wide-bound') set('vitamin_d-qualifier','>=');
    const contextIds = p === 'routine' ? ['albumin'] : ['b12','ferritin','albumin'];
    if(p !== 'routine'){set('b12',p === 'low'?75:p === 'plateau'?400:150);set('b12-unit','pmol/L');set('b12-lower',150);set('b12-upper',600);el('b12-applicable').checked=true;set('ferritin',100);set('ferritin-unit','ug/L');set('ferritin-lower',15);set('ferritin-upper',300);el('ferritin-applicable').checked=true;}
    if(p === 'high')set('ferritin',301);
    if(p === 'bound')set('ferritin-qualifier','<');
    if(p === 'wide-bound')set('b12-qualifier','>=');
    if (p === 'optional') {set('b12',350);set('b12-unit','pg/mL');set('ferritin',45);set('ferritin-unit','ng/mL');}
    else {set('albumin',30);set('albumin-unit','g/L');set('albumin-flag','Low (synthetic example range)');set('albumin-lower',35);set('albumin-upper',50);el('albumin-applicable').checked=true;}
    for (const id of ['vitamin_d',...contextIds]) {set(`${id}-report`,'synthetic-report');set(`${id}-date`,today);set(`${id}-reliability`,'valid');set(`${id}-specimen`,'serum');}
    if (p === 'missing-date') set('b12-date','');
    el('profile-note').textContent='Synthetic demonstration with illustrative laboratory limits and today’s date. Not a patient record.'; calculate();
  });
  fetch('/model/nutrition').then(r=>{if(!r.ok) throw Error();return r.json();}).then(model=>{
    for(const marker of model.required){const table=node('table','');table.append(node('caption',`${human(marker)} (${model.curves[marker].unit}): 50% weight`));for(const [value,points] of model.curves[marker].anchors){const row=node('tr','');row.append(node('td',String(value)),node('td',`${points} points`));table.append(row);}el('curve').append(table);}el('curve').append(node('p','Linear interpolation between anchors; 100-point plateau only up to the applicable laboratory upper limit. Zero is a curve limit, not an accepted measurement. Curves and weights are provisional design choices.'));
    const ns='http://www.w3.org/2000/svg', svg=document.createElementNS(ns,'svg'); svg.setAttribute('viewBox','0 0 500 190');svg.setAttribute('role','img');svg.setAttribute('aria-label','Experimental vitamin D curve in nmol/L. Above 125 and all bounded results: points withheld.');
    const line=document.createElementNS(ns,'polyline'); line.setAttribute('points',model.points.map(([x,y])=>`${40+x*3.2},${145-y*1.2}`).join(' '));line.setAttribute('fill','none');line.setAttribute('stroke','currentColor');line.setAttribute('stroke-width','3');svg.append(line);
    for (const [x,y,text] of [[5,20,'100'],[10,148,'0'],[40,172,'0'],[126,172,'30'],[192,172,'50'],[390,172,'125 nmol/L']]) {const t=document.createElementNS(ns,'text');t.setAttribute('x',x);t.setAttribute('y',y);t.setAttribute('fill','currentColor');t.textContent=text;svg.append(t);}
    const table=node('table',''), caption=node('caption','Experimental curve examples for eligible exact results'); table.append(caption);
    const head=node('tr','');head.append(node('th','Vitamin D (nmol/L)'),node('th','Points'));table.append(head);
    for (const x of [15,30,40,50,125]) {const row=node('tr','');row.append(node('td',String(x)),node('td',String(model.points.find(p=>p[0]===x)[1])));table.append(row);}
    el('curve').append(svg,table,node('p',`Curve sampled from scoring engine ${model.model_version}. Only eligible exact results receive points. No reward for increasing within the plateau.`));
  }).catch(()=>el('curve').append(node('p','Curve preview unavailable. Results still come from the scoring engine.')));
})();
