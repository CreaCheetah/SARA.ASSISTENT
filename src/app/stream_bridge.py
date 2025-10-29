from __future__ import annotations
import os, json, base64, asyncio, audioop, time
from typing import Optional
from fastapi import APIRouter, WebSocket
import websockets

router = APIRouter()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview")
OPENAI_VOICE = os.getenv("OPENAI_VOICE", "alloy")  # bv. "alloy", "verse", "aria"

# ---------- audio helpers ----------
def ulaw_to_pcm8k(ulaw: bytes) -> bytes:
    # μ-law 8k, 8-bit -> PCM16 8k mono
    return audioop.ulaw2lin(ulaw, 2)

def pcm_resample(pcm: bytes, src_rate: int, dst_rate: int) -> bytes:
    # mono 16-bit
    if src_rate == dst_rate:
        return pcm
    return audioop.ratecv(pcm, 2, 1, src_rate, dst_rate, None)[0]

def pcm16_to_ulaw8k(pcm16_mono_8k: bytes) -> bytes:
    return audioop.lin2ulaw(pcm16_mono_8k, 2)

def chunk(iter_bytes: bytes, size: int):
    for i in range(0, len(iter_bytes), size):
        yield iter_bytes[i:i+size]

# ---------- OpenAI realtime ----------
async def openai_connect():
    url = f"wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1",
    }
    ws = await websockets.connect(url, extra_headers=headers, ping_interval=20, ping_timeout=20)
    # configure voice output (16k PCM frames)
    await ws.send(json.dumps({
        "type": "response.create",
        "response": {
            "instructions": "Je bent SARA. Spreek kort en natuurlijk Nederlands.",
            "modalities": ["audio"],
            "audio": {"voice": OPENAI_VOICE, "format": "pcm16"},
        }
    }))
    return ws

# ---------- Twilio <-> OpenAI bridge ----------
@router.websocket("/ws/twilio")
async def ws_twilio(ws: WebSocket):
    await ws.accept(subprotocol="twilio")
    if not OPENAI_API_KEY:
        print("OPENAI_API_KEY ontbreekt"); await ws.close(); return

    oai = await openai_connect()
    print("WS: connected Twilio <-> OpenAI")

    # buffers
    last_create_ts = 0.0
    pending_pcm_to_openai: bytearray = bytearray()
    pending_pcm_from_openai: bytearray = bytearray()

    async def pump_openai_to_twilio():
        # leest OpenAI events en speelt terug naar Twilio
        nonlocal pending_pcm_from_openai
        try:
            async for msg in oai:
                try:
                    data = json.loads(msg)
                except Exception:
                    continue

                t = data.get("type")
                if t == "output_audio_buffer.delta":
                    pcm16_16k = base64.b64decode(data["audio"])
                    # naar 8k resamplen en naar μ-law omzetten
                    pcm16_8k = pcm_resample(pcm16_16k, 16000, 8000)
                    ulaw_8k = pcm16_to_ulaw8k(pcm16_8k)
                    # Twilio verwacht 20ms frames: 8k * 0.02 = 160 bytes
                    for frame in chunk(ulaw_8k, 160):
                        await ws.send_text(json.dumps({
                            "event": "media",
                            "media": {"payload": base64.b64encode(frame).decode()}
                        }))
                elif t == "response.completed":
                    # mark voor debug
                    await ws.send_text(json.dumps({"event": "mark", "mark": {"name": "oai_done"}}))
        except Exception as e:
            print("pump_openai_to_twilio error:", e)

    task_back = asyncio.create_task(pump_openai_to_twilio())

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            ev = msg.get("event")

            if ev == "start":
                print("WS start:", msg.get("start", {}))

            elif ev == "media":
                ulaw_b64 = msg["media"]["payload"]
                ulaw = base64.b64decode(ulaw_b64)
                pcm8k = ulaw_to_pcm8k(ulaw)               # PCM16 8k
                pcm16k = pcm_resample(pcm8k, 8000, 16000) # PCM16 16k
                pending_pcm_to_openai += pcm16k

                # stuur in kleine brokken om latency laag te houden
                if len(pending_pcm_to_openai) >= 3200:  # ~100ms bij 16kHz
                    await oai.send(json.dumps({"type": "input_audio_buffer.append",
                                               "audio": base64.b64encode(bytes(pending_pcm_to_openai)).decode()}))
                    pending_pcm_to_openai.clear()
                    await oai.send(json.dumps({"type": "input_audio_buffer.commit"}))

                    # throttle response.create tot max 4x/sec
                    now = time.time()
                    if now - last_create_ts > 0.25:
                        await oai.send(json.dumps({"type": "response.create"}))
                        last_create_ts = now

            elif ev == "stop":
                print("WS stop")
                break

    except Exception as e:
        print("WS error:", e)
    finally:
        try:
            await oai.close()
        except Exception:
            pass
        task_back.cancel()
        await ws.close()
        print("WS closed")
