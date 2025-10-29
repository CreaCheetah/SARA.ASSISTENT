# src/app/dashboard/settings_adapter.py
@router.post("/api/settings")
def dashboard_save(p: DashboardSaveIn):
    s = get_live_settings()
    if p.sara_active is not None:
        s["sara_active"] = p.sara_active
    if p.pickup_enabled is not None:
        s["pickup_enabled"] = p.pickup_enabled
    if p.pastas_available is not None:
        s["pasta_available"] = p.pastas_available
    if p.delay_pizza_min is not None:
        s["category_delay_min"]["pizza"] = int(p.delay_pizza_min)
    if p.delay_schotel_min is not None:
        s["category_delay_min"]["schotel"] = int(p.delay_schotel_min)
    save_live_settings(s)
    return {"ok": True}
