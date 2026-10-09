const $ = id => document.getElementById(id);
let state = null, token = '', dirty = true, requestPending = false;
let previewTimer, previewPending = false, previewRevision = 0, eventsKey = "";
let previewGeometry = null;
const editIds = ['text','paper','style','font','line','margin','pen','speed'];
function setText(id, value) { const el=$(id); if(el.textContent!==value) el.textContent=value; }
function error(message) { setText('error',message); $('error').hidden=!message; }
async function api(path, body) {
  const response=await fetch(path, body===undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-Control-Token':token},body:JSON.stringify(body)});
  const data=await response.json();
  if(!response.ok) throw new Error(data.error || 'Anfrage fehlgeschlagen');
  return data;
}
function payload() {
  const [width,height]=$('paper').value.split(',').map(Number);
  return {text:$('text').value,width,height,style:$('style').value,font_height:Number($('font').value),line_height:Number($('line').value),margin:Number($('margin').value),speed_percent:Number($('speed').value),pen_s:Number($('pen').value)};
}
function render() {
  if(!state) return;
  const idle=state.connected&&!state.busy&&!requestPending&&!previewPending, validJob=state.job&&!dirty&&!previewPending;
  setText('connection',state.connected ? (state.busy ? 'Verbunden · aktiv':'Verbunden · bereit') : 'Nicht verbunden');
  $('dot').classList.toggle('on',state.connected);
  setText('mode',state.demo?'SIMULATION':'LOKAL'); $('mode').classList.toggle('demo',state.demo);
  setText('connect',state.connected?'Verbindung trennen':'Mit Roboter verbinden');
  $('connect').disabled=state.busy||requestPending||(!state.connected&&!$('port').value);
  $('port').disabled=state.connected||state.busy; $('refresh').disabled=state.busy;
  for(const id of ['origin','pen-up','pen-down']) $(id).disabled=!idle;
  document.querySelectorAll('[data-axis]').forEach(b=>b.disabled=!idle);
  $('calibrate').disabled=!idle||state.tested_s!==Number($('pen').value);
  setText('origin-state',state.origin?'✓ Startpunkt oben links gesetzt':'Startpunkt noch nicht gesetzt');
  setText('calibration',state.calibrated_s===null?'Stiftwert noch nicht bestätigt':'✓ Papierkontakt bei S'+state.calibrated_s+' bestätigt');
  $('prepare').disabled=state.busy||requestPending||previewPending;
  // Short servo actions must not interrupt typing or trigger a document repaint.
  const editingLocked=state.busy && !['Stift hoch','Stift absenken','Stiftwert bestätigen und anheben'].includes(state.operation);
  for(const id of editIds) $(id).disabled=editingLocked;
  updatePenPosition();
  $('dryrun').disabled=!(idle&&validJob&&state.origin&&$('area').checked);
  $('write').disabled=!(idle&&validJob&&state.origin&&$('area').checked&&state.dry_completed&&$('dry-ok').checked&&state.calibrated_s===state.job.settings.pen_down_s);
  $('dry-ok').disabled=!validJob||!state.dry_completed||state.busy;
  $('pause').disabled=!state.busy||!state.connected;
  setText('pause',state.paused?'Fortsetzen':'Pause');
  $('stop').disabled=!state.connected;
  setText('operation',(state.paused?'Pausiert · ':'')+(state.operation||'Bereit für deine Ideen')+(state.busy?' …':''));
  $('progress').max=state.total||1; $('progress').value=state.progress;
  setText('progress-text',state.progress+' / '+state.total);
  setText('identity',state.identity);
  setText('position',state.position?'Arbeitsposition X '+state.position.x.toFixed(2)+' / Y '+state.position.y.toFixed(2)+' mm':'Position unbekannt');
  const nextEventsKey=JSON.stringify(state.events);
  if(nextEventsKey!==eventsKey) {
    $('events').replaceChildren(...state.events.slice().reverse().map(event=>{const li=document.createElement('li'); li.textContent=event.time+'  '+event.message;return li;}));
    eventsKey=nextEventsKey;
  }
  document.querySelectorAll('.downloads a').forEach(a=>{a.style.pointerEvents=validJob?'auto':'none';a.style.opacity=validJob?'1':'.35';});
}
async function poll() {
  try {
    const next=await api('/api/state');
    if(next.error && next.error!==state?.error) error(next.error);
    state=next; token=next.token; render();
  } catch(e) {error('Server nicht erreichbar. Bei laufender Fahrt am Gerät prüfen.');}
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
  try {const data=await api('/api/ports');$('port').replaceChildren(...data.ports.map(p=>new Option(p.port+' · '+p.description,p.port)));if(!data.ports.length)$('port').add(new Option('Kein USB-Port gefunden',''));if(data.ports.some(p=>p.port==='COM4'))$('port').value='COM4';render();}catch(e){error(e.message);}
}
$('connect').onclick=()=>act(state.connected?'disconnect':'connect',{port:$('port').value});
$('refresh').onclick=ports;
$('origin').onclick=()=>{$('dry-ok').checked=false;act('origin');};
$('pen-up').onclick=()=>act('pen_up');
$('pen-down').onclick=()=>act('pen_down',{pen_s:Number($('pen').value)});
$('calibrate').onclick=()=>act('calibrate',{confirmed:true});
document.querySelectorAll('[data-axis]').forEach(b=>b.onclick=()=>{$('dry-ok').checked=false;act('jog',{axis:b.dataset.axis,distance:Number(b.dataset.sign)*Number($('step').value)});});
$('stop').onclick=()=>{$('dry-ok').checked=false;act('stop');};
$('pause').onclick=()=>act(state.paused?'resume':'pause');
$('dryrun').onclick=()=>{$('dry-ok').checked=false;act('dryrun',{job_id:state.job.id,area_confirmed:$('area').checked});};
$('write').onclick=()=>act('write',{job_id:state.job.id,area_confirmed:$('area').checked,dry_confirmed:$('dry-ok').checked});
async function preparePreview() {
  if (previewPending) return;
  if (state?.busy || requestPending) {
    if(dirty) { clearTimeout(previewTimer); previewTimer=setTimeout(preparePreview,500); }
    return;
  }
  clearTimeout(previewTimer);
  const revision=previewRevision, requested=payload();
  previewPending=true;render();error('');
  try {
    const result=await api('/api/prepare',requested);
    if(revision!==previewRevision) return;
    // Decode the replacement off-screen; leave the old document in place.
    const image=new Image();
    image.src='/api/preview?v='+result.job.id;
    await image.decode();
    if(revision!==previewRevision) return;
    $('preview').src=image.src;
    $('preview').hidden=false;
    $('document-sheet').hidden=false;
    previewGeometry=result.geometry;
    updatePreviewOverlays();
    $('empty-preview').hidden=true;
    dirty=false;$('dry-ok').checked=false;
    const b=result.job.bounds;
    setText('bounds','Tempo '+result.job.settings.speed_percent+' % · Fahrbereich: X '+b.x_min+'–'+b.x_max+' mm · Y '+b.y_min+'–'+b.y_max+' mm · '+result.job.strokes+' Striche');
    setText('paper-size',result.job.settings.page_width+' × '+result.job.settings.page_height+' mm');
    await poll();
  } catch(e){
    if(revision===previewRevision) error(e.message);
  } finally {
    previewPending=false;render();
    // An edit made during the request needs its own preview; never approve stale input.
    if(revision!==previewRevision) {
      clearTimeout(previewTimer);
      previewTimer=setTimeout(preparePreview,500);
    }
  }
}
$('prepare').onclick=preparePreview;
editIds.forEach(id=>$(id).addEventListener('input',()=>{
  previewRevision++;
  dirty=true;$('dry-ok').checked=false;
  setText('char-count',$('text').value.length+' / 1200');
  setText('bounds','Vorschau wird aktualisiert …');
  // Keep the current preview visible instead of collapsing and rebuilding it.
  clearTimeout(previewTimer);
  previewTimer=setTimeout(preparePreview,500);
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
  $('travel-overlay').hidden=!$('show-travel').checked;
  $('travel-overlay').style.display=$('show-travel').checked?'':'none';
  $('margin-overlay').style.display=$('show-margins').checked?'':'none';
  updatePenPosition();
}
function updatePenPosition() {
  const point=$('pen-position'), pos=state?.position;
  const visible=previewGeometry && state?.connected && state.frame_valid && pos && $('show-position').checked;
  point.style.display=visible?'':'none';
  point.removeAttribute('hidden');
  if(visible) {
    if(point.getAttribute('cx')!==String(pos.x)) point.setAttribute('cx',pos.x);
    if(point.getAttribute('cy')!==String(pos.y)) point.setAttribute('cy',pos.y);
  }
}
['show-travel','show-margins','show-position'].forEach(id=>$(id).onchange=updatePreviewOverlays);
['area','dry-ok'].forEach(id=>$(id).onchange=render);
// Never silently resume a saved job after reload; require a new preview.
setText('char-count',$('text').value.length+' / 1200');
(async()=>{await poll();await ports();await preparePreview();setInterval(poll,200);})();
