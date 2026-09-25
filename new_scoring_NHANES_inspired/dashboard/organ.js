'use strict';
(() => {
  const root = document.getElementById('domain-organ-stress');
  const el = id => document.getElementById(`organ-${id}`);
  const humanize = value => String(value).replaceAll('_', ' ');
  const node = (tag, value, cls) => {
    const n = document.createElement(tag); n.textContent = value;
    if (cls) n.className = cls;
    return n;
  };
  const input = (id, label, type = 'number', extra = '') => `<label>${label}<input id="organ-${id}" type="${type}" ${type === 'number' ? 'step="any" min="0"' : ''} ${extra}></label>`;
  const select = (id, label, options) => `<label>${label}<select id="organ-${id}">${options.map(([v, t]) => `<option value="${v}">${t}</option>`).join('')}</select></label>`;
  const check = (id, label) => `<label class="check"><input id="organ-${id}" type="checkbox">${label}</label>`;
  const unknown = [['unknown', 'Unknown'], ['no', 'No'], ['yes', 'Yes']];
  const reliability = [['unknown', 'Unknown'], ['valid', 'Laboratory valid'], ['invalid', 'Laboratory invalid']];
  const equations = [['unknown', 'Unknown / not stated'], ['ckd_epi_2021_creatinine', 'CKD-EPI 2021 creatinine'], ['ckd_epi_2021_creatinine_cystatin_c', 'CKD-EPI 2021 creatinine + cystatin C'], ['ckid_u25_creatinine', 'CKiD U25 creatinine']];
  const qualifiers = [['=', 'Exact (=)'], ['>', 'Greater than (>)'], ['>=', 'At least (≥)'], ['<', 'Less than (<)'], ['<=', 'At most (≤)']];
  const core = [['egfr', 'Reported eGFR'], ['creatinine', 'Creatinine'], ['height', 'Height'], ['alt', 'ALT'], ['alp', 'ALP']];
  const optional = [['ast', 'AST'], ['bilirubin', 'Bilirubin'], ['ggt', 'GGT'], ['albumin', 'Albumin'], ['bun', 'BUN'], ['uric_acid', 'Uric acid'], ['uacr', 'Urine albumin-to-creatinine ratio (UACR)'], ['cystatin_c', 'Cystatin C']];
  const names = Object.fromEntries([...core, ...optional]);
  const metadata = id => `<div class="grid">${input(`${id}-report`, 'Report identifier', 'text', 'maxlength="120"')}${input(`${id}-date`, 'Specimen date', 'date')}${select(`${id}-reliability`, 'Laboratory reliability', reliability)}${input(`${id}-flag`, 'Laboratory flag (optional)', 'text', 'maxlength="120"')}</div>`;
  const measurement = (id, label, units, extra = '') => `<fieldset class="organ-measurement" id="organ-${id}-fields"><legend>${label}</legend><div class="grid">${input(id, 'Reported value')}${select(`${id}-unit`, 'Unit', units.map(u => [u, u]))}${extra}</div>${metadata(id)}</fieldset>`;
  root.innerHTML = `
    <div class="section-head domain-intro"><div><h2>Organ stress</h2><p>Liver &amp; kidney v0.2 · One weighted domain score out of 100.</p></div></div>
    <div class="toolbar">${select('profile', 'Try a synthetic profile', [['blank', 'Manual entry'], ['example', 'Worked example · overall 86.3'], ['bound', 'eGFR >60 · range only'], ['plateau', 'eGFR ≥90 · plateau score'], ['missing', 'Missing ALP · partial results'], ['creatinine', 'Calculate from creatinine'], ['pregnant', 'Pregnancy · points withheld'], ['younger', 'Age 16 · U25 estimate only']])}<button id="organ-load" type="button">Load organ profile</button><button id="organ-reset" type="button" class="secondary">Clear organ stress</button></div>
    <p id="organ-profile-note" class="muted">Manual entry. These inputs are independent of metabolism; nothing is saved after a reload.</p>
    <form id="organ-form">
      <section class="panel"><h3>Person and kidney context</h3><div class="grid">
        ${input('age', 'Age at collection (years)')}
        ${select('pregnancy', 'Pregnancy status', [['unknown', 'Unknown / not answered'], ['not_pregnant', 'Not pregnant'], ['not_applicable', 'Not applicable'], ['pregnant', 'Pregnant']])}
        ${select('sex', 'Sex used for creatinine equation', [['unknown', 'Unknown / not provided'], ['female', 'Female'], ['male', 'Male']])}
        ${select('dialysis', 'Dialysis', unknown)}${select('aki', 'Acute kidney injury', unknown)}
      </div><p class="muted">Use the person’s context at collection. Sex is required only when calculating eGFR from creatinine. Under age 18, estimates may be available but points are not defined.</p></section>
      <section class="panel"><h3>Kidney filtration input</h3>
        ${select('route', 'Choose the kidney input', [['reported', 'Use laboratory-reported eGFR'], ['creatinine', 'Calculate eGFR from creatinine']])}
        <p class="muted">The selected kidney input needs a report identifier and specimen date. Enter a bound as a number and qualifier, such as 60 with &gt;.</p>
        ${measurement('egfr', 'Reported eGFR', ['mL/min/1.73m2'], select('egfr-qualifier', 'Result qualifier', qualifiers) + select('egfr-equation', 'Equation stated on report', equations))}
        <fieldset id="organ-creatinine-route"><legend>Creatinine calculation</legend>
          ${select('calculation-equation', 'Calculation equation', equations.filter(([v]) => ['ckd_epi_2021_creatinine', 'ckid_u25_creatinine'].includes(v)))}
          ${measurement('creatinine', 'Creatinine', ['umol/L', 'mg/dL'], select('calibration', 'Creatinine calibration', [['unknown', 'Unknown'], ['idms_traceable', 'IDMS traceable'], ['research_calibrated', 'Research calibrated']]) + input('calibration-provenance', 'Research calibration description', 'text', 'maxlength="500"') + select('assay', 'Assay method', [['unknown', 'Unknown'], ['enzymatic', 'Enzymatic'], ['other', 'Other']]))}
          ${measurement('height', 'Height · required for U25', ['cm', 'm'])}
        </fieldset>
      </section>
      <section class="panel"><h3>Liver enzyme inputs</h3><p class="muted">Copy each report’s reference limits. Use applicability supplied by the laboratory or importer; leave it unconfirmed if unknown. ALT and ALP need matching report identifiers; conflicting dates cannot be combined.</p>
        ${['alt', 'alp'].map(id => measurement(id, id.toUpperCase(), ['U/L', 'IU/L'], input(`${id}-lower`, 'Laboratory lower limit') + input(`${id}-upper`, 'Laboratory upper limit')) + check(`${id}-applicable`, `${id.toUpperCase()} report or importer confirms the reference range applies to this result`)).join('')}
        ${check('snapshot', 'I confirm ALT and ALP are from the same snapshot if a specimen date is missing.')}
      </section>
      <section class="panel"><details><summary>Optional laboratory context · no point contribution</summary><p class="muted">Leave tests you do not have blank. Values and laboratory flags are retained as context; this prototype does not interpret their units or assign them points.</p>
        ${optional.map(([id, label]) => `<fieldset class="organ-measurement"><legend>${label}</legend><div class="grid">${input(id, 'Reported value')}${input(`${id}-unit`, 'Unit exactly as reported', 'text', 'maxlength="80"')}${select(`${id}-qualifier`, 'Result qualifier', qualifiers)}</div>${metadata(id)}</fieldset>`).join('')}
      </details></section>
      <button id="organ-calculate" type="submit">Calculate organ-stress score</button><p id="organ-error" role="alert"></p>
    </form>
    <section class="panel" aria-labelledby="organ-result-heading"><h3 id="organ-result-heading">Organ-stress snapshot</h3><p id="organ-state" role="status">Add bloodwork or load a synthetic profile.</p><div id="organ-results"><p class="empty">Kidney and liver results will appear here.</p></div>
      <details class="education"><summary>How this score works</summary><div class="education-body"><h4>Kidney filtration estimate</h4><p>The existing Python engine uses the reported eGFR or calculates it from creatinine using the selected equation. A bounded report can yield a possible point range instead of an exact score. No midpoint is substituted. High points do not establish absence of kidney disease; urine albumin adds separate context.</p><h4>Liver enzyme pattern</h4><p>ALT and ALP are compared with their applicable laboratory reference intervals. The liver summary weights ALT at 60% and ALP at 40%. The domain total weights eGFR at 50%, ALT at 30% and ALP at 20%. Both markers must be usable and from the same snapshot. A missing or below-range marker can prevent a combined liver score.</p><h4>Coverage and interpretation</h4><p>Missing information is not a zero score. Pregnancy, age and other eligibility rules can withhold points. Laboratory flags remain visible. All three core inputs are required for the domain total, with kidney and liver dates within 90 days. Missing weights are never redistributed. A high average can coexist with an abnormal marker; review individual results. These preliminary model points are not organ-function percentages or disease probabilities.</p></div></details>
    </section>`;

  const number = id => el(id).value.trim() === '' ? null : Number(el(id).value);
  let revision = 0;
  function invalidate() {
    window.dispatchEvent(new CustomEvent('scorer-result', {detail: {domain: 'organ-stress', result: null}}));
    revision++;
    el('state').textContent = 'Inputs changed. Calculate to see current results.';
    el('results').replaceChildren(node('p', 'Results will appear after calculation.', 'empty'));
    el('error').textContent = '';
  }
  function updateRoute() {
    const reported = el('route').value === 'reported';
    el('egfr-fields').hidden = !reported; el('egfr-fields').disabled = !reported;
    el('creatinine-route').hidden = reported; el('creatinine-route').disabled = reported;
    const heightNeeded = !reported && el('calculation-equation').value === 'ckid_u25_creatinine';
    el('height-fields').hidden = !heightNeeded; el('height-fields').disabled = !heightNeeded;
  }
  function observation(id) {
    if (number(id) === null) return null;
    const obs = {value: number(id), unit: el(`${id}-unit`).value, report_id: el(`${id}-report`).value.trim(), reliability: el(`${id}-reliability`).value, source_id: 'manual-dashboard'};
    if (el(`${id}-date`).value) obs.specimen_date = el(`${id}-date`).value;
    if (el(`${id}-flag`).value.trim()) obs.lab_flag = el(`${id}-flag`).value.trim();
    if (el(`${id}-qualifier`)) obs.qualifier = el(`${id}-qualifier`).value;
    return obs;
  }
  function buildRequest() {
    const route = el('route').value;
    const request = {person: {age: number('age'), pregnancy_status: el('pregnancy').value, equation_sex: el('sex').value}, context: {kidney_route: route, dialysis: el('dialysis').value, acute_kidney_injury: el('aki').value, same_snapshot_confirmed: el('snapshot').checked}, observations: {}, optional_observations: {}};
    const keys = route === 'reported' ? ['egfr', 'alt', 'alp'] : ['creatinine', 'alt', 'alp'];
    if (route === 'creatinine') {
      request.context.creatinine_equation = el('calculation-equation').value;
      if (request.context.creatinine_equation === 'ckid_u25_creatinine') keys.push('height');
    }
    for (const id of keys) {
      const obs = observation(id); if (!obs) continue;
      if (id === 'egfr') obs.equation = el('egfr-equation').value;
      if (id === 'creatinine') Object.assign(obs, {calibration: el('calibration').value, calibration_provenance: el('calibration-provenance').value.trim(), assay_method: el('assay').value});
      if (id === 'alt' || id === 'alp') Object.assign(obs, {lower_limit: number(`${id}-lower`), upper_limit: number(`${id}-upper`), reference_range_applicable: el(`${id}-applicable`).checked});
      request.observations[id] = obs;
    }
    for (const [id] of optional) { const obs = observation(id); if (obs) request.optional_observations[id] = obs; }
    return request;
  }
  const reasonText = reason => ({
    matching_report_ids_required: 'Enter a report identifier for both ALT and ALP.',
    report_id_mismatch: 'ALT and ALP report identifiers differ; liver grouping is withheld.',
    same_snapshot_confirmation_required: 'Confirm the liver snapshot when a specimen date is missing.',
    invalid_or_missing_reference_limits: 'Enter valid laboratory lower and upper reference limits.',
    reference_range_applicability_required: 'Confirm that this reference interval applies to this person and assay.',
    pregnancy_eligibility_required: 'Pregnancy status must be known before points can be assigned.',
    pediatric_points_not_defined: 'Points are not defined below age 18; usable estimates remain visible.',
  }[reason] || humanize(reason));
  function render(result) {
    window.dispatchEvent(new CustomEvent('scorer-result', {detail: {domain: 'organ-stress', result: result}}));
    el('state').textContent = `${humanize(result.status)} · ${result.model_version}`;
    const out = el('results'); out.replaceChildren();
    const total = node('article', '', 'card');
    total.append(node('h3', 'Organ-stress score'), node('strong', result.display_score ?? '—'), node('p', result.domain_score === null ? 'Overall score unavailable' : 'out of 100 model points'));
    total.append(node('p', `${result.coverage.scored}/${result.coverage.required} core markers scored · eGFR 50%, ALT 30%, ALP 20%`));
    if (result.review_required) total.append(node('p', 'Abnormal result or laboratory flag present. Review individual markers even when the total is high.', 'notice'));
    for (const reason of result.reasons) total.append(node('p', reasonText(reason), 'notice'));
    out.append(total);
    const cards = node('div', '', 'organ-components');
    for (const [key, title] of [['kidney', 'Kidney filtration estimate'], ['liver', 'Liver marker summary']]) {
      const c = result.components[key], card = node('article', '', 'card');
      card.append(node('h3', title), node('strong', c.display_score ?? '—'), node('p', c.score === null ? 'Point score unavailable' : 'out of 100 model points'), node('p', humanize(c.status)));
      if (key === 'kidney') {
        if (c.egfr !== null) card.append(node('p', `eGFR: ${Number(c.egfr.toFixed(2))} mL/min/1.73m²`));
        if (c.egfr_bound) card.append(node('p', `Reported eGFR: ${c.egfr_bound.qualifier}${c.egfr_bound.value} mL/min/1.73m²`));
        if (c.score_envelope && c.score === null) card.append(node('p', `Possible point range: ${c.score_envelope.join('–')}. No exact score assigned.`, 'notice'));
        if (c.status === 'scored_from_bound') card.append(node('p', 'This bound falls entirely on the model’s constant plateau; the eGFR itself remains a bound.', 'notice'));
        card.append(node('p', `Route: ${humanize(c.route)} · Equation: ${humanize(c.equation ?? 'unknown')}`));
        card.append(node('p', `Selected input: ${names[c.coverage.selected_input]} · ${c.coverage.available ? 'Observation supplied' : 'Observation missing'}`));
      } else card.append(node('p', `Coverage: ${c.coverage.available}/${c.coverage.required} observations supplied · ${c.coverage.scored}/${c.coverage.required} markers scored`));
      for (const reason of c.reasons) card.append(node('p', reasonText(reason), 'notice'));
      for (const [id, marker] of Object.entries(c.markers)) {
        const detail = node('details', ''), raw = marker.observation ?? result.provenance.observations[id];
        detail.append(node('summary', `${names[id] ?? id}: ${marker.display_score ?? humanize(marker.status)}`));
        if (raw && typeof raw === 'object') {
          detail.append(node('p', `Entered: ${raw.qualifier ?? '='} ${raw.value} ${raw.unit ?? ''}`));
          detail.append(node('p', `Report: ${raw.report_id || 'Not provided'} · Specimen: ${raw.specimen_date || 'Not provided'}`));
        }
        if (marker.upper_limit_ratio != null) detail.append(node('p', `Ratio to laboratory upper limit: ${Number(marker.upper_limit_ratio.toFixed(3))}`));
        if (marker.specimen_age_days != null) detail.append(node('p', `Specimen age: ${marker.specimen_age_days} days`));
        for (const reason of marker.reasons) detail.append(node('p', reasonText(reason)));
        card.append(detail);
      }
      cards.append(card);
    }
    out.append(cards, node('h3', 'Interpretation notices'));
    for (const flag of result.flags) out.append(node('p', `${flag.marker ? (names[flag.marker] ?? flag.marker) + ': ' : ''}${flag.text}`, 'notice'));
    const supplied = Object.entries(result.optional_context).filter(([id]) => Object.hasOwn(result.provenance.optional_observations ?? {}, id) || Object.hasOwn(result.provenance.observations ?? {}, id));
    if (supplied.length) {
      out.append(node('h3', 'Optional laboratory context'));
      for (const [id, marker] of supplied) {
        const raw = marker.observation;
        out.append(node('p', `${names[id]}: ${raw.qualifier ?? '='} ${raw.value} ${raw.unit} · ${humanize(marker.status)} · no points`));
        for (const reason of marker.reasons) out.append(node('p', reasonText(reason), 'notice'));
      }
    }
    const details = node('details', '');
    details.append(node('summary', 'Developer details: calculation output (JSON)'), node('pre', JSON.stringify(result, null, 2)));
    out.append(details);
  }
  el('form').addEventListener('input', invalidate);
  el('form').addEventListener('change', () => { updateRoute(); invalidate(); });
  el('form').addEventListener('submit', async event => {
    event.preventDefault(); const current = ++revision;
    el('calculate').disabled = true; el('error').textContent = ''; el('results').replaceChildren(); el('state').textContent = 'Calculating…';
    try {
      const response = await fetch('/score/organ-stress', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(buildRequest())});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Calculation failed.');
      if (current === revision) render(result);
    } catch (error) {
      if (current === revision) { el('error').textContent = `Unable to calculate. Check that the local server is running. ${error.message}`; el('state').textContent = 'Calculation unavailable.'; }
    } finally { el('calculate').disabled = false; }
  });
  function reset() { el('form').reset(); updateRoute(); invalidate(); }
  el('reset').addEventListener('click', () => { reset(); el('profile').value = 'blank'; el('profile-note').textContent = 'Manual entry. Nothing is saved after a reload.'; });
  el('load').addEventListener('click', () => {
    const profile = el('profile').value; reset();
    el('profile-note').textContent = profile === 'blank' ? 'Manual entry. Nothing is saved after a reload.' : 'Synthetic demonstration values and reference intervals. Replace with actual report details for manual entry.';
    if (profile === 'blank') return;
    const today = new Date(), date = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
    const values = {age: 40, pregnancy: 'not_pregnant', sex: 'male', dialysis: 'no', aki: 'no', egfr: 75, 'egfr-equation': 'ckd_epi_2021_creatinine', alt: 80, alp: 80, 'alt-lower': 5, 'alt-upper': 40, 'alp-lower': 40, 'alp-upper': 120};
    if (profile === 'bound') Object.assign(values, {egfr: 60, 'egfr-qualifier': '>'});
    if (profile === 'plateau') Object.assign(values, {egfr: 90, 'egfr-qualifier': '>='});
    if (profile === 'missing') values.alp = '';
    if (profile === 'pregnant') values.pregnancy = 'pregnant';
    if (profile === 'creatinine' || profile === 'younger') Object.assign(values, {route: 'creatinine', creatinine: 88.4, calibration: 'idms_traceable', assay: 'enzymatic'});
    if (profile === 'younger') Object.assign(values, {age: 16, 'calculation-equation': 'ckid_u25_creatinine', height: 170});
    for (const [id, value] of Object.entries(values)) el(id).value = value;
    for (const [id] of core) { el(`${id}-report`).value = 'synthetic-report'; el(`${id}-date`).value = date; el(`${id}-reliability`).value = 'valid'; }
    el('alt-applicable').checked = true; el('alp-applicable').checked = true;
    updateRoute(); el('form').requestSubmit();
  });
  updateRoute();
})();
