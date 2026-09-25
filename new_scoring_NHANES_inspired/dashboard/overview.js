'use strict';
(() => {
  const get=id=>document.getElementById(id);
  const domains=[
    {id:'metabolism',name:'Metabolism',subtitle:'Blood sugar & lipids',prefix:'',form:'score-form'},
    {id:'organ-stress',name:'Organ stress',subtitle:'Liver & kidney markers',prefix:'organ-',form:'organ-form'},
    {id:'inflammation',name:'Inflammation',subtitle:'hs-CRP & WBC baseline profile',prefix:'infl-',form:'infl-form'},
    {id:'nutrition',name:'Nutrition',subtitle:'B12 & iron-marker profile',prefix:'nutr-',form:'nutr-form'},
    {id:'system-stability',name:'System Stability',subtitle:'Sodium & potassium profile',prefix:'stab-',form:'stab-form'},
  ];
  const results=new Map();let person=null;
  // One coherent fictional record. Values illustrate the UI, not population means.
  const demoPerson={age:'42',sex:'male',pregnancy:'not_applicable'};
  let demoActive=false;
  const stabilityLabels={all_within_reference:'Within report ranges',outside_reference:'Outside report ranges',partial:'Partial results',unavailable:'Insufficient information',source_critical_flag:'Critical laboratory flag',source_flag_conflict:'Conflicting laboratory flags'};
  const make=(tag,value,cls)=>{const n=document.createElement(tag);n.textContent=value;if(cls)n.className=cls;return n;};
  const onboarding=make('section','','onboarding panel');onboarding.id='onboarding';
  onboarding.innerHTML=`<p class="eyebrow">01 / A LITTLE CONTEXT</p><h1>Start with you.</h1><p class="onboarding-lead">A few details help us interpret your bloodwork. Next, explore your five domains and add the results you have.</p>
    <form id="onboarding-form"><div class="grid"><label>Age at the time of your blood draw<input id="person-age" type="number" min="0.1" step="any" required placeholder="Years"></label>
    <label>Sex recorded for laboratory interpretation<select id="person-sex"><option value="unknown">Not sure / prefer not to say</option><option value="female">Female</option><option value="male">Male</option></select></label>
    <label>Pregnancy status at the time of the blood draw<select id="person-pregnancy"><option value="unknown">Not sure / prefer not to say</option><option value="not_pregnant">Not pregnant</option><option value="pregnant">Pregnant</option><option value="not_applicable">Not applicable</option></select></label></div>
    <p class="muted">These details prefill each domain. You can adjust them for results from a different date. Unknown answers stay unknown.</p><div class="onboarding-actions"><button type="submit">Continue to my overview →</button><button id="cancel-person" class="secondary" type="button" hidden>Cancel</button></div></form><p class="session-note">Your entries are kept only for this open page. Reloading starts a new session.</p>`;
  const overview=make('section','','overview');overview.id='overview';overview.hidden=true;
  overview.innerHTML=`<div class="overview-heading"><div><p class="eyebrow">YOUR HEALTH / FIVE DOMAINS</p><h1>Your health dashboard.</h1><p id="person-summary" class="muted"></p></div><button id="edit-person" class="secondary" type="button">Edit my details</button></div>
    <div class="overview-prompt"><div><h2>Your five domains</h2><p>Choose a domain to enter results, or try an example.</p><p id="dashboard-progress" role="status">No domains calculated yet.</p></div><div class="dashboard-actions"><button id="calculate-all" type="button">Calculate all domains</button><button id="load-all-demo" type="button" class="secondary">Try a full example</button></div></div>
    <div id="overview-cards" class="overview-cards"></div><section class="panel profile-panel"><div><p class="eyebrow">YOUR RESULTS / 0–100 MODEL POINTS</p><h2>A five-domain view.</h2><p id="radar-status" role="status"></p><p class="muted">Model points, not an overall health score. Missing results leave gaps.</p><details class="chart-explainer"><summary>How to read this chart</summary><p class="muted">Each axis shows a provisional score from 0 to 100. Only adjacent available scores connect. Nutrition uses B12 and ferritin; vitamin D is separate. System Stability uses sodium and potassium. Points are not percentages of health.</p></details><div class="chart-key"><span><i class="key-dot"></i>Available points</span></div></div><div id="domain-radar"></div></section>`;
  const editor=make('section','','biomarker-editor');editor.id='biomarker-editor';editor.hidden=true;
  editor.innerHTML='<div class="editor-heading"><div><p class="eyebrow">YOUR BIOMARKERS</p><h2>Enter results by domain</h2><p>Your entries stay in place when you switch domains.</p></div><button id="back-overview" type="button" class="secondary">Overview</button></div>';
  const main=document.querySelector('main');document.querySelector('.intro').hidden=true;
  const wearable=get('wearable-data');
  onboarding.querySelector('.onboarding-actions').before(wearable);
  for(const section of [onboarding,overview,editor])main.insertBefore(section,get('domain-nav'));
  overview.append(editor);
  const wearableSummary=make('section','','panel wearable-summary');
  wearableSummary.innerHTML='<div><p class="eyebrow">WEARABLE DEVICE DATA</p><h2>Daily steps</h2><p id="wearable-summary-text" class="muted"></p></div><button id="edit-wearable" type="button" class="secondary">Edit wearable data</button>';
  editor.before(wearableSummary);
  get('load-all-demo').textContent='Demo score';
  const demoHint=make('p','Demo score replaces all five domains with fictional data.','muted demo-hint');
  get('load-all-demo').parentElement.append(demoHint);
  const startDemo=make('button','Explore a demo score','secondary');startDemo.type='button';startDemo.id='start-demo';
  startDemo.addEventListener('click',()=>loadDemo());onboarding.querySelector('.onboarding-actions').append(startDemo);
  overview.querySelector('.overview-heading').after(get('domain-nav'));
  get('domain-nav').classList.add('sticky-domain-nav');
  for(const [index,domain] of domains.entries()){
    const section=make('details','','unified-domain');section.id=`entry-${domain.id}`;
    const summary=make('summary','');
    summary.append(make('span',`0${index+1}`,'domain-number'),make('strong',domain.name),make('span',domain.subtitle,'domain-subtitle'));
    const status=make('span','Not calculated','inline-domain-status');status.id=`inline-${domain.id}`;summary.append(status);
    const panel=get(`domain-${domain.id}`);panel.hidden=false;
    section.append(summary,panel);editor.append(section);section.hidden=true;
    get(`nav-${domain.id}`).removeAttribute('aria-pressed');
    get(`nav-${domain.id}`).setAttribute('aria-expanded','false');
    get(`nav-${domain.id}`).setAttribute('aria-controls',section.id);
  }

  for(const domain of domains){
    const details=make('details','','education');details.append(make('summary','Personal details for this report'));
    details.append(make('p','Prefilled from your questionnaire. Adjust these only if this report needs different details; synthetic profiles use their own example details.','muted'));
    const fields=make('div','','grid');
    for(const key of ['age','sex','pregnancy']){const field=get(`${domain.prefix}${key}`);if(field)fields.append(field.closest('label'));}
    details.append(fields);get(domain.form).querySelector('section').prepend(details);
  }
  for(const domain of domains){
    const form=get(domain.form);
    const context=form.querySelector('section');
    const fold=make('details','','education compact-context');
    fold.append(make('summary','Collection context & personal details'));
    const body=make('div','','compact-body');
    while(context.firstChild)body.append(context.firstChild);
    fold.append(body);context.append(fold);
    // Optional vitamin D remains available without dominating core entry.
    if(domain.id==='nutrition')for(const panel of form.querySelectorAll('section')){
      const heading=panel.querySelector(':scope > h3');
      if(heading?.textContent==='Optional vitamin D result'){
        const optional=make('details','','education');optional.append(make('summary',heading.textContent));
        heading.remove();const content=make('div','','compact-body');
        while(panel.firstChild)content.append(panel.firstChild);
        optional.append(content);panel.append(optional);
      }
    }
  }
  const workspaces=new Map();
  // Match the other domains' marker-entry cards without changing input IDs or values.
  const metabolismRows=get('inputs');
  const markerFields=make('div','','marker-entry-cards');
  for(const row of [...metabolismRows.rows]){
    const fieldset=make('fieldset','','organ-measurement');
    fieldset.append(make('legend',row.cells[0].textContent));
    const grid=make('div','','grid');
    for(const [index,labelText]of ['Reported value','Unit','Reliability stated on report'].entries()){
      const label=make('label',labelText);label.append(row.cells[index+1].firstElementChild);grid.append(label);
    }
    fieldset.append(grid);markerFields.append(fieldset);
  }
  metabolismRows.closest('.table-wrap').replaceWith(markerFields);
  for(const domain of domains){
    const root=get(`domain-${domain.id}`),form=get(domain.form);
    const toolbar=root.querySelector('.toolbar');
    const scenarios=make('details','','example-scenarios');scenarios.append(make('summary','Other example scenarios'));
    scenarios.append(get(`${domain.prefix}profile`).closest('label'),get(`${domain.prefix}load`));
    toolbar.prepend(scenarios);
    const demoButton=make('button','Load demo person','secondary');demoButton.type='button';
    demoButton.classList.add('load-demo-person');
    demoButton.title='Load the same fictional person across all five domains';demoButton.addEventListener('click',()=>loadDemo());toolbar.prepend(demoButton);
    get(`${domain.prefix}load`).addEventListener('click',event=>{if(get(`${domain.prefix}profile`).value==='demo'){event.stopImmediatePropagation();loadDemo();}},true);
    const inputView=make('div','','workspace-scroll'),resultView=make('div','','workspace-scroll');
    inputView.id=`inputs-view-${domain.id}`;resultView.id=`results-view-${domain.id}`;
    for(const [view,label]of [[inputView,'Biomarker entry'],[resultView,'Results']]){view.tabIndex=0;view.setAttribute('role','region');view.setAttribute('aria-label',`${domain.name}: ${label}`);}
    const switcher=make('nav','','workspace-switcher');switcher.setAttribute('aria-label',`${domain.name} view`);
    const views=[['Results',resultView],['Edit biomarkers',inputView]];
    const select=view=>{for(const [,node]of views)node.hidden=node!==view;for(const button of switcher.children)button.setAttribute('aria-pressed',String(button.getAttribute('aria-controls')===view.id));};
    for(const [label,view]of views){const button=make('button',label,'secondary');button.type='button';button.setAttribute('aria-controls',view.id);button.addEventListener('click',()=>select(view));switcher.append(button);}
    for(const child of [...root.children]){
      if(child===form||child.classList.contains('toolbar'))inputView.append(child);
      else if(!child.classList.contains('domain-intro'))resultView.append(child);
    }
    root.append(switcher,inputView,resultView);select(inputView);
    workspaces.set(domain.id,{select,inputView,resultView});
  }
  const dashboardHome=make('div','','dashboard-home');dashboardHome.id='dashboard-home';
  for(const node of [...overview.children])if(!node.matches('.overview-heading,.sticky-domain-nav,.biomarker-editor'))dashboardHome.append(node);
  get('domain-nav').after(dashboardHome);
  const homeButton=make('button','Overview','secondary dashboard-home-button');homeButton.type='button';
  homeButton.addEventListener('click',()=>showDashboard());
  overview.querySelector('.overview-heading').append(homeButton);
  function showDashboard(){
    dashboardHome.hidden=false;editor.hidden=true;
    for(const domain of domains){get(`entry-${domain.id}`).open=false;get(`entry-${domain.id}`).hidden=true;get(`nav-${domain.id}`).setAttribute('aria-expanded','false');}
    homeButton.setAttribute('aria-current','page');focusHeading(overview);
    overview.scrollIntoView?.({behavior:'instant',block:'start'});
  }
  const focusHeading=section=>{const h=section.querySelector('h1,h2');if(h){h.tabIndex=-1;h.focus();}};
  const showOverview=()=>{onboarding.hidden=true;overview.hidden=false;showDashboard();get('wearable-summary-text').textContent=get('activity').querySelector('.activity-stats')?.textContent||get('activity').textContent;draw();focusHeading(overview);};
  let wearableSnapshot=null;
  const captureWearable=()=>({end:get('week-end').value,source:get('step-source').value,days:[...get('step-inputs').querySelectorAll('input')].map(input=>input.value)});
  const editPerson=()=>{wearableSnapshot=captureWearable();overview.hidden=true;editor.hidden=true;onboarding.hidden=false;focusHeading(onboarding);};
  get('edit-wearable').addEventListener('click',()=>{editPerson();wearable.open=true;wearable.querySelector('summary').focus();wearable.scrollIntoView?.({behavior:'smooth',block:'start'});});
  get('onboarding-form').addEventListener('invalid',event=>{if(wearable.contains(event.target))wearable.open=true;},true);
  function openDomain(id){
    if(!person)return;
    dashboardHome.hidden=true;editor.hidden=false;homeButton.removeAttribute('aria-current');
    for(const domain of domains){get(`entry-${domain.id}`).hidden=domain.id!==id;get(`entry-${domain.id}`).open=domain.id===id;get(`nav-${domain.id}`).setAttribute('aria-expanded',String(domain.id===id));}
    editor.querySelector('h2').textContent=domains.find(d=>d.id===id).name;
    const workspace=workspaces.get(id);workspace.select(results.has(id)?workspace.resultView:workspace.inputView);
    const section=get(`entry-${id}`);section.open=true;
    focusHeading(editor);overview.scrollIntoView?.({behavior:'instant',block:'start'});
  }
  window.addEventListener('domain-focus',event=>openDomain(event.detail.id));
  function applyPerson(){
    const fields={age:person.age,sex:person.sex,pregnancy:({not_pregnant:'no',pregnant:'yes'})[person.pregnancy]||person.pregnancy,'organ-sex':person.sex};
    for(const prefix of ['organ-','infl-','nutr-','stab-']){fields[`${prefix}age`]=person.age;fields[`${prefix}pregnancy`]=person.pregnancy;}
    for(const [id,value]of Object.entries(fields)){get(id).value=value;get(id).dispatchEvent(new Event('change',{bubbles:true}));}
    get('stab-form').dispatchEvent(new Event('change',{bubbles:true}));
    results.clear();
  }
  get('onboarding-form').addEventListener('submit',event=>{event.preventDefault();if(!get('onboarding-form').reportValidity())return;
    const nextPerson={age:get('person-age').value,sex:get('person-sex').value,pregnancy:get('person-pregnancy').value};
    const changed=JSON.stringify(person)!==JSON.stringify(nextPerson);person=nextPerson;if(changed){demoActive=false;wearableSummary.hidden=false;applyPerson();}get('cancel-person').hidden=false;
    get('person-summary').textContent=demoActive?'Demo: Alex, 42, male. Fictional bloodwork; illustrative values, not population averages.':`Age ${person.age} at collection · ${person.sex==='unknown'?'Sex not provided':person.sex==='female'?'Female':'Male'} · Details can be adjusted per report`;showOverview();});
  get('edit-person').addEventListener('click',editPerson);
  get('cancel-person').addEventListener('click',()=>{
    get('person-age').value=person.age;get('person-sex').value=person.sex;get('person-pregnancy').value=person.pregnancy;
    if(wearableSnapshot){get('week-end').value=wearableSnapshot.end;get('step-source').value=wearableSnapshot.source;renderDays();[...get('step-inputs').querySelectorAll('input')].forEach((input,i)=>{input.value=wearableSnapshot.days[i]??'';});renderActivity();}
    showOverview();
  });
  get('back-overview').addEventListener('click',showDashboard);
  function updateProgress(){
    const busy=domains.some(d=>get(`${d.prefix}calculate`).disabled);
    const errors=domains.filter(d=>get(`${d.prefix}error`).textContent.trim()).length;
    get('calculate-all').disabled=busy;get('load-all-demo').disabled=busy;
    startDemo.disabled=busy;for(const button of document.querySelectorAll('.load-demo-person'))button.disabled=busy;
    get('calculate-all').textContent=busy?'Calculating domains...':'Calculate all domains';
    get('dashboard-progress').textContent=`${results.size}/5 domains calculated`+(busy?' / updating...':errors?` / ${errors} request error(s). Open the affected domains to review.`:' / missing data stays unavailable');
  }
  get('calculate-all').addEventListener('click',()=>{for(const domain of domains)get(domain.form).requestSubmit();updateProgress();});
  function loadDemo(){
    if(domains.some(d=>get(`${d.prefix}calculate`).disabled))return;
    const date=new Date(),today=`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
    const report='DEMO-ALEX-42';
    const set=(id,value)=>{const field=get(id);if(!field)throw Error(`Missing demo field: ${id}`);if(field.type==='checkbox')field.checked=value;else field.value=value;};
    const fields=(prefix,values)=>{for(const [id,value]of Object.entries(values))set(prefix+id,value);};
    const marker=(prefix,id,value,unit,lower,upper,specimen)=>{
      fields(prefix,{[id]:value,[`${id}-unit`]:unit,[`${id}-report`]:report,[`${id}-date`]:today,[`${id}-reliability`]:'valid'});
      if(lower!==undefined)fields(prefix,{[`${id}-lower`]:lower,[`${id}-upper`]:upper,[`${id}-applicable`]:true});
      if(specimen)set(`${prefix}${id}-specimen`,specimen);
    };
    for(const domain of domains)get(`${domain.prefix}reset`).click();
    person={...demoPerson};demoActive=true;applyPerson();
    fields('person-',demoPerson);get('cancel-person').hidden=false;
    fields('',{interference:'no',illness:'no',mobility:'no',medications:'None in this fictional record',conditions:'None in this fictional record',fasting:'fasting',hours:10,'ldl-method':'direct',report,'lipid-date':today,'a1c-date':today,hba1c:5.4,ldl_c:3.1,triglycerides:1.4,hdl_c:1.25});
    for(const id of ['hba1c','ldl_c','triglycerides','hdl_c'])set(`${id}-reliability`,'valid');
    fields('organ-',{dialysis:'no',aki:'no',route:'reported','egfr-equation':'ckd_epi_2021_creatinine'});
    marker('organ-','egfr',95,'mL/min/1.73m2');marker('organ-','alt',26,'U/L',5,40);marker('organ-','alp',78,'U/L',40,120);
    for(const [id,value,unit]of [['ast',24,'U/L'],['bilirubin',12,'umol/L'],['ggt',28,'U/L'],['albumin',43,'g/L'],['bun',5,'mmol/L'],['uric_acid',320,'umol/L'],['uacr',0.8,'mg/mmol'],['cystatin_c',0.9,'mg/L']])marker('organ-',id,value,unit);
    fields('infl-',{acute:'absent',chronic:'absent',treatment:'absent',assay:'hs_crp'});
    marker('infl-','crp',1.6,'mg/L',0,3);marker('infl-','wbc',6.4,'10^9/L',4,11);
    marker('infl-','absolute_neutrophils',3.7,'10^9/L',2,7.5);marker('infl-','absolute_lymphocytes',2,'10^9/L',1,4);marker('infl-','esr',8,'mm/h',0,15);
    fields('nutr-',{'evaluation-date':today,supplementation:'absent',treatment:'absent',conditions:'absent','iron-confounders':'absent','iron-treatment':'absent','b12-treatment':'absent',analyte:'total_25_hydroxyvitamin_d'});
    const nutrition=[['vitamin_d',62,'nmol/L',50,125],['b12',330,'pmol/L',150,600],['ferritin',100,'ug/L',30,300],['serum_folate',18,'nmol/L',7,45],['rbc_folate',600,'nmol/L',350,1500,'rbc'],['iron',18,'umol/L',10,30],['transferrin',2.5,'g/L',2,3.6],['tibc',63,'umol/L',45,72],['transferrin_saturation',28.6,'%',20,50],['albumin',43,'g/L',35,50],['prealbumin',0.28,'g/L',0.2,0.4],['total_protein',72,'g/L',60,80],['hemoglobin',148,'g/L',135,175,'whole_blood'],['mcv',89,'fL',80,100,'whole_blood'],['rdw',13,'%',11.5,14.5,'whole_blood'],['calcium',2.35,'mmol/L',2.1,2.6],['magnesium',0.85,'mmol/L',0.7,1.05]];
    for(const [id,value,unit,lo,hi,specimen='serum']of nutrition)marker('nutr-',id,value,unit,lo,hi,specimen);
    fields('stab-',{date:today,report,specimen:'DEMO-SERUM',type:'serum',assay:'chemistry_total_co2'});
    for(const [id,value,lo,hi]of [['sodium',140,135,145],['potassium',4.2,3.5,5],['chloride',103,98,107],['total_co2',25,22,29],['total_calcium',2.35,2.1,2.6],['ionized_calcium',1.22,1.15,1.33]])fields('stab-',{[id]:value,[`${id}-lower`]:lo,[`${id}-upper`]:hi,[`${id}-applicable`]:'confirmed',[`${id}-provenance`]:'Illustrative demo interval only',[`${id}-reliability`]:'not_flagged'});
    for(const domain of domains){
      const select=get(`${domain.prefix}profile`);if(!select.querySelector('option[value="demo"]')){const option=make('option','Alex, 42 - shared demo');option.value='demo';select.append(option);}select.value='demo';
      get(domain.form).dispatchEvent(new Event('change',{bubbles:true}));
      get(`${domain.prefix}profile-note`).textContent=`Synthetic demo: Alex, age 42, male. Collection ${today}. Illustrative values and reference intervals, not population averages or a patient record.`;
    }
    get('person-summary').textContent='Demo: Alex, 42, male. Fictional bloodwork; illustrative values, not population averages.';
    wearableSummary.hidden=false;showOverview();
    for(const domain of domains)get(domain.form).requestSubmit();updateProgress();
  }
  get('load-all-demo').addEventListener('click',loadDemo);
  const activityObserver=new MutationObserver(updateProgress);
  for(const domain of domains){activityObserver.observe(get(`${domain.prefix}calculate`),{attributes:true,attributeFilter:['disabled']});activityObserver.observe(get(`${domain.prefix}error`),{childList:true,subtree:true,characterData:true});}

  for(const domain of domains)get(domain.form).addEventListener('submit',()=>{results.delete(domain.id);draw();},true);
  for(const domain of domains)get(domain.form).addEventListener('invalid',event=>{
    openDomain(domain.id);
    const workspace=workspaces.get(domain.id);workspace.select(workspace.inputView);
    for(let parent=event.target.parentElement;parent;parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;
  },true);
  window.addEventListener('scorer-result',event=>{const {domain,result}=event.detail;if(!domains.some(d=>d.id===domain))return;if(result)results.set(domain,result);else results.delete(domain);const workspace=workspaces.get(domain);workspace.select(result?workspace.resultView:workspace.inputView);draw();});
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
  function points(r,id){if(!r)return [];if(id==='metabolism')return [{label:'Metabolism',...r}];if(id==='organ-stress')return [{label:'Organ stress',...r,score:r.domain_score}];if(id==='inflammation')return [{label:'Inflammation',...r,score:r.domain_score}];if(id==='system-stability')return [{label:'System Stability',...r,score:r.domain_score}];if(id==='nutrition')return [{label:'Nutrition',...r,score:r.domain_score}];return [];}
  function draw(){
    const cards=get('overview-cards');cards.replaceChildren();
    for(const [index,domain]of domains.entries()){
      const r=results.get(domain.id),card=make('article','','overview-card');card.id=`overview-${domain.id}`;
      card.append(make('p',`0${index+1} / ${domain.subtitle}`,'eyebrow'),make('h2',domain.name));
      get(`inline-${domain.id}`).textContent=!r?'Not calculated':points(r,domain.id).map(p=>`${p.label}: ${valid(p)?p.display_score??p.score:'Unavailable'}`).join(' / ');
      if(!r)card.append(make('p','—','overview-value'),make('p','Add biomarkers to see your results.','muted'));
      else{for(const p of points(r,domain.id)){const row=make('p','','overview-points');row.append(make('strong',valid(p)?`${p.display_score??p.score} / 100`:p.score_envelope?`${p.score_envelope.join('–')} / 100 (range)`:'Unavailable'));card.append(row);}if(domain.id==='nutrition')card.append(make('p',`${r.coverage.scored_component_count}/${r.coverage.defined_component_count} core markers scored`,'muted'));else if(!['metabolism','organ-stress','inflammation','system-stability'].includes(domain.id))card.append(make('p','Component points · no domain total','muted'));else card.append(make('p',`${Array.isArray(r.coverage.scored)?r.coverage.scored.length:r.coverage.scored}/${Array.isArray(r.coverage.required)?r.coverage.required.length:r.coverage.required} markers scored`,'muted'));}
      if(r){
        if(['organ-stress','system-stability'].includes(domain.id)&&r.review_required)card.append(make('p','Flagged result: review markers.','notice'));
        const notes=notices(r);
        if(notes.length){
          if(notes.some(n=>/critical/i.test(n)))card.append(make('p','Laboratory critical flag present. Review the report notices.','notice'));
          const details=make('details','');details.append(make('summary',`${notes.length} notices`));
          for(const note of notes)details.append(make('p',note,'overview-review'));card.append(details);
        }
        if(/synthetic/i.test(get(`${domain.prefix}profile-note`)?.textContent||''))card.querySelector('h2').append(make('span',get(`${domain.prefix}profile`).value==='demo'?'Demo':'Example','example-label'));
      }
      const button=make('button',r?'View domain':'Add results','secondary');button.type='button';button.setAttribute('aria-label',`${button.textContent}: ${domain.name}`);button.addEventListener('click',()=>openDomain(domain.id));card.append(button);cards.append(card);
    }
    drawRadar();updateProgress();
  }
  function drawRadar(){
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 560 460');svg.setAttribute('role','img');svg.setAttribute('aria-labelledby','radar-title radar-desc');
    const add=(tag,attrs={},content)=>{const n=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);if(content!==undefined)n.textContent=content;svg.append(n);return n;};
    const xy=(axis,score)=>{const a=-Math.PI/2+axis*2*Math.PI/5,r=150*score/100;return[280+r*Math.cos(a),225+r*Math.sin(a)];};
    add('title',{id:'radar-title'},'Five-domain profile on a zero to one hundred point scale');
    for(const value of [20,40,60,80,100]){add('polygon',{points:domains.map((_,i)=>xy(i,value).join(',')).join(' '),class:'radar-grid'});const[x,y]=xy(0,value);add('text',{x:x+7,y:y+4,class:'radar-tick'},String(value));}
    add('text',{x:287,y:237,class:'radar-tick'},'0');const description=[];let count=0,scoredDomains=0;
    const vertices=domains.map((domain,i)=>{
      const point=points(results.get(domain.id),domain.id).find(valid);
      return point?xy(i,point.score):null;
    });
    if(vertices.every(Boolean))add('polygon',{points:vertices.map(p=>p.join(',')).join(' '),class:'radar-profile'});
    else vertices.forEach((point,i)=>{
      const next=vertices[(i+1)%domains.length];
      if(point&&next)add('line',{x1:point[0],y1:point[1],x2:next[0],y2:next[1],class:'radar-connection'});
    });
    for(const[i,domain]of domains.entries()){
      const[x,y]=xy(i,100);add('line',{x1:280,y1:225,x2:x,y2:y,class:'radar-axis'});const[lx,ly]=xy(i,128);add('text',{x:lx,y:ly,'text-anchor':'middle',class:'radar-label'},domain.name);
      const series=points(results.get(domain.id),domain.id).filter(valid);
      if(series.length)scoredDomains++;
      for(const p of series){const[px,py]=xy(i,p.score),mark=add('circle',{cx:px,cy:py,r:6,class:p.label==='Liver'?'radar-point radar-liver':'radar-point','data-domain':domain.id,'data-score':p.score});const title=document.createElementNS(ns,'title');title.textContent=`${p.label}: ${p.display_score??p.score} / 100`;mark.append(title);description.push(`${p.label}: ${p.display_score??p.score}`);count++;}
      if(!series.length){add('text',{x:lx,y:ly+18,'text-anchor':'middle',class:'radar-unavailable'},'No points available');description.push(`${domain.name}: no numerical points`);}
    }
    add('desc',{id:'radar-desc'},description.join('. ')+'. Missing axes have no point and are not assigned zero. Organ stress uses one weighted domain score.');get('domain-radar').replaceChildren(svg);
    get('radar-status').textContent=count?`${count} numerical point${count===1?'':'s'} across ${scoredDomains} of 5 domains. Open a domain card to see its full results.`:'No numerical points available yet. Open a domain card to enter biomarkers or review its results.';
  }
  draw();
})();
