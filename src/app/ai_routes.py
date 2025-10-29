from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

# reuse bestaande helpers
from src.ai.tts import synthesize_tts  # -> verwacht functie(text:str)->bytes (audio/mpeg)
from src.ai.audio_asr import transcribe_file  # -> verwacht functie(file:bytes, mime:str)->str

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/tts", summary="Text -> Speech (MP3)")
def ai_tts(payload: dict):
    text = (payload or {}).get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="missing: text")
    audio_bytes = synthesize_tts(text)
    return StreamingResponse(iter([audio_bytes]), media_type="audio/mpeg")

@router.post("/asr", summary="Speech -> Text")
async def ai_asr(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")
    transcript = transcribe_file(data, file.content_type or "audio/wav")
    return JSONResponse({"text": transcript})
