from __future__ import annotations
from fastapi import APIRouter, WebSocket
import json, base64

router = APIRouter()

@router.websocket("/ws/twilio")
async def ws_twilio(ws: WebSocket):
    # Twilio verwacht subprotocol "twilio", maar accepteert zonder ook vaak.
    await ws.accept(subprotocol="twilio")
    print("WS: connected")

    media_frames = 0
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            ev = msg.get("event")
            if ev == "start":
                print("WS start:", msg.get("start", {}))
            elif ev == "media":
                media_frames += 1
                # payload = base64.b64decode(msg["media"]["payload"])  # μ-law 8k
            elif ev == "mark":
                pass
            elif ev == "stop":
                print("WS stop")
                break
    except Exception as e:
        print("WS error:", e)
    finally:
        print(f"WS closed, frames={media_frames}")
        await ws.close()
