from __future__ import annotations
from fastapi import APIRouter, Request
from fastapi.responses import Response
from datetime import datetime, time
from zoneinfo import ZoneInfo
from twilio.twiml.voice_response import VoiceResponse, Dial, Say

from src.infra.settings import settings, is_dev
from src.infra.live_settings import get_all as get_live_settings

router = APIRouter()

# ---------- helpers ----------
TZ = ZoneInfo(getattr(settings, "TZ", "Europe/Amsterdam"))

def now_local() -> datetime:
    return datetime.now(TZ)

def within_open_hours(dt: datetime) -> bool:
    # Open 16:00–22:00
    return time(16, 0) <= dt.time() <= time(22, 0)

def xml(resp: VoiceResponse) -> Response:
    return Response(content=str(resp), media_type="application/xml")

# ---------- main entry ----------
@router.post("/twilio/voice")
@router.get("/twilio/voice")
async def twilio_voice(request: Request) -> Response:
    """
    Gate voor inkomende calls:
      - bot_enabled=False  -> direct doorschakelen naar FAILSAFE_NUMBER (prod) of simulatie (dev)
      - buiten openingstijden -> gesloten-bericht
      - anders -> door naar 'normale Sara-flow' (hier gesimuleerd met korte welkom)
    """
    ls = get_live_settings()
    bot_enabled: bool = bool(ls.get("bot_enabled", True))

    now = now_local()
    resp = VoiceResponse()

    # 1) Handmatig uitgezet -> direct fallback
    if not bot_enabled:
        fallback = (settings.FAILSAFE_NUMBER or "").strip()
        if not fallback:
            # Geen fallback geconfigureerd: nette melding en ophangen
            msg = "De lijn is tijdelijk niet beschikbaar. Probeer het later opnieuw."
            resp.say(msg, language="nl-NL", voice="Alice")
            resp.hangup()
            return xml(resp)

        if is_dev():
            # Testmodus: NIET echt doorverbinden
            resp.say("Testmodus. Sara staat uit. Zou nu doorverbinden naar het fallbacknummer.", language="nl-NL", voice="Alice")
            resp.hangup()
            return xml(resp)
        else:
            # Productie: echte doorverbinding
            d = Dial(caller_id=settings.TWILIO_NUMBER or None)
            d.number(fallback)
            resp.append(d)
            return xml(resp)

    # 2) Buiten openingstijden -> gesloten-bericht
    if not within_open_hours(now):
        resp.say(
            "Ristorante Adam. We zijn momenteel gesloten. Onze openingstijden zijn van zestien uur tot tweeëntwintig uur. "
            "Probeer het later opnieuw.",
            language="nl-NL",
            voice="Alice",
        )
        resp.hangup()
        return xml(resp)

    # 3) Normale flow (hier alleen placeholder; je huidige AI-flow kan je hier aanroepen/redirecten)
    #    Laat voor nu een korte welkom horen zodat we de gate kunnen testen zonder echte AI-flow te wijzigen.
    resp.say("Ristorante Adam. Sara is beschikbaar. Dit is de testingang; de volledige bestelassistent volgt hierna.",
             language="nl-NL", voice="Alice")
    # Tip: vervang bovenstaande door een Redirect naar je bestaande AI-handler wanneer je die wilt koppelen:
    # resp.redirect("/twilio/ai")  # voorbeeldpad, alleen als je zo'n route al hebt
    return xml(resp)
