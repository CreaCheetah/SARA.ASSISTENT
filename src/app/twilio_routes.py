from __future__ import annotations
from fastapi import APIRouter, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather

from src.workflows.call_flow import (
    now_ams, time_status, greeting, Item,
    total_minutes, time_phrase, payment_phrase, summarize
)
from src.infra import live_settings
from src.nlu.parse_order import parse_items

router = APIRouter(prefix="/twilio", tags=["twilio"])
VOICE_OPTS = dict(language="nl-NL")  # evt. voice toevoegen als je Polly gebruikt


@router.post("/voice")
async def inbound_call(_: Request):
    """Start van het gesprek: tijdcheck + (eventuele) melding + opening + luisteren."""
    resp = VoiceResponse()
    ts = time_status(now_ams())

    if ts:
        # Gesloten (incl. begroeting in de tekst): melden en ophangen
        if ("niet geopend" in ts.lower()) or ("gesloten" in ts.lower()):
            resp.say(ts, **VOICE_OPTS)
            resp.hangup()
            return Response(str(resp), media_type="application/xml")
        # Alleen bezorgstop (na 21:30): melden en verdergaan
        resp.say(ts, **VOICE_OPTS)

    # Open uren: tijdsafhankelijke opening + luisteren
    resp.say(greeting(now_ams()), **VOICE_OPTS)
    gather = Gather(
        input="speech",
        action="/twilio/intent",
        method="POST",
        language="nl-NL",
        speech_timeout="auto",
    )
    gather.say("Waarmee kan ik u helpen?", **VOICE_OPTS)
    resp.append(gather)
    # Geen input? Nog een poging
    resp.redirect("/twilio/voice")

    return Response(str(resp), media_type="application/xml")


@router.post("/intent")
async def handle_intent(request: Request):
    """
    Vereenvoudigde intentverwerking:
    - Bepaalt modus (bezorgen/afhalen)
    - Parseert items uit spraak (multi-item, menukaartprijzen)
    - Berekent tijd + bedrag en vraagt bevestiging
    """
    form = await request.form()
    speech = (form.get("SpeechResult") or "").lower()

    # 1) Modus bepalen
    mode = ""
    if "bezorg" in speech:
        mode = "bezorgen"
    elif "afhaal" in speech or "afhalen" in speech:
        mode = "afhalen"

    resp = VoiceResponse()

    if not mode:
        resp.say("Wilt u laten bezorgen of komt u het afhalen?", **VOICE_OPTS)
        gather = Gather(
            input="speech", action="/twilio/intent", method="POST",
            language="nl-NL", speech_timeout="auto"
        )
        resp.append(gather)
        return Response(str(resp), media_type="application/xml")

    # 2) Items uit de spraak halen
    items, misses = parse_items(speech)
    if not items:
        hint = "Noem bijvoorbeeld: twee pizza margherita en een shoarma schotel."
        resp.say(f"Welke gerechten wilt u bestellen? {hint}", **VOICE_OPTS)
        gather = Gather(
            input="speech", action="/twilio/intent", method="POST",
            language="nl-NL", speech_timeout="auto"
        )
        resp.append(gather)
        return Response(str(resp), media_type="application/xml")

    # 3) Tijd + bedrag + betaallijn
    settings = live_settings.get_all()
    mins = total_minutes(mode, items, settings)
    tline = time_phrase(mode, mins)
    summary, total = summarize(items)
    payline = payment_phrase(mode)

    # 4) Bevestiging
    resp.say(
        f"Ik heb genoteerd: {summary}. Dat is in totaal {total} euro. "
        f"{tline} {payline}. Klopt dat zo?",
        **VOICE_OPTS
    )
    gather = Gather(
        input="speech", action="/twilio/confirm", method="POST",
        language="nl-NL", speech_timeout="auto"
    )
    gather.say("Antwoord alstublieft met ja of nee.", **VOICE_OPTS)
    resp.append(gather)
    return Response(str(resp), media_type="application/xml")


@router.post("/confirm")
async def confirm_intent(request: Request):
    """Bevestigt of corrigeert de bestelling."""
    form = await request.form()
    speech = (form.get("SpeechResult") or "").lower()

    resp = VoiceResponse()
    if "ja" in speech:
        resp.say("Dank u wel. De bestelling staat genoteerd. Een fijne avond!", **VOICE_OPTS)
        resp.hangup()
        return Response(str(resp), media_type="application/xml")

    if "nee" in speech:
        resp.say("Geen probleem. Wat wilt u wijzigen of toevoegen?", **VOICE_OPTS)
        resp.redirect("/twilio/intent")
        return Response(str(resp), media_type="application/xml")

    # Onbegrepen antwoord
    resp.say("Ik heb u niet goed verstaan. Ik verbind u even door.", **VOICE_OPTS)
    resp.hangup()
    return Response(str(resp), media_type="application/xml")
