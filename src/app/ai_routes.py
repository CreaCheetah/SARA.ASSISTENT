from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List

# ABSOLUTE imports i.p.v. mixed relative/absolute
from src.workflows.speak_text import speak_text
from src.workflows.transcribe_and_return import transcribe_and_return
from src.workflows.call_flow import (
    Item, greeting, time_status, category_blocked,
    total_minutes, time_phrase, payment_phrase, summarize, now_ams
)
from src.infra import live_settings

router = APIRouter(prefix="/ai", tags=["ai"])


# -------- TTS / ASR --------

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


# -------- Call-flow planning endpoint --------

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
    # 1) Tijd-check eerst
    ts = time_status(now_ams())
    if ts:
        # Gesloten? (bevat 'niet geopend' of 'gesloten') -> géén extra opening teruggeven
        closed = ("niet geopend" in ts.lower()) or ("gesloten" in ts.lower())
        if closed:
            return {"message": ts, "closed": True}
        # Alleen bezorgstop (na 21:30): wél een normale opening erbij
        open_line = greeting(now_ams())
        return {"opening": open_line, "message": ts, "closed": False}

    # 2) We zijn open → normale opening
    open_line = greeting(now_ams())

    # 3) Categorie-beschikbaarheid
    settings = live_settings.get_all()
    cats = {i.category for i in payload.items}
    blocked = category_blocked(list(cats), settings)
    if blocked:
        return {
            "opening": open_line,
            "message": (
                f"{blocked.capitalize()} is op dit moment niet beschikbaar. "
                f"Wilt u in plaats daarvan een pizza of schotel bestellen?"
            ),
            "blocked": blocked
        }

    # 4) Wachttijd
    items = [Item(**i.model_dump()) for i in payload.items]
    mins = total_minutes(payload.mode, items, settings)
    tline = time_phrase(payload.mode, mins)

    # 5) Bedrag + betaling
    summary, total = summarize(items)
    payline = payment_phrase(payload.mode)

    # 6) Bevestiging
    confirm = (
        f"Ik herhaal uw bestelling: {summary}. Dat is in totaal €{total:.2f}. "
        f"{tline} {payline} Klopt dat?"
    )

    return {
        "opening": open_line,
        "time_message": tline,
        "summary": summary,
        "total_eur": total,
        "payment": payline,
        "confirm": confirm
    }
