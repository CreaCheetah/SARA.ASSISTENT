# src/app/admin.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os, secrets
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

@router.get("/dashboard/logging", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def dashboard_logging(request: Request):
    level = request.query_params.get("level")  # INFO/WARN/ERROR of None
    q     = request.query_params.get("q")      # zoekterm of None
    rows  = get_events(300, level=level, q=q)

    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    options = '<option value="">INFO/WARN/ERROR</option><option>INFO</option><option>WARN</option><option>ERROR</option>'
    html = [
        "<html><head><meta charset='utf-8'><title>Logging</title>",
        "<style>body{font-family:system-ui;margin:24px} table{width:100%;border-collapse:collapse} th,td{border:1px solid #ddd;padding:8px} th{background:#f3f3f3;text-align:left} .ctrls{margin:0 0 12px 0}</style>",
        "</head><body>",
        "<h2>Logging (beveiligd)</h2>",
        "<form class='ctrls' method='get'><label>Niveau: </label>",
        f"<select name='level'>{options}</select> ",
        "<label>Zoeken: </label><input name='q' placeholder='tekst'/> ",
        "<button type='submit'>Filter</button> <a href='?'>Reset</a></form>",
        "<table><thead><tr><th>Tijd</th><th>Niveau</th><th>Bericht</th></tr></thead><tbody>",
    ]
    for r in rows:
        html.append(
            f"<tr><td>{esc(str(r['ts']))}</td><td>{esc(r['level'])}</td><td>{esc(r['msg'])}</td></tr>"
        )
    html += ["</tbody></table></body></html>"]
    return HTMLResponse("".join(html))
