from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

# juiste paden volgens jouw projectstructuur
from src.workflows.speak_text import speak_text
from src.workflows.transcribe_and_return import transcribe_and_return

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
