from __future__ import annotations
from fastapi import APIRouter, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from src.workflows.call_flow import (
    now_ams, time_status, greeting, Item,
    total_minutes, time_phrase, payment_phrase, summarize
)
from src.infra import live_settings
from src.nlu.parse_order import parse_items
import json

router = APIRouter(prefix="/twilio", tags=["twilio"])
VOICE_OPTS = dict(language="nl-NL")  # evt. voice toevoegen als je Polly gebruikt

@router.post("/voice")
async def inbound_call(_: Request):
    from twilio.twiml.voice_response import VoiceResponse, Connect
    resp = VoiceResponse()
    resp.say("Een moment, ik verbind u met SARA.", language="nl-NL")
    connect = Connect()
    connect.stream(url="wss://sara-assistent.onrender.com/ws/twilio")
    resp.append(connect)
    return Response(str(resp), media_type="application/xml")

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
    Intentverwerking met logging:
    - Modus (bezorgen/afhalen)
    - Multi-item parsing (meervoud/hoeveelheden)
    - Totaal + tijd + betaalwijze
    """
    form = await request.form()
    speech = (form.get("SpeechResult") or "").lower().strip()

    # ---- logging: wat Twilio verstaan heeft
    print(json.dumps({"twilio_speech": speech}, ensure_ascii=False))

    # 1) Modus bepalen
    mode = ""
    if "bezorg" in speech:
        mode = "bezorgen"
    elif "afhaal" in speech or "afhalen" in speech:
        mode = "afhalen"

    # 2) Items uit de spraak halen
    items, misses = parse_items(speech)

    # ---- logging: parserresultaat
    print(json.dumps({
        "mode": mode or None,
        "parsed_items": [i.__dict__ for i in items],
        "misses": misses
    }, ensure_ascii=False))

    resp = VoiceResponse()

    if not mode:
        resp.say("Wilt u laten bezorgen of komt u het afhalen?", **VOICE_OPTS)
        gather = Gather(
            input="speech", action="/twilio/intent", method="POST",
            language="nl-NL", speech_timeout="auto"
        )
        resp.append(gather)
        return Response(str(resp), media_type="application/xml")

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
    speech = (form.get("SpeechResult") or "").lower().strip()

    # ---- logging: bevestiging
    print(json.dumps({"confirm_speech": speech}, ensure_ascii=False))

    resp = VoiceResponse()
    if "ja" in speech:
        resp.say("Dank u wel. De bestelling staat genoteerd. Een fijne avond!", **VOICE_OPTS)
        resp.hangup()
        return Response(str(resp), media_type="application/xml")

    if "nee" in speech:
        resp.say("Geen probleem. Wat wilt u wijzigen of toevoegen?", **VOICE_OPTS)
        resp.redirect("/twilio/intent")
        return Response(str(resp), media_type="application/xml")

    resp.say("Ik heb u niet goed verstaan. Ik verbind u even door.", **VOICE_OPTS)
    resp.hangup()
    return Response(str(resp), media_type="application/xml")
