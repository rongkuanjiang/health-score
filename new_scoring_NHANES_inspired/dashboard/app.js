'use strict';
const $ = id => document.getElementById(id);
// Presentation only: theme changes never clear inputs or recalculate results.
$('theme').addEventListener('change', () => {
  document.documentElement.dataset.theme = $('theme').value;
});
const markers = [['hba1c', 'HbA1c', '%', 'mmol/mol'], ['ldl_c', 'LDL-C', 'mmol/L', 'mg/dL'], ['triglycerides', 'Triglycerides', 'mmol/L', 'mg/dL'], ['hdl_c', 'HDL-C', 'mmol/L', 'mg/dL']];
const names = Object.fromEntries(markers.map(([id, name]) => [id, name]));
const text = (tag, value, className) => { const el = document.createElement(tag); el.textContent = value; if (className) el.className = className; return el; };
const human = value => String(value).replaceAll('_', ' ').replaceAll(':', ': ');
const numeric = id => $(id).value.trim() === '' ? null : Number($(id).value);
const iso = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
let revision = 0;
for (const [value, label] of [['younger','Age 16 · experimental estimate'], ['older','Age 95 · limited age evidence']]) {
  const option = document.createElement('option'); option.value = value; option.textContent = label; $('profile').append(option);
}
for (const [id, name, unit, alternate] of markers) {
  const row = document.createElement('tr');
  row.innerHTML = `<td><label for="${id}">${name}</label></td><td><input id="${id}" type="number" min="0.000001" step="any" placeholder="Not available"></td><td><select id="${id}-unit" aria-label="${name} unit"><option>${unit}</option><option>${alternate}</option></select></td><td><select id="${id}-reliability" aria-label="${name} reliability"><option value="unknown">Unknown</option><option value="valid">Reported valid</option><option value="invalid">Reported invalid</option></select></td>`;
  $('inputs').append(row);
}
function invalidate() {
    window.dispatchEvent(new CustomEvent('scorer-result', {detail: {domain: 'metabolism', result: null}}));
  revision++;
  $('result-state').textContent = 'Inputs changed. Calculate to see the current results.';
  $('results').replaceChildren(text('p', 'Results will appear after calculation.', 'empty'));
  $('error').textContent = '';
}
$('score-form').addEventListener('input', invalidate);
$('score-form').addEventListener('change', invalidate);
function requestFromForm() {
  const request = {person: {age: numeric('age'), pregnancy_status: $('pregnancy').value, sex_reference: $('sex').value}, context: {fasting_status: $('fasting').value, ldl_method: $('ldl-method').value, hba1c_interference: $('interference').value, acute_illness: $('illness').value, medications: $('medications').value, relevant_conditions: $('conditions').value, mobility_limitations: $('mobility').value}, observations: {}};
  if (numeric('hours') !== null) request.context.fasting_hours = numeric('hours');
  if ($('bundle').checked) request.snapshot_id = 'explicit-manual-snapshot';
  for (const [id] of markers) {
    const value = numeric(id);
    if (value === null) continue;
    request.observations[id] = {value, unit: $(id+'-unit').value, reliability: $(id+'-reliability').value, report_id: id === 'hba1c' ? 'selected-hba1c' : $('report').value.trim(), source_id: 'manual-dashboard'};
    const date = $(id === 'hba1c' ? 'a1c-date' : 'lipid-date').value;
    if (date) request.observations[id].specimen_date = date;
  }
  return request;
}
function render(result) {
    window.dispatchEvent(new CustomEvent('scorer-result', {detail: {domain: 'metabolism', result: result}}));
  $('result-state').textContent = `${human(result.status)} · ${result.model_version} · ${result.coverage.scored}/${result.coverage.required} markers scored`;
  const root = $('results'); root.replaceChildren();
  const summary = text('div', '', 'summary');
  const total = text('div', '', 'total');
  total.append(text('p', 'METABOLISM SCORE'), text('div', result.display_score ?? '—', 'big'), text('p', result.score === null ? 'Combined score withheld' : 'out of 100 model points'), text('p', `Latest known specimen: ${result.snapshot_date ?? 'Not available'}`));
  const notices = text('div', '');
  if (result.blocking_reasons.length) {
    notices.append(text('h3', 'What is needed'));
    for (const reason of result.blocking_reasons) notices.append(text('p', human(reason), 'notice'));
  }
  if (result.flags.length) {
    notices.append(text('h3', 'Interpretation notices'));
    for (const flag of result.flags) notices.append(text('p', `${flag.marker ? names[flag.marker] + ': ' : ''}${flag.text}`, 'notice'));
  } else notices.append(text('p', 'No additional marker notices were returned. This does not establish absence of disease.', 'muted'));
  if (result.age_applicability === 'younger_age_extrapolation' || result.age_applicability === 'older_age_limited_evidence') total.append(text('p', 'Experimental age extension · may be inaccurate', 'notice'));
  summary.append(total, notices); root.append(summary);
  const cards = text('div', '', 'cards');
  for (const [id, name] of markers) {
    const marker = result.markers[id], card = text('article', '', 'card');
    card.append(text('h3', name), text('strong', marker.display_score ?? '—'), text('p', marker.original ? `Entered: ${marker.original.value} ${marker.original.unit}` : 'No measurement entered'));
    if (marker.normalized_value !== null) card.append(text('p', `Normalized: ${Number(marker.normalized_value.toFixed(4))} ${marker.normalized_unit}`));
    card.append(text('p', human(marker.status)));
    card.append(markerDetails(id, name, result));
    for (const reason of marker.reasons.slice(1)) card.append(text('p', human(reason)));
    cards.append(card);
  }
  root.append(cards);
  const components = text('div', '', 'components');
  for (const [key, value] of Object.entries(result.components)) components.append(text('span', `${human(key)}: ${value.display_score ?? 'Not available'}`));
  root.append(components);
  if (result.alternative_nonfasting) {
    const alt = result.alternative_nonfasting;
    root.append(text('p', `Unknown fasting status: nonfasting-curve sensitivity gives TG ${alt.triglycerides.toFixed(1)} and metabolism ${alt.metabolism === null ? 'not available' : alt.metabolism.toFixed(1)}. ${alt.interpretation}`, 'notice'));
  }
  root.append(text('p', 'Blood sugar = HbA1c. TG/HDL = their average. Lipid health = average of LDL and TG/HDL. Metabolism = average of blood sugar and lipid health. Missing prerequisites are never reweighted.', 'muted'));
  root.append(calculationDetails(result));
  const details = document.createElement('details');
  details.append(text('summary', 'Developer details: calculation output (JSON)'), text('pre', JSON.stringify(result, null, 2)));
  root.append(details);
}
$('score-form').addEventListener('submit', async event => {
  event.preventDefault();
  const current = ++revision;
  $('calculate').disabled = true; $('error').textContent = '';
  $('result-state').textContent = 'Calculating…';
  $('results').replaceChildren();
  try {
    const response = await fetch('/score', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(requestFromForm())});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Calculation failed.');
    if (current === revision) render(result);
  } catch (error) {
    if (current === revision) { $('error').textContent = 'Unable to calculate. Check that the local server is running. ' + error.message; $('result-state').textContent = 'Calculation unavailable.'; }
  } finally { $('calculate').disabled = false; }
});
function clearForm() { $('score-form').reset(); invalidate(); }
$('load').addEventListener('click', () => {
  clearForm();
  const profile = $('profile').value;
  $('profile-note').textContent = profile === 'blank' ? 'Manual entry. Nothing is saved after a reload.' : 'Synthetic demonstration values. Edit any field and recalculate.';
  if (profile === 'blank') return;
  const values = {age:40, pregnancy:'no', sex:'female', interference:'no', illness:'no', fasting:'fasting', 'ldl-method':'direct', report:'synthetic-report', 'lipid-date':iso(new Date()), 'a1c-date':iso(new Date()), hba1c:5.5, ldl_c:3, triglycerides:1.7, hdl_c:1.3};
  if (profile === 'ldl') Object.assign(values, {hba1c:5, ldl_c:5.2, triglycerides:1, hdl_c:1.5});
  if (profile === 'missing') values.triglycerides = '';
  if (profile === 'hdl') values.hdl_c = 2.6;
  if (profile === 'unknown') values.fasting = 'unknown';
  if (profile === 'pregnant') values.pregnancy = 'yes';
  if (profile === 'younger') values.age = 16;
  if (profile === 'older') values.age = 95;
  for (const [key, value] of Object.entries(values)) $(key).value = value;
  for (const [id] of markers) $(id+'-reliability').value = 'valid';
  $('score-form').requestSubmit();
});
function renderDays() {
  $('step-inputs').replaceChildren();
  const end = new Date($('week-end').value + 'T12:00:00');
  if (Number.isNaN(end.getTime()) || $('week-end').value > iso(new Date())) { $('activity').textContent = 'Choose a valid end date no later than today.'; return; }
  for (let i=6;i>=0;i--) {
    const day = new Date(end); day.setDate(day.getDate()-i);
    const label = text('label', day.toLocaleDateString(undefined, {month:'short',day:'numeric'}));
    const input = document.createElement('input'); input.type='number'; input.min='0'; input.step='1'; input.placeholder='Missing'; input.dataset.date=iso(day); input.setAttribute('aria-label', `Steps ${iso(day)}`); input.addEventListener('input', renderActivity); label.append(input); $('step-inputs').append(label);
  }
  renderActivity();
}
function renderActivity() {
  const inputs = [...$('step-inputs').querySelectorAll('input')];
  const data = inputs.map(input => ({date:input.dataset.date, available:input.value !== '', steps:input.value === '' ? null : Number(input.value), source:$('step-source').value}));
  if (inputs.some(input => input.validity.badInput) || data.some(day => day.available && (!Number.isSafeInteger(day.steps) || day.steps < 0))) { $('activity').textContent = 'Use whole, nonnegative step totals, or leave a day blank.'; return; }
  const available = data.filter(day => day.available);
  const mean = days => days.reduce((sum,day) => sum+day.steps,0)/days.length;
  const root = $('activity'); root.replaceChildren();
  root.append(text('p', `${available.length}/7 days recorded · Average on recorded days: ${available.length ? Math.round(mean(available)).toLocaleString() + ' steps' : 'Not available'}`, 'activity-stats'));
  root.append(text('p', available.length === 7 ? `Last 3 days vs first 3 days: ${Math.round(mean(data.slice(4))-mean(data.slice(0,3))).toLocaleString()} steps/day difference.` : 'Trend requires all seven days. Missing days are excluded from the recorded-day average.', 'muted'));
  if ($('mobility').value === 'yes') root.append(text('p', 'Mobility limitations recorded. Step counts do not capture every form of activity or physical ability.', 'notice'));
  root.append(text('p', 'No activity score or step target is assigned. These entries never alter your bloodwork scores.', 'muted'));
  const details = document.createElement('details'); details.append(text('summary', 'Inspect daily activity records'), text('pre', JSON.stringify(data,null,2))); root.append(details);
}
$('week-end').value=iso(new Date()); $('week-end').max=iso(new Date());
$('week-end').addEventListener('change', renderDays); $('step-source').addEventListener('change', renderDays); $('mobility').addEventListener('change', renderActivity);
$('reset').addEventListener('click', () => { clearForm(); $('profile').value='blank'; $('profile-note').textContent='Enter your own values. Nothing is saved after a reload.'; });
renderDays();
// Explanations remain available before anyone enters health information.
$('learn-score').append(calculationDetails(null));
for (const [id, name] of markers) $('learn-markers').append(markerDetails(id, name, null));
