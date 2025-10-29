from fastapi import APIRouter
from pydantic import BaseModel, conint
from typing import Optional
from ...infra import live_settings

router = APIRouter()

class UiSaveIn(BaseModel):
    bot_enabled: Optional[bool] = None
    pastas_enabled: Optional[bool] = None
    pickup_enabled: Optional[bool] = None
    delay_pizzas_min: Optional[conint(ge=10, le=60)] = None
    delay_schotels_min: Optional[conint(ge=10, le=60)] = None


@router.get("/dashboard/api/settings")
def ui_read():
    """Retourneer huidige instellingen voor de dashboard-UI."""
    values = live_settings.get_all()
    return {
        "bot_enabled": values.get("bot_enabled"),
        "pastas_enabled": values.get("pastas_enabled"),
        "pickup_enabled": values.get("pickup_enabled"),
        "delay_pizzas_min": values.get("delay_pizzas_min"),
        "delay_schotels_min": values.get("delay_schotels_min"),
        "ok": True,
    }


@router.post("/dashboard/api/settings")
def ui_save(p: UiSaveIn):
    """Slaat dashboardinstellingen op in de database."""
    updates = {}
    if p.bot_enabled is not None:
        updates["bot_enabled"] = p.bot_enabled
    if p.pastas_enabled is not None:
        updates["pastas_enabled"] = p.pastas_enabled
    if p.pickup_enabled is not None:
        updates["pickup_enabled"] = p.pickup_enabled
    if p.delay_pizzas_min is not None:
        updates["delay_pizzas_min"] = p.delay_pizzas_min
    if p.delay_schotels_min is not None:
        updates["delay_schotels_min"] = p.delay_schotels_min

    ok, msg = live_settings.set_many(updates)
    return {"ok": ok, "message": msg}
