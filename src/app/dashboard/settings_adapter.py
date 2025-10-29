from fastapi import APIRouter
from pydantic import BaseModel, conint
from typing import Optional
from ...infra.live_settings import get_live_settings, save_live_settings

router = APIRouter()

class UiSaveIn(BaseModel):
    bot_enabled: Optional[bool] = None
    pastas_enabled: Optional[bool] = None
    pickup_enabled: Optional[bool] = None
    delay_pizzas_min: Optional[conint(ge=0, le=180)] = None
    delay_schotels_min: Optional[conint(ge=0, le=180)] = None

@router.get("/dashboard/api/settings")
def ui_read():
    s = get_live_settings()
    return {
        "bot_enabled": bool(s["sara_active"]),
        "pastas_enabled": bool(s["pasta_available"]),
        "pickup_enabled": bool(s["pickup_enabled"]),
        "delay_pizzas_min": int(s["category_delay_min"].get("pizza", 0)),
        "delay_schotels_min": int(s["category_delay_min"].get("schotel", 0)),
        "message": "OK",
        "ok": True,
    }

@router.post("/dashboard/api/settings")
def ui_save(p: UiSaveIn):
    s = get_live_settings()
    if p.bot_enabled is not None:
        s["sara_active"] = p.bot_enabled
    if p.pastas_enabled is not None:
        s["pasta_available"] = p.pastas_enabled
    if p.pickup_enabled is not None:
        s["pickup_enabled"] = p.pickup_enabled
    if p.delay_pizzas_min is not None:
        s["category_delay_min"]["pizza"] = int(p.delay_pizzas_min)
    if p.delay_schotels_min is not None:
        s["category_delay_min"]["schotel"] = int(p.delay_schotels_min)
    save_live_settings(s)
    return {"ok": True, "message": "Opgeslagen"}
