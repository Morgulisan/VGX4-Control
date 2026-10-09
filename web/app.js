const $ = id => document.getElementById(id);
let state = null, token = '', dirty = true, requestPending = false;
let previewTimer;
const editIds = ['text','paper','style','font','line','margin','pen','speed'];
function error(message) { $('error').textContent=message; $('error').hidden=!message; }
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
  const idle=state.connected&&!state.busy&&!requestPending, validJob=state.job&&!dirty;
  $('connection').textContent=state.connected ? (state.busy ? 'Verbunden · aktiv':'Verbunden · bereit') : 'Nicht verbunden';
  $('dot').classList.toggle('on',state.connected);
  $('mode').textContent=state.demo?'SIMULATION':'LOKAL'; $('mode').classList.toggle('demo',state.demo);
  $('connect').textContent=state.connected?'Verbindung trennen':'Mit Roboter verbinden';
  $('connect').disabled=state.busy||requestPending||(!state.connected&&!$('port').value);
  $('port').disabled=state.connected||state.busy; $('refresh').disabled=state.busy;
  for(const id of ['origin','pen-up','pen-down']) $(id).disabled=!idle;
  document.querySelectorAll('[data-axis]').forEach(b=>b.disabled=!idle);
  $('calibrate').disabled=!idle||state.tested_s!==Number($('pen').value);
  $('origin-state').textContent=state.origin?'✓ Startpunkt oben links gesetzt':'Startpunkt noch nicht gesetzt';
  $('calibration').textContent=state.calibrated_s===null?'Stiftwert noch nicht bestätigt':'✓ Papierkontakt bei S'+state.calibrated_s+' bestätigt';
  $('prepare').disabled=state.busy||requestPending;
  for(const id of editIds) $(id).disabled=state.busy||requestPending;
  $('dryrun').disabled=!(idle&&validJob&&state.origin&&$('area').checked);
  $('write').disabled=!(idle&&validJob&&state.origin&&$('area').checked&&state.dry_completed&&$('dry-ok').checked&&state.calibrated_s===state.job.settings.pen_down_s);
  $('dry-ok').disabled=!validJob||!state.dry_completed||state.busy;
  $('pause').disabled=!state.busy||!state.connected;
  $('pause').textContent=state.paused?'Fortsetzen':'Pause';
  $('stop').disabled=!state.connected;
  $('operation').textContent=(state.paused?'Pausiert · ':'')+(state.operation||'Bereit für deine Ideen')+(state.busy?' …':'');
  $('progress').max=state.total||1; $('progress').value=state.progress;
  $('progress-text').textContent=state.progress+' / '+state.total;
  $('identity').textContent=state.identity;
  $('position').textContent=state.position?'Arbeitsposition X '+state.position.x.toFixed(2)+' / Y '+state.position.y.toFixed(2)+' mm':'Position unbekannt';
  $('events').replaceChildren(...state.events.slice().reverse().map(event=>{const li=document.createElement('li'); li.textContent=event.time+'  '+event.message;return li;}));
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
  try { await api('/api/action/'+name,data); await poll(); }
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
  if (state?.busy || requestPending) return;
  clearTimeout(previewTimer);
  requestPending=true;render();error('');
  try {
    const result=await api('/api/prepare',payload());
    dirty=false;$('dry-ok').checked=false;
    $('preview').src='/api/preview?v='+result.job.id;$('preview').hidden=false;$('empty-preview').hidden=true;
    const b=result.job.bounds;
    $('bounds').textContent='Tempo '+result.job.settings.speed_percent+' % · Fahrbereich: X '+b.x_min+'–'+b.x_max+' mm · Y '+b.y_min+'–'+b.y_max+' mm · '+result.job.strokes+' Striche';
    $('paper-size').textContent=result.job.settings.page_width+' × '+result.job.settings.page_height+' mm';
    await poll();
  } catch(e){error(e.message);}finally{requestPending=false;render();}
}
$('prepare').onclick=preparePreview;
editIds.forEach(id=>$(id).addEventListener('input',()=>{dirty=true;$('dry-ok').checked=false;$('char-count').textContent=$('text').value.length+' / 1200';$('bounds').textContent='Vorschau wird aktualisiert …';$('preview').hidden=true;$('empty-preview').hidden=false;
clearTimeout(previewTimer);previewTimer=setTimeout(preparePreview,500);render();}));
['area','dry-ok'].forEach(id=>$(id).onchange=render);
// Never silently resume a saved job after reload; require a new preview.
$('char-count').textContent=$('text').value.length+' / 1200';
(async()=>{await poll();await ports();await preparePreview();setInterval(poll,700);})();
