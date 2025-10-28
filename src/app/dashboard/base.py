from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from src.app.dashboard.settings_api import router as settings_api_router
from src.app.dashboard.settings_live_page import router as settings_live_page_router

# Subrouters
from src.app.dashboard.settings_page import router as settings_router
from src.app.dashboard.reports_page import router as reports_router
from src.app.dashboard.monitoring_page import router as monitoring_router

router = APIRouter()

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_root():
    return HTMLResponse("""
    <html><head><meta charset="utf-8"><title>SARA • Dashboard</title>
    <style>
      :root{--bg:#faf7f2;--pri:#512da8;--ink:#1b1b1b}
      body{font-family:system-ui;margin:24px;background:var(--bg);color:var(--ink)}
      h2{margin:0 0 16px 0}
      .grid{display:flex;gap:12px;flex-wrap:wrap}
      a.btn{display:inline-block;padding:12px 16px;border-radius:12px;background:var(--pri);color:#fff;text-decoration:none;font-weight:600}
      .muted{color:#666;font-size:14px;margin-top:8px}
    </style></head>
    <body>
      <h2>SARA • Dashboard</h2>
      <div class="grid">
        <a class="btn" href="/dashboard/settings">Live instellingen</a>
        <a class="btn" href="/dashboard/reports">Rapportage</a>
        <a class="btn" href="/dashboard/monitoring">Monitoring</a>
      </div>
      <p class="muted">Monitoring vraagt een wachtwoord.</p>
    </body></html>
    """)

# Subrouters koppelen
router.include_router(settings_router)
router.include_router(reports_router)
router.include_router(monitoring_router)
router.include_router(settings_api_router, prefix="")
router.include_router(settings_live_page_router, prefix="")
