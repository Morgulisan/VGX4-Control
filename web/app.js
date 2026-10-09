const $ = id => document.getElementById(id);
let state = null, token = '', dirty = true, requestPending = false, serverAvailable = null;
let previewTimer, previewPending = false, previewRevision = 0, eventsKey = '';
let previewGeometry = null, previewError = '', displayedJobId = null, jobSummary = null;
let liveSpeedPending = false, liveSpeedTimer, liveSpeedRevision = 0;
const editIds = ['text','paper','typeface','style','font','line','margin','pen','speed','pen-pause'];
const numberIds = ['speed','font','line','margin','pen','pen-pause'];
const penOperations = ['Stift hoch','Stift absenken','Stiftwert bestätigen und anheben'];
const runOperations = ['Schreiben','Trockenlauf'];
const serverDown = 'Steuerungsserver nicht erreichbar. Läuft das Terminal noch? Bei laufender Fahrt am Gerät prüfen.';
const preferencesKey = 'vgx4.preferences.v1';
const preferenceIds = ['text','paper','typeface','style','font','line','margin','pen','speed','pen-pause','show-travel','show-margins','show-position'];
let preferences = {};

const stepValue = () => Number(document.querySelector('input[name=step]:checked').value);
const decimal = value => Number(value).toLocaleString('de-DE',{minimumFractionDigits:1,maximumFractionDigits:1});
const clock = seconds => { seconds=Math.max(0,Math.round(seconds)); return Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0'); };

function savePreferences() {
  try {
    for(const id of preferenceIds) { const el=$(id); preferences[id]=el.type==='checkbox'?el.checked:el.value; }
    preferences.step=String(stepValue());
    localStorage.setItem(preferencesKey,JSON.stringify(preferences));
  } catch (_) { /* Storage may be unavailable; controls remain usable. */ }
}
function restorePreferences() {
  try {
    const values=JSON.parse(localStorage.getItem(preferencesKey)||'{}');
    if(!values||typeof values!=='object'||Array.isArray(values)) return;
    preferences=values;
    for(const id of preferenceIds) {
      const el=$(id), value=values[id];
      if(el.type==='checkbox') {
        if(typeof value==='boolean') el.checked=value;
      } else if(el.tagName==='TEXTAREA') {
        if(typeof value==='string'&&value.trim()) el.value=value.slice(0,Number(el.maxLength));
      } else if(el.tagName==='SELECT') {
        if(typeof value==='string'&&Array.from(el.options).some(option=>option.value===value)) el.value=value;
      } else if(typeof value==='string'&&value.trim()!==''&&Number.isFinite(Number(value))) {
        const number=Number(value);
        if(number>=Number(el.min)&&number<=Number(el.max)) el.value=value;
      }
    }
    const step=document.querySelector('input[name=step][value="'+Number(values.step)+'"]');
    if(step) step.checked=true;
  } catch (_) { /* Ignore corrupt or inaccessible saved preferences. */ }
}
restorePreferences();
preferenceIds.forEach(id=>{
  $(id).addEventListener('input',savePreferences);
  $(id).addEventListener('change',savePreferences);
});
document.querySelectorAll('input[name=step]').forEach(radio=>radio.addEventListener('change',()=>{
  setText('jog-step',stepValue()+' mm');
  savePreferences();
}));

const themes = {auto:['◐','automatisch (System)'], light:['☀','hell'], dark:['☾','dunkel']};
function applyTheme() {
  const theme=Object.hasOwn(themes,preferences.theme)?preferences.theme:'auto';
  if(theme==='auto') delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme=theme;
  $('theme').textContent=themes[theme][0];
  $('theme').title='Farbschema: '+themes[theme][1];
}
$('theme').onclick=()=>{
  const order=Object.keys(themes);
  preferences.theme=order[(order.indexOf(Object.hasOwn(themes,preferences.theme)?preferences.theme:'auto')+1)%order.length];
  applyTheme();
  savePreferences();
};
applyTheme();

function setText(id, value) { const el=$(id); if(el.textContent!==value) el.textContent=value; }
function error(message) { setText('error-text',message); $('error').hidden=!message; }
$('error-close').onclick=()=>error('');
async function api(path, body) {
  const options={signal:AbortSignal.timeout(15000)};
  if(body!==undefined) Object.assign(options,{method:'POST',headers:{'Content-Type':'application/json','X-Control-Token':token},body:JSON.stringify(body)});
  const response=await fetch(path,options);
  const data=await response.json().catch(()=>({}));
  if(!response.ok) throw new Error(data.error||'Anfrage fehlgeschlagen ('+response.status+').');
  return data;
}
function payload() {
  const [width,height]=$('paper').value.split(',').map(Number);
  return {text:$('text').value,width,height,typeface:$('typeface').value,style:$('style').value,font_height:Number($('font').value),line_height:Number($('line').value),margin:Number($('margin').value),speed_percent:Number($('speed').value),pen_s:Number($('pen').value),pen_pause:Number($('pen-pause').value)};
}
// Catch half-typed or out-of-range numbers locally instead of flashing server errors while typing.
function inputProblem() {
  let problem='';
  for(const id of numberIds) {
    const el=$(id), v=el.validity, bad=v.badInput||v.rangeUnderflow||v.rangeOverflow||el.value.trim()==='';
    el.setAttribute('aria-invalid',String(bad));
    if(bad&&!problem) problem=el.dataset.label+': erlaubt sind '+String(el.min).replace('.',',')+' bis '+String(el.max).replace('.',',')+'.';
  }
  if(!problem&&!$('text').value.trim()) problem='Bitte Text eingeben.';
  return problem;
}

function readiness(s) {
  const previewOk=!!(s?.job&&!previewPending&&!previewError&&!dirty&&s.job.id===displayedJobId);
  const contactKnown=!!(s&&s.calibrated_s!==null&&s.calibrated_s===Number($('pen').value));
  return {connected:!!s?.connected, origin:!!s?.origin, preview:previewOk,
          contact:contactKnown||$('contact-ok').checked, contactKnown, area:$('area').checked};
}
function transientBlocker(s) {
  if(serverAvailable===false) return 'Keine Verbindung zum Steuerungsserver.';
  if(!s) return 'Roboterstatus wird geladen.';
  if(s.busy) return 'Vorgang läuft: '+(s.operation||'Roboter beschäftigt')+(s.paused?' (pausiert).':'.');
  if(requestPending) return 'Befehl wird bestätigt …';
  if(previewPending) return 'Vorschau wird erstellt …';
  return '';
}
function renderReadiness() {
  const s=state, c=readiness(s), blocker=transientBlocker(s);
  for(const key of ['connected','origin','preview','contact','area']) {
    $('check-'+key).classList.toggle('ok',c[key]);
    $('check-'+key).classList.toggle('todo',!c[key]);
  }
  let previewText='Vorschau aktuell';
  if(previewPending||(dirty&&!previewError)) previewText='Vorschau wird erstellt …';
  else if(previewError) previewText='Vorschau ungültig – Text oder Einstellungen anpassen';
  else if(s?.job&&displayedJobId&&s.job.id!==displayedJobId) previewText='Auftrag in einem anderen Tab geändert – Vorschau neu erstellen (↻)';
  setText('preview-check-text',previewText);
  $('contact-confirm').hidden=c.contactKnown;
  $('contact-done').hidden=!c.contactKnown;
  $('check-contact').classList.toggle('confirm',!c.contactKnown);
  document.querySelectorAll('.pen-value').forEach(el=>{ if(el.textContent!=='S'+$('pen').value) el.textContent='S'+$('pen').value; });
  const dryDone=!!(s?.dry_completed&&c.preview);
  $('check-dry').classList.toggle('ok',dryDone);
  setText('dry-text',dryDone?'Trockenlauf für diesen Auftrag abgeschlossen':'Trockenlauf mit Stift oben (optional)');
  const missing=['connected','origin','preview','contact','area'].filter(key=>!c[key]).length;
  setText('ready-count',missing?missing+' offen':'bereit');
  $('ready-count').className='badge '+(missing?'open':'ok');
  const ready=!missing&&!blocker;
  const message=blocker||(missing?(missing===1?'Noch 1 Punkt offen.':'Noch '+missing+' Punkte offen.'):'Bereit zum Schreiben. Trockenlauf ist optional.');
  $('write').disabled=!ready;
  $('write').title=message;
  setText('write-readiness',message);
  $('write-readiness').classList.toggle('ready',ready);
  $('dryrun').disabled=!(c.connected&&c.origin&&c.preview&&c.area&&!blocker);
}
function renderStats() {
  const el=$('job-stats'), failed=!!previewError&&!previewPending;
  el.classList.toggle('error',failed);
  if(failed) return setText('job-stats','⚠ '+previewError);
  if(!jobSummary) return setText('job-stats','Noch keine Vorschau');
  const j=jobSummary, b=j.bounds;
  const items=[['Dauer','ca. '+clock(j.duration)+' min'],['davon Stiftpausen',clock(j.pen_time)+' min'],['Striche',String(j.strokes)],['Tempo',j.settings.speed_percent+' %'],
               ['Fahrbereich','X '+decimal(b.x_min)+'–'+decimal(b.x_max)+' · Y '+decimal(b.y_min)+'–'+decimal(b.y_max)+' mm']];
  el.replaceChildren(...items.flatMap(([label,value],i)=>{ const strong=document.createElement('b'); strong.textContent=value; return [(i?' · ':'')+label+' ',strong]; }));
}
function renderPreviewStatus() {
  const updating=previewPending||(dirty&&!previewError), failed=!!previewError&&!previewPending;
  $('paper-stage').classList.toggle('updating',updating);
  $('paper-stage').classList.toggle('invalid',failed);
  setText('preview-status',updating?'wird aktualisiert …':failed?'ungültig':'');
  $('preview-status').classList.toggle('error',failed);
  setText('empty-preview',failed?'Keine Vorschau – siehe Hinweis unten.':'Vorschau wird erstellt …');
  renderStats();
}
function renderRunbar(s, visible) {
  $('runbar').hidden=!visible;
  document.body.classList.toggle('running',visible);
  if(!visible) return;
  const run=runOperations.includes(s.operation);
  setText('operation',(s.paused?'Pausiert · ':'')+s.operation+(s.paused?'':' …'));
  const parts=[];
  if(s.total) parts.push(Math.floor(100*s.progress/s.total)+' %');
  if(s.elapsed!==null) parts.push(clock(s.elapsed)+' vergangen');
  if(s.remaining!==null) parts.push('noch ca. '+clock(s.remaining));
  setText('progress-text',parts.join(' · '));
  if(s.total) { $('progress').max=s.total; $('progress').value=s.progress; }
  else $('progress').removeAttribute('value');
  $('speed-control').hidden=!run;
  $('live-speed').disabled=!(s.connected&&run);
  if(document.activeElement!==$('live-speed')&&!liveSpeedPending) { $('live-speed').value=s.live_speed; setText('live-speed-value',s.live_speed+' %'); }
  $('pause').hidden=!run;
  $('pause').disabled=!s.connected;
  setText('pause',s.paused?'Fortsetzen':'Pause');
  $('stop').disabled=!s.connected;
}
function renderResult(s) {
  const r=s.result, show=!!(!s.busy&&r&&(runOperations.includes(r.operation)||!r.ok));
  $('last-result').hidden=!show;
  if(!show) return;
  $('last-result').classList.toggle('failed',!r.ok);
  const next=r.operation==='Schreiben'&&!$('area').checked?' Für das nächste Blatt den freien Fahrbereich erneut bestätigen.':'';
  setText('last-result',r.ok?'✓ '+r.operation+' abgeschlossen um '+r.time+' · Dauer '+clock(r.seconds)+' min.'+next:'✕ '+r.operation+' fehlgeschlagen um '+r.time+': '+r.message);
}
function render() {
  renderReadiness();
  if(!state) return;
  const s=state, idle=s.connected&&!s.busy&&!requestPending&&!previewPending, shortOperation=penOperations.includes(s.operation);
  const simulated=s.connected&&s.demo, simulationServer=!!s.simulation_only;
  setText('connection',s.connected?(simulated?'Simulation':'Verbunden')+(s.busy?' · aktiv':' · bereit'):(s.busy?s.operation+' …':'Nicht verbunden'));
  $('dot').classList.toggle('on',s.connected&&!s.busy);
  $('dot').classList.toggle('busy',s.busy);
  $('mode').hidden=!(simulated||simulationServer);
  $('sim-banner').hidden=!(simulated||simulationServer);
  setText('sim-title',simulationServer?'Simulationsmodus (--demo)':'Simulation aktiv');
  setText('sim-text',simulationServer?'Dieser Server zeigt keine echten Roboter. Für den echten Roboter START_WINDOWS.bat ohne --demo starten.':'kein echter Roboter verbunden. Es wird nichts bewegt und nichts geschrieben.');
  $('sim-end').hidden=simulationServer||!simulated;
  $('sim-end').disabled=s.busy||requestPending;
  // The pen moves up and down throughout a job; only show its state between operations.
  $('pen-state').hidden=!s.connected||(s.busy&&!shortOperation);
  setText('pen-state',{up:'Stift oben',down:'Stift unten'}[s.pen]||'Stift unbekannt');
  setText('connect',s.busy&&s.operation==='Verbinden'?'Verbinde …':simulated?'Simulation beenden':s.connected?'Verbindung trennen':'Mit Roboter verbinden');
  $('connect').disabled=s.busy||requestPending||(!s.connected&&!$('port').value);
  $('port').disabled=s.connected||s.busy; $('refresh').disabled=s.connected||s.busy;
  $('simulate-box').hidden=s.connected||simulationServer;
  $('simulate').disabled=s.busy||requestPending;
  setText('connected-text',simulated?'Simulation verbunden (kein echter Roboter)':'Roboter verbunden');
  setText('write',simulated?'Simuliert schreiben →':'Auf Papier schreiben →');
  for(const id of ['origin','pen-up','pen-down']) $(id).disabled=!idle;
  document.querySelectorAll('[data-axis]').forEach(b=>b.disabled=!idle);
  const penValue=Number($('pen').value), penDownHere=s.tested_s!==null&&s.tested_s===penValue;
  $('calibrate').disabled=!idle||!penDownHere;
  setText('origin-state',s.origin?'Startpunkt gesetzt · 0 / 0':s.connected?'Wagen zur oberen linken Papierecke fahren, dann Startpunkt setzen.':'Zuerst verbinden.');
  $('origin-state').className='status'+(s.origin?' ok':'');
  setText('jog-hint',s.origin?'Bewegen verwirft den gesetzten Startpunkt. Der Stift wird vorher angehoben.':'Der Stift wird vor jeder Bewegung angehoben. Nur bei freiem Fahrweg bewegen.');
  let calibration='Stift runter, Kontakt prüfen, dann bestätigen.', calibrationClass='';
  if(s.calibrated_s!==null&&s.calibrated_s===penValue) { calibration='Papierkontakt bei S'+penValue+' bestätigt'; calibrationClass=' ok'; }
  else if(penDownHere) { calibration='Stift ist unten bei S'+penValue+'. Kontakt am Papier prüfen, dann bestätigen.'; calibrationClass=' todo'; }
  else if(s.calibrated_s!==null) calibration='Bestätigt ist S'+s.calibrated_s+'. Für S'+penValue+' erneut absenken und prüfen.';
  setText('calibration',calibration);
  $('calibration').className='status'+calibrationClass;
  $('prepare').disabled=s.busy||requestPending||previewPending;
  // Short servo actions must not interrupt typing or trigger a document repaint.
  const editingLocked=s.busy&&!shortOperation;
  for(const id of editIds) $(id).disabled=editingLocked;
  updatePenPosition();
  renderRunbar(s,s.busy&&!shortOperation&&s.operation!=='Verbinden');
  renderResult(s);
  setText('identity',s.identity);
  setText('position',s.position?'Arbeitsposition X '+decimal(s.position.x)+' / Y '+decimal(s.position.y)+' mm':'Position unbekannt');
  const nextEventsKey=JSON.stringify(s.events);
  if(nextEventsKey!==eventsKey) {
    $('events').replaceChildren(...s.events.slice().reverse().map(event=>{const li=document.createElement('li'); li.textContent=event.time+'  '+event.message;return li;}));
    eventsKey=nextEventsKey;
  }
  const validJob=readiness(s).preview;
  document.querySelectorAll('.downloads a').forEach(a=>{ a.setAttribute('aria-disabled',String(!validJob)); a.tabIndex=validJob?0:-1; });
}
async function poll() {
  try {
    const next=await api('/api/state');
    if(next.error&&next.error!==state?.error) error(next.error);
    if($('error-text').textContent===serverDown) error('');
    // A finished write used up the confirmed sheet; the next job needs a fresh confirmation.
    if(state?.busy&&state.operation==='Schreiben'&&!next.busy&&next.result?.ok) $('area').checked=false;
    serverAvailable=true; state=next; token=next.token; render();
  } catch(e) {serverAvailable=false; render(); error(serverDown);}
}
async function pollLoop() {
  await poll();
  setTimeout(pollLoop,state?.busy?200:serverAvailable===false?1000:document.hidden?2000:600);
}
async function act(name, data={}) {
  requestPending=true; render(); error('');
  try {
    await api('/api/action/'+name,data);
    await poll();
    if(['pen_up','pen_down','calibrate'].includes(name)) {
      while(state?.busy) {
        await new Promise(resolve=>setTimeout(resolve,60));
        await poll();
      }
    }
  }
  catch(e) {error(e.message);} finally {requestPending=false;render();}
}
async function ports() {
  try {
    const data=await api('/api/ports'), select=$('port'), previous=select.value;
    select.replaceChildren(...data.ports.map(p=>new Option(p.port+' · '+p.description,p.port)));
    if(!data.ports.length) select.add(new Option('Kein USB-Port gefunden',''));
    const preferred=[previous,preferences.port,'COM4'].find(port=>port&&data.ports.some(p=>p.port===port));
    if(preferred) select.value=preferred;
    setText('connect-hint',data.ports.length?'115200 Baud · VigoWriter 1.1f':'Roboter einschalten, USB-Kabel prüfen, dann ↻ drücken.');
    render();
  } catch(e) {error(e.message);}
}
$('connect').onclick=()=>{
  if(!state.connected) { preferences.port=$('port').value; savePreferences(); }
  act(state.connected?'disconnect':'connect',{port:$('port').value});
};
$('simulate').onclick=()=>{ $('simulate-box').open=false; act('connect',{simulate:true}); };
$('sim-end').onclick=()=>act('disconnect');
$('refresh').onclick=ports;
$('origin').onclick=()=>act('origin');
$('pen-up').onclick=()=>act('pen_up');
$('pen-down').onclick=()=>act('pen_down',{pen_s:Number($('pen').value)});
$('calibrate').onclick=()=>act('calibrate',{confirmed:true});
document.querySelectorAll('[data-axis]').forEach(b=>b.onclick=()=>act('jog',{axis:b.dataset.axis,distance:Number(b.dataset.sign)*stepValue()}));
$('stop').onclick=()=>act('stop');
$('pause').onclick=()=>act(state.paused?'resume':'pause');
$('dryrun').onclick=()=>act('dryrun',{job_id:displayedJobId,area_confirmed:$('area').checked});
$('write').onclick=()=>act('write',{job_id:displayedJobId,area_confirmed:$('area').checked,contact_confirmed:$('contact-ok').checked});
document.querySelectorAll('[data-goto]').forEach(b=>b.onclick=()=>{
  const target=$(b.dataset.goto);
  target.scrollIntoView({behavior:'smooth',block:'center'});
  target.focus({preventScroll:true});
});
async function preparePreview() {
  if (previewPending) return;
  if (state?.busy || requestPending) {
    if(dirty) { clearTimeout(previewTimer); previewTimer=setTimeout(preparePreview,500); }
    return;
  }
  clearTimeout(previewTimer);
  const problem=inputProblem();
  if(problem) { previewError=problem; renderPreviewStatus(); render(); return; }
  const revision=previewRevision, requested=payload();
  previewPending=true;previewError='';renderPreviewStatus();render();
  try {
    const result=await api('/api/prepare',requested);
    if(revision!==previewRevision) return;
    // Decode the replacement off-screen; leave the old document in place.
    const image=new Image();
    image.src='/api/preview?v='+result.job.id;
    await image.decode();
    if(revision!==previewRevision) return;
    previewGeometry=result.geometry;
    $('document-sheet').style.setProperty('--ratio',previewGeometry.width/previewGeometry.height);
    $('preview').src=image.src;
    $('document-sheet').hidden=false;
    $('empty-preview').hidden=true;
    displayedJobId=result.job.id;
    jobSummary=result.job;
    updatePreviewOverlays();
    dirty=false;
    setText('paper-size',result.job.settings.page_width+' × '+result.job.settings.page_height+' mm');
    await poll();
  } catch(e){
    if(revision===previewRevision) previewError=e.message;
  } finally {
    previewPending=false;renderPreviewStatus();render();
    // An edit made during the request needs its own preview; never approve stale input.
    if(revision!==previewRevision) {
      clearTimeout(previewTimer);
      previewTimer=setTimeout(preparePreview,500);
    }
  }
}
$('prepare').onclick=preparePreview;
function updateCharCount() {
  const count=$('text').value.length;
  setText('char-count',count+' / 1200');
  $('char-count').classList.toggle('near',count>1100);
}
editIds.forEach(id=>$(id).addEventListener('input',()=>{
  if(id==='pen') $('contact-ok').checked=false;
  previewError='';
  previewRevision++;
  dirty=true;
  inputProblem();
  updateCharCount();
  // Keep the current preview visible instead of collapsing and rebuilding it.
  clearTimeout(previewTimer);
  previewTimer=setTimeout(preparePreview,500);
  renderPreviewStatus();
  render();
}));
function updatePreviewOverlays() {
  if(!previewGeometry) return;
  const g=previewGeometry, m=g.margins;
  $('preview-overlay').setAttribute('viewBox','0 0 '+g.width+' '+g.height);
  $('travel-overlay').setAttribute('d',g.travel.map(([a,b])=>'M'+a.join(',')+' L'+b.join(',')).join(' '));
  const r=$('margin-overlay');
  r.setAttribute('x',m.x);r.setAttribute('y',m.top);
  r.setAttribute('width',g.width-2*m.x);r.setAttribute('height',g.height-m.top-m.bottom);
  $('travel-overlay').style.display=$('show-travel').checked?'':'none';
  $('margin-overlay').style.display=$('show-margins').checked?'':'none';
  updatePenPosition();
}
function updatePenPosition() {
  const point=$('pen-position'), pos=state?.position;
  const visible=previewGeometry && state?.connected && state.frame_valid && pos && $('show-position').checked;
  point.style.display=visible?'':'none';
  if(visible) {
    if(point.getAttribute('cx')!==String(pos.x)) point.setAttribute('cx',pos.x);
    if(point.getAttribute('cy')!==String(pos.y)) point.setAttribute('cy',pos.y);
  }
}
['show-travel','show-margins','show-position'].forEach(id=>$(id).onchange=updatePreviewOverlays);
['area','contact-ok'].forEach(id=>$(id).onchange=render);
$('live-speed').oninput=()=>{
  setText('live-speed-value',$('live-speed').value+' %');
  const revision=++liveSpeedRevision;
  liveSpeedPending=true;
  clearTimeout(liveSpeedTimer);
  liveSpeedTimer=setTimeout(async()=>{
    try { await api('/api/action/speed',{percent:Number($('live-speed').value)}); }
    catch(e) { error(e.message); }
    finally { if(revision===liveSpeedRevision) { liveSpeedPending=false; await poll(); } }
  },100);
};
// Never silently resume a saved job after reload; require a new preview.
setText('jog-step',stepValue()+' mm');
updateCharCount();
renderReadiness();
(async()=>{await poll();await ports();await preparePreview();pollLoop();})();
