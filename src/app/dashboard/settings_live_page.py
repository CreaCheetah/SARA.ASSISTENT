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
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600&family=Poppins:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#faf9f6; --card:#ffffff; --ink:#222; --muted:#6b7280;
    --green:#1f6f4a; --green-soft:#e6f3ed; --red:#b4231a; --pri:#1f6f4a;
    --shadow:0 1px 4px rgba(0,0,0,.06);
  }
  html,body{background:var(--bg); color:var(--ink); margin:0}
  body{font-family:Poppins,system-ui,Arial,sans-serif}
  h1,h2,h3{font-family:"Playfair Display",serif}
  .wrap{max-width:980px;margin:28px auto;padding:0 16px}
  .top{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
  a.link{color:#1d4ed8;text-decoration:none}
  .badge{padding:6px 12px;border-radius:999px;font-size:13px}
  .badge.on{background:#dcfce7;color:#166534}
  .badge.off{background:#fee2e2;color:#991b1b}
  .grid{display:grid;grid-template-columns:1fr;gap:22px;margin-top:16px}
  @media(min-width:900px){ .grid{grid-template-columns:1fr 1fr} }
  .card{background:var(--card);border-radius:14px;box-shadow:var(--shadow);padding:18px}
  .card h3{margin:0 0 8px 0;font-size:18px}
  .note{color:var(--muted);font-size:13px;margin-top:4px}
  .row{display:flex;align-items:center;gap:12px;margin:10px 0}
  .switch{position:relative;width:64px;height:34px;background:#e5e7eb;border-radius:999px;cursor:pointer;transition:background .15s}
  .switch.on{background:#22c55e}
  .knob{position:absolute;top:3px;left:3px;width:28px;height:28px;border-radius:999px;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.2);transition:left .15s}
  .switch.on .knob{left:33px}
  .switch + span{min-width:160px}
  .slider{width:100%}
  .ticks{display:flex;justify-content:space-between;font-size:12px;color:#555;margin-top:4px}
  .stickybar{position:sticky;bottom:0;background:rgba(250,249,246,.9);backdrop-filter:saturate(150%) blur(2px);
             padding:12px 0;margin-top:12px;border-top:1px solid #eee}
  .actions{display:flex;gap:10px;justify-content:space-between}
  button{border:1px solid #d1d5db;border-radius:10px;padding:12px 16px;cursor:pointer;font-weight:600}
  .primary{background:var(--green);color:#fff;border-color:#18583a}
  .secondary{background:#f3f4f6;color:#111;border-color:#e5e7eb}
</style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <p><a class="link" href="/dashboard">← Terug</a></p>
      <h1 style="margin:6px 0">Live instellingen</h1>
      <span id="status" class="badge off">Sara is inactief</span>
    </div>

    <div class="card" style="grid-column:1 / -1">
      <h3>Botstatus</h3>
      <div class="row">
        <div id="bot_toggle" class="switch"><div class="knob"></div></div>
        <span>Sara actief</span>
      </div>
      <p class="note">Buiten 16:00–22:00 is Sara automatisch uit.</p>
    </div>

    <div class="grid">
      <div class="card">
        <h3>Menu-opties</h3>
        <div class="row">
          <div id="pasta_toggle" class="switch"><div class="knob"></div></div>
          <span>Pasta’s beschikbaar</span>
        </div>
        <div class="row">
          <div id="pickup_toggle" class="switch"><div class="knob"></div></div>
          <span>Afhalen ingeschakeld</span>
        </div>
      </div>

      <div class="card">
        <h3>Vertraging pizza’s</h3>
        <div class="row"><strong id="pizz_lbl">10 min</strong></div>
        <input id="pizz_slider" class="slider" type="range" min="10" max="60" step="10" value="10"/>
        <div class="ticks"><span>10</span><span>20</span><span>30</span><span>40</span><span>50</span><span>60</span></div>
      </div>

      <div class="card">
        <h3>Vertraging schotels</h3>
        <div class="row"><strong id="sch_lbl">10 min</strong></div>
        <input id="sch_slider" class="slider" type="range" min="10" max="60" step="10" value="10"/>
        <div class="ticks"><span>10</span><span>20</span><span>30</span><span>40</span><span>50</span><span>60</span></div>
      </div>
    </div>

    <div class="stickybar">
      <div class="actions">
        <button id="reloadBtn" class="secondary">Herladen</button>
        <div style="display:flex;gap:10px">
          <span id="msg" class="note" style="align-self:center"></span>
          <button id="saveBtn" class="primary">Opslaan</button>
        </div>
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
  const now=new Date(), cur=now.getHours()*60+now.getMinutes();
  return cur>=16*60 && cur<=22*60;
}
function updateStatusBadge(botEnabled){
  const on = botEnabled && withinBotHours();
  const el=document.getElementById('status');
  el.textContent = on ? 'Sara is actief' : 'Sara is inactief';
  el.className = 'badge ' + (on ? 'on' : 'off');
}

async function loadSettings(){
  const r=await fetch('/dashboard/api/settings',{credentials:'include'});
  const s=await r.json();
  setSwitch(document.getElementById('bot_toggle'), !!s.bot_enabled);
  setSwitch(document.getElementById('pasta_toggle'), !!s.pastas_enabled);
  setSwitch(document.getElementById('pickup_toggle'), !!s.pickup_enabled);

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
    pickup_enabled: valSwitch(document.getElementById('pickup_toggle')),
    delay_pizzas_min: parseInt(document.getElementById('pizz_slider').value||'10'),
    delay_schotels_min: parseInt(document.getElementById('sch_slider').value||'10')
  };
  const r=await fetch('/dashboard/api/settings',{
    method:'POST',headers:{'Content-Type':'application/json'},
    credentials:'include',body:JSON.stringify(payload)
  });
  const out=await r.json();
  const el=document.getElementById('msg');
  el.style.color=r.ok?'#1f6f4a':'#b4231a';
  el.textContent= out.message || (r.ok?'Opgeslagen':'Fout');
  setTimeout(()=>el.textContent='',3000);
  updateStatusBadge(payload.bot_enabled);
}

function bindUI(){
  bindSlider('pizz_slider','pizz_lbl');
  bindSlider('sch_slider','sch_lbl');
  document.getElementById('reloadBtn').addEventListener('click',loadSettings);
  document.getElementById('saveBtn').addEventListener('click',save);
  ['bot_toggle','pasta_toggle','pickup_toggle'].forEach(id=>{
    document.getElementById(id).addEventListener('click',e=>e.currentTarget.classList.toggle('on'))
  });
}
bindUI(); loadSettings();
</script>
</body></html>
"""
