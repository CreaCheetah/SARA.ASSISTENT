from __future__ import annotations
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from src.app.dashboard.auth import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])

@router.get("/dashboard/live-settings", response_class=HTMLResponse)
def live_settings_page() -> str:
    return """
<!doctype html><html lang="nl"><head><meta charset="utf-8"/>
<title>Live instellingen</title>
<style>
 body{font-family:system-ui;margin:24px;max-width:760px}
 fieldset{border:1px solid #ddd;border-radius:8px;padding:12px 16px;margin:12px 0;background:#fff}
 legend{padding:0 6px;color:#333} label{display:inline-block;margin:6px 12px 6px 0}
 input[type=time],input[type=number]{padding:4px 6px} #msg{margin-left:12px}
 button{padding:10px 14px;border-radius:8px;border:1px solid #ccc;background:#f6f6f6;cursor:pointer}
</style></head><body>
<h2>Live instellingen</h2>
<fieldset><legend>Openingstijden</legend>
<label>Bot: <input id="bot_start" type="time"> - <input id="bot_end" type="time"></label><br/>
<label>Bezorging: <input id="del_start" type="time"> - <input id="del_end" type="time"></label><br/>
<label>Afhalen: <input id="pick_start" type="time"> - <input id="pick_end" type="time"></label>
<label><input id="pickup_flex_enabled" type="checkbox"> Flex tot 22:00</label></fieldset>
<fieldset><legend>Menu en vertragingen</legend>
<label><input id="pastas_enabled" type="checkbox"> Pasta's beschikbaar</label><br/>
<label>Vertraging pizza's (min): <input id="delay_pizzas_min" type="number" min="0" max="60" step="5"></label><br/>
<label>Vertraging schotels (min): <input id="delay_schotels_min" type="number" min="0" max="60" step="5"></label></fieldset>
<button id="saveBtn">Opslaan</button><span id="msg"></span>
<p style="margin-top:16px"><a href="/dashboard">Terug</a></p>
<script>
async function loadSettings(){
  const r=await fetch('/dashboard/api/settings',{credentials:'include'}); const s=await r.json();
  bot_start.value=s.bot_hours_daily.start; bot_end.value=s.bot_hours_daily.end;
  del_start.value=s.delivery_hours.start;  del_end.value=s.delivery_hours.end;
  pick_start.value=s.pickup_hours.start;   pick_end.value=s.pickup_hours.end;
  pickup_flex_enabled.checked=!!s.pickup_flex_enabled; pastas_enabled.checked=!!s.pastas_enabled;
  delay_pizzas_min.value=s.delay_pizzas_min; delay_schotels_min.value=s.delay_schotels_min;
}
async function saveSettings(){
  const p={bot_hours_daily:{start:bot_start.value,end:bot_end.value},
  delivery_hours:{start:del_start.value,end:del_end.value},
  pickup_hours:{start:pick_start.value,end:pick_end.value},
  pickup_flex_enabled:pickup_flex_enabled.checked,pastas_enabled:pastas_enabled.checked,
  delay_pizzas_min:parseInt(delay_pizzas_min.value||'0'),
  delay_schotels_min:parseInt(delay_schotels_min.value||'0')};
  const r=await fetch('/dashboard/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},
    credentials:'include',body:JSON.stringify(p)}); const out=await r.json();
  const el=document.getElementById('msg'); el.style.color=r.ok?'#0a0':'#a00'; el.textContent=out.message||'';
  setTimeout(()=>el.textContent='',3000);
}
document.getElementById('saveBtn').addEventListener('click',saveSettings); loadSettings();
</script></body></html>
"""
