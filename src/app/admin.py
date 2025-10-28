from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets, os
from src.infra.logs import get_events

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
def dashboard_home():
    html = """
    <html><head><meta charset="utf-8"><title>SARA • Dashboard</title>
    <style>
      body{font-family:system-ui;margin:40px;background:#faf7f2}
      .wrap{max-width:980px;margin:auto}
      .title{font-size:28px;font-weight:700;margin-bottom:24px}
      .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
      .tile{padding:22px;border-radius:14px;color:#fff;text-decoration:none;display:block}
      .g{background:#1f8a4c}.r{background:#c0392b}.b{background:#2c3e50}
      .tile h3{margin:0 0 8px 0;font-size:18px}
    </style></head>
    <body><div class="wrap">
      <div class="title">🇮🇹 SARA • Dashboard</div>
      <div class="tiles">
        <a class="tile g" href="/dashboard/live"><h3>Live instellingen</h3></a>
        <a class="tile r" href="/dashboard/reports"><h3>Rapportage</h3></a>
        <a class="tile b" href="/dashboard/logging"><h3>Logging</h3></a>
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
def dashboard_logging(level: str | None = Query(None), q: str | None = Query(None)):
    rows = get_events(300, level=level, q=q)
    tr = "\n".join(
        f"<tr><td>{r['ts']}</td><td>{r['level']}</td><td>{r['msg']}</td></tr>"
        for r in rows
    )
    html = f"""
    <html><head><meta charset="utf-8"><title>Logging</title>
    <style>
      body{{font-family:system-ui;margin:24px}}
      table{{border-collapse:collapse;width:100%}}
      th,td{{border:1px solid #ddd;padding:8px;font-size:14px}}
      th{{background:#f2f2f2;text-align:left}}
      .bar{{margin:0 0 12px 0}}
      input{{padding:6px}}
    </style></head>
    <body>
      <h2>Logging (beveiligd)</h2>
      <form class="bar" method="get">
        Niveau: <input name="level" value="{level or ''}" placeholder="INFO/WARN/ERROR"/>
        Zoeken: <input name="q" value="{q or ''}" placeholder="tekst"/>
        <button type="submit">Filter</button>
        <a href="/dashboard/logging">Reset</a>
      </form>
      <table>
        <thead><tr><th>Tijd</th><th>Niveau</th><th>Bericht</th></tr></thead>
        <tbody>{tr or '<tr><td colspan="3">Geen regels</td></tr>'}</tbody>
      </table>
    </body></html>
    """
    return HTMLResponse(html)
