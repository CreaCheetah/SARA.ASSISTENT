from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/dashboard/settings", response_class=HTMLResponse)
def dashboard_settings():
    return HTMLResponse("""
    <html><head><meta charset="utf-8"><title>Live instellingen</title>
    <style>
      body{font-family:system-ui;margin:24px}
      ul{line-height:1.8}
    </style></head>
    <body>
      <h3>Live instellingen</h3>
      <p>Hier komen toggles en live parameters.</p>
      <ul>
        <li>OPENAI model en stem</li>
        <li>Telefoonnummer mapping</li>
        <li>Auto-refresh standaardwaarden</li>
      </ul>
      <p><a href="/dashboard">Terug</a></p>
    </body></html>
    """)
