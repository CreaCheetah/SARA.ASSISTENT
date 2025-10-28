# src/app/twilio_routes.py
from fastapi import APIRouter, Form, Request
from fastapi.responses import PlainTextResponse
from urllib.parse import urlencode
import os, time, logging, requests

from src.workflows.transcribe_and_return import transcribe_bytes
from src.workflows.speak_text import speak_text  # tts_get gebruikt dit elders

router = APIRouter()
log = logging.getLogger("uvicorn.error")

def _base() -> str:
    return os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

@router.post("/twilio/voice", response_class=PlainTextResponse)
async def twilio_voice():
    log.info({"evt": "twilio_voice"})
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
    log.info({"evt": "twilio_handle_in", "RecordingUrl": RecordingUrl, "fmt": RecordingFormat})

    # extra context uit het Twilio-formulier
    form = await request.form()
    sid = form.get("CallSid")
    frm = form.get("From")
    to = form.get("To")
    dur = form.get("RecordingDuration")
    log.info({"evt": "twilio_form", "sid": sid, "from": frm, "to": to, "dur": dur})

    try:
        # opname ophalen (met Twilio basic auth)
        tw_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        tw_tok = os.getenv("TWILIO_AUTH_TOKEN", "")
        audio_url = RecordingUrl  # Twilio voegt zelf de extensie toe in RecordingUrl
        r = requests.get(audio_url, auth=(tw_sid, tw_tok), timeout=30)
        r.raise_for_status()
        log.info({"evt": "download_ok", "sid": sid, "bytes": len(r.content)})

        # ASR
        text = transcribe_bytes(
            r.content, suffix=f".{RecordingFormat}", language="nl"
        ).strip()[:400]
        asr_ms = int((time.monotonic() - t0) * 1000)
        log.info({"evt": "asr_ok", "sid": sid, "chars": len(text), "ms": asr_ms})

        # TTS via streaming endpoint
        tts_url = f"{_base()}/tts_get?{urlencode({'text': text})}"
        log.info({"evt": "tts_out", "sid": sid, "chars": len(text)})

        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<Response><Play>{tts_url}</Play></Response>'
        )

    except Exception as e:
        log.error({"evt": "error", "sid": sid, "msg": str(e)})
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '  <Say language="nl-NL">Er ging iets mis bij het verwerken. Probeer opnieuw.</Say>'
            '</Response>'
        )
