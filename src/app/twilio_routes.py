from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from fastapi import Form
import os, time, logging, requests
from src.workflows.transcribe_and_return import transcribe_bytes
from src.workflows.speak_text import speak_text
from src.infra.logs import log_call_start, log_call_event, log_call_end

router = APIRouter()
log = logging.getLogger(__name__)

def _base() -> str:
    # eigen base-url afleiden voor absolute URLs in TwiML
    host = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    return host or ""

@router.post("/twilio/voice", response_class=PlainTextResponse)
async def twilio_voice(request: Request):
    """Inkomende call: geef instructies en start sessie."""
    form = await request.form()
    sid = form.get("CallSid")
    frm = form.get("From")
    to = form.get("To")
    log.info({"evt": "twilio_voice", "sid": sid})
    if sid:
        log_call_start(sid, frm, to)

    # Vraag om opname
    action = f"{_base()}/twilio/handle_recording"
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="nl-NL">Spreek uw bericht in na de toon.</Say>
  <Record maxLength="10" timeout="3" playBeep="true" action="{action}" />
  <Say language="nl-NL">Geen opname ontvangen.</Say>
</Response>
"""
    return PlainTextResponse(twiml, media_type="application/xml")

@router.post("/twilio/handle_recording", response_class=PlainTextResponse)
async def twilio_handle_recording(
    request: Request,
    RecordingUrl: str = Form(...),
    RecordingFormat: str = Form("wav"),
):
    """Download opname, transcribeer, syntheseer antwoord en speel af."""
    t0 = time.monotonic()
    form = await request.form()
    sid = form.get("CallSid")
    log.info({"evt": "twilio_handle_in", "sid": sid, "RecordingUrl": RecordingUrl})

    # Opname downloaden
    try:
        acc = os.getenv("TWILIO_ACCOUNT_SID", "")
        tok = os.getenv("TWILIO_AUTH_TOKEN", "")
        r = requests.get(RecordingUrl, auth=(acc, tok), timeout=30)
        r.raise_for_status()
        log_call_event(sid or "", "recording_downloaded", data={"bytes": len(r.content)})
    except Exception as e:
        log_call_event(sid or "", "recording_download_error", level="ERROR", data={"error": str(e)})
        if sid:
            log_call_end(sid, None, "error", error_msg=str(e))
        # kort antwoord terug naar Twilio
        return PlainTextResponse("""<Response><Say>Er ging iets mis.</Say></Response>""",
                                 media_type="application/xml")

    # ASR
    text = transcribe_bytes(r.content, suffix=f".{RecordingFormat}", language="nl")
    log_call_event(sid or "", "asr_done", data={"chars": len(text or "")})

    # TTS
    reply_bytes = speak_text(f"U zei: {text}")
    log_call_event(sid or "", "tts_stream_done", data={"ms": len(reply_bytes)})

    # Eindtijd/duration
    dur = int((time.monotonic() - t0) * 1000)
    if sid:
        log_call_end(sid, None, "ok")

    # Terugspelen
    tts_url = f"{_base()}/tts_get?text={requests.utils.quote('Bedankt voor uw bericht')}"
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?><Response><Play>{tts_url}</Play></Response>"""
    return PlainTextResponse(twiml, media_type="application/xml")
