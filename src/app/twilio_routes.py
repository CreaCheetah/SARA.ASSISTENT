# src/app/twilio_routes.py
from fastapi import APIRouter, Form, Request
from fastapi.responses import PlainTextResponse
import logging, os, requests
from src.workflows.transcribe_and_return import transcribe_bytes

router = APIRouter()
log = logging.getLogger(__name__)

def _base(request: Request) -> str:
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.client.host)
    return f"{scheme}://{host}"

@router.post("/twilio/voice", response_class=PlainTextResponse)
async def twilio_voice(request: Request):
    log.info("twilio_voice")
    base = _base(request)
    # simpele instructie: neem op en stuur naar /twilio/handle_recording
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="nl-NL">Spreek uw bericht in na de toon.</Say>
  <Record playBeep="true" action="{base}/twilio/handle_recording" />
  <Say language="nl-NL">Geen opname ontvangen.</Say>
</Response>"""
    return PlainTextResponse(xml, media_type="application/xml")

@router.post("/twilio/handle_recording", response_class=PlainTextResponse)
async def twilio_handle_recording(
    request: Request,
    RecordingUrl: str = Form(...),
    RecordingFormat: str = Form("wav"),
):
    log.info(f"twilio_handle_in RecordingUrl={RecordingUrl} fmt={RecordingFormat}")
    try:
        sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        tok = os.getenv("TWILIO_AUTH_TOKEN", "")
        r = requests.get(RecordingUrl, auth=(sid, tok), timeout=30)
        r.raise_for_status()
        log.info(f"download_ok bytes={len(r.content)}")

        text = transcribe_bytes(r.content, suffix=f".{RecordingFormat}", language="nl")
        log.info("asr_done_twilio")

        tts_url = f"{_base(request)}/tts_get?text={requests.utils.quote(text)}"
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Play>{tts_url}</Play>
</Response>"""
        return PlainTextResponse(xml, media_type="application/xml")
    except Exception as e:
        log.error(f"twilio_handle_error {type(e).__name__}: {e}")
        # val terug met foutmelding voor de beller
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response><Say language="nl-NL">Er ging iets mis.</Say></Response>"""
        return PlainTextResponse(xml, media_type="application/xml")
