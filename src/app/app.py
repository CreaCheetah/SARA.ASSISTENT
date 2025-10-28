# src/app/app.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
import logging

from src.workflows.transcribe_and_return import transcribe_bytes
from src.workflows.speak_text import speak_text
from src.app.twilio_routes import router as twilio_router
from src.app.admin import router as admin_router
from src.infra.logs import setup_logging

setup_logging()
log = logging.getLogger(__name__)

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "SARA backend actief"}

@app.get("/healthz")
def health():
    return {"ok": True}

# --- ASR ---
@app.post("/asr")
async def asr_endpoint(file: UploadFile = File(...), language: str = "nl"):
    data = await file.read()
    if not data:
        log.warning("asr_empty_file")
        raise HTTPException(status_code=400, detail="empty file")
    try:
        text = transcribe_bytes(
            data,
            suffix=f".{file.filename.split('.')[-1]}",
            language=language,
        )
        log.info("asr_done")
        return {"text": text}
    except Exception as e:
        log.error(f"asr_error {type(e).__name__}: {e}")
        raise

# --- TTS: file download ---
@app.post("/tts")
async def tts_endpoint(text: str):
    try:
        audio_bytes = speak_text(text)
        tmp_path = "/tmp/output.mp3"
        with open(tmp_path, "wb") as f:
            f.write(audio_bytes)
        log.info("tts_done")
        return FileResponse(tmp_path, media_type="audio/mpeg", filename="output.mp3")
    except Exception as e:
        log.error(f"tts_error {type(e).__name__}: {e}")
        raise

# --- TTS: streaming ---
@app.get("/tts_get")
def tts_get(text: str):
    try:
        audio_bytes = speak_text(text)
        log.info("tts_stream_done")
        return StreamingResponse(iter([audio_bytes]), media_type="audio/mpeg",
                                 headers={"Content-Disposition": 'inline; filename="tts.mp3"'})
    except Exception as e:
        log.error(f"tts_stream_error {type(e).__name__}: {e}")
        raise

# Routers
app.include_router(twilio_router)
app.include_router(admin_router)
