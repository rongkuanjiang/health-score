'use strict';
// Educational content is separate from the calculation; chart data comes from Python.
const markerEducation = {
  hba1c: {
    meaning: 'HbA1c measures how much glucose is attached to hemoglobin, a protein in red blood cells. It reflects average blood sugar over roughly the past three months.',
    context: 'You do not need to fast for HbA1c itself. Some blood conditions or changes in red blood cell lifespan can affect the result. The score cannot determine whether those circumstances apply to you.',
    model: 'This prototype gives 100 points from 4% to 5%, then fewer points as HbA1c rises. Below 4% it withholds points. Above 10%, points halve for each additional 2 percentage points. These are model choices, not treatment targets.',
    sources: [['NIDDK: understanding the A1C test', 'https://www.niddk.nih.gov/health-information/diagnostic-tests/a1c-test']]
  },
  ldl_c: {
    meaning: 'LDL-C measures cholesterol carried in low-density lipoproteins. Excess LDL cholesterol can contribute to plaque buildup in arteries over time.',
    context: 'A suitable LDL goal depends on your health history and overall cardiovascular risk. LDL may be measured directly or calculated by the lab; high triglycerides can affect some calculations.',
    model: 'Positive values up to 2 mmol/L receive 100 points. Points decrease above that level; above 7 mmol/L they halve for each additional 2 mmol/L. The plateau is a prototype choice, not your personal LDL goal.',
    sources: [['NHLBI: blood cholesterol explained', 'https://www.nhlbi.nih.gov/health/blood-cholesterol'], ['Canadian Cardiovascular Society: adult lipid guidance', 'https://ccs.ca/guideline/2021-lipids/chapter-3-overview-of-the-management-of-dyslipidemia-in-primary-prevention/']]
  },
  triglycerides: {
    meaning: 'Triglycerides are a type of fat in your blood. Your body uses them for energy. Eating before a blood test can affect the measurement.',
    context: 'Fasting and nonfasting results use different reference points. Very high results need individual attention even when the combined score looks high. This marker alone does not diagnose insulin resistance.',
    model: 'Positive values up to 1 mmol/L receive 100 points. The fasting curve reaches 80 points at 1.7 mmol/L; the nonfasting curve at 2.0 mmol/L. Unknown fasting uses the fasting curve and shows the alternative. Above 10 mmol/L, points halve every additional 5 mmol/L.',
    sources: [['NHLBI: understanding triglycerides', 'https://www.nhlbi.nih.gov/health/high-blood-triglycerides'], ['Canadian Cardiovascular Society: lipid measurement limitations', 'https://ccs.ca/guideline/2021-lipids/chapter-5-pico-questions-evidence-review-and-new-recommendations/']]
  },
  hdl_c: {
    meaning: 'HDL-C measures cholesterol carried in high-density lipoproteins. HDL helps carry cholesterol back to the liver, where it can be removed from the body.',
    context: 'A high HDL result does not cancel out another concerning result. Very high HDL is not necessarily more protective; this prototype does not assign points in that region.',
    model: 'Points rise to 100 at 1.5 mmol/L, stay at 100 below 2.5 mmol/L, and are withheld at 2.5 mmol/L or above. Below 0.5 mmol/L, points follow a squared curve. These boundaries are provisional, not universal clinical cutoffs.',
    sources: [['NHLBI: blood cholesterol explained', 'https://www.nhlbi.nih.gov/health/blood-cholesterol'], ['Original study: extreme HDL and mortality (2017)', 'https://pubmed.ncbi.nlm.nih.gov/28419274/']]
  }
};
let explanationModel;
function getExplanationModel() {
  if (!explanationModel) explanationModel = fetch('/model').then(response => {
    if (!response.ok) throw new Error('Model data unavailable');
    return response.json();
  }).catch(error => { explanationModel = null; throw error; });
  return explanationModel;
}
function educationalText(tag, value, className) {
  const el = document.createElement(tag); el.textContent = value;
  if (className) el.className = className;
  return el;
}
function referenceLinks(sources) {
  const list = document.createElement('ul'); list.className = 'reference-links';
  for (const [label, url] of sources) {
    const item = document.createElement('li'), link = document.createElement('a');
    link.href = url; link.textContent = label; link.target = '_blank'; link.rel = 'noopener noreferrer';
    item.append(link); list.append(item);
  }
  return list;
}
function curveGraphic(id, name, curve, marker, fasting) {
  const figure = document.createElement('figure'); figure.className = 'curve-figure';
  const ns = 'http://www.w3.org/2000/svg';
  const node = (name, attrs, value) => {
    const el = document.createElementNS(ns, name);
    for (const [key, val] of Object.entries(attrs)) el.setAttribute(key, val);
    if (value !== undefined) el.textContent = value;
    return el;
  };
  const svg = node('svg', {viewBox:'0 0 520 255', role:'img', 'aria-label':`${name}: provisional score versus measurement; equivalent values are in the table below.`});
  const points = id === 'triglycerides' && fasting === 'nonfasting' ? curve.nonfasting_points : curve.points;
  const min = points[0][0], max = id === 'hdl_c' ? 2.5 : points.at(-1)[0];
  const x = value => 48 + (value-min)/(max-min)*446, y = value => 207-value*1.65;
  for (const score of [0, 25, 50, 75, 100]) {
    svg.append(node('line', {x1:48, x2:494, y1:y(score), y2:y(score), class:'chart-grid'}));
    svg.append(node('text', {x:37, y:y(score)+4, 'text-anchor':'end', class:'chart-label'}, score));
  }
  svg.append(node('text', {x:48,y:20,class:'chart-label'}, 'Model points'));
  const path = values => values.map(([a,b],i) => `${i?'L':'M'}${x(a)},${y(b)}`).join(' ');
  svg.append(node('path', {d:path(points),class:'chart-curve'}));
  if (id === 'triglycerides' && fasting === 'unknown') svg.append(node('path', {d:path(curve.nonfasting_points),class:'chart-alternative'}));
  for (const value of [min, (min+max)/2, max]) svg.append(node('text', {x:x(value),y:228,'text-anchor':'middle',class:'chart-label'}, Number(value.toFixed(2))));
  svg.append(node('text', {x:270,y:249,'text-anchor':'middle',class:'chart-label'}, `${name} (${curve.unit})`));
  let position = 'Enter bloodwork and calculate to see your position on this curve.';
  if (marker?.normalized_value != null) {
    const value = marker.normalized_value;
    position = marker.score === null ? 'Your result is not scored. See the explanation beside your result.' : value < min || value > max ? 'Your measurement is beyond the displayed chart range; its calculated score is still shown on your card.' : 'The outlined dot marks your measurement and its score.';
    if (marker.score !== null && value >= min && value <= max) svg.append(node('circle', {cx:x(value),cy:y(marker.score),r:6,class:'chart-position'}));
  }
  figure.append(svg, educationalText('figcaption', position + (id === 'triglycerides' ? ` Shown: ${fasting === 'nonfasting' ? 'nonfasting' : 'fasting'} curve.${fasting === 'unknown' ? ' Dashed line: nonfasting alternative.' : ''}` : '') + (id === 'hdl_c' ? ' No points are assigned at or above 2.5 mmol/L.' : '')));
  return figure;
}
function markerDetails(id, name, result) {
  const content = markerEducation[id], details = document.createElement('details'); details.className = 'education';
  details.append(educationalText('summary', `About ${name} & how it is scored`));
  const body = educationalText('div', '', 'education-body');
  for (const [heading, message] of [['What it measures',content.meaning], ['What can affect interpretation',content.context], ['How this prototype assigns points',content.model]]) body.append(educationalText('h4',heading), educationalText('p',message));
  body.append(educationalText('p', 'These adult-derived curves are not validated for children or individualized for older adults. Clinical references inform interpretation; they do not validate these points or weights.', 'muted'));
  const chart = educationalText('div', ''); body.append(chart);
  body.append(educationalText('h4','Read more'), referenceLinks(content.sources));
  details.append(body);
  let loaded = false;
  details.addEventListener('toggle', async () => {
    if (!details.open || loaded) return;
    loaded = true; chart.textContent = 'Loading scoring diagram…';
    try {
      const model = await getExplanationModel(), curve = model.curves[id];
      if (result && model.model_version !== result.model_version) throw new Error('Version changed');
      chart.replaceChildren(curveGraphic(id,name,curve,result?.markers[id],result?.fasting_status ?? 'unknown'));
      const table = document.createElement('table'); table.className = 'anchor-table';
      const caption = educationalText('caption', 'Exact anchor points; straight lines connect adjacent anchors.');
      const head = document.createElement('thead'), row = document.createElement('tr');
      for (const heading of [`Measurement (${curve.unit})`,'Model points']) {const th=educationalText('th',heading); th.scope='col';row.append(th);}
      head.append(row); const tbody = document.createElement('tbody');
      const anchors = id === 'triglycerides' && result?.fasting_status === 'nonfasting' ? curve.nonfasting_anchors : curve.anchors;
      for (const [value,score] of anchors) {const row=document.createElement('tr');row.append(educationalText('td',value),educationalText('td',score));tbody.append(row);}
      table.append(caption,head,tbody); chart.append(table);
    } catch (_) { loaded = false; chart.textContent = 'The scoring diagram could not load. Close and reopen these details to retry, or refresh and recalculate.'; }
  });
  return details;
}
function calculationDetails(result) {
  const details = document.createElement('details'); details.className = 'education calculation-details';
  details.append(educationalText('summary','How is my metabolism score calculated?'));
  const body = educationalText('div','','education-body');
  body.append(educationalText('p','Each measurement is converted into 0–100 model points using a provisional curve. The points are then combined in three simple averages. A high total can hide a concerning individual result, so read the marker notices too.'));
  const flow = educationalText('ol','','score-flow');
  const score = key => result?.markers[key]?.display_score ?? '—';
  const component = key => result?.components[key]?.display_score ?? '—';
  flow.append(educationalText('li',`Triglycerides (${score('triglycerides')}) + HDL (${score('hdl_c')}) → divide by 2 → TG/HDL (${component('triglycerides_hdl')})`), educationalText('li',`LDL (${score('ldl_c')}) + TG/HDL (${component('triglycerides_hdl')}) → divide by 2 → Lipid health (${component('lipid_health')})`), educationalText('li',`HbA1c (${score('hba1c')}) + Lipid health (${component('lipid_health')}) → divide by 2 → Metabolism (${result?.display_score ?? '—'})`));
  body.append(flow,educationalText('p','Each marker’s share of the final score:'));
  const weights=educationalText('div','','weight-diagram'); weights.setAttribute('role','img'); weights.setAttribute('aria-label','HbA1c 50 percent, LDL 25 percent, triglycerides 12.5 percent, HDL 12.5 percent');
  for (const [label, cls] of [['HbA1c · 50%','weight-a1c'],['LDL · 25%','weight-ldl'],['TG · 12.5%','weight-tg'],['HDL · 12.5%','weight-hdl']]) weights.append(educationalText('span',label,cls));
  body.append(weights,educationalText('p','These weights are design choices, not proportions of your health. Calculations use full precision; displayed values are rounded. A dash means a required result is unavailable, not zero. Missing results are never replaced or given to another marker.'));
  body.append(educationalText('h4','What this number can—and cannot—tell you'),educationalText('p','It summarizes four measurements under this prototype’s rules. It is not a percentage of health, a diagnosis, or your probability of developing disease. A score of 100 does not rule out illness. Medication and daily steps do not add or subtract points.'));
  body.append(educationalText('h4','Age and evidence'),educationalText('p','The original behavior check used NHANES 2005–2006 participants aged 20+. NHANES includes younger people, but our evaluation excluded them. Public ages 85 and above are grouped together. Scores below 20 reuse adult curves without pediatric validation; scores at 85+ lack exact-age evaluation. Numerical points are not age- or sex-adjusted. No age group has clinical validation of this score.'));
  body.append(referenceLinks([['CDC: NHANES 2005–2006 population and age grouping','https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/overview.aspx?BeginYear=2005'],['NHLBI: separate guidance for children and adolescents','https://www.nhlbi.nih.gov/health-topics/integrated-guidelines-for-cardiovascular-health-and-risk-reduction-in-children-and-adolescents'],['Canadian Cardiovascular Society: adult lipid guidelines','https://ccs.ca/guideline/2021-lipids/']]));
  body.append(educationalText('p','Source links explain the underlying measurements and clinical context. The exact curves, coverage boundaries, and weighting are our provisional modeling choices.', 'muted'));
  details.append(body); return details;
}

// Shared presentation for all five domain totals; calculation stays in Python.
function domainScoreHeader(name, score) {
  const box = document.createElement('div'); box.className = 'domain-score-header';
  for (const [tag, value, cls] of [['p', name + ' score', 'eyebrow'], ['strong', score ?? '—', 'domain-score-value'], ['p', score == null ? 'Score unavailable · review coverage below' : 'out of 100 model points', 'muted']]) {
    const item = document.createElement(tag); item.textContent = value; item.className = cls; box.append(item);
  }
  return box;
}
