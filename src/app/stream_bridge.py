from __future__ import annotations
from fastapi import APIRouter, WebSocket
import os, json, base64, asyncio, audioop
import websockets

router = APIRouter()

OPENAI_KEY   = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview")
VOICE        = os.getenv("OPENAI_REALTIME_VOICE", "marin")  # bv. marin / aria / alloy / verse / luna / sol / shimmer

# Twilio 8k μ-law ↔ PCM16
def ulaw_to_pcm16(ulaw: bytes) -> bytes:
    return audioop.ulaw2lin(ulaw, 2)

def pcm16_to_ulaw(pcm16: bytes) -> bytes:
    return audioop.lin2ulaw(pcm16, 2)

async def openai_connect():
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI_API_KEY ontbreekt")
    url = f"wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}"
    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "OpenAI-Beta": "realtime=v1",
    }
    return await websockets.connect(
        url, extra_headers=headers,
        ping_interval=20, ping_timeout=20, max_size=10_000_000
    )

@router.websocket("/ws/twilio")
async def ws_twilio(ws: WebSocket):
    # Twilio verwacht subprotocol "twilio"
    await ws.accept(subprotocol="twilio")
    if not OPENAI_KEY:
        await ws.close(); return

    oai = await openai_connect()
    print("WS: Twilio connected, OpenAI session up")

    # 1) NL-setup: VAD + transcriptie NL + TTS-stem
    async def init_openai():
        try:
            # a) sessieconfig (VAD + transcript NL)
            await oai.send(json.dumps({
                "type": "session.update",
                "session": {
                    # NL transcriptie
                    "input_audio_transcription": { "model": "gpt-4o-transcribe", "language": "nl" },
                    # server-side VAD (pauze detectie)
                    "turn_detection": { "type": "server_vad", "threshold": 0.5, "silence_duration_ms": 600 },
                }
            }))
            # b) openingsrespons + persona + flow
            await oai.send(json.dumps({
                "type": "response.create",
                "response": {
                    "modalities": ["audio"],
                    "instructions": (
                        "Je bent SARA, de Nederlandse bestelassistent voor Ristorante Adam Spanbroek. "
                        "Spreek kort, vriendelijk en natuurlijk. "
                        "Gespreksflow:\n"
                        "1) Groet passend bij het moment van de dag. Vraag: 'Wat wilt u bestellen?'\n"
                        "2) Luister naar gerechten; herhaal kort wat je hebt genoteerd.\n"
                        "3) Vraag daarna: 'Wilt u laten bezorgen of komt u het afhalen?'\n"
                        "4) Noem de totale prijs en de tijd (zeg 'bezorgtijd' of 'afhaaltijd'). "
                        "   Betaalopties: bezorgen = contant; afhalen = contant of pin.\n"
                        "5) Vraag: 'Klopt dat?' en rond af.\n"
                        "Houd zinnen kort, geen onnodige voorbeelden. Taal = Nederlands."
                    ),
                    "audio": { "voice": VOICE }
                }
            }))
        except Exception as e:
            print("OpenAI init error:", e)

    # Twilio -> OpenAI (caller audio → ASR → antwoord)
    async def pump_twilio_to_openai():
        try:
            started = False
            while True:
                raw = await ws.receive_text()
                msg = json.loads(raw)
                ev = msg.get("event")

                if ev == "start":
                    if not started:
                        started = True
                        await init_openai()

                elif ev == "media":
                    # μ-law → PCM16 → naar OAI buffer
                    ulaw_b64 = msg["media"]["payload"]
                    pcm16 = ulaw_to_pcm16(base64.b64decode(ulaw_b64))

                    await oai.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(pcm16).decode()
                    }))
                    # commit + vraag om respons (streamend, met VAD werkt turn-taking natuurlijk)
                    await oai.send(json.dumps({"type": "input_audio_buffer.commit"}))
                    await oai.send(json.dumps({"type": "response.create"}))

                elif ev == "stop":
                    break

        except Exception as e:
            print("pump_twilio_to_openai err:", e)
        finally:
            try:
                await oai.send(json.dumps({"type": "session.close"}))
            except Exception:
                pass

    # OpenAI -> Twilio (TTS-audio terug)
    async def pump_openai_to_twilio():
        try:
            async for frame in oai:
                try:
                    data = json.loads(frame)
                except Exception:
                    continue

                t = data.get("type")

                # Audio-chunks (PCM16 b64) → μ-law → naar Twilio
                if t == "output_audio_buffer.delta":
                    pcm16 = base64.b64decode(data["audio"])
                    ulaw = pcm16_to_ulaw(pcm16)
                    await ws.send_text(json.dumps({
                        "event": "media",
                        "media": { "payload": base64.b64encode(ulaw).decode() }
                    }))

                # (optioneel) teksttranscript tonen in logs (handig voor debug)
                elif t == "response.output_text.delta":
                    # print zonder breken (Render logs)
                    fragment = data.get("delta","")
                    if fragment:
                        print("TTS>", fragment)

                # segmentmarkering
                elif t == "response.completed":
                    await ws.send_text(json.dumps({ "event": "mark", "mark": { "name": "oai_done" } }))

        except Exception as e:
            print("pump_openai_to_twilio err:", e)

    t1 = asyncio.create_task(pump_twilio_to_openai())
    t2 = asyncio.create_task(pump_openai_to_twilio())
    await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)

    try:
        await oai.close()
    except Exception:
        pass
    try:
        await ws.close()
    except Exception:
        pass
    print("WS closed")