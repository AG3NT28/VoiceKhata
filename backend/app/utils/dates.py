"""Relative date resolution using shop timezone (Asia/Kolkata)."""
from datetime import date, timedelta, datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None

# Fallback for Windows machines without the `tzdata` package installed.
_IST = timezone(timedelta(hours=5, minutes=30), name="IST")


def _zone(tz_name: str):
    if ZoneInfo is None:
        return _IST
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return _IST


def today_in_tz(tz_name: str = "Asia/Kolkata") -> date:
    return datetime.now(_zone(tz_name)).date()


def resolve_date(expr: str | None, tz_name: str = "Asia/Kolkata") -> tuple[date, bool]:
    """
    Resolve a relative date expression to an ISO date.
    Returns (date, was_inferred). If expr is None or 'aaj', returns today.
    """
    if not expr:
        return today_in_tz(tz_name), True
    e = expr.strip().lower()
    today = today_in_tz(tz_name)
    if e in ("aaj", "today", "aj"):
        return today, False
    if e in ("kal", "yesterday"):
        return today - timedelta(days=1), True
    if e in ("parso", "day before yesterday"):
        return today - timedelta(days=2), True
    if e in ("tomorrow", "kal (future)"):
        return today + timedelta(days=1), True
    # Default: today, inferred
    return today, True
