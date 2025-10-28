from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()  # géén Depends(require_admin)

@router.get("/dashboard/live-settings", response_class=HTMLResponse)
def live_settings_page() -> str:
    return """
<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8"/>
<title>Belservice • Live instellingen</title>
<style>
  :root{--bg:#f6f4f2;--card:#ffffff;--ink:#222;--muted:#6b7280;--ok:#16a34a;--warn:#d97706;--pri:#0ea5e9}
  html,body{background:var(--bg);font-family:system-ui,Segoe UI,Arial,sans-serif;color:var(--ink);margin:0}
  .wrap{max-width:980px;margin:28px auto;padding:0 16px}
  a.link{color:#2563eb;text-decoration:none}
  h1{font-size:22px;margin:6px 0 18px 0}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:22px}
  .card{background:var(--card);border-radius:14px;box-shadow:0 1px 4px rgba(0,0,0,.06);padding:18px}
  .card h3{margin:0 0 8px 0;font-size:16px}
  .note{color:var(--muted);font-size:13px;margin-top:4px}
  .row{display:flex;align-items:center;gap:12px;margin:8px 0}
  .switch{position:relative;width:52px;height:28px;background:#e5e7eb;border-radius:999px;cursor:pointer;transition:background .15s}
  .switch.on{background:#22c55e}
  .knob{position:absolute;top:3px;left:3px;width:22px;height:22px;border-radius:999px;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.2);transition:left .15s}
  .switch.on .knob{left:27px}
  .slider{width:100%}
  .actions{display:flex;gap:10px;margin-top:14px}
  button{border:1px solid #d1d5db;border-radius:10px;padding:9px 14px;background:#10b981;color:#fff;cursor:pointer}
  button.secondary{background:#f3f4f6;color:#111;border-color:#e5e7eb}
  .brand{float:right;font-size:20px}
</style>
</head>
<body>
  <div class="wrap">
    <p><a class="link" href="/dashboard">← Terug</a> <span class="brand">🇮🇹</span></p>
    <h1>Belservice • Live instellingen</h1>

    <div class="grid">
      <div class="card">
        <h3>Botstatus</h3>
        <div class="row">
          <div id="bot_toggle" class="switch"><div class="knob"></div></div>
          <span>Belbot actief</span>
        </div>
        <p class="note">Zet de belbot aan/uit. Buiten boottijden wordt automatisch uitgeschakeld.</p>
      </div>

      <div class="card">
        <h3>Menu-opties</h3>
        <div class="row">
          <div id="pasta_toggle" class="switch"><div class="knob"></div></div>
          <span>Pasta’s beschikbaar</span>
        </div>
      </div>

      <div class="card">
        <h3>Extra bereidingstijd (ophalen)</h3>
        <div class="row"><span>Huidige instelling</span><span id="mins_lbl">0 min</span></div>
        <input id="prep_slider" class="slider" type="range" min="0" max="60" step="5" value="0"/>
        <p class="note">Wordt toegepast op wachttijd voor afhalen. Voor nu wordt dezelfde waarde op pizza’s en schotels gezet.</p>
      </div>

      <div class="card">
        <h3>Acties</h3>
        <div class="actions">
          <button id="saveBtn">Opslaan</button>
          <button id="reloadBtn" class="secondary">Herladen</button>
        </div>
      </div>
    </div>

    <p id="msg" class="note" style="margin-top:14px"></p>
  </div>

<script>
let state=null;

function setSwitch(el, on){ el.classList.toggle('on', !!on); }
function valSwitch(el){ return el.classList.contains('on'); }

async function loadSettings(){
  const r=await fetch('/dashboard/api/settings',{credentials:'include'});
  if(!r.ok){document.getElementById('msg').textContent='Fout bij laden';return;}
  state=await r.json();

  // UI vullen
  setSwitch(document.getElementById('pasta_toggle'), !!state.pastas_enabled);

  // Bot "aan" afleiden: binnen tijdvenster == aan
  const botOn = true; // visuele toggle; runtime-cutoff doen we in call-flow
  setSwitch(document.getElementById('bot_toggle'), botOn);

  // Slider toont één waarde; we koppelen aan beide vertragingen
  const curDelay = Number(state.delay_pizzas_min||0);
  document.getElementById('prep_slider').value = curDelay;
  document.getElementById('mins_lbl').textContent = curDelay+' min';
}

function bindUI(){
  const slider=document.getElementById('prep_slider');
  slider.addEventListener('input',()=>{document.getElementById('mins_lbl').textContent=slider.value+' min';});

  document.getElementById('reloadBtn').addEventListener('click', loadSettings);

  document.getElementById('saveBtn').addEventListener('click', async ()=>{
    const payload={
      pastas_enabled: valSwitch(document.getElementById('pasta_toggle')),
      delay_pizzas_min: parseInt(document.getElementById('prep_slider').value||'0'),
      delay_schotels_min: parseInt(document.getElementById('prep_slider').value||'0')
    };
    const r=await fetch('/dashboard/api/settings',{
      method:'POST',headers:{'Content-Type':'application/json'},
      credentials:'include',body:JSON.stringify(payload)
    });
    const out=await r.json();
    const el=document.getElementById('msg');
    el.style.color=r.ok?'#16a34a':'#b91c1c';
    el.textContent= out.message || (r.ok?'Opgeslagen':'Fout');
    setTimeout(()=>el.textContent='',3000);
  });

  // visuele bot-toggle zonder opslag
  document.getElementById('bot_toggle').addEventListener('click', e=>{
    e.currentTarget.classList.toggle('on');
  });
  document.getElementById('pasta_toggle').addEventListener('click', e=>{
    e.currentTarget.classList.toggle('on');
  });
}

bindUI();
loadSettings();
</script>
</body>
</html>
"""
