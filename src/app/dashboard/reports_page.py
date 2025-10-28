from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from src.infra.db import engine

router = APIRouter()

@router.get("/dashboard/reports", response_class=HTMLResponse)
def dashboard_reports():
    with engine.connect() as conn:
        total_calls = conn.execute(text("SELECT COUNT(*) FROM call_sessions")).scalar() or 0
        calls_today = conn.execute(
            text("SELECT COUNT(*) FROM call_sessions WHERE started_at::date = now()::date")
        ).scalar() or 0

    return HTMLResponse(f"""
    <html><head><meta charset="utf-8"><title>Rapportage</title>
    <style>
      body{{font-family:system-ui;margin:24px}}
      .cards{{display:flex;gap:12px;flex-wrap:wrap}}
      .card{{padding:16px 20px;border:1px solid #ddd;border-radius:12px;min-width:160px}}
      .big{{font-size:28px;font-weight:700}}
    </style></head>
    <body>
      <h3>Rapportage</h3>
      <div class="cards">
        <div class="card"><div>Totaal calls</div><div class="big">{int(total_calls)}</div></div>
        <div class="card"><div>Calls vandaag</div><div class="big">{int(calls_today)}</div></div>
      </div>
      <p><a href="/dashboard">Terug</a></p>
    </body></html>
    """)
