from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse
from urllib.parse import urlencode
import html

from sqlalchemy import text
from src.infra.db import engine
from src.infra.logs import get_events, get_calls
from src.app.dashboard.base import require_admin

router = APIRouter()


def esc(v):
    return html.escape("" if v is None else str(v), quote=True)


@router.get("/dashboard/monitoring", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def dashboard_monitoring(request: Request):
    qp = request.query_params
    tab = qp.get("tab", "logs")
    q = qp.get("q")
    level = qp.get("level")
    start = qp.get("start")
    end = qp.get("end")

    if tab == "calls":
        rows = get_calls(limit=50, q=q, start=start, end=end)
    else:
        rows = get_events(limit=100, level=level, q=q, start=start, end=end)

    def table_logs(items):
        head = "<tr><th>Tijd</th><th>Niveau</th><th>Bericht</th></tr>"
        body = "".join(
            f"<tr><td>{esc(i['ts'])}</td><td>{esc(i['level'])}</td><td>{esc(i['msg'])}</td></tr>"
            for i in items
        )
        return f"<table><thead>{head}</thead><tbody>{body}</tbody></table>"

    def table_calls(items):
        head = "<tr><th>Call ID</th><th>From</th><th>To</th><th>Start</th><th>Result</th></tr>"
        body = "".join(
            f"<tr><td>{esc(i['call_id'])}</td><td>{esc(i['from_masked'])}</td><td>{esc(i['to_number'])}</td><td>{esc(i['started_at'])}</td><td>{esc(i['result'])}</td></tr>"
            for i in items
        )
        return f"<table><thead>{head}</thead><tbody>{body}</tbody></table>"

    html_doc = f"""
    <html><head><meta charset="utf-8"><title>Monitoring</title>
    <style>
      body{{font-family:system-ui;margin:24px}}
      a.tab{{display:inline-block;margin-right:8px;padding:8px 12px;border-radius:10px;text-decoration:none;border:1px solid #ccc}}
      a.tab.active{{background:#512da8;color:#fff;border-color:#512da8}}
      table{{border-collapse:collapse;width:100%;margin-top:12px}}
      td,th{{border:1px solid #ddd;padding:8px;font-size:14px}}
      th{{background:#eee;text-align:left}}
    </style>
    </head>
    <body>
      <h3>Monitoring (beveiligd)</h3>
      <div>
        <a class="tab {'active' if tab=='logs' else ''}" href="/dashboard/monitoring?tab=logs">Logs</a>
        <a class="tab {'active' if tab=='calls' else ''}" href="/dashboard/monitoring?tab=calls">Calls</a>
      </div>
      <p><form method="get">
        <input type="hidden" name="tab" value="{esc(tab)}">
        <label>Zoek:</label>
        <input name="q" value="{esc(q or '')}">
        <label>Level:</label>
        <input name="level" value="{esc(level or '')}">
        <label>Start:</label>
        <input type="datetime-local" name="start" value="{esc(start or '')}">
        <label>Einde:</label>
        <input type="datetime-local" name="end" value="{esc(end or '')}">
        <button type="submit">Filter</button>
      </form></p>
      {(table_logs(rows) if tab=='logs' else table_calls(rows))}
      <p><a href="/dashboard">Terug</a></p>
    </body></html>
    """
    return HTMLResponse(html_doc)
