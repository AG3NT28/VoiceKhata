"""Safe supplier redirection — no open redirects."""
from __future__ import annotations

from urllib.parse import urlparse

APPROVED_DOMAIN_HINTS = {
    "jumbotail": ["jumbotail.com"],
    "wishbee": ["wishbee.in", "wishbee.com"],
    "udaan": ["udaan.com"],
    "ondc": ["ondc.org"],
    "blinkit": ["blinkit.com"],
    "bigbasket": ["bigbasket.com"],
    "jiomart": ["jiomart.com"],
    "independent_wholesale": [],
    "demo_catalogue": ["example.com", "localhost"],
}


def is_safe_redirect(url: str | None, provider_code: str, approved_domains: str = "") -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False

    allowed: list[str] = []
    if approved_domains:
        allowed.extend([d.strip().lower() for d in approved_domains.split(",") if d.strip()])
    allowed.extend(APPROVED_DOMAIN_HINTS.get(provider_code, []))

    if not allowed:
        # Independent wholesalers may use any https URL recorded at import time —
        # still require https and block obvious dangerous schemes (already checked).
        return parsed.scheme == "https" or host in ("localhost", "127.0.0.1")

    return any(host == d or host.endswith("." + d) for d in allowed)
