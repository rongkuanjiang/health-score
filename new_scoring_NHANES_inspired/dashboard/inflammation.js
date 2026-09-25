'use strict';
(() => {
  const root = document.getElementById('domain-inflammation');
  const el = id => document.getElementById(`infl-${id}`);
  const human = x => String(x).replaceAll('_', ' ');
  const node = (tag, text, cls) => {const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n;};
  const input = (id, label, type = 'number') => `<label>${label}<input id="infl-${id}" type="${type}" ${type === 'number' ? 'step="any" min="0"' : ''}></label>`;
  const select = (id, label, options) => `<label>${label}<select id="infl-${id}">${options.map(([v,t]) => `<option value="${v}">${t}</option>`).join('')}</select></label>`;
  const states = [['unknown','Not sure'],['absent','No'],['present','Yes']];
  const markers = [['crp','CRP result'], ['wbc','White blood cells'], ['absolute_neutrophils','Neutrophils'], ['absolute_lymphocytes','Lymphocytes'], ['esr','ESR'], ['other_differential_counts','Other differential count']];
  const qualifiers = [['=','Exact (=)'],['<','Less than (<)'],['<=','At most (≤)'],['>','Greater than (>)'],['>=','At least (≥)']];
  const profiles = [['blank','Manual entry'],['example','Worked example · 82.2 domain points'],['low','Low hs-CRP · 98.2 domain points + WBC flag'],['high','Above 10 mg/L · withheld'],['bound','hs-CRP <1 · plateau points'],['uncertain-bound','hs-CRP <2 · withheld'],['cbc','Blood-cell results only'],['standard','Standard CRP · context only'],['unknown','Unknown collection context'],['pregnant','Pregnancy · withheld'],['younger','Age 16 · observations only']];
  const fields = markers.map(([id,label]) => {
    const units = id === 'crp' ? ['mg/L','mg/dL'] : id === 'esr' ? ['mm/h'] : ['10^9/L','10^3/uL','cells/uL', ...(id === 'wbc' ? [] : ['%'])];
    return `<fieldset class="organ-measurement"><legend>${label}</legend><div class="grid">${input(id,'Reported value')}${select(`${id}-unit`,'Unit',units.map(u=>[u,u]))}${select(`${id}-qualifier`,'Result qualifier',qualifiers)}${input(`${id}-report`,'Report identifier','text')}${input(`${id}-date`,'Collection date','date')}${input(`${id}-flag`,'Laboratory flag (optional)','text')}</div><details><summary>Reference limits and report metadata</summary><p>Copy limits in the selected unit. Leave unknown information blank.</p><div class="grid">${input(`${id}-lower`,'Lower reference limit')}${input(`${id}-upper`,'Upper reference limit')}${select(`${id}-reliability`,'Reliability stated by laboratory',[['unknown','Not stated'],['valid','Valid'],['unreliable','Unreliable']])}</div><label class="check"><input id="infl-${id}-applicable" type="checkbox">The report identifies this reference range as applicable to this result.</label></details></fieldset>`;
  });
  root.innerHTML = `<div class="section-head domain-intro"><div><h2>Inflammation markers</h2><p>One baseline profile from hs-CRP (80%) and white blood cells (20%). Higher points mean a more favourable marker profile.</p></div></div>
    <div class="toolbar">${select('profile','Try a synthetic profile',profiles)}<button id="infl-load" type="button">Load inflammation profile</button><button id="infl-reset" class="secondary" type="button">Clear inflammation</button></div><p id="infl-profile-note">Manual entry. Leave unavailable tests blank.</p>
    <form id="infl-form"><section class="panel"><h3>Context at collection</h3><div class="grid">${input('age','Age at collection (years)')}${select('pregnancy','Pregnancy status',[['unknown','Not sure / not answered'],['not_pregnant','Not pregnant'],['not_applicable','Not applicable'],['pregnant','Pregnant']])}${select('acute','Illness, infection, injury, surgery or inflammatory flare around collection?',states)}${select('chronic','Known chronic inflammatory condition?',states)}${select('treatment','Treatment known to affect inflammation?',states)}</div><p>Use what you know about the time of the blood draw. Unknown answers remain unknown. Points are not defined below age 18.</p></section>
    <section class="panel"><h3>Selected CRP result</h3><p>Enter one chosen result from your report. Do not average results from different dates.</p>${select('assay','Test name on report',[['unknown_assay_crp','CRP · sensitivity not stated'],['hs_crp','High-sensitivity CRP (hs-CRP)'],['standard_crp','Standard CRP']])}${fields[0]}</section>
    <section class="panel"><h3>White blood cells · required core marker</h3><p>Use the same collection date as hs-CRP. Enter the applicable lower and upper limits from your report under reference metadata.</p>${fields[1]}</section><section class="panel"><details><summary>Differential counts and ESR · optional context</summary><p>These results do not contribute points. Differential percentages remain percentages.</p>${fields.slice(2).join('')}</details></section>
    <button id="infl-calculate" type="submit">Calculate inflammation score</button><p id="infl-error" role="alert"></p></form>
    <section class="panel"><h3>Inflammation-marker snapshot</h3><p id="infl-state" role="status">Add bloodwork or load a synthetic profile.</p><div id="infl-results"></div></section>
    <section class="panel"><details class="education"><summary>Understand these markers and points</summary><p>This provisional baseline profile combines 80% hs-CRP points and 20% WBC points. Both usable markers from the same collection date are required; missing weights are never redistributed. Acute illness or unknown collection context withholds baseline points. It does not measure all inflammation or diagnose its cause.</p><h4>hs-CRP</h4><p>The point curve is a provisional design, not an endorsed clinical scale. Standard CRP and tests of unknown sensitivity remain context only. Above-range results and uncertain bounds can withhold points. A bounded result is never shown as an exact concentration.</p><div id="infl-curve"></div><h4>Blood cells and ESR</h4><p>WBC earns 100 points within the applicable laboratory range. Below its lower limit, points decline linearly toward zero at zero cells; above its upper limit, points decline to zero at twice that limit. These are provisional modelling choices, not clinical severity thresholds. Differential counts and ESR provide context only. Missing tests are not zero scores and do not imply that additional testing is required.</p><p>Read more: <a href="https://medlineplus.gov/lab-tests/c-reactive-protein-crp-test/" target="_blank" rel="noopener noreferrer">CRP testing</a> · <a href="https://medlineplus.gov/lab-tests/white-blood-count-wbc/" target="_blank" rel="noopener noreferrer">White blood cell counts</a></p></details></section>`;
  const number = id => el(id).value.trim() === '' ? null : Number(el(id).value);
  let revision = 0;
  function invalidate() {
    window.dispatchEvent(new CustomEvent('scorer-result', {detail: {domain: 'inflammation', result: null}}));revision++; el('results').replaceChildren(); el('state').textContent = 'Inputs changed. Calculate to see current results.'; el('error').textContent = '';}
  function request() {
    const r = {person:{age:number('age'),pregnancy_status:el('pregnancy').value},context:{acute_context:el('acute').value,chronic_inflammatory_condition:el('chronic').value,inflammation_affecting_treatment:el('treatment').value},observations:{}};
    for (const [id] of markers) {
      if (number(id) === null) continue;
      const key = id === 'crp' ? el('assay').value : id;
      const o = {value:number(id),unit:el(`${id}-unit`).value,qualifier:el(`${id}-qualifier`).value,report_id:el(`${id}-report`).value.trim(),reliability:el(`${id}-reliability`).value,observation_id:`manual-${id}`};
      if (el(`${id}-date`).value) o.specimen_date = el(`${id}-date`).value;
      if (el(`${id}-flag`).value) o.lab_flag = el(`${id}-flag`).value;
      if (id === 'crp') o.assay_type = key;
      for (const [field,suffix] of [['lower_limit','lower'],['upper_limit','upper']]) if (number(`${id}-${suffix}`) !== null) o[field] = number(`${id}-${suffix}`);
      o.reference_range_applicable = el(`${id}-applicable`).checked;
      r.observations[key] = o;
    }
    return r;
  }
  const reasons = {missing_hs_crp:'No high-sensitivity CRP result was supplied.',invalid_age:'Enter a valid age at collection.',pediatric_points_not_defined:'Points are not defined below age 18.',pregnancy_outside_scope:'Points are not defined during pregnancy.',pregnancy_eligibility_unknown:'Pregnancy eligibility is unknown.',acute_context_present:'Illness, injury, surgery or a flare around collection prevents these baseline-oriented points.',acute_context_unknown:'Collection context is unknown.',specimen_date_required:'Collection date is required.',invalid_specimen_date:'Check the collection date; future dates are not supported.',report_id_required:'A report identifier is required.',unsupported_or_unknown_assay:'A confirmed high-sensitivity CRP test is required.',above_scoring_range:'This result is above the scoring range; it remains visible below.',bounded_result:'This bound does not support one exact point value.',unreliable_result:'The laboratory marked this result unreliable.'};
  const reasonText = code => reasons[code] || human(code);
  function notices(parent, list) {for (const n of list) parent.append(node('p',typeof n.text === 'string' ? n.text : JSON.stringify(n.text),'notice'));}
  function render(r) {
    window.dispatchEvent(new CustomEvent('scorer-result', {detail: {domain: 'inflammation', result: r}}));
    const out = el('results'), c = r.components.hs_crp; out.replaceChildren();
    el('state').textContent = `${human(r.status)} · ${r.model_version}`;
    out.append(domainScoreHeader('Inflammation', r.display_score));
    for (const [marker, weight] of Object.entries(r.weights)) { const part = r.components[marker]; out.append(node('p',`${human(marker)}: ${part.display_score ?? 'Unavailable'} / 100 · ${weight*100}% weight · contribution ${r.weighted_contributions[marker] === null ? 'unavailable' : r.weighted_contributions[marker].toFixed(2)} points`)); }
    out.append(node('p',c.status === 'scored_from_bound' ? 'Points from a reported bound, not an exact concentration.' : 'This result describes the selected measurement at collection.'));
    if (r.domain_score === null) out.append(node('p','Both eligible hs-CRP and WBC results from the same date are needed. Available marker points remain visible.'));
    for (const reason of r.reasons) out.append(node('p',reason.includes(':') ? `${human(reason.split(':')[0])}: ${reasonText(reason.split(':')[1])}` : reasonText(reason),'notice'));
    notices(out,r.notices); notices(out,c.notices);
    out.append(node('h4','Coverage'),node('p',`hs-CRP supplied: ${r.coverage.hs_crp_present ? 'yes' : 'no'}; usable for points: ${r.coverage.hs_crp_usable ? 'yes' : 'no'}. Context markers: ${r.coverage.context_markers_present.map(human).join(', ') || 'none'}. Core points available: ${r.coverage.scored.length}/2. Same-date core results required. This is a limited baseline marker profile.`));
    for (const o of r.observations) {
      const raw = o.observation, card = node('section','', 'component');
      card.append(node('h4',human(o.marker)),node('p',`Reported: ${raw.qualifier || '='} ${raw.value} ${raw.unit}`),node('p',`Collection: ${raw.specimen_date || 'unknown'}${o.specimen_age_days === null ? '' : ` (${o.specimen_age_days} days before evaluation)`} · Report: ${raw.report_id || 'unknown'}`));
      if (o.normalized_value !== null) card.append(node('p',`Normalized: ${o.qualifier} ${o.normalized_value} ${o.normalized_unit}`));
      card.append(node('p',`Laboratory comparison: ${human(o.reference_status)}`));
      for (const reason of [...o.errors,...o.metadata_reasons]) card.append(node('p',reasonText(reason),'notice'));
      notices(card,o.notices); out.append(card);
    }
    const details = node('details',''); details.append(node('summary','Result JSON'),node('pre',JSON.stringify(r,null,2))); out.append(details);
  }
  async function calculate() {
    const token = ++revision; el('calculate').disabled = true; el('error').textContent = ''; el('results').replaceChildren(); el('state').textContent = 'Calculating…';
    try {const response = await fetch('/score/inflammation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request())}); const result = await response.json(); if (!response.ok) throw Error(result.error || 'Calculation failed.'); if (token === revision) render(result);}
    catch (error) {if (token === revision) {el('error').textContent = error.message; el('state').textContent = 'Calculation unavailable. Check the local server and try again.';}}
    finally {el('calculate').disabled = false;}
  }
  el('form').addEventListener('submit',event => {event.preventDefault(); calculate();});
  el('form').addEventListener('input',invalidate); el('form').addEventListener('change',invalidate);
  function reset() {el('form').reset(); invalidate(); el('profile-note').textContent = 'Manual entry. Leave unavailable tests blank.';}
  el('reset').addEventListener('click',()=>{reset();el('profile').value='blank';});
  el('load').addEventListener('click',()=>{
    const p = el('profile').value; reset(); if (p === 'blank') return;
    const set = (id,value) => {el(id).value=value;};
    const now = new Date(), today = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
    set('age',p === 'younger' ? 16 : 40); set('pregnancy',p === 'pregnant' ? 'pregnant' : 'not_pregnant'); set('acute',p === 'unknown' ? 'unknown' : 'absent');set('chronic','absent');set('treatment','absent');set('assay',p === 'standard' ? 'standard_crp' : 'hs_crp');
    if (p !== 'cbc') set('crp',p === 'high' ? 12 : p === 'low' ? 0.5 : p === 'bound' ? 1 : 2);
    if (['bound','uncertain-bound'].includes(p)) set('crp-qualifier','<');
    set('wbc',12); set('wbc-flag','High (synthetic example range)');set('wbc-lower',4);set('wbc-upper',11);el('wbc-applicable').checked=true;
    for (const id of ['crp','wbc']) {set(`${id}-report`,'synthetic-report');set(`${id}-date`,today);set(`${id}-reliability`,'valid');}
    el('profile-note').textContent='Synthetic demonstration with illustrative laboratory limits and today’s date. Not a patient record.'; calculate();
  });
  fetch('/model/inflammation').then(r=>{if(!r.ok) throw Error();return r.json();}).then(model=>{
    const ns='http://www.w3.org/2000/svg', svg=document.createElementNS(ns,'svg'); svg.setAttribute('viewBox','0 0 500 180');svg.setAttribute('role','img');svg.setAttribute('aria-label','Experimental hs-CRP curve: 100 points at 1 mg/L, 80 at 2, 60 at 3, 20 at 10. Above 10, points withheld.');
    const line=document.createElementNS(ns,'polyline'); line.setAttribute('points',model.points.map(([x,y])=>`${40+x*42},${145-y*1.2}`).join(' '));line.setAttribute('fill','none');line.setAttribute('stroke','currentColor');line.setAttribute('stroke-width','3');svg.append(line);
    for (const [x,y,text] of [[5,20,'100'],[10,148,'0'],[40,172,'0 mg/L'],[410,172,'10 mg/L']]) {const t=document.createElementNS(ns,'text');t.setAttribute('x',x);t.setAttribute('y',y);t.setAttribute('fill','currentColor');t.textContent=text;svg.append(t);}
    el('curve').append(svg,node('p',`Curve from scoring engine ${model.model_version}. Only eligible results receive points; above 10 mg/L, points are withheld.`));
  }).catch(()=>el('curve').append(node('p','Curve preview unavailable. Results still come from the scoring engine.')));
})();
