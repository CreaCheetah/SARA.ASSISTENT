from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse
from urllib.parse import urlencode
import os, requests, logging
from src.workflows.transcribe_and_return import transcribe_bytes
from src.workflows.speak_text import speak_text
from fastapi import APIRouter, Form, Request
import logging
log = logging.getLogger("uvicorn.error")

router = APIRouter()
log = logging.getLogger("uvicorn.error")

def _base() -> str:
    return os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

@router.post("/twilio/voice", response_class=PlainTextResponse)
async def twilio_voice():
    log.info({"evt":"twilio_voice"})  # <— logt elke inkomende call
    ...
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
async def twilio_handle_recording(RecordingUrl: str = Form(...), RecordingFormat: str = Form("wav")):
    log.info({"event": "twilio_handle_recording", "RecordingUrl": RecordingUrl})
    try:
        sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        tok = os.getenv("TWILIO_AUTH_TOKEN", "")
        audio_url = RecordingUrl
        r = requests.get(audio_url, auth=(sid, tok), timeout=30)
        r.raise_for_status()

        text = transcribe_bytes(r.content, suffix=f".{RecordingFormat}", language="nl").strip()[:400]
        tts_url = f"{_base()}/tts_get?{urlencode({'text': text})}"
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            f'  <Play>{tts_url}</Play>'
            '</Response>'
        )
    except Exception as e:
        log.exception("handle_recording failed: %s", e)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '  <Say language="nl-NL">Er ging iets mis bij het verwerken. Probeer opnieuw.</Say>'
            '</Response>'
        )
