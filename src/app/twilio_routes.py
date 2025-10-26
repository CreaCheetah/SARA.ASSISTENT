from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse
from urllib.parse import urlencode
import os, requests
from src.workflows.transcribe_and_return import transcribe_bytes
from src.workflows.speak_text import speak_text

router = APIRouter()

def _base() -> str:
    return os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

@router.post("/twilio/voice", response_class=PlainTextResponse)
async def twilio_voice():
    action = f"{_base()}/twilio/handle_recording"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response>'
        '  <Say language="nl-NL">Spreek uw bericht in na de toon.</Say>'
        f'  <Record maxLength="10" timeout="3" playBeep="true" action="{action}" />'
        '  <Say language="nl-NL">Geen opname ontvangen.</Say>'
        '</Response>'
    )

@router.post("/twilio/handle_recording", response_class=PlainTextResponse)
async def twilio_handle_recording(RecordingUrl: str = Form(...), RecordingFormat: str = Form("mp3")):
    audio_url = f"{RecordingUrl}.{RecordingFormat}"
    r = requests.get(audio_url, timeout=30)
    r.raise_for_status()
    text = transcribe_bytes(r.content, suffix=f".{RecordingFormat}", language="nl")

    q = urlencode({"text": text[:400].strip()})
    tts_url = f"{_base()}/tts_get?{q}"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response>'
        f'  <Play>{tts_url}</Play>'
        '</Response>'
    )
