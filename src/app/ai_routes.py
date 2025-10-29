from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from src.workflows.speak_text import speak_text
from src.workflows.transcribe_and_return import transcribe_and_return
from pydantic import BaseModel, Field
from typing import List
from ..workflows.call_flow import (
    Item, greeting, time_status, category_blocked,
    total_minutes, time_phrase, payment_phrase, summarize, now_ams
)
from ..infra import live_settings
from fastapi import APIRouter
router = APIRouter(prefix="/ai", tags=["ai"])

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/tts", summary="Text → Speech (MP3)")
def ai_tts(payload: dict):
    text = (payload or {}).get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="missing: text")
    audio_bytes = speak_text(text)
    return StreamingResponse(iter([audio_bytes]), media_type="audio/mpeg")

@router.post("/asr", summary="Speech → Text")
async def ai_asr(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")
    transcript = transcribe_and_return(data, file.content_type or "audio/wav")
    return JSONResponse({"text": transcript})

class ItemIn(BaseModel):
    name: str
    category: str
    qty: int = Field(ge=1)
    unit_price: float = Field(ge=0)

class PlanIn(BaseModel):
    mode: str  # "bezorgen" | "afhalen"
    items: List[ItemIn]

@router.post("/plan")
def plan_callflow(payload: PlanIn):
    open_line = greeting(now_ams())

    ts = time_status(now_ams())
    if ts:
        closed = "gesloten" in ts.lower()
        return {"opening": open_line, "message": ts, "closed": closed}

    settings = live_settings.get_all()
    cats = {i.category for i in payload.items}
    blocked = category_blocked(list(cats), settings)
    if blocked:
        return {
            "opening": open_line,
            "message": f"{blocked.capitalize()} is op dit moment niet beschikbaar. Wilt u in plaats daarvan een pizza of schotel bestellen?",
            "blocked": blocked
        }

    items = [Item(**i.model_dump()) for i in payload.items]
    mins = total_minutes(payload.mode, items, settings)
    tline = time_phrase(payload.mode, mins)

    summary, total = summarize(items)
    payline = payment_phrase(payload.mode)

    confirm = f"Ik herhaal uw bestelling: {summary}. Dat is in totaal €{total:.2f}. {tline} {payline} Klopt dat?"

    return {
        "opening": open_line,
        "time_message": tline,
        "summary": summary,
        "total_eur": total,
        "payment": payline,
        "confirm": confirm
    }
