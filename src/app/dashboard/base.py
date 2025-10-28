from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets, os

# routers van submodules
from src.app.dashboard.settings_page import router as settings_router
from src.app.dashboard.reports_page import router as reports_router
from src.app.dashboard.monitoring_page import router as monitoring_router

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


@router.get("/dashboard")
def dashboard_root():
    """Hoofd-dashboardpagina met knoppen."""
    return {
        "message": "SARA dashboard actief",
        "routes": {
            "Live instellingen": "/dashboard/settings",
            "Rapportage": "/dashboard/reports",
            "Monitoring": "/dashboard/monitoring",
        },
    }


# subrouters koppelen
router.include_router(settings_router)
router.include_router(reports_router)
router.include_router(monitoring_router)
