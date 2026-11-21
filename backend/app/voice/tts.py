"""Text-to-speech via Gnani Timbre (Vachana) REST API.

Endpoint : POST https://api.vachana.ai/api/v1/tts/inference
Auth     : X-API-Key-ID header
Docs     : https://docs.gnani.ai/api/TTS/tts-inference.md

Returns raw audio bytes (WAV by default). Returns None when GNANI_API_KEY is
not configured so the frontend can fall back to browser SpeechSynthesis.
"""
from __future__ import annotations

import httpx

from app.config import settings
from app.voice.stt import _client

GNANI_TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
DEFAULT_VOICE = "Shivani"   # Hindi female, timbre-v3.0 (speaks all 10 languages)
DEFAULT_MODEL = "timbre-v3.0"


class TTSError(RuntimeError):
    """Raised when the TTS service rejects or fails a request."""


async def synthesize(
    text: str,
    language: str = "hi-en",
    voice: str = DEFAULT_VOICE,
    speed: float = 1.0,
    sample_rate: int = 24000,
) -> bytes | None:
    """Synthesize speech. Returns audio bytes, or None if not configured."""
    if not text or not text.strip():
        return None
    if not settings.GNANI_API_KEY:
        return None

    payload = {
        "text": text.strip(),
        "voice": voice,
        "model": DEFAULT_MODEL,
        "language": language,
        "speed": speed,
        "audio_config": {
            "sample_rate": sample_rate,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }

    client = _client()
    try:
        resp = await client.post(
            GNANI_TTS_URL,
            headers={
                "X-API-Key-ID": settings.GNANI_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
        )
    except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as exc:
        raise TTSError(f"Network error talking to Gnani TTS: {exc}")

    if resp.status_code == 401:
        raise TTSError("Gnani rejected the API key (401).")
    if resp.status_code == 402:
        raise TTSError("Gnani account has insufficient credit (402).")
    if resp.status_code == 403:
        raise TTSError(f"Gnani key lacks the TTS scope (403): {resp.text[:200]}")
    if resp.status_code == 429:
        raise TTSError("Gnani TTS rate limit hit (429).")
    if resp.status_code >= 400:
        raise TTSError(f"Gnani TTS failed ({resp.status_code}): {resp.text[:300]}")

    if not resp.content:
        raise TTSError("Gnani TTS returned empty audio.")
    return resp.content
