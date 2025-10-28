from __future__ import annotations
from typing import Dict, Any
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from src.infra.live_settings import get_all as ls_get_all, set_many as ls_set_many

router = APIRouter()  # geen Basic Auth op Live-instellingen

@router.get("/dashboard/api/settings")
def get_settings() -> JSONResponse:
    return JSONResponse(ls_get_all())

@router.post("/dashboard/api/settings")
def post_settings(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    ok, msg = ls_set_many(payload)
    return JSONResponse({"ok": ok, "message": msg}, status_code=200 if ok else 400)
