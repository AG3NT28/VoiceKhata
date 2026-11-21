"""Relative date resolution using shop timezone (Asia/Kolkata)."""
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo

def today_in_tz(tz_name: str = "Asia/Kolkata") -> date:
    return datetime.now(ZoneInfo(tz_name)).date()

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
