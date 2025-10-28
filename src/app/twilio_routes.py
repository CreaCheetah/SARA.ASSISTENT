# src/app/twilio_routes.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import PlainTextResponse
from urllib.parse import urlencode
import os, time, requests

from src.workflows.transcribe_and_return import transcribe_bytes
from src.infra.logs import log_call_start, log_call_end, log_call_event

router = APIRouter()


def _base(request: Request) -> str:
    # bv. https://sara-assistent.onrender.com
    url = str(request.url)
    return url[: -len(request.url.path)]


@router.post("/twilio/voice", response_class=PlainTextResponse)
async def twilio_voice(request: Request):
    form = await request.form()
    sid = form.get("CallSid")
    frm = form.get("From")
    to = form.get("To")

    if sid:
        # start van de call vastleggen
        log_call_start(sid, frm, to)
        log_call_event(sid, "twilio_voice", data={"From": frm, "To": to})

    # Vraag om een korte opname
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        '<Say language="nl-NL">Spreek uw bericht in na de toon.</Say>'
        '<Record maxLength="10" timeout="3" playBeep="true" action="/twilio/handle_recording" method="POST" />'
        '<Say language="nl-NL">Geen opname ontvangen.</Say>'
        "</Response>"
    )
    return PlainTextResponse(twiml, media_type="application/xml")


@router.post("/twilio/handle_recording", response_class=PlainTextResponse)
async def twilio_handle_recording(
    request: Request,
    RecordingUrl: str = Form(...),
    RecordingFormat: str = Form("wav"),
):
    t0 = time.monotonic()
    form = await request.form()
    sid = form.get("CallSid")
    frm = form.get("From")
    to = form.get("To")
    dur = form.get("RecordingDuration")

    log_call_event(
        sid or "unknown",
        "twilio_handle_recording",
        data={
            "RecordingUrl": RecordingUrl,
            "RecordingFormat": RecordingFormat,
            "From": frm,
            "To": to,
            "Duration": dur,
        },
    )

    try:
        # download opname via Twilio met basic auth
        tw_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        tw_tok = os.getenv("TWILIO_AUTH_TOKEN", "")
        r = requests.get(RecordingUrl, auth=(tw_sid, tw_tok), timeout=30)
        r.raise_for_status()
        log_call_event(
            sid or "unknown",
            "download_ok",
            data={"bytes": len(r.content)},
        )

        # transcribe
        text = transcribe_bytes(
            r.content,
            suffix=f".{RecordingFormat}",
            language="nl",
        ).strip()[:400]

        # TTS endpoint van deze app
        tts_url = f"{_base(request)}/tts_get?{urlencode({'text': text})}"

        # afronden en TwiML teruggeven
        latency_ms = int((time.monotonic() - t0) * 1000)
        log_call_event(
            sid or "unknown",
            "tts_stream_done",
            data={"len_text": len(text)},
            latency_ms=latency_ms,
        )
        log_call_end(sid or "unknown", int(dur) if str(dur).isdigit() else None, "ok")

        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f"<Play>{tts_url}</Play>"
            "</Response>"
        )
        return PlainTextResponse(twiml, media_type="application/xml")

    except Exception as e:
        # log fout en sluit call netjes af
        log_call_event(
            sid or "unknown",
            "error",
            level="ERROR",
            data={"msg": str(e)},
        )
        log_call_end(sid or "unknown", None, "error", error_msg=str(e))

        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            '<Say language="nl-NL">Er ging iets mis bij het verwerken.</Say>'
            "</Response>"
        )
        return PlainTextResponse(twiml, media_type="application/xml")
