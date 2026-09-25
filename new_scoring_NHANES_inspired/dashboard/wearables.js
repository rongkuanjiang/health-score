'use strict';
(() => {
  const get = id => document.getElementById(id);
  const make = (tag, text, cls) => { const n=document.createElement(tag); n.textContent=text; if(cls)n.className=cls; return n; };
  const metrics = [
    ['steps','Steps','steps',0,1000000,1], ['sleep','Sleep','hours',0,24,0.1],
    ['active','Active minutes','min',0,1440,1], ['rhr','Resting heart rate','bpm',1,400,1],
    ['hrv','HRV (RMSSD)','ms',0,1000,0.1], ['spo2','Oxygen saturation','%',0,100,0.1],
    ['resp','Respiratory rate','breaths/min',1,100,0.1]
  ];
  const records=new Map(), demos=new Map(), quickImported=new Map(); let demo=false;
  const today=iso(new Date());
  const section=document.querySelector('.wearable-summary'); section.className='panel wearable-dashboard'; section.id='wearable-dashboard';
  const quick=get('edit-wearable'); quick.textContent='Quick step entry';
  const legacySummary=get('wearable-summary-text'); legacySummary.hidden=true;
  section.replaceChildren();
  section.innerHTML=`<div class="wearable-heading"><div><p class="eyebrow">BEYOND BLOODWORK</p><h2>Wearable device data</h2><p class="muted">Daily activity, recovery and ECG records. Separate from all five domain scores.</p></div><span class="pill">Not scored</span></div>
    <div class="wearable-controls"><label>30-day window ending<input id="wear-end" type="date" value="${today}" max="${today}" required></label><label>Trend measurement<select id="wear-metric">${metrics.map(([id,label])=>`<option value="${id}">${label}</option>`).join('')}</select></label><button id="wear-demo" type="button" class="secondary">Preview 30-day example</button></div>
    <p id="wear-mode" class="muted" role="status"></p><div id="wear-cards" class="wearable-cards"></div>
    <div class="wearable-trend"><div class="wearable-heading"><h3 id="wear-chart-title">30-day trend</h3><p id="wear-coverage" class="muted"></p></div><div id="wear-chart"></div><p class="muted">Averages use recorded days only. Gaps mean no measurement; zero is a recorded value. Values are transcribed from your device, without interpretation.</p></div>
    <details class="education" id="wear-entry"><summary>Add or edit a daily record</summary><form id="wear-form" class="wearable-form"><div class="grid"><label>Record date<input id="wear-date" type="date" max="${today}" value="${today}" required></label><label>Device / source<input id="wear-source" maxlength="100" placeholder="e.g. watch or phone" required></label>${metrics.map(([id,label,unit,min,max,step])=>`<label>${label} (${unit})<input id="wear-${id}" type="number" min="${min}" max="${max}" step="${step}" placeholder="Not recorded"></label>`).join('')}</div>
    <h3>ECG record</h3><p class="muted">Copy the device-reported result. This log does not analyze ECG waveforms or diagnose rhythm.</p><div class="grid"><label>Device-reported ECG result<select id="wear-ecg"><option value="">Not recorded</option><option>Sinus rhythm</option><option>Atrial fibrillation notification</option><option>Inconclusive</option><option>Poor recording</option><option>Other device result</option></select></label><label>ECG time (local)<input id="wear-time" type="time"></label><label>Heart rate during ECG (bpm)<input id="wear-ecg-hr" type="number" min="1" max="400" step="1"></label><label>Report reference / notes<input id="wear-note" maxlength="300" placeholder="Optional device report reference"></label></div><p class="muted">One daily summary and one ECG record per date. Saving replaces that date's record. Leave unavailable values blank. Use one source for daily totals; do not add overlapping watch and phone counts.</p><div class="wearable-actions"><button type="submit">Save daily record</button><button id="wear-delete" type="button" class="secondary">Delete this date</button></div><p id="wear-save-status" role="status"></p></form></details>
    <details class="education"><summary>Daily records and ECG log</summary><div class="table-wrap"><table><caption>Records in the selected 30-day window</caption><thead><tr><th>Date / source</th><th>Steps</th><th>Sleep</th><th>Active</th><th>Resting HR</th><th>HRV</th><th>SpO₂</th><th>Respiration</th><th>ECG / device report</th></tr></thead><tbody id="wear-log"></tbody></table></div></details><p class="muted">Manual entry only; no device connection. Records stay in this open page and are cleared on reload.</p>`;
  section.append(quick,legacySummary);
  // Keep one bounded dashboard surface; editing and logs replace the trend view.
  const heading=section.querySelector('.wearable-heading');
  heading.querySelector('.eyebrow').remove();
  heading.querySelector('.muted').textContent='Activity, recovery & ECG · excluded from health scores';
  const controls=section.querySelector('.wearable-controls');
  controls.querySelector('label').firstChild.textContent='Window ending';
  controls.querySelectorAll('label')[1].hidden=true; // Metric buttons select the chart.
  const tabs=make('nav','','wearable-tabs');tabs.setAttribute('aria-label','Wearable views');
  const body=make('div','','wearable-viewport');
  const trends=make('div','','wearable-trends-view');trends.id='wear-view-trends';
  const trend=section.querySelector('.wearable-trend');
  trend.querySelector(':scope > p').remove();
  trends.append(get('wear-cards'),trend);
  const entry=make('div','','wearable-entry-view');entry.id='wear-view-entry';
  entry.append(get('wear-form'),quick);get('wear-entry').remove();
  const log=make('div','','wearable-log-view');log.id='wear-view-log';
  const logDetails=get('wear-log').closest('details');log.append(logDetails.querySelector('.table-wrap'));logDetails.remove();
  const views=[['Trends',trends],['Daily entry',entry],['Records & ECG',log]];
  for(const [label,view]of views){
    const button=make('button',label,'secondary');button.type='button';button.id=`${view.id}-button`;button.setAttribute('aria-controls',view.id);
    view.setAttribute('role','region');view.setAttribute('aria-labelledby',button.id);
    button.addEventListener('click',()=>selectView(view));tabs.append(button);body.append(view);
  }
  function selectView(selected){for(const [,view]of views){view.hidden=view!==selected;get(`${view.id}-button`).setAttribute('aria-pressed',String(view===selected));}body.scrollTop=0;}
  const footer=make('p','Recorded-day averages · gaps are missing days · manual data clears on reload.','muted wearable-footnote');
  section.replaceChildren(heading,controls,tabs,get('wear-mode'),body,footer,legacySummary);
  selectView(trends);
  function dates(){const end=new Date(get('wear-end').value+'T12:00:00');return Array.from({length:30},(_,i)=>{const d=new Date(end);d.setDate(d.getDate()-29+i);return iso(d);});}
  function format(value){return value==null?'—':Number(value.toFixed(1)).toLocaleString();}
  function draw(){
    if(!get('wear-end').checkValidity()){get('wear-end').reportValidity();return;}
    const days=dates(),data=demo?demos:records;
    get('wear-mode').textContent=demo?'Fictional example · personal records preserved':'Your records · 30 days';
    get('wear-demo').textContent=demo?'My records':'Try example';
    get('wear-cards').replaceChildren();
    for(const [id,label,unit]of metrics){
      const values=days.map(d=>data.get(d)?.[id]).filter(v=>v!=null);
      const card=make('button','','wearable-metric secondary');card.type='button';card.setAttribute('aria-pressed',String(get('wear-metric').value===id));
      card.title=`${label}: recorded-day average in ${unit}; ${values.length} of 30 days recorded`;
      card.append(make('span',label),make('strong',values.length?format(values.reduce((a,b)=>a+b,0)/values.length):'—'),make('span',unit,'muted'));
      card.addEventListener('click',()=>{get('wear-metric').value=id;draw();});get('wear-cards').append(card);
    }
    const [id,label,unit]=metrics.find(m=>m[0]===get('wear-metric').value);
    const values=days.map(d=>data.get(d)?.[id]??null), available=values.filter(v=>v!=null);
    get('wear-chart-title').textContent=`${label} · 30-day tracking`;
    get('wear-coverage').textContent=`${available.length}/30 days recorded`;
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 800 220');svg.setAttribute('role','img');svg.setAttribute('aria-label',`${label} in ${unit}, ${days[0]} through ${days[29]}. ${available.length} days recorded. Daily values are in the records table.`);
    const add=(tag,attrs,text)=>{const n=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);if(text!=null)n.textContent=text;svg.append(n);return n;};
    const high=Math.max(1,...available)*1.1,x=i=>64+i*24,y=v=>175-v/high*145;
    for(let i=0;i<4;i++){const value=high*i/3;add('line',{x1:64,y1:y(value),x2:760,y2:y(value),class:'wear-grid'});add('text',{x:56,y:y(value)+4,'text-anchor':'end',class:'wear-axis'},format(value));}
    add('text',{x:64,y:18,class:'wear-axis'},unit);
    values.forEach((v,i)=>{if(v==null)return;if(i&&values[i-1]!=null)add('line',{x1:x(i-1),y1:y(values[i-1]),x2:x(i),y2:y(v),class:'wear-line'});const dot=add('circle',{cx:x(i),cy:y(v),r:4,class:'wear-point'});const title=document.createElementNS(ns,'title');title.textContent=`${days[i]}: ${format(v)} ${unit}`;dot.append(title);});
    for(const i of [0,7,14,21,29])add('text',{x:x(i),y:205,'text-anchor':'middle',class:'wear-axis'},days[i].slice(5));
    if(!available.length)add('text',{x:410,y:100,'text-anchor':'middle',class:'wear-axis'},'No records yet. Add a day or preview an example.');
    get('wear-chart').replaceChildren(svg);get('wear-log').replaceChildren();
    for(const date of [...days].reverse()){
      const r=data.get(date);if(!r)continue;const tr=make('tr','');tr.append(make('td',`${date} · ${r.source}`));
      for(const [key,,u]of metrics)tr.append(make('td',r[key]==null?'—':`${format(r[key])} ${u}`));
      tr.append(make('td',r.ecg?`${r.time||'Time not recorded'} · ${r.ecg}${r.ecgHr?` · ${r.ecgHr} bpm`:''}${r.note?` · ${r.note}`:''}`:'Not recorded'));get('wear-log').append(tr);
    }
    if(!get('wear-log').children.length){const tr=make('tr',''),td=make('td','No records in this window.');td.colSpan=9;tr.append(td);get('wear-log').append(tr);}
  }
  function loadDate(){const r=records.get(get('wear-date').value)||{};for(const[id]of metrics)get(`wear-${id}`).value=r[id]??'';for(const[id,key]of [['source','source'],['ecg','ecg'],['time','time'],['ecg-hr','ecgHr'],['note','note']])get(`wear-${id}`).value=r[key]??'';get('wear-save-status').textContent='';}
  get('wear-form').addEventListener('submit',e=>{e.preventDefault();if(!get('wear-form').reportValidity())return;const r={source:get('wear-source').value.trim(),ecg:get('wear-ecg').value,time:get('wear-time').value,ecgHr:get('wear-ecg-hr').value,note:get('wear-note').value.trim()};
    if(!r.source){get('wear-save-status').textContent='Enter a device or source.';return;}
    for(const[id]of metrics)r[id]=get(`wear-${id}`).value===''?null:Number(get(`wear-${id}`).value);
    if(!metrics.some(([id])=>r[id]!=null)&&!r.ecg){get('wear-save-status').textContent='Add at least one measurement or an ECG result.';return;}
    if(!r.ecg&&(r.time||r.ecgHr||r.note)){get('wear-save-status').textContent='Select the device-reported ECG result for these ECG details.';return;}
    records.set(get('wear-date').value,r);demo=false;get('wear-end').value=get('wear-date').value;draw();get('wear-save-status').textContent='Daily record saved. Bloodwork scores are unchanged.';
  });
  get('wear-date').addEventListener('change',loadDate);
  get('wear-delete').addEventListener('click',()=>{records.delete(get('wear-date').value);demo=false;loadDate();draw();get('wear-save-status').textContent='Record removed for this date.';});
  get('wear-end').addEventListener('change',()=>{if(demo)fillDemo();draw();});get('wear-metric').addEventListener('change',draw);
  function fillDemo(){if(!get('wear-end').checkValidity())return;demos.clear();dates().forEach((date,i)=>{if([5,12,13,23].includes(i))return;demos.set(date,{source:'Fictional example',steps:Math.round(5500+i*70+1800*Math.sin(i)),sleep:7+0.6*Math.cos(i),active:20+i%5*7,rhr:65+Math.round(4*Math.sin(i/3)),hrv:42+7*Math.cos(i/4),spo2:97+i%3,resp:14+i%3,ecg:i%9===0?'Sinus rhythm':'',time:'08:30',ecgHr:66,note:'Fictional device report'});});}
  get('wear-demo').addEventListener('click',()=>{demo=!demo;if(demo)fillDemo();draw();});
  // Existing quick-step entry remains available; copy only on saving that form.
  get('onboarding-form').addEventListener('submit',()=>{if(!get('onboarding-form').checkValidity())return;for(const input of get('step-inputs').querySelectorAll('input')){if(input.value===''||!input.checkValidity())continue;const signature=get('step-source').value+':'+input.value;if(quickImported.get(input.dataset.date)===signature)continue;quickImported.set(input.dataset.date,signature);const prior=records.get(input.dataset.date)||{};records.set(input.dataset.date,{...prior,source:get('step-source').selectedOptions[0].textContent,steps:Number(input.value)});}draw();});
  draw();
})();
