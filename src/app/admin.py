# src/app/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from urllib.parse import urlencode
import secrets, os

from src.infra.logs import get_events  # uit logs.py

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
        <a class="tile red"   href="/dashboard/reports"><h3>Rapportage</h3></a>
        <a class="tile blue"  href="/dashboard/logging"><h3>Logging</h3></a>
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

@router.get(
    "/dashboard/logging",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin)],
)
def dashboard_logging(level: str = "ALL", q: str = "", limit: int = 200, refresh: int = 5):
    rows = get_events(limit=limit, level=level, q=q)
    export_qs = urlencode({"level": level, "q": q, "limit": limit})
    meta_refresh = f'<meta http-equiv="refresh" content="{refresh}">' if refresh > 0 else ""
    html = f"""
    <html><head><meta charset="utf-8"><title>Logging</title>{meta_refresh}
    <style>
      body{{font-family:system-ui;margin:24px;background:#f7f7f7}}
      h2{{margin:0 0 16px 0}}
      form{{display:flex;gap:8px;align-items:center;margin:0 0 12px 0;flex-wrap:wrap}}
      input,select,button{{padding:6px 8px}}
      table{{width:100%;border-collapse:collapse;background:#fff}}
      th,td{{border-bottom:1px solid #eee;padding:8px 10px;text-align:left;font-size:14px;vertical-align:top}}
      th{{background:#fafafa}}
      .mono{{font-family:ui-monospace,monospace;white-space:pre-wrap}}
    </style></head>
    <body>
      <h2>Logging (beveiligd)</h2>

      <form method="get" action="/dashboard/logging">
        <label>Niveau
          <select name="level">
            <option {"selected" if level=="ALL" else ""}>ALL</option>
            <option {"selected" if level=="INFO" else ""}>INFO</option>
            <option {"selected" if level=="WARN" else ""}>WARN</option>
            <option {"selected" if level=="ERROR" else ""}>ERROR</option>
          </select>
        </label>
        <label>Zoek <input name="q" value="{q}" placeholder="tekst"/></label>
        <label>Limit <input type="number" name="limit" value="{limit}" min="1" max="5000" /></label>
        <label>Auto-refresh (s)
          <input type="number" name="refresh" value="{refresh}" min="0" max="120" />
        </label>
        <button type="submit">Toepassen</button>
        <a href="/dashboard/logging.csv?{export_qs}" style="margin-left:auto">Export CSV</a>
      </form>

      <table>
        <thead><tr><th>Tijd</th><th>Niveau</th><th>Bericht</th></tr></thead>
        <tbody>
          {''.join(f"<tr><td>{r['ts']}</td><td>{r['level']}</td><td class='mono'>{r['msg']}</td></tr>" for r in rows)}
        </tbody>
      </table>
    </body></html>
    """
    return HTMLResponse(html)

@router.get(
    "/dashboard/logging.csv",
    response_class=PlainTextResponse,
    dependencies=[Depends(require_admin)],
)
def logging_csv(level: str = "ALL", q: str = "", limit: int = 200):
    rows = get_events(limit=limit, level=level, q=q)

    def esc(s: str) -> str:
        s = str(s).replace('"', '""')
        return f'"{s}"'

    csv = "ts,level,msg\n" + "\n".join(
        f"{esc(r['ts'])},{esc(r['level'])},{esc(r['msg'])}" for r in rows
    )
    headers = {"Content-Disposition": 'attachment; filename="logs.csv"'}
    return PlainTextResponse(csv, media_type="text/csv", headers=headers)
