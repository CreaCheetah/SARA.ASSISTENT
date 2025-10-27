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

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    html = """
    <html><head><meta charset="utf-8"><title>SARA • Dashboard</title>
    <style>
      body{font-family:system-ui;margin:40px;background:#faf7f2}
      .wrap{max-width:900px;margin:auto}
      .title{font-size:28px;font-weight:700;margin-bottom:24px}
      .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
      .tile{padding:22px;border-radius:14px;color:#fff;text-decoration:none;display:block}
      .green{background:#1f8a4c} .red{background:#c0392b} .blue{background:#2c3e50}
      .tile h3{margin:0 0 8px 0;font-size:18px}
    </style></head>
    <body><div class="wrap">
      <div class="title">🇮🇹 SARA • Dashboard</div>
      <div class="tiles">
        <a class="tile green" href="/dashboard/live"><h3>Live instellingen</h3></a>
        <a class="tile red" href="/dashboard/reports"><h3>Rapportage</h3></a>
        <a class="tile blue" href="/dashboard/logging"><h3>Logging</h3></a>
      </div>
    </div></body></html>
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
