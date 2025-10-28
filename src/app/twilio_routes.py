from fastapi import APIRouter, Form, Request
from fastapi.responses import PlainTextResponse
from urllib.parse import urlencode
import os, requests, logging, time
from src.workflows.transcribe_and_return import transcribe_bytes
from src.workflows.speak_text import speak_text

router = APIRouter()
log = logging.getLogger("uvicorn.error")

def _base() -> str:
    return os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

@router.post("/twilio/voice", response_class=PlainTextResponse)
async def twilio_voice():
    log.info({"evt":"twilio_voice"})               # inkomende call
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
async def twilio_handle_recording(
    request: Request,
    RecordingUrl: str = Form(...),
    RecordingFormat: str = Form("wav"),
):
    t0 = time.monotonic()
    log.info({"evt":"twilio_handle_in", "RecordingUrl": RecordingUrl, "fmt": RecordingFormat})
    form = await request.form()
    sid = form.get("CallSid"); frm = form.get("From"); to = form.get("To"); dur = form.get("RecordingDuration")
    log.info({"evt":"twilio_form", "sid": sid, "from": frm, "to": to, "dur": dur})
    try:
        # Download
        acc = os.getenv("TWILIO_ACCOUNT_SID", "")
        tok = os.getenv("TWILIO_AUTH_TOKEN", "")
        audio_url = RecordingUrl
        r = requests.get(audio_url, auth=(acc, tok), timeout=30)
        r.raise_for_status()
        log.info({"evt":"download_ok", "sid": sid, "bytes": len(r.content)})

        # Transcribe
        text = transcribe_bytes(r.content, suffix=f".{RecordingFormat}", language="nl").strip()[:400]
        log.info({"evt":"asr_ok", "ms": int((time.monotonic()-t0)*1000), "len": len(text)})

        # TTS terug
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
