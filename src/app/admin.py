from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets, os
from src.infra.logs import get_events  # komt uit logs.py

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

@router.get("/dashboard/logging", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def dashboard_logging():
    rows = get_events(200)
    trs = "\n".join(
        f"<tr><td>{r['ts']:%Y-%m-%d %H:%M:%S}</td><td>{r['level']}</td><td>{r['msg']}</td></tr>"
        for r in rows
    )
    html = f"""
    <html><head><meta charset="utf-8"><title>Logging</title>
    <meta http-equiv="refresh" content="5">
    <style>
      body{{font-family:system-ui;margin:24px;background:#fff}}
      table{{width:100%;border-collapse:collapse}}
      th,td{{padding:8px 10px;border-bottom:1px solid #eee;text-align:left}}
      th{{background:#f6f6f6}}
      .lvl-ERROR{{color:#c0392b;font-weight:600}}
      .lvl-WARNING{{color:#d35400}}
      .lvl-INFO{{color:#2c3e50}}
    </style></head>
    <body>
      <h2>Logging (beveiligd)</h2>
      <table>
        <thead><tr><th>Tijd</th><th>Niveau</th><th>Bericht</th></tr></thead>
        <tbody>{trs or '<tr><td colspan="3">Nog geen regels</td></tr>'}</tbody>
      </table>
    </body></html>
    """
    return HTMLResponse(html)

@router.get("/dashboard/live", response_class=HTMLResponse)
def dashboard_live():
    return HTMLResponse("<h2>Live instellingen</h2>")

@router.get("/dashboard/reports", response_class=HTMLResponse)
def dashboard_reports():
    return HTMLResponse("<h2>Rapportage</h2>")

@router.get("/dashboard/logging", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def dashboard_logging():
    rows = get_events(200)
    body = "\n".join(f"{r['ts']}  {r['level']:<5}  {r['msg']}" for r in rows)
    html = f"""
    <html><head><meta charset="utf-8"><title>Logging</title>
    <meta http-equiv="refresh" content="5"></head>
    <body style="font-family:ui-monospace,monospace;background:#fefefe;padding:20px">
      <h2>Logging (beveiligd)</h2>
      <pre>{body}</pre>
    </body></html>
    """
    return HTMLResponse(html)
