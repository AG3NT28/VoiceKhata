"""Speech-to-text via Gnani Prisma (Vachana) REST API.

Endpoint : POST https://api.vachana.ai/stt/v3
Auth     : X-API-Key-ID header
Docs     : https://docs.gnani.ai/api/STT/speech-to-text

Falls back to Groq Whisper when GNANI_API_KEY is not configured, and to a
canned transcript when neither is available (offline demo mode).
"""
from __future__ import annotations

import asyncio
import httpx

from app.config import settings

GNANI_STT_URL = "https://api.vachana.ai/stt/v3"
DEFAULT_LANGUAGES = "hi-IN,en-IN"

MOCK_TRANSCRIPT = "Ramesh ka 340 rupaye udhaar likho"

# Reusable client — avoids a fresh TLS handshake on every request (saves ~2-3s).
_http: httpx.AsyncClient | None = None


def _client() -> httpx.AsyncClient:
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(
            timeout=20.0,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _http


async def close_client() -> None:
    global _http
    if _http is not None and not _http.is_closed:
        await _http.aclose()
    _http = None


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


_RETRYABLE = {429, 500, 502, 503, 504}


async def transcribe_detailed(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    language_code: str = DEFAULT_LANGUAGES,
    output_format: str = "transliterate",
    previous_text: str | None = None,
    max_retries: int = 3,
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

    # Gnani Prisma is biased via keyterms/topic (not offline fine-tunes).
    # Price-comparison JSONL trains these lists for grocery / marketplace ASR.
    try:
        from app.ai.price_dataset import gnani_keyterms_json, gnani_topic

        keyterms = gnani_keyterms_json(200)
        topic = gnani_topic()
    except Exception:
        keyterms = (
            '["udhaar","khata","rupaye","baaki","jama","payment","balance","likho","diye",'
            '"customer","sau","hazaar","lakh","credit","wholesale","compare","atta","dal","oil"]'
        )
        topic = "Indian kirana shopkeeper speaking about khata ledger and wholesale prices."

    data = {
        "model": "prisma-v3.0",
        "language_code": language_code,
        "format": output_format,
        "keyterms": keyterms,
        "topic": topic[:1600],
    }
    if previous_text:
        data["previous_text"] = previous_text[-600:]
    files = {"audio_file": (filename, audio_bytes, _mime_for(filename))}

    client = _client()
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = await client.post(
                GNANI_STT_URL,
                headers={"X-API-Key-ID": settings.GNANI_API_KEY},
                files=files,
                data=data,
            )
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as exc:
            last_exc = STTError(f"Network error talking to Gnani: {exc}")
            await asyncio.sleep(0.5 * (2 ** attempt))
            continue

        if resp.status_code in _RETRYABLE:
            last_exc = STTError(f"Gnani STT temporary failure ({resp.status_code}): {resp.text[:200]}")
            await asyncio.sleep(0.5 * (2 ** attempt))
            continue

        if resp.status_code == 401:
            raise STTError("Gnani rejected the API key (401). Check GNANI_API_KEY.")
        if resp.status_code == 402:
            raise STTError("Gnani account has insufficient credit (402).")
        if resp.status_code == 403:
            raise STTError(f"Gnani key lacks the STT scope (403): {resp.text[:200]}")
        if resp.status_code == 422:
            raise STTError(f"Gnani validation error (422): {resp.text[:300]}")
        if resp.status_code >= 400:
            raise STTError(f"Gnani STT failed ({resp.status_code}): {resp.text[:300]}")

        body = resp.json()
        if not body.get("success", True):
            err = body.get("error") or {}
            raise STTError(f"Gnani STT error {err.get('type')}: {err.get('message')}")

        truncated = bool(body.get("truncated"))
        result = {
            "transcript": (body.get("transcript") or "").strip(),
            "engine": "gnani-prisma-v3",
            "model": body.get("model", "prisma-v3.0"),
            "language": body.get("detected_language_code", language_code),
            "processing_time": body.get("processing_time"),
            "latency": body.get("end_to_end_latency"),
            "request_id": body.get("request_id"),
            "truncated": truncated,
        }
        if truncated:
            result["warning"] = "Transcript was truncated (audio too long). Split the recording."
        return result

    raise last_exc or STTError("Gnani STT failed after retries.")


async def transcribe(audio_bytes: bytes, filename: str = "audio.wav", language_code: str = DEFAULT_LANGUAGES) -> str:
    """Backwards-compatible helper that returns only the transcript string."""
    result = await transcribe_detailed(audio_bytes, filename, language_code)
    return result["transcript"]


async def _transcribe_groq(audio_bytes: bytes, filename: str) -> str:
    client = _client()
    resp = await client.post(
        f"{settings.LLM_BASE_URL}/audio/transcriptions",
        headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
        files={"file": (filename, audio_bytes, _mime_for(filename))},
        data={"model": "whisper-large-v3", "language": "hi", "response_format": "json"},
    )
    if resp.status_code >= 400:
        raise STTError(f"Groq Whisper failed ({resp.status_code}): {resp.text[:200]}")
    return (resp.json().get("text") or "").strip()
