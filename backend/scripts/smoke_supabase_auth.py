"""Manual smoke: mint a Supabase-like JWT and exchange it for a shop token."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from jose import jwt

from app.config import settings

BASE = "http://127.0.0.1:8000"


def main() -> None:
    secret = (settings.SUPABASE_JWT_SECRET or "").strip() or "dev-smoke-supabase-secret"
    # Temporarily use the same secret the server has; if empty in .env, patch is not live.
    # For smoke we call verify path by posting a token signed with whatever is configured.
    if not (settings.SUPABASE_JWT_SECRET or "").strip():
        print("SKIP_EXCHANGE: set SUPABASE_JWT_SECRET in backend/.env to smoke /auth/supabase")
    else:
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": "11111111-1111-1111-1111-111111111111",
                "email": "smoke@example.com",
                "role": "authenticated",
                "aud": "authenticated",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(hours=1)).timestamp()),
            },
            settings.SUPABASE_JWT_SECRET.strip(),
            algorithm="HS256",
        )
        r = httpx.post(f"{BASE}/auth/supabase", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        print("supabase_exchange", r.status_code, r.text[:200])
        r.raise_for_status()

    demo = httpx.post(f"{BASE}/auth/demo", timeout=10)
    print("demo_auth", demo.status_code)
    demo.raise_for_status()
    shop_token = demo.json()["access_token"]
    customers = httpx.get(
        f"{BASE}/customers?status=active",
        headers={"Authorization": f"Bearer {shop_token}"},
        timeout=10,
    )
    print("customers", customers.status_code, "total=", customers.json().get("total"))
    customers.raise_for_status()
    print("OK")


if __name__ == "__main__":
    main()
