'use strict';
(() => {
  const get=id=>document.getElementById(id);
  const domains=[
    {id:'metabolism',name:'Metabolism',subtitle:'Blood sugar & lipids',prefix:'',form:'score-form'},
    {id:'organ-stress',name:'Organ stress',subtitle:'Liver & kidney markers',prefix:'organ-',form:'organ-form'},
    {id:'inflammation',name:'Inflammation',subtitle:'hs-CRP & blood-cell context',prefix:'infl-',form:'infl-form'},
    {id:'nutrition',name:'Nutrition',subtitle:'Vitamin D & nutritional context',prefix:'nutr-',form:'nutr-form'},
    {id:'system-stability',name:'System Stability',subtitle:'Electrolyte reference summary',prefix:'stab-',form:'stab-form'},
  ];
  const results=new Map();let person=null;
  const make=(tag,value,cls)=>{const n=document.createElement(tag);n.textContent=value;if(cls)n.className=cls;return n;};
  const onboarding=make('section','','onboarding panel');onboarding.id='onboarding';
  onboarding.innerHTML=`<p class="eyebrow">01 / A LITTLE CONTEXT</p><h1>Start with you.</h1><p class="onboarding-lead">A few details help us interpret your bloodwork. Next, explore your five domains and add the results you have.</p>
    <form id="onboarding-form"><div class="grid"><label>Age at the time of your blood draw<input id="person-age" type="number" min="0.1" step="any" required placeholder="Years"></label>
    <label>Sex recorded for laboratory interpretation<select id="person-sex"><option value="unknown">Not sure / prefer not to say</option><option value="female">Female</option><option value="male">Male</option></select></label>
    <label>Pregnancy status at the time of the blood draw<select id="person-pregnancy"><option value="unknown">Not sure / prefer not to say</option><option value="not_pregnant">Not pregnant</option><option value="pregnant">Pregnant</option><option value="not_applicable">Not applicable</option></select></label></div>
    <p class="muted">These details prefill each domain. You can adjust them for results from a different date. Unknown answers stay unknown.</p><div class="onboarding-actions"><button type="submit">Continue to my overview →</button><button id="cancel-person" class="secondary" type="button" hidden>Cancel</button></div></form><p class="session-note">Your entries are kept only for this open page. Reloading starts a new session.</p>`;
  const overview=make('section','','overview');overview.id='overview';overview.hidden=true;
  overview.innerHTML=`<div class="overview-heading"><div><p class="eyebrow">YOUR HEALTH / FIVE DOMAINS</p><h1>Your health dashboard.</h1><p id="person-summary" class="muted"></p></div><button id="edit-person" class="secondary" type="button">Edit my details</button></div>
    <div class="overview-prompt"><div><h2>Five domains. One picture.</h2><p>Enter your biomarkers below and calculate all domains together. Your scores and chart update here.</p><p id="dashboard-progress" role="status">No domains calculated yet.</p></div><div class="dashboard-actions"><button id="calculate-all" type="button">Calculate all domains</button><button id="load-all-demo" type="button" class="secondary">Try a full example</button></div></div>
    <div id="overview-cards" class="overview-cards"></div><section class="panel profile-panel"><div><p class="eyebrow">YOUR RESULTS / 0–100 MODEL POINTS</p><h2>A five-domain view.</h2><p id="radar-status" role="status"></p><p class="muted">Metabolism is a domain score. Kidney, liver, hs-CRP and vitamin D are separate component points. System Stability reports reference findings, without numerical points.</p><p class="muted">Missing points remain gaps, not zero. These are not percentages of health or an overall health score.</p><div class="chart-key"><span><i class="key-dot"></i>Available points</span><span><i class="key-dot secondary-dot"></i>Liver component</span></div></div><div id="domain-radar"></div></section>`;
  const editor=make('section','','biomarker-editor');editor.id='biomarker-editor';editor.hidden=true;
  editor.innerHTML='<div class="editor-heading"><div><p class="eyebrow">YOUR BIOMARKERS</p><h2>Enter results by domain</h2><p>Expand any domain below. Your five-domain summary stays on this page.</p></div><button id="back-overview" type="button" class="secondary">Jump to scores</button></div>';
  const main=document.querySelector('main');document.querySelector('.intro').hidden=true;
  const wearable=get('wearable-data');
  onboarding.querySelector('.onboarding-actions').before(wearable);
  for(const section of [onboarding,overview,editor])main.insertBefore(section,get('domain-nav'));
  overview.append(editor);
  const wearableSummary=make('section','','panel wearable-summary');
  wearableSummary.innerHTML='<div><p class="eyebrow">WEARABLE DEVICE DATA</p><h2>Daily steps</h2><p id="wearable-summary-text" class="muted"></p></div><button id="edit-wearable" type="button" class="secondary">Edit wearable data</button>';
  editor.before(wearableSummary);
  editor.append(get('domain-nav'));
  for(const [index,domain] of domains.entries()){
    const section=make('details','','unified-domain');section.id=`entry-${domain.id}`;
    const summary=make('summary','');
    summary.append(make('span',`0${index+1}`,'domain-number'),make('strong',domain.name),make('span',domain.subtitle,'domain-subtitle'));
    const status=make('span','Not calculated','inline-domain-status');status.id=`inline-${domain.id}`;summary.append(status);
    const panel=get(`domain-${domain.id}`);panel.hidden=false;
    section.append(summary,panel);editor.append(section);
    section.addEventListener('toggle',()=>get(`nav-${domain.id}`).setAttribute('aria-expanded',String(section.open)));
    get(`nav-${domain.id}`).removeAttribute('aria-pressed');
    get(`nav-${domain.id}`).setAttribute('aria-expanded','false');
    get(`nav-${domain.id}`).setAttribute('aria-controls',section.id);
  }

  for(const domain of domains.filter(d=>d.id!=='system-stability')){
    const details=make('details','','education');details.append(make('summary','Personal details for this report'));
    details.append(make('p','Prefilled from your questionnaire. Adjust these only if this report needs different details; synthetic profiles use their own example details.','muted'));
    const fields=make('div','','grid');
    for(const key of ['age','sex','pregnancy']){const field=get(`${domain.prefix}${key}`);if(field)fields.append(field.closest('label'));}
    details.append(fields);get(domain.form).querySelector('section').prepend(details);
  }
  const focusHeading=section=>{const h=section.querySelector('h1,h2');if(h){h.tabIndex=-1;h.focus();}};
  const showOverview=()=>{onboarding.hidden=true;editor.hidden=false;overview.hidden=false;get('wearable-summary-text').textContent=get('activity').querySelector('.activity-stats')?.textContent||get('activity').textContent;draw();focusHeading(overview);};
  let wearableSnapshot=null;
  const captureWearable=()=>({end:get('week-end').value,source:get('step-source').value,days:[...get('step-inputs').querySelectorAll('input')].map(input=>input.value)});
  const editPerson=()=>{wearableSnapshot=captureWearable();overview.hidden=true;editor.hidden=true;onboarding.hidden=false;focusHeading(onboarding);};
  get('edit-wearable').addEventListener('click',()=>{editPerson();wearable.open=true;wearable.querySelector('summary').focus();wearable.scrollIntoView?.({behavior:'smooth',block:'start'});});
  get('onboarding-form').addEventListener('invalid',event=>{if(wearable.contains(event.target))wearable.open=true;},true);
  function openDomain(id){
    if(!person)return;
    const section=get(`entry-${id}`);section.open=true;
    section.querySelector('summary').focus();section.scrollIntoView?.({behavior:'smooth',block:'start'});
  }
  window.addEventListener('domain-focus',event=>openDomain(event.detail.id));
  function applyPerson(){
    const fields={age:person.age,sex:person.sex,pregnancy:({not_pregnant:'no',pregnant:'yes'})[person.pregnancy]||person.pregnancy,'organ-sex':person.sex};
    for(const prefix of ['organ-','infl-','nutr-']){fields[`${prefix}age`]=person.age;fields[`${prefix}pregnancy`]=person.pregnancy;}
    for(const [id,value]of Object.entries(fields)){get(id).value=value;get(id).dispatchEvent(new Event('change',{bubbles:true}));}
    get('stab-form').dispatchEvent(new Event('change',{bubbles:true}));
    results.clear();
  }
  get('onboarding-form').addEventListener('submit',event=>{event.preventDefault();if(!get('onboarding-form').reportValidity())return;
    const nextPerson={age:get('person-age').value,sex:get('person-sex').value,pregnancy:get('person-pregnancy').value};
    const changed=JSON.stringify(person)!==JSON.stringify(nextPerson);person=nextPerson;if(changed)applyPerson();get('cancel-person').hidden=false;
    get('person-summary').textContent=`Age ${person.age} at collection · ${person.sex==='unknown'?'Sex not provided':person.sex==='female'?'Female':'Male'} · Details can be adjusted per report`;showOverview();});
  get('edit-person').addEventListener('click',editPerson);
  get('cancel-person').addEventListener('click',()=>{
    get('person-age').value=person.age;get('person-sex').value=person.sex;get('person-pregnancy').value=person.pregnancy;
    if(wearableSnapshot){get('week-end').value=wearableSnapshot.end;get('step-source').value=wearableSnapshot.source;renderDays();[...get('step-inputs').querySelectorAll('input')].forEach((input,i)=>{input.value=wearableSnapshot.days[i]??'';});renderActivity();}
    showOverview();
  });
  get('back-overview').addEventListener('click',()=>{focusHeading(overview);overview.scrollIntoView?.({behavior:'smooth',block:'start'});});
  function updateProgress(){
    const busy=domains.some(d=>get(`${d.prefix}calculate`).disabled);
    const errors=domains.filter(d=>get(`${d.prefix}error`).textContent.trim()).length;
    get('calculate-all').disabled=busy;get('load-all-demo').disabled=busy;
    get('calculate-all').textContent=busy?'Calculating domains...':'Calculate all domains';
    get('dashboard-progress').textContent=`${results.size}/5 domains calculated`+(busy?' / updating...':errors?` / ${errors} request error(s). Expand the affected domains to review.`:' / missing data stays unavailable');
  }
  get('calculate-all').addEventListener('click',()=>{for(const domain of domains)get(domain.form).requestSubmit();updateProgress();});
  get('load-all-demo').addEventListener('click',()=>{for(const domain of domains){get(`${domain.prefix}profile`).value='example';get(`${domain.prefix}load`).click();}updateProgress();});
  const activityObserver=new MutationObserver(updateProgress);
  for(const domain of domains){activityObserver.observe(get(`${domain.prefix}calculate`),{attributes:true,attributeFilter:['disabled']});activityObserver.observe(get(`${domain.prefix}error`),{childList:true,subtree:true,characterData:true});}

  for(const domain of domains)get(domain.form).addEventListener('submit',()=>{results.delete(domain.id);draw();},true);
  for(const domain of domains)get(domain.form).addEventListener('invalid',event=>{
    for(let parent=event.target.parentElement;parent;parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;
  },true);
  window.addEventListener('scorer-result',event=>{const {domain,result}=event.detail;if(!domains.some(d=>d.id===domain))return;if(result)results.set(domain,result);else results.delete(domain);draw();});
  const valid=p=>typeof p.score==='number'&&Number.isFinite(p.score)&&p.score>=0&&p.score<=100;
  function notices(result){
    const found=new Set();
    const collect=node=>{
      if(!node||typeof node!=='object')return;
      if(Array.isArray(node)){node.forEach(collect);return;}
      for(const key of ['flags','notices','source_flags'])for(const item of node[key]||[]){
        const value=typeof item==='string'?item:item.text||item.message||item.code;
        if(value)found.add(`${typeof item==='object'&&item.marker?item.marker+': ':''}${String(value).replaceAll('_',' ')}${item.selected===false?' (unselected result)':''}`);
      }
      for(const [key,value]of Object.entries(node))if(!['flags','notices','source_flags','input','original','provenance','observation'].includes(key))collect(value);
    };collect(result);return [...found];
  }
  function points(r,id){if(!r)return [];if(id==='metabolism')return [{label:'Metabolism',...r}];if(id==='organ-stress')return ['kidney','liver'].map(k=>({label:k==='kidney'?'Kidney':'Liver',...r.components[k]}));if(id==='inflammation')return [{label:'hs-CRP',...r.components.hs_crp}];if(id==='nutrition')return [{label:'Vitamin D',...r.components.vitamin_d}];return [];}
  function draw(){
    const cards=get('overview-cards');cards.replaceChildren();
    for(const [index,domain]of domains.entries()){
      const r=results.get(domain.id),card=make('article','','overview-card');card.id=`overview-${domain.id}`;
      card.append(make('p',`0${index+1} / ${domain.subtitle}`,'eyebrow'),make('h2',domain.name));
      get(`inline-${domain.id}`).textContent=!r?'Not calculated':domain.id==='system-stability'?r.panel_status.replaceAll('_',' '):points(r,domain.id).map(p=>`${p.label}: ${valid(p)?p.display_score??p.score:'Unavailable'}`).join(' / ');
      if(!r)card.append(make('p','—','overview-value'),make('p','Add biomarkers to see your results.','muted'));
      else if(domain.id==='system-stability'){
        const labels={all_within_reference:'Within report ranges',outside_reference:'Outside report ranges',partial:'Partial results',unavailable:'Insufficient information',source_critical_flag:'Critical laboratory flag',source_flag_conflict:'Conflicting laboratory flags'};
        card.append(make('p',labels[r.panel_status]||'Review results','overview-category'),make('p',`${r.coverage.interpretable_count}/${r.coverage.expected_count} core results interpretable · No numerical score`,'muted'));
      }else{for(const p of points(r,domain.id)){const row=make('p','','overview-points');row.append(make('span',p.label),make('strong',valid(p)?`${p.display_score??p.score} / 100`:p.score_envelope?`${p.score_envelope.join('–')} / 100 (range)`:'Unavailable'));card.append(row);}if(domain.id!=='metabolism')card.append(make('p','Component points · no domain total','muted'));else card.append(make('p',`${r.coverage.scored}/${r.coverage.required} markers scored`,'muted'));}
      if(r){
        const notes=notices(r);
        if(notes.length){
          if(notes.some(n=>/critical/i.test(n)))card.append(make('p','Laboratory critical flag present. Review the report notices.','notice'));
          const details=make('details','');details.append(make('summary',`${notes.length} report & interpretation notices`));
          for(const note of notes)details.append(make('p',note,'overview-review'));card.append(details);
        }
        card.append(make('p','Review details for coverage, laboratory flags and interpretation notices.','overview-review'));if(/synthetic/i.test(get(`${domain.prefix}profile-note`)?.textContent||''))card.append(make('p','Synthetic example · may use different personal details','example-label'));
      }
      const button=make('button',r?'Review results & biomarkers':'Enter biomarkers','secondary');button.type='button';button.setAttribute('aria-label',`${button.textContent}: ${domain.name}`);button.addEventListener('click',()=>openDomain(domain.id));card.append(button);cards.append(card);
    }
    drawRadar();updateProgress();
  }
  function drawRadar(){
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 560 460');svg.setAttribute('role','img');svg.setAttribute('aria-labelledby','radar-title radar-desc');
    const add=(tag,attrs={},content)=>{const n=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);if(content!==undefined)n.textContent=content;svg.append(n);return n;};
    const xy=(axis,score)=>{const a=-Math.PI/2+axis*2*Math.PI/5,r=150*score/100;return[280+r*Math.cos(a),225+r*Math.sin(a)];};
    add('title',{id:'radar-title'},'Five-domain profile on a zero to one hundred point scale');
    for(const value of [20,40,60,80,100]){add('polygon',{points:domains.map((_,i)=>xy(i,value).join(',')).join(' '),class:'radar-grid'});const[x,y]=xy(0,value);add('text',{x:x+7,y:y+4,class:'radar-tick'},String(value));}
    add('text',{x:287,y:237,class:'radar-tick'},'0');const description=[];let count=0;
    for(const[i,domain]of domains.entries()){
      const[x,y]=xy(i,100);add('line',{x1:280,y1:225,x2:x,y2:y,class:'radar-axis'});const[lx,ly]=xy(i,128);add('text',{x:lx,y:ly,'text-anchor':'middle',class:'radar-label'},domain.name);
      const series=points(results.get(domain.id),domain.id).filter(valid);
      for(const p of series){const[px,py]=xy(i,p.score),mark=add('circle',{cx:px,cy:py,r:6,class:p.label==='Liver'?'radar-point radar-liver':'radar-point','data-domain':domain.id,'data-score':p.score});const title=document.createElementNS(ns,'title');title.textContent=`${p.label}: ${p.display_score??p.score} / 100`;mark.append(title);description.push(`${p.label}: ${p.display_score??p.score}`);count++;}
      if(!series.length){add('text',{x:lx,y:ly+18,'text-anchor':'middle',class:'radar-unavailable'},domain.id==='system-stability'?'Reference summary':'No points available');description.push(`${domain.name}: no numerical points`);}
    }
    add('desc',{id:'radar-desc'},description.join('. ')+'. Missing axes have no point and are not assigned zero. Kidney and liver are separate points on the organ-stress axis.');get('domain-radar').replaceChildren(svg);
    get('radar-status').textContent=count?`${count} available score${count===1?'':'s'} shown. Open a domain card to see its full results.`:'Your profile will appear here as you add biomarkers and calculate results.';
  }
  draw();
})();
