from __future__ import annotations
from fastapi import APIRouter, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from src.workflows.call_flow import now_ams, time_status, greeting

router = APIRouter(prefix="/twilio", tags=["twilio"])

VOICE_OPTS = dict(language="nl-NL")  # kies evt. voice="Polly.Ruben" als je Polly gebruikt

@router.post("/voice")
async def inbound_call(_: Request):
    """Inkomende call: tijdcheck + (eventueel) melding + opening + luisteren."""
    resp = VoiceResponse()
    ts = time_status(now_ams())

    if ts:
        # Gesloten: vriendelijke sluitboodschap (incl. korte begroeting) en ophangen
        if ("niet geopend" in ts.lower()) or ("gesloten" in ts.lower()):
            resp.say(ts, **VOICE_OPTS)
            resp.hangup()
            return Response(str(resp), media_type="application/xml")
        # Alleen bezorgstop (na 21:30): meld dit en ga verder
        resp.say(ts, **VOICE_OPTS)

    # Open uren: tijdsafhankelijke opening + luisteren
    resp.say(greeting(now_ams()), **VOICE_OPTS)
    gather = Gather(
        input="speech",
        action="/twilio/intent",
        method="POST",
        language="nl-NL",
        speech_timeout="auto"
    )
    gather.say("Waarmee kan ik u helpen?", **VOICE_OPTS)
    resp.append(gather)
    # Geen input ontvangen? Nog een keer proberen
    resp.redirect("/twilio/voice")

    return Response(str(resp), media_type="application/xml")


@router.post("/intent")
async def handle_intent(_: Request):
    """Placeholder voor de volgende stap (NLU/intent)."""
    resp = VoiceResponse()
    resp.say("Dank u. Ik heb uw vraag ontvangen. We ronden dit deel nog af in de volgende stap.", **VOICE_OPTS)
    resp.hangup()
    return Response(str(resp), media_type="application/xml")
