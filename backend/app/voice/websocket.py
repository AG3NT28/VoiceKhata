"""WebSocket voice channel (optional transport for the prototype)."""
from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.voice import get_demo_shop
from app.database.db import SessionLocal
from app.voice.pipeline import handle_transcript
from app.voice.stt import STTError, transcribe_detailed

router = APIRouter()


@router.websocket("/ws/voice")
async def voice_socket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "ready"})
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            audio = message.get("bytes")
            text = message.get("text")
            if not audio and not text:
                continue

            async with SessionLocal() as db:
                shop = await get_demo_shop(db)

                if audio:
                    try:
                        stt = await transcribe_detailed(audio, "audio.wav")
                    except STTError as exc:
                        await websocket.send_json({"type": "error", "message": str(exc)})
                        continue
                    transcript = stt["transcript"]
                else:
                    try:
                        payload = json.loads(text)
                    except json.JSONDecodeError:
                        payload = {"text": text}
                    transcript = payload.get("text", "")
                    stt = {"engine": "typed", "transcript": transcript}

                result = await handle_transcript(db, shop.id, transcript)
                result["stt"] = stt
                await websocket.send_json({"type": "result", **result})
    except WebSocketDisconnect:
        pass
