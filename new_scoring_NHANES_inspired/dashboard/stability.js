'use strict';
(() => {
  const root = document.getElementById('domain-system-stability');
  const el = id => document.getElementById(`stab-${id}`);
  const human = x => String(x).replaceAll('_', ' ');
  const node = (tag, text, cls) => {const n=document.createElement(tag); n.textContent=text; if(cls)n.className=cls; return n;};
  const input = (id,label,type='number') => `<label>${label}<input id="stab-${id}" type="${type}" ${type==='number'?'step="any"':''}></label>`;
  const select = (id,label,options) => `<label>${label}<select id="stab-${id}">${options.map(([v,t])=>`<option value="${v}">${t}</option>`).join('')}</select></label>`;
  const markers = [['sodium','Sodium'],['potassium','Potassium'],['chloride','Chloride'],['total_co2','Chemistry total CO2'],['total_calcium','Total calcium'],['ionized_calcium','Ionized calcium']];
  const labels = Object.fromEntries(markers);
  const qualifiers = [['=','Exact (=)'],['<','Less than (<)'],['<=','At most (≤)'],['>','Greater than (>)'],['>=','At least (≥)']];
  const profiles = [['blank','Manual entry'],['example','All four within illustrative ranges'],['partial','Missing CO2'],['abnormal','High potassium only'],['critical','Critical report flag with missing value'],['conflict','Report flag conflicts with range'],['bound','Potassium ≤3.5 · uncertain comparison'],['ranges','Missing reference information'],['interference','Potassium affected by interference'],['calcium','Core within ranges + critical calcium flag']];
  const fields = markers.map(([id,label]) => {
    const units=id.includes('calcium')?['mmol/L','mg/dL']:['mmol/L','mEq/L'];
    return `<fieldset class="organ-measurement"><legend>${label}</legend><div class="grid">${input(id,'Reported value')}${select(`${id}-unit`,'Reported unit',units.map(u=>[u,u]))}${select(`${id}-qualifier`,'Result qualifier',qualifiers)}${input(`${id}-lower`,'Lower reference limit')}${input(`${id}-upper`,'Upper reference limit')}${select(`${id}-refunit`,'Reference unit',units.map(u=>[u,u]))}</div><details><summary>Metadata from this laboratory report</summary><p>Copy the report metadata. Applicability is a report/importer assertion about the person, specimen and method; leave it unknown if the report does not establish it.</p><div class="grid">${select(`${id}-applicable`,'Applicable reference interval',[['unknown','Unknown'],['confirmed','Confirmed by report / importer']])}${input(`${id}-provenance`,'Reference interval source','text')}${select(`${id}-reliability`,'Result reliability',[['unknown','Not stated'],['not_flagged','Not flagged by laboratory'],['unreliable','Marked unreliable']])}${input(`${id}-flags`,'Report flags (comma separated)','text')}${input(`${id}-instructions`,'Report instructions / comments','text')}${input(`${id}-interference-note`,'Interference note','text')}</div><p>Flag codes: low, high, within_reference, critical_low, critical_high, critical. Other text remains visible as an unmapped flag.</p><label class="check"><input id="stab-${id}-interference" type="checkbox">The report states interference affects this result.</label></details></fieldset>`;
  });
  root.innerHTML = `<div class="section-head domain-intro"><div><h2>System Stability</h2><p>Electrolyte balance at collection · laboratory reference summary</p></div></div>
    <div class="toolbar">${select('profile','Try a synthetic profile',profiles)}<button id="stab-load" type="button">Load stability profile</button><button id="stab-reset" type="button" class="secondary">Clear stability</button></div><p id="stab-profile-note">Manual entry. Leave unavailable information blank.</p>
    <form id="stab-form"><section class="panel"><h3>One selected collection</h3><p>Enter results from one report and specimen only. Use each result’s actual reference limits. No default ranges are supplied.</p><div class="grid">${input('report','Report identifier','text')}${input('date','Collection date','date')}${input('specimen','Specimen identifier (when supplied)','text')}${select('type','Specimen type',[['unknown','Unknown'],['serum','Serum'],['plasma','Plasma'],['whole_blood','Whole blood']])}${select('assay','CO2 test identity',[['unknown','Unknown'],['chemistry_total_co2','Chemistry total CO2'],['chemistry_bicarbonate','Chemistry bicarbonate (verified alias)'],['blood_gas','Blood-gas bicarbonate / pCO2']])}</div><label class="check"><input id="stab-alias" type="checkbox">The laboratory/importer verified the chemistry bicarbonate alias.</label></section>
    <section class="panel"><h3>Four core electrolytes</h3>${fields.slice(0,4).join('')}</section><section class="panel"><details><summary>Optional calcium results from this collection</summary><p>Total and ionized calcium remain separate. They do not change the four-marker coverage.</p>${fields.slice(4).join('')}</details></section><button id="stab-calculate" type="submit">Review electrolyte results</button><p id="stab-error" role="alert"></p></form>
    <section class="panel"><h3>Electrolyte balance at collection</h3><p id="stab-state" role="status">Add a report or load a synthetic profile.</p><div id="stab-results"></div></section>
    <section class="panel"><details class="education"><summary>Understand this summary</summary><div class="education-body"><p>This panel compares the selected results with their applicable laboratory reference ranges. It does not assign wellness points or measure stability over time. Missing information is not a zero score.</p><p>Sodium, potassium, chloride and chemistry total CO2 form the core panel. CO2 test identity must be preserved; a blood-gas result is not substituted. Total and ionized calcium are optional, distinct observations.</p><p>Range diagrams use the engine’s normalized values and limits. They show position, not severity. Bounded measurements retain their qualifier and are not plotted as exact values. Report warnings remain visible even when a comparison is unavailable.</p><p>Read more: <a href="https://medlineplus.gov/lab-tests/electrolyte-panel/" target="_blank" rel="noopener noreferrer">Electrolyte panel</a> · <a href="https://medlineplus.gov/lab-tests/carbon-dioxide-co2-in-blood/" target="_blank" rel="noopener noreferrer">CO2 testing</a> · <a href="https://medlineplus.gov/ency/article/003477.htm" target="_blank" rel="noopener noreferrer">Calcium testing</a></p></div></details></section>`;
  const number = id => el(id).value.trim()===''?null:Number(el(id).value);
  let revision=0;
  function invalidate(){
    window.dispatchEvent(new CustomEvent('scorer-result', {detail: {domain: 'system-stability', result: null}}));revision++;el('results').replaceChildren();el('error').textContent='';el('state').textContent='Inputs changed. Review to see current results.';}
  function request(){
    const selection={report_id:el('report').value.trim(),specimen_date:el('date').value,observation_ids:{}};
    if(el('specimen').value.trim())selection.specimen_id=el('specimen').value.trim();
    const r={selection,observations:{}};
    for(const [id,label] of markers){
      // Preserve source warnings even when the measurement itself is missing.
      if(number(id)===null && !['lower','upper','flags','instructions','interference-note','provenance'].some(s=>el(`${id}-${s}`).value.trim()) && !el(`${id}-interference`).checked && el(`${id}-reliability`).value!=='unreliable')continue;
      const o={observation_id:`manual-${id}`,raw_analyte_name:label,value:number(id),unit:el(`${id}-unit`).value,qualifier:el(`${id}-qualifier`).value,lower_limit:number(`${id}-lower`),upper_limit:number(`${id}-upper`),reference_unit:el(`${id}-refunit`).value,reference_applicability:el(`${id}-applicable`).value,reference_provenance:el(`${id}-provenance`).value,report_id:selection.report_id,specimen_date:selection.specimen_date,specimen_type:el('type').value,reliability:el(`${id}-reliability`).value,source_flags:el(`${id}-flags`).value.split(',').map(s=>s.trim()).filter(Boolean),report_instructions:el(`${id}-instructions`).value,interference_affects_result:el(`${id}-interference`).checked,interference_note:el(`${id}-interference-note`).value};
      if(selection.specimen_id)o.specimen_id=selection.specimen_id;
      if(id==='total_co2'){o.assay_type=el('assay').value;o.chemistry_alias_verified=el('alias').checked;}
      r.observations[id]=o;selection.observation_ids[id]=o.observation_id;
    }return r;
  }
  const headlines={all_within_reference:'All four electrolyte results are within the reference ranges on this report.',partial:'Some electrolyte results or reference information are missing.',unavailable:'A reference summary is unavailable with the supplied information.',outside_reference:'One or more electrolyte results are outside the laboratory reference range.',source_critical_flag:'The laboratory reported a critical electrolyte flag.',source_flag_conflict:'A laboratory flag conflicts with another flag or the reference comparison.'};
  const explanations={single_collection_not_temporal_stability:'These results describe one collection. They do not measure stability over time.',source_critical_flag:'Critical flag supplied by the laboratory. Follow the report’s instructions.',outside_reference:'Outside the laboratory reference range. Review the flagged result with your healthcare professional.',source_flag_conflict:'Report flag and reference interpretation disagree; both are retained.',unmapped_source_flag:'An unmapped report flag needs review before a complete within-range summary is possible.',specimen_interference:'The report states that specimen interference affects this result.',reliability_unknown:'Result reliability was not stated by the laboratory.'};
  Object.assign(explanations,{
    selected_report_required:'Enter the identifier of the selected laboratory report.',
    invalid_selected_specimen_date:'Enter a valid collection date, no later than today.',
    invalid_specimen_date:'The collection date is missing or invalid.',
    invalid_reference_limits:'Both valid laboratory reference limits are needed for comparison.',
    reference_applicability_unconfirmed:'Applicability of this reference interval has not been confirmed from the report.',
    reference_provenance_required:'The source of the reference interval is missing.',
    unsupported_or_unknown_specimen:'The specimen type is unknown or unsupported for this measurement.',
    chemistry_co2_identity_required:'A confirmed chemistry total CO2 result or verified chemistry bicarbonate alias is needed.',
    invalid_value:'A valid positive measurement is unavailable; report flags are still shown.',
    indeterminate_bound:'The reported bound does not place every possible value in one reference category.',
    unreliable_result:'The report marks this result as unreliable or affected by interference. Comparison is withheld.',
    missing_selected_observation:'No result was supplied for this collection.',
    laboratory_flag:'The laboratory supplied a flag; see the result card below.',
    report_id_required:'The laboratory report identifier is missing.'
  });
  const explain = code => {const parts=code.split(':');return parts.length===2?`${labels[parts[0]]||human(parts[0])}: ${explanations[parts[1]]||human(parts[1])}`:explanations[code]||human(code);};
  function rangeDiagram(o,card){
    if(o.classification_basis!=='derived'||o.qualifier!=='='||!['low','high','within_reference'].includes(o.reference_status))return;
    const lo=o.normalized_lower_limit,hi=o.normalized_upper_limit,v=o.normalized_value;
    const span=hi-lo,min=Math.min(lo-span/2,v),max=Math.max(hi+span/2,v),x=n=>30+(n-min)/(max-min)*440;
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 500 85');svg.setAttribute('role','img');svg.setAttribute('aria-label',`${labels[o.marker]}: ${v} ${o.normalized_unit}, reference ${lo} to ${hi}; ${human(o.reference_status)}.`);
    const add=(tag,attrs)=>{const n=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,v);svg.append(n);return n;};
    add('line',{x1:30,y1:28,x2:470,y2:28,stroke:'currentColor','stroke-width':2});add('line',{x1:x(lo),y1:28,x2:x(hi),y2:28,stroke:'currentColor','stroke-width':12,opacity:0.25});add('circle',{cx:x(v),cy:28,r:6,fill:'currentColor'});
    for(const [value,label] of [[lo,String(lo)],[hi,String(hi)]]){const t=add('text',{x:x(value),y:62,'text-anchor':'middle',fill:'currentColor'});t.textContent=label;}
    const figure=node('figure','','stability-range');figure.append(svg,node('figcaption',`Shaded segment: report reference interval (${o.normalized_unit}). Dot: exact reported result. Position is not severity.`));card.append(figure);
  }
  function render(r){
    window.dispatchEvent(new CustomEvent('scorer-result', {detail: {domain: 'system-stability', result: r}}));
    const out=el('results');out.replaceChildren();el('state').textContent=headlines[r.panel_status]||human(r.panel_status);
    out.append(node('p',`Collection: ${r.selection.specimen_date||'unknown'} · Report: ${r.selection.report_id||'unknown'}`),node('p',`${r.coverage.interpretable_count}/${r.coverage.expected_count} core results interpretable · ${r.coverage.present_count}/4 supplied. Coverage is not confidence. No numerical score is assigned.`));
    // Warnings precede marker cards, including optional calcium warnings.
    for(const n of r.notices)out.append(node('p',`${n.marker?(labels[n.marker]||human(n.marker))+': ':''}${explain(n.code)}${n.selected===false?' (Unselected observation)':''}`,'notice'));
    if(r.coverage.missing_markers.length)out.append(node('p',`Missing: ${r.coverage.missing_markers.map(m=>labels[m]).join(', ')}.`));
    for(const reason of r.reasons)out.append(node('p',explain(reason),'notice'));
    for(const [heading,observations] of [['Core electrolyte results',r.observations],['Optional calcium context',r.context_observations]]){
      if(!observations.length)continue;out.append(node('h4',heading));
      for(const o of observations){const raw=o.observation,card=node('section','','component');
        card.append(node('h4',labels[o.marker]||human(o.marker)),node('p',`Reported: ${raw.qualifier||'='} ${raw.value??'unavailable'} ${raw.unit||''}`),node('p',`Reference comparison: ${human(o.reference_status)} · Basis: ${human(o.classification_basis)}`));
        card.append(node('p',`Report reference: ${raw.lower_limit??'unknown'} to ${raw.upper_limit??'unknown'} ${raw.reference_unit||''}`));
        if(o.normalized_value!==null)card.append(node('p',`Normalized: ${o.qualifier} ${o.normalized_value} ${o.normalized_unit}`));
        if(o.source_flags.length)card.append(node('p',`Laboratory flags: ${o.source_flags.map(human).join(', ')}`,'notice'));
        for(const field of ['report_instructions','interference_note'])if(raw[field])card.append(node('p',raw[field],'notice'));
        for(const reason of [...o.errors,...o.reasons])card.append(node('p',explain(reason),'notice'));
        rangeDiagram(o,card);out.append(card);
      }
    }
    out.append(node('p',`Prototype ${r.model_version}. A missing critical flag does not establish that a result is noncritical.`));
    const detail=node('details','');detail.append(node('summary','Result JSON'),node('pre',JSON.stringify(r,null,2)));out.append(detail);
  }
  async function calculate(){const token=++revision;el('calculate').disabled=true;el('error').textContent='';el('results').replaceChildren();el('state').textContent='Reviewing…';
    try{const response=await fetch('/score/system-stability',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request())});const r=await response.json();if(!response.ok)throw Error(r.error||'Review failed.');if(token===revision)render(r);}
    catch(error){if(token===revision){el('error').textContent=error.message;el('state').textContent='Review unavailable. Check the local server and try again.';}}
    finally{el('calculate').disabled=false;}
  }
  el('form').addEventListener('submit',e=>{e.preventDefault();calculate();});el('form').addEventListener('input',invalidate);el('form').addEventListener('change',invalidate);
  function reset(){el('form').reset();invalidate();el('profile-note').textContent='Manual entry. Leave unavailable information blank.';}
  el('reset').addEventListener('click',()=>{reset();el('profile').value='blank';});
  el('load').addEventListener('click',()=>{const p=el('profile').value;reset();if(p==='blank')return;const set=(id,v)=>{el(id).value=v;};
    const now=new Date();set('date',`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`);set('report','synthetic-report');set('specimen','synthetic-specimen');set('type','serum');set('assay','chemistry_total_co2');
    const fixtures={sodium:[140,135,145],potassium:[4,3.5,5],chloride:[102,98,107],total_co2:[25,22,29]};if(p==='calcium')fixtures.total_calcium=[3,2.1,2.6];
    for(const [id,[v,lo,hi]]of Object.entries(fixtures)){if((p==='partial'&&id==='total_co2')||(p==='abnormal'&&id!=='potassium'))continue;set(id,v);if(p!=='ranges'){set(`${id}-lower`,lo);set(`${id}-upper`,hi);set(`${id}-applicable`,'confirmed');set(`${id}-provenance`,'Synthetic fixture interval, not a patient reference');}set(`${id}-reliability`,'not_flagged');}
    if(p==='abnormal')set('potassium',5.5);if(p==='critical'){set('potassium','');set('potassium-flags','critical_high');set('potassium-instructions','Synthetic report instruction: contact the reporting care team.');}if(p==='conflict')set('potassium-flags','high');if(p==='bound'){set('potassium',3.5);set('potassium-qualifier','<=');}if(p==='interference'){el('potassium-interference').checked=true;set('potassium-interference-note','Synthetic hemolysis flag affecting result.');}if(p==='calcium')set('total_calcium-flags','critical_high');
    el('profile-note').textContent='Synthetic demonstration: illustrative reference intervals and today’s date. Not a patient record or default clinical ranges.';calculate();
  });
})();
