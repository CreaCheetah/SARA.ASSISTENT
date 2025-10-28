from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()  # geen Basic Auth op Live-instellingen

@router.get("/dashboard/live-settings", response_class=HTMLResponse)
def live_settings_page() -> str:
    return """
<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8"/>
<title>Live instellingen</title>
<style>
  :root{--bg:#f6f4f2;--card:#fff;--ink:#222;--muted:#6b7280;--ok:#16a34a;--err:#b91c1c;--pri:#198754}
  html,body{background:var(--bg);font-family:system-ui,Segoe UI,Arial,sans-serif;color:var(--ink);margin:0}
  .wrap{max-width:980px;margin:28px auto;padding:0 16px}
  a.link{color:#2563eb;text-decoration:none}
  h1{font-size:22px;margin:6px 0 18px 0}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:22px}
  .card{background:var(--card);border-radius:14px;box-shadow:0 1px 4px rgba(0,0,0,.06);padding:18px}
  .card h3{margin:0 0 8px 0;font-size:16px}
  .note{color:var(--muted);font-size:13px;margin-top:4px}
  .row{display:flex;align-items:center;gap:12px;margin:8px 0}
  .pill{display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px}
  .pill.ok{background:#dcfce7;color:#166534}
  .pill.off{background:#fee2e2;color:#991b1b}
  .switch{position:relative;width:52px;height:28px;background:#e5e7eb;border-radius:999px;cursor:pointer;transition:background .15s}
  .switch.on{background:#22c55e}
  .knob{position:absolute;top:3px;left:3px;width:22px;height:22px;border-radius:999px;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.2);transition:left .15s}
  .switch.on .knob{left:27px}
  .slider{width:100%}
  .actions{display:flex;gap:10px;margin-top:14px}
  button{border:1px solid #d1d5db;border-radius:10px;padding:9px 14px;background:var(--pri);color:#fff;cursor:pointer}
  button.secondary{background:#f3f4f6;color:#111;border-color:#e5e7eb}
</style>
</head>
<body>
  <div class="wrap">
    <p><a class="link" href="/dashboard">← Terug</a></p>
    <h1>Live instellingen <span id="status" class="pill off">Sara is inactief</span></h1>

    <div class="grid">
      <div class="card">
        <h3>Botstatus</h3>
        <div class="row">
          <div id="bot_toggle" class="switch"><div class="knob"></div></div>
          <span>Sara actief</span>
        </div>
        <p class="note">Kill-switch. Buiten 16:00–22:00 is Sara sowieso uit.</p>
      </div>

      <div class="card">
        <h3>Menu-opties</h3>
        <div class="row">
          <div id="pasta_toggle" class="switch"><div class="knob"></div></div>
          <span>Pasta’s beschikbaar</span>
        </div>
      </div>

      <div class="card">
        <h3>Vertraging pizza’s</h3>
        <div class="row"><span>Huidig</span><span id="pizz_lbl">10 min</span></div>
        <input id="pizz_slider" class="slider" type="range" min="10" max="60" step="10" value="10"/>
      </div>

      <div class="card">
        <h3>Vertraging schotels</h3>
        <div class="row"><span>Huidig</span><span id="sch_lbl">10 min</span></div>
        <input id="sch_slider" class="slider" type="range" min="10" max="60" step="10" value="10"/>
      </div>

      <div class="card">
        <h3>Acties</h3>
        <div class="actions">
          <button id="saveBtn">Opslaan</button>
          <button id="reloadBtn" class="secondary">Herladen</button>
        </div>
        <p id="msg" class="note"></p>
      </div>
    </div>
  </div>

<script>
function setSwitch(el,on){el.classList.toggle('on',!!on)}
function valSwitch(el){return el.classList.contains('on')}
function bindSlider(id,label){
  const s=document.getElementById(id), l=document.getElementById(label);
  s.addEventListener('input',()=>{l.textContent=s.value+' min'})
}
function withinBotHours(){
  const now=new Date();
  const hh=now.getHours(), mm=now.getMinutes();
  const cur=hh*60+mm, start=16*60, end=22*60;
  return cur>=start && cur<=end;
}
function updateStatusBadge(botEnabled){
  const on = botEnabled && withinBotHours();
  const el=document.getElementById('status');
  el.textContent = on ? 'Sara is actief' : 'Sara is inactief';
  el.className = 'pill ' + (on ? 'ok' : 'off');
}

async function loadSettings(){
  const r=await fetch('/dashboard/api/settings',{credentials:'include'});
  const s=await r.json();
  setSwitch(document.getElementById('bot_toggle'), !!s.bot_enabled);
  setSwitch(document.getElementById('pasta_toggle'), !!s.pastas_enabled);

  const ps=Number(s.delay_pizzas_min||10), ss=Number(s.delay_schotels_min||10);
  const pizz=document.getElementById('pizz_slider'), sch=document.getElementById('sch_slider');
  pizz.value=ps; sch.value=ss;
  document.getElementById('pizz_lbl').textContent=ps+' min';
  document.getElementById('sch_lbl').textContent=ss+' min';

  updateStatusBadge(!!s.bot_enabled);
}

async function save(){
  const payload={
    bot_enabled: valSwitch(document.getElementById('bot_toggle')),
    pastas_enabled: valSwitch(document.getElementById('pasta_toggle')),
    delay_pizzas_min: parseInt(document.getElementById('pizz_slider').value||'10'),
    delay_schotels_min: parseInt(document.getElementById('sch_slider').value||'10')
  };
  const r=await fetch('/dashboard/api/settings',{
    method:'POST',headers:{'Content-Type':'application/json'},
    credentials:'include',body:JSON.stringify(payload)
  });
  const out=await r.json(); const el=document.getElementById('msg');
  el.style.color=r.ok?'#16a34a':'#b91c1c'; el.textContent= out.message || (r.ok?'Opgeslagen':'Fout');
  setTimeout(()=>el.textContent='',3000);
  updateStatusBadge(payload.bot_enabled);
}

function bindUI(){
  bindSlider('pizz_slider','pizz_lbl');
  bindSlider('sch_slider','sch_lbl');
  document.getElementById('reloadBtn').addEventListener('click',loadSettings);
  document.getElementById('saveBtn').addEventListener('click',save);
  ['bot_toggle','pasta_toggle'].forEach(id=>{
    document.getElementById(id).addEventListener('click',e=>e.currentTarget.classList.toggle('on'))
  });
}
bindUI(); loadSettings();
</script>
</body></html>
"""
