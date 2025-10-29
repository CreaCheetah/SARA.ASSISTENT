from __future__ import annotations
from fastapi import APIRouter, WebSocket
import os, json, base64, asyncio, audioop, websockets
from typing import List

# ── jouw workflow: ALLE businesslogica hieruit ────────────────────────────────
from src.workflows import call_flow as cf
from src.nlu.parse_order import parse_items
from src.infra import live_settings as ls

router = APIRouter()

# ── ENV ───────────────────────────────────────────────────────────────────────
OPENAI_KEY   = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview")
VOICE        = os.getenv("OPENAI_REALTIME_VOICE", "marin")

# ── Audio helpers (Twilio μ-law 8kHz ↔ PCM16) ─────────────────────────────────
def ulaw_to_pcm16(b: bytes) -> bytes: return audioop.ulaw2lin(b, 2)
def pcm16_to_ulaw(b: bytes) -> bytes: return audioop.lin2ulaw(b, 2)

async def oai_connect():
    if not OPENAI_KEY: raise RuntimeError("OPENAI_API_KEY ontbreekt")
    url = f"wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}"
    headers = {"Authorization": f"Bearer {OPENAI_KEY}", "OpenAI-Beta": "realtime=v1"}
    return await websockets.connect(url, extra_headers=headers, ping_interval=20, ping_timeout=20, max_size=10_000_000)

# ── Gespreks-state (dun; echte logica zit in cf.*) ───────────────────────────
class State:
    def __init__(self):
        self.mode: str|None = None            # "bezorgen"|"afhalen"
        self.items: List[cf.Item] = []
    def merge(self, new: List[cf.Item]):
        by = {(i.category,i.name,i.unit_price): i for i in self.items}
        for it in new:
            k = (it.category,it.name,it.unit_price)
            if k in by: by[k].qty += it.qty
            else: by[k] = cf.Item(**it.__dict__)
        self.items = list(by.values())

def detect_mode(t: str) -> str|None:
    t=t.lower()
    if any(w in t for w in ["bezorg","lever","brengen"]): return "bezorgen"
    if any(w in t for w in ["afhaal","afhalen","ophalen"]): return "afhalen"
    return None

def detect_yesno(t: str) -> str|None:
    t=t.lower()
    if any(w in t for w in ["ja","klopt"]): return "ja"
    if any(w in t for w in ["nee","niet goed"]): return "nee"
    return None

async def say(oai, text: str):
    await oai.send(json.dumps({
        "type":"response.create",
        "response":{"modalities":["audio"],"instructions":text,"audio":{"voice":VOICE}}
    }))

# ── Twilio WS endpoint ────────────────────────────────────────────────────────
@router.websocket("/ws/twilio")
async def ws_twilio(ws: WebSocket):
    await ws.accept(subprotocol="twilio")
    oai = await oai_connect()
    print("WS: Twilio connected, OpenAI up")

    # NL transcript + VAD
    await oai.send(json.dumps({
        "type":"session.update",
        "session":{
            "input_audio_transcription":{"model":"gpt-4o-transcribe","language":"nl"},
            "turn_detection":{"type":"server_vad","threshold":0.5,"silence_duration_ms":600}
        }
    }))

    st = State()

    async def pump_in():
        try:
            opened=False
            while True:
                raw = await ws.receive_text()
                m = json.loads(raw); ev=m.get("event")

                if ev=="start" and not opened:
                    opened=True
                    ts = cf.time_status(cf.now_ams())
                    if ts and any(k in ts.lower() for k in ("gesloten","niet geopend")):
                        await say(oai, ts)
                    else:
                        await say(oai, "Goedendag, u spreekt met Sara, de belassistent van Ristorante Adam Spanbroek. Wat wilt u bestellen?")

                elif ev=="media":
                    pcm16 = ulaw_to_pcm16(base64.b64decode(m["media"]["payload"]))
                    await oai.send(json.dumps({"type":"input_audio_buffer.append","audio":base64.b64encode(pcm16).decode()}))
                    await oai.send(json.dumps({"type":"input_audio_buffer.commit"}))
                    # geen auto-response.create hier; we reageren op transcript-events

                elif ev=="stop":
                    break
        except Exception as e:
            print("IN err:", e)
        finally:
            try: await oai.send(json.dumps({"type":"session.close"}))
            except: pass

    async def pump_out():
        try:
            async for frame in oai:
                try: d = json.loads(frame)
                except: continue
                t = d.get("type")

                # audio terug naar Twilio
                if t=="output_audio_buffer.delta":
                    ulaw = pcm16_to_ulaw(base64.b64decode(d["audio"]))
                    await ws.send_text(json.dumps({"event":"media","media":{"payload":base64.b64encode(ulaw).decode()}}))
                    continue

                # transcript ontvangen → beslissen via jouw workflow
                if t in ("input_audio_transcription.completed","response.input_audio_transcription.completed","conversation.item.input_audio_transcription.completed"):
                    tx = d.get("transcript") or d.get("input_audio_transcription",{}).get("text") or d.get("text","")
                    user = (tx or "").strip().lower()
                    if not user: continue
                    print("USER>", user)

                    # update state
                    md = detect_mode(user)
                    if md: st.mode = md
                    items, _ = parse_items(user)
                    if items: st.merge(items)

                    # beslis vervolgstap (alle berekeningen via cf.* + ls.get_all())
                    if not st.items:
                        await say(oai, "Wat wilt u bestellen?")
                        continue

                    if st.items and not st.mode:
                        await say(oai, "Wilt u laten bezorgen of komt u het afhalen?")
                        continue

                    # we hebben items + modus → berekenen
                    s = ls.get_all()
                    mins = cf.total_minutes(st.mode, st.items, s)
                    tline = cf.time_phrase(st.mode, mins)
                    summary, total = cf.summarize(st.items)
                    pay = cf.payment_phrase(st.mode)

                    yn = detect_yesno(user)
                    if yn=="ja":
                        await say(oai, f"Dank u wel. De bestelling staat genoteerd: {summary}. Totaal {total} euro. {tline} {pay}. Fijne avond!")
                        continue
                    if yn=="nee":
                        await say(oai, "Geen probleem. Wat wilt u wijzigen of toevoegen?")
                        continue

                    await say(oai, f"Ik heb genoteerd: {summary}. Dat is in totaal {total} euro. {tline} {pay}. Klopt dat?")
                    continue

                if t=="response.completed":
                    await ws.send_text(json.dumps({"event":"mark","mark":{"name":"oai_done"}}))
        except Exception as e:
            print("OUT err:", e)

    t1 = asyncio.create_task(pump_in())
    t2 = asyncio.create_task(pump_out())
    await asyncio.wait([t1,t2], return_when=asyncio.FIRST_COMPLETED)

    try: await oai.close()
    except: pass
    try: await ws.close()
    except: pass
    print("WS closed")