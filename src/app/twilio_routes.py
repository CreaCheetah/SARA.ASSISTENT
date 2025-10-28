# src/app/twilio_routes.py
from fastapi import APIRouter, Form, Request
from fastapi.responses import PlainTextResponse
from urllib.parse import urlencode
import os, requests, logging

from src.workflows.transcribe_and_return import transcribe_bytes
from src.workflows.speak_text import speak_text  # niet verplicht hier, maar handig voor later

router = APIRouter()
log = logging.getLogger("uvicorn.error")

def _base() -> str:
    # PUBLIC_BASE_URL zonder trailing slash
    return os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

@router.post("/twilio/voice", response_class=PlainTextResponse)
async def twilio_voice():
    """Eerste webhook: begroet en start opnemen"""
    action = f"{_base()}/twilio/handle_recording"
    log.info({"evt": "twilio_voice"})
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        '  <Say language="nl-NL">Spreek uw bericht in na de toon.</Say>'
        f'  <Record maxLength="10" timeout="3" playBeep="true" action="{action}" />'
        '  <Say language="nl-NL">Geen opname ontvangen.</Say>'
        "</Response>"
    )

@router.post("/twilio/handle_recording", response_class=PlainTextResponse)
async def twilio_handle_recording(
    request: Request,
    RecordingUrl: str = Form(...),
    RecordingFormat: str = Form("wav"),           # Twilio geeft wav/mp3 terug
    RecordingDuration: str = Form(None),          # optioneel, voor logging
):
    """Tweede webhook: opname ophalen, transcriberen, TTS terugspelen"""
    try:
        # Basis logging van binnenkomende call
        form = await request.form()
        sid = form.get("CallSid")
        frm = form.get("From")
        to = form.get("To")
        dur = RecordingDuration
        log.info({
            "evt": "twilio_handle_in",
            "sid": sid, "from": frm, "to": to,
            "duration": dur, "recordingUrl": RecordingUrl, "fmt": RecordingFormat
        })

        # Twilio download met Basic Auth
        tw_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        tw_tok = os.getenv("TWILIO_AUTH_TOKEN", "")
        candidates = [
            f"{RecordingUrl}.{RecordingFormat}",
            f"{RecordingUrl}.mp3",
            f"{RecordingUrl}.wav",
            RecordingUrl,
        ]

        audio_bytes = None
        used_url = None
        for url in candidates:
            try:
                r = requests.get(url, auth=(tw_sid, tw_tok), timeout=30)
                log.info({"evt": "download_try", "sid": sid, "url": url, "status": r.status_code})
                if r.status_code == 200 and r.content:
                    audio_bytes = r.content
                    used_url = url
                    break
            except requests.RequestException as e:
                log.info({"evt": "download_err", "url": url, "err": str(e)})

        if not audio_bytes:
            raise RuntimeError("Kon opname niet downloaden van Twilio")

        # Bepaal suffix voor ASR
        suffix = ".mp3" if (used_url or "").endswith(".mp3") else ".wav"
        text = transcribe_bytes(audio_bytes, suffix=suffix, language="nl").strip()[:400]
        log.info({"evt": "transcribe_ok", "sid": sid, "chars": len(text)})

        # Bouw TTS-stream URL
        tts_url = f"{_base()}/tts_get?{urlencode({'text': text})}"
        log.info({"evt": "reply_tts", "sid": sid, "url": tts_url})

        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f"  <Play>{tts_url}</Play>"
            "</Response>"
        )

    except Exception as e:
        log.exception("twilio_handle_recording failed")
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            '  <Say language="nl-NL">Er ging iets mis bij het verwerken. Probeer opnieuw.</Say>'
            "</Response>"
        )
