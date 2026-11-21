"""Speech-to-text via Gnani Prisma (Vachana) REST API.

Endpoint : POST https://api.vachana.ai/stt/v3
Auth     : X-API-Key-ID header
Docs     : https://docs.gnani.ai/api/STT/speech-to-text

Falls back to Groq Whisper when GNANI_API_KEY is not configured, and to a
canned transcript when neither is available (offline demo mode).
"""
from __future__ import annotations

import httpx

from app.config import settings

GNANI_STT_URL = "https://api.vachana.ai/stt/v3"
DEFAULT_LANGUAGES = "hi-IN,en-IN"

MOCK_TRANSCRIPT = "Ramesh ka 340 rupaye udhaar likho"


class STTError(RuntimeError):
    """Raised when the speech service rejects or fails a request."""


def _mime_for(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "wav"
    return {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
        "aac": "audio/aac",
        "m4a": "audio/mp4",
    }.get(ext, "audio/wav")


async def transcribe_detailed(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    language_code: str = DEFAULT_LANGUAGES,
    output_format: str = "transliterate",
) -> dict:
    """Transcribe audio and return the provider response plus engine metadata."""
    if not audio_bytes:
        raise STTError("Empty audio payload")

    if not settings.GNANI_API_KEY:
        if settings.LLM_API_KEY:
            text = await _transcribe_groq(audio_bytes, filename)
            return {"transcript": text, "engine": "groq-whisper", "language": language_code}
        return {
            "transcript": MOCK_TRANSCRIPT,
            "engine": "mock",
            "language": language_code,
            "note": "GNANI_API_KEY not set - returning mock transcript",
        }

    data = {
        "model": "prisma-v3.0",
        "language_code": language_code,
        "format": output_format,
        "topic": "Kirana store customer ledger, udhaar and payment entries in Hindi and English",
        "keyterms": '["udhaar","khata","rupaye","baaki","jama","payment","balance"]',
    }
    files = {"audio_file": (filename, audio_bytes, _mime_for(filename))}

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            GNANI_STT_URL,
            headers={"X-API-Key-ID": settings.GNANI_API_KEY},
            files=files,
            data=data,
        )

    if resp.status_code == 401:
        raise STTError("Gnani rejected the API key (401). Check GNANI_API_KEY.")
    if resp.status_code == 402:
        raise STTError("Gnani account has insufficient credit (402).")
    if resp.status_code == 403:
        raise STTError(f"Gnani key lacks the STT scope (403): {resp.text[:200]}")
    if resp.status_code == 429:
        raise STTError("Gnani rate limit hit (429). Wait a moment and retry.")
    if resp.status_code >= 400:
        raise STTError(f"Gnani STT failed ({resp.status_code}): {resp.text[:300]}")

    body = resp.json()
    if not body.get("success", True):
        err = body.get("error") or {}
        raise STTError(f"Gnani STT error {err.get('type')}: {err.get('message')}")

    return {
        "transcript": (body.get("transcript") or "").strip(),
        "engine": "gnani-prisma-v3",
        "model": body.get("model", "prisma-v3.0"),
        "language": body.get("detected_language_code", language_code),
        "processing_time": body.get("processing_time"),
        "latency": body.get("end_to_end_latency"),
        "request_id": body.get("request_id"),
    }


async def transcribe(audio_bytes: bytes, filename: str = "audio.wav", language_code: str = DEFAULT_LANGUAGES) -> str:
    """Backwards-compatible helper that returns only the transcript string."""
    result = await transcribe_detailed(audio_bytes, filename, language_code)
    return result["transcript"]


async def _transcribe_groq(audio_bytes: bytes, filename: str) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.LLM_BASE_URL}/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
            files={"file": (filename, audio_bytes, _mime_for(filename))},
            data={"model": "whisper-large-v3", "language": "hi", "response_format": "json"},
        )
    if resp.status_code >= 400:
        raise STTError(f"Groq Whisper failed ({resp.status_code}): {resp.text[:200]}")
    return (resp.json().get("text") or "").strip()
