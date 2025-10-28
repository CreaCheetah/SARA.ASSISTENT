from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets, os
from src.infra.logs import get_events
from sqlalchemy import text
from src.infra.db import engine

router = APIRouter()
security = HTTPBasic()

ADMIN_USER = os.getenv("ADMIN_USER", "")
ADMIN_PASS = os.getenv("ADMIN_PASS", "")

def require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username, ADMIN_USER)
    ok_pass = secrets.compare_digest(credentials.password, ADMIN_PASS)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        )

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse("""
    <html><head><meta charset="utf-8"><title>SARA • Dashboard</title>
    <style>
      body{font-family:system-ui;margin:24px;background:#faf7f2}
      a.btn{display:inline-block;margin:6px 8px 12px 0;padding:10px 14px;border-radius:10px;background:#512da8;color:#fff;text-decoration:none}
    </style></head>
    <body>
      <h2>SARA • Dashboard</h2>
      <a class="btn" href="/dashboard/logging">Logging</a>
      <a class="btn" href="/dashboard/calls">Calls</a>
    </body></html>
    """)

@router.get("/dashboard/logging", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def dashboard_logging(request: Request):
    level = request.query_params.get("level")
    q = request.query_params.get("q")
    rows = get_events(300, level=level, q=q)

    def tr(r):
        return f"<tr><td>{r['ts']}</td><td>{r['level']}</td><td>{r['msg']}</td></tr>"

    html = f"""
    <html><head><meta charset="utf-8"><title>Logging</title>
    <style>
      body{{font-family:system-ui;margin:24px}}
      table{{border-collapse:collapse;width:100%}}
      td,th{{border:1px solid #ddd;padding:8px;font-size:14px}}
      th{{background:#eee;text-align:left}}
      .toolbar input{{padding:6px;margin-right:6px}}
    </style></head>
    <body>
      <h3>Logging (beveiligd)</h3>
      <div class="toolbar">
        <form method="get">
          <label>Niveau:</label>
          <input name="level" placeholder="INFO/WARN/ERROR" value="{level or ''}">
          <label>Zoeken:</label>
          <input name="q" placeholder="tekst" value="{q or ''}">
          <button type="submit">Filter</button>
          <a href="/dashboard/logging">Reset</a>
        </form>
      </div>
      <table>
        <thead><tr><th>Tijd</th><th>Niveau</th><th>Bericht</th></tr></thead>
        <tbody>
          {''.join(tr(r) for r in rows)}
        </tbody>
      </table>
      <p><a href="/dashboard">Terug</a></p>
    </body></html>
    """
    return HTMLResponse(html)

@router.get("/dashboard/calls", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def dashboard_calls():
    with engine.connect() as conn:
        sess = conn.execute(text("""
            SELECT call_id, from_masked, to_number, started_at, ended_at, duration_sec, result
            FROM call_sessions
            ORDER BY started_at DESC
            LIMIT 200
        """)).mappings().all()

    def tr(s):
        href = f'/dashboard/calls/{s["call_id"]}'
        return (
          "<tr>"
          f"<td><a href='{href}'>{s['call_id']}</a></td>"
          f"<td>{s['from_masked'] or ''}</td>"
          f"<td>{s['to_number'] or ''}</td>"
          f"<td>{s['started_at']}</td>"
          f"<td>{s['ended_at'] or ''}</td>"
          f"<td>{s['duration_sec'] or ''}</td>"
          f"<td>{s['result'] or ''}</td>"
          "</tr>"
        )

    html = f"""
    <html><head><meta charset="utf-8"><title>Calls</title>
    <style>
      body{{font-family:system-ui;margin:24px}}
      table{{border-collapse:collapse;width:100%}}
      td,th{{border:1px solid #ddd;padding:8px;font-size:14px}}
      th{{background:#eee;text-align:left}}
    </style></head>
    <body>
      <h3>Calls (laatste 200)</h3>
      <table>
        <thead><tr>
          <th>Call ID</th><th>From</th><th>To</th>
          <th>Start</th><th>Einde</th><th>Duur(s)</th><th>Result</th>
        </tr></thead>
        <tbody>{''.join(tr(s) for s in sess)}</tbody>
      </table>
      <p><a href="/dashboard">Terug</a></p>
    </body></html>
    """
    return HTMLResponse(html)

@router.get("/dashboard/calls/{call_id}", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def dashboard_call_detail(call_id: str):
    with engine.connect() as conn:
        s = conn.execute(text("""
            SELECT call_id, from_masked, to_number, started_at, ended_at, duration_sec, result, error_code, error_msg
            FROM call_sessions WHERE call_id = :cid
        """), {"cid": call_id}).mappings().first()
        ev = conn.execute(text("""
            SELECT ts, event, level, data_json, latency_ms, status_code
            FROM call_events WHERE call_id = :cid
            ORDER BY ts ASC
        """), {"cid": call_id}).mappings().all()

    def row(e):
        return (
          "<tr>"
          f"<td>{e['ts']}</td><td>{e['level']}</td><td>{e['event']}</td>"
          f"<td>{(e['data_json'] and str(e['data_json'])) or ''}</td>"
          f"<td>{e['latency_ms'] or ''}</td><td>{e['status_code'] or ''}</td>"
          "</tr>"
        )

    html = f"""
    <html><head><meta charset="utf-8"><title>Call {call_id}</title>
    <style>
      body{{font-family:system-ui;margin:24px}}
      table{{border-collapse:collapse;width:100%}}
      td,th{{border:1px solid #ddd;padding:8px;font-size:14px}}
      th{{background:#eee;text-align:left}}
      .kv td{{border:none;padding:4px 8px}}
    </style></head>
    <body>
      <h3>Call {call_id}</h3>
      <table class="kv">
        <tr><td><b>From</b></td><td>{s['from_masked'] if s else ''}</td></tr>
        <tr><td><b>To</b></td><td>{s['to_number'] if s else ''}</td></tr>
        <tr><td><b>Start</b></td><td>{s['started_at'] if s else ''}</td></tr>
        <tr><td><b>Einde</b></td><td>{s['ended_at'] if s else ''}</td></tr>
        <tr><td><b>Duur(s)</b></td><td>{(s and s['duration_sec']) or ''}</td></tr>
        <tr><td><b>Result</b></td><td>{(s and s['result']) or ''}</td></tr>
        <tr><td><b>Error</b></td><td>{(s and (s['error_code'] or s['error_msg'])) or ''}</td></tr>
      </table>
      <h4>Events</h4>
      <table>
        <thead><tr><th>Tijd</th><th>Niveau</th><th>Event</th><th>Data</th><th>Latency(ms)</th><th>Status</th></tr></thead>
        <tbody>{''.join(row(e) for e in ev)}</tbody>
      </table>
      <p><a href="/dashboard/calls">Terug</a></p>
    </body></html>
    """
    return HTMLResponse(html)
