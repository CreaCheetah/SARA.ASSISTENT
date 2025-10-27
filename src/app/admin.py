from fastapi import APIRouter

router = APIRouter()

@router.get("/dashboard")
async def dashboard_home():
    return {"ok": True, "app": "SARA dashboard"}
