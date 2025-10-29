from __future__ import annotations
from fastapi import APIRouter, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from src.workflows.call_flow import (
    now_ams, time_status, greeting, Item,
    total_minutes, time_phrase, payment_phrase, summarize
)
from src.infra import live_settings
import json

router = APIRouter(prefix="/twilio", tags=["twilio"])
VOICE_OPTS = dict(language="nl-NL")

# ---------- Eerste oproep ----------
@router.post("/voice")
async def inbound_call(_: Request):
    """Start van het gesprek: tijdcheck + melding + luisteren."""
    resp = VoiceResponse()
    ts = time_status(now_ams())

    if ts:
        if ("niet geopend" in ts.lower()) or ("gesloten" in ts.lower()):
            resp.say(ts, **VOICE_OPTS)
            resp.hangup()
            return Response(str(resp), media_type="application/xml")
        resp.say(ts, **VOICE_OPTS)

    # Opening en luisteren naar intent
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
    resp.redirect("/twilio/voice")
    return Response(str(resp), media_type="application/xml")


# ---------- Intentverwerking ----------
@router.post("/intent")
async def handle_intent(request: Request):
    """
    Vereenvoudigde simulatie van AI/plan:
    - Analyseert klanttekst (rudimentair)
    - Roept call-flow berekening aan
    """
    form = await request.form()
    speech_result = (form.get("SpeechResult") or "").lower()
    print("SpeechResult:", speech_result)

    resp = VoiceResponse()

    # Basisdetectie voor demo: bezorgen of afhalen
    if "bezorg" in speech_result:
        mode = "bezorgen"
    elif "afhaal" in speech_result or "afhalen" in speech_result:
        mode = "afhalen"
    else:
        resp.say("Ik heb niet helemaal verstaan of u wilt bezorgen of afhalen. Kunt u dat herhalen?", **VOICE_OPTS)
        gather = Gather(
            input="speech",
            action="/twilio/intent",
            method="POST",
            language="nl-NL",
            speech_timeout="auto"
        )
        gather.say("Wilt u laten bezorgen of komt u het afhalen?", **VOICE_OPTS)
        resp.append(gather)
        return Response(str(resp), media_type="application/xml")

    # Demo: vaste bestelling (1 pizza €12)
    items = [Item(name="Margherita", category="pizza", qty=1, unit_price=12)]
    settings = live_settings.get_all()
    mins = total_minutes(mode, items, settings)
    tline = time_phrase(mode, mins)
    summary, total = summarize(items)
    payline = payment_phrase(mode)

    resp.say(
        f"Ik heb genoteerd: {summary}. Dat is in totaal {total} euro. "
        f"{tline} {payline}", **VOICE_OPTS
    )
    resp.say("Klopt dat zo?", **VOICE_OPTS)

    gather = Gather(
        input="speech",
        action="/twilio/confirm",
        method="POST",
        language="nl-NL",
        speech_timeout="auto"
    )
    gather.say("Antwoord alstublieft met ja of nee.", **VOICE_OPTS)
    resp.append(gather)
    return Response(str(resp), media_type="application/xml")


# ---------- Bevestiging ----------
@router.post("/confirm")
async def confirm_intent(request: Request):
    """Bevestiging van bestelling."""
    form = await request.form()
    speech_result = (form.get("SpeechResult") or "").lower()
    print("Confirm:", speech_result)

    resp = VoiceResponse()
    if "ja" in speech_result:
        resp.say("Dank u wel. De bestelling staat genoteerd. Een fijne avond!", **VOICE_OPTS)
    elif "nee" in speech_result:
        resp.say("Geen probleem. Wat wilt u wijzigen?", **VOICE_OPTS)
        resp.redirect("/twilio/intent")
        return Response(str(resp), media_type="application/xml")
    else:
        resp.say("Ik heb u niet goed verstaan. Ik verbind u even door.", **VOICE_OPTS)

    resp.hangup()
    return Response(str(resp), media_type="application/xml")
