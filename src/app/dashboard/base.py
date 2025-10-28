from fastapi import APIRouter
from src.app.dashboard.settings_page import router as settings_router
from src.app.dashboard.reports_page import router as reports_router
from src.app.dashboard.monitoring_page import router as monitoring_router

router = APIRouter()

@router.get("/dashboard")
def dashboard_root():
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
