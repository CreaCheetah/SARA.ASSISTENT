from fastapi import APIRouter, Form, Request
from fastapi.responses import PlainTextResponse
import os, time, requests, logging

from src.workflows.transcribe_and_return import transcribe_bytes
from src.workflows.speak_text import speak_text
from src.infra.logs import start_call, end_call, log_call_event

router = APIRouter()
log = logging.getLogger(__name__)

def _base() -> str:
    return os.getenv("PUBLIC_BASE_URL", "").rstrip("/")


@router.post("/twilio/voice", response_class=PlainTextResponse)
async def twilio_voice(request: Request):
    form = await request.form()
    sid = form.get("CallSid", "")
    frm = form.get("From", "")
    to  = form.get("To", "")

    # start sessie + event
    start_call(sid, frm[:5] + "…", to)
    log_call_event(sid, "twilio_voice", data={"from": frm, "to": to})

    # eenvoudige TwiML
    tts_url = f"{_base()}/tts_get?text={requests.utils.quote('Spreek uw bestelling in na de toon.')}"
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Play>{tts_url}</Play>
  <Record maxLength="10" timeout="3" playBeep="true" action="/twilio/handle_recording" />
  <Say language="nl-NL">Geen opname ontvangen.</Say>
</Response>"""
    return PlainTextResponse(twiml, media_type="application/xml")


@router.post("/twilio/handle_recording", response_class=PlainTextResponse)
async def twilio_handle_recording(
    request: Request,
    RecordingUrl: str = Form(...),
    RecordingFormat: str = Form("wav"),
):
    t0 = time.monotonic()
    form = await request.form()
    sid = form.get("CallSid", "")

    log_call_event(sid, "twilio_handle_in",
                   data={"RecordingUrl": RecordingUrl, "fmt": RecordingFormat})

    # download Recording
    try:
        tok = os.getenv("TWILIO_AUTH_TOKEN", "")
        r = requests.get(RecordingUrl, auth=(os.getenv("TWILIO_ACCOUNT_SID",""), tok), timeout=30)
        r.raise_for_status()
        log_call_event(sid, "download_ok", data={"bytes": len(r.content)})

        # ASR
        text = transcribe_bytes(r.content, suffix=f".{RecordingFormat}", language="nl").strip()[:400]
        asr_ms = int((time.monotonic() - t0) * 1000)
        log_call_event(sid, "asr_done", data={"text": text}, latency_ms=asr_ms)

        # TTS url teruggeven aan Twilio
        tts_url = f"{_base()}/tts_get?text={requests.utils.quote(text)}"
        end_call(sid, result="ok")
        return PlainTextResponse(
            f'<?xml version="1.0" encoding="UTF-8"?><Response><Play>{tts_url}</Play></Response>',
            media_type="application/xml"
        )

    except Exception as e:
        log.exception({"evt": "handle_rec_error", "err": str(e)})
        log_call_event(sid, "error", level="ERROR", data={"err": str(e)})
        end_call(sid, result="error", error_msg=str(e))
        return PlainTextResponse(
            '<?xml version="1.0" encoding="UTF-8"?><Response><Say language="nl-NL">Er ging iets mis.</Say></Response>',
            media_type="application/xml"
        )
