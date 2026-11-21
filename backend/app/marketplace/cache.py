"""Simple in-memory TTL cache for marketplace search results."""
from __future__ import annotations

import time
from threading import Lock
from typing import Any

_DEFAULT_TTL = 120  # seconds
_lock = Lock()
_store: dict[str, tuple[float, Any]] = {}


def cache_get(key: str) -> Any | None:
    now = time.time()
    with _lock:
        item = _store.get(key)
        if not item:
            return None
        expires, value = item
        if expires < now:
            _store.pop(key, None)
            return None
        return value


def cache_set(key: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
    with _lock:
        _store[key] = (time.time() + ttl, value)


def cache_clear() -> None:
    with _lock:
        _store.clear()
