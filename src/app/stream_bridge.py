from __future__ import annotations
from fastapi import APIRouter, WebSocket
import os, json, base64, asyncio, logging, websockets

# audioop fallback (Py3.13)
try:
    import audioop  # type: ignore
except ModuleNotFoundError:
    from audioop_lts import audioop  # type: ignore

# jouw workflow
from src.workflows import call_flow as cf
from src.nlu.parse_order import parse_items
from src.infra import live_settings as ls

router = APIRouter()
log = logging.getLogger("sara.ws")

# ── ENV
OPENAI_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview")
VOICE        = os.getenv("OPENAI_REALTIME_VOICE", "marin")

# ── OpenAI realtime connect (websockets>=12)
async def openai_connect():
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY ontbreekt")
    url = f"wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}"
    headers = [
        ("Authorization", f"Bearer {key}"),
        ("OpenAI-Beta", "realtime=v1"),
    ]
    try:
        ws = await websockets.connect(
            url,
            extra_headers=headers,
            ping_interval=20,
            ping_timeout=20,
            max_size=10_000_000,
        )
        log.info("OpenAI websocket connected")
        return ws
    except Exception as e:
        log.error(f"OpenAI connect error: {e}")
        raise

# ── μ-law 8kHz ↔ PCM16
def ulaw_to_pcm16(b: bytes) -> bytes: return audioop.ulaw2lin(b, 2)
def pcm16_to_ulaw(b: bytes) -> bytes: return audioop.lin2ulaw(b, 2)

# ── dunne state (businesslogica zit in cf.*)
class State:
    def __init__(self):
        self.mode: str | None = None
        self.items: list[cf.Item] = []
    def merge(self, new: list[cf.Item]):
        by = {(i.category, i.name, i.unit_price): i for i in self.items}
        for it in new:
            k = (it.category, it.name, it.unit_price)
            if k in by: by[k].qty += it.qty
            else: by[k] = cf.Item(**it.__dict__)
        self.items = list(by.values())

def detect_mode(t: str) -> str | None:
    t = t.lower()
    if any(w in t for w in ["bezorg", "lever", "brengen"]): return "bezorgen"
    if any(w in t for w in ["afhaal", "afhalen", "ophalen"]): return "afhalen"
    return None

def detect_yesno(t: str) -> str | None:
    t = t.lower()
    if any(w in t for w in ["ja", "klopt"]): return "ja"
    if any(w in t for w in ["nee", "niet goed"]): return "nee"
    return None

async def say(oai, text: str):
    await oai.send(json.dumps({
        "type": "response.create",
        "response": {
            "modalities": ["audio"],
            "instructions": text,
            "audio": {"voice": VOICE}
        }
    }))

@router.websocket("/ws/twilio")
async def ws_twilio(ws: WebSocket):
    # accepteer wat Twilio aanbiedt, zonder forceren
    proto = ws.headers.get("sec-websocket-protocol")
    try:
        await ws.accept(subprotocol=proto if proto else None)
    except Exception as e:
        log.error(f"WS accept failed: {e} proto={proto}")
        return
    log.info(f"WS accepted. proto={proto}")

    try:
        oai = await openai_connect()
    except Exception:
        await ws.close()
        return

    # NL transcript + VAD; content genereren doen wij zelf met say()
    await oai.send(json.dumps({
        "type": "session.update",
        "session": {
            "input_audio_transcription": {"model": "gpt-4o-transcribe", "language": "nl"},
            "turn_detection": {"type": "server_vad", "threshold": 0.5, "silence_duration_ms": 600}
        }
    }))

    st = State()

    async def pump_in():
        try:
            opened = False
            while True:
                raw = await ws.receive_text()
                m = json.loads(raw)
                ev = m.get("event")

                if ev == "start" and not opened:
                    opened = True
                    ts = cf.time_status(cf.now_ams())
                    if ts and any(k in ts.lower() for k in ("gesloten", "niet geopend")):
                        await say(oai, ts)
                    else:
                        await say(oai, "Goedendag, u spreekt met Sara, de belassistent van Ristorante Adam Spanbroek. Wat wilt u bestellen?")

                elif ev == "media":
                    pcm16 = ulaw_to_pcm16(base64.b64decode(m["media"]["payload"]))
                    await oai.send(json.dumps({"type": "input_audio_buffer.append", "audio": base64.b64encode(pcm16).decode()}))
                    await oai.send(json.dumps({"type": "input_audio_buffer.commit"}))
                    # geen auto response.create; we wachten transcript-event en spreken zelf met say()

                elif ev == "stop":
                    break
        except Exception as e:
            log.error(f"IN err: {e}")
        finally:
            try: await oai.send(json.dumps({"type": "session.close"}))
            except: pass

    async def pump_out():
        try:
            async for frame in oai:
                try:
                    d = json.loads(frame)
                except Exception:
                    continue
                t = d.get("type")

                # audio terug naar Twilio
                if t == "output_audio_buffer.delta":
                    ulaw = pcm16_to_ulaw(base64.b64decode(d["audio"]))
                    await ws.send_text(json.dumps({"event": "media", "media": {"payload": base64.b64encode(ulaw).decode()}}))
                    continue

                # transcript ontvangen
                if t in (
                    "input_audio_transcription.completed",
                    "response.input_audio_transcription.completed",
                    "conversation.item.input_audio_transcription.completed",
                ):
                    tx = d.get("transcript") or d.get("input_audio_transcription", {}).get("text") or d.get("text", "")
                    user = (tx or "").strip().lower()
                    if not user:
                        continue
                    log.info(f"USER> {user}")

                    # update state
                    md = detect_mode(user)
                    if md: st.mode = md
                    items, _ = parse_items(user)
                    if items: st.merge(items)

                    # beslis vervolgstap via jouw workflow
                    if not st.items:
                        await say(oai, "Wat wilt u bestellen?")
                        continue

                    if st.items and not st.mode:
                        await say(oai, "Wilt u laten bezorgen of komt u het afhalen?")
                        continue

                    s = ls.get_all()
                    mins = cf.total_minutes(st.mode, st.items, s)
                    tline = cf.time_phrase(st.mode, mins)
                    summary, total = cf.summarize(st.items)
                    pay = cf.payment_phrase(st.mode)

                    yn = detect_yesno(user)
                    if yn == "ja":
                        await say(oai, f"Dank u wel. De bestelling staat genoteerd: {summary}. Totaal {total} euro. {tline} {pay}. Fijne avond!")
                        continue
                    if yn == "nee":
                        await say(oai, "Geen probleem. Wat wilt u wijzigen of toevoegen?")
                        continue

                    await say(oai, f"Ik heb genoteerd: {summary}. Dat is in totaal {total} euro. {tline} {pay}. Klopt dat?")
                    continue

                if t == "response.completed":
                    await ws.send_text(json.dumps({"event": "mark", "mark": {"name": "oai_done"}}))
        except Exception as e:
            log.error(f"OUT err: {e}")

    t1 = asyncio.create_task(pump_in())
    t2 = asyncio.create_task(pump_out())
    await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)

    try: await oai.close()
    except: pass
    try: await ws.close()
    except: pass
    log.info("WS closed")
