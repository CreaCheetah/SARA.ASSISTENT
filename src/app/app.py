from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from src.workflows.transcribe_and_return import transcribe_bytes
from src.workflows.speak_text import speak_text
from src.app.twilio_routes import router as twilio_router
from src.app.dashboard.base import router as admin_router
from src.infra.logs import setup_logging
from src.infra.live_settings import ensure_table
from src.app.ai_routes import router as ai_router
from src.app.dashboard import settings_adapter
from src.app.stream_bridge import router as stream_router

setup_logging()
app = FastAPI()

@app.on_event("startup")
def _init_live_settings():
    ensure_table()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "SARA backend actief"}

@app.get("/healthz")
def health():
    return {"ok": True}

@app.post("/asr")
async def asr_endpoint(file: UploadFile = File(...), language: str = "nl"):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")
    text = transcribe_bytes(data, suffix=f".{file.filename.split('.')[-1]}", language=language)
    return {"text": text}

@app.post("/tts")
async def tts_endpoint(text: str):
    audio_bytes = speak_text(text)
    tmp_path = "/tmp/output.mp3"
    with open(tmp_path, "wb") as f:
        f.write(audio_bytes)
    return FileResponse(tmp_path, media_type="audio/mpeg", filename="output.mp3")

@app.get("/tts_get")
def tts_get(text: str):
    audio_bytes = speak_text(text)
    return StreamingResponse(iter([audio_bytes]), media_type="audio/mpeg",
                             headers={"Content-Disposition": 'inline; filename="tts.mp3"'})

app.include_router(twilio_router)
app.include_router(admin_router)
app.include_router(ai_router)
app.include_router(settings_adapter.router)
app.include_router(stream_router)
