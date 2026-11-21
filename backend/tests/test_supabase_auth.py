"""Smoke tests for Supabase → demo-shop token exchange."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from jose import jwt

from app.config import settings
from app.main import app


def _mint_supabase_token(secret: str, email: str = "shop@example.com") -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_supabase_exchange_issues_shop_token(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "test-supabase-jwt-secret")
    token = _mint_supabase_token("test-supabase-jwt-secret")
    with TestClient(app) as client:
        res = client.post("/auth/supabase", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    assert body["shop_name"]


def test_supabase_exchange_rejects_bad_token(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "test-supabase-jwt-secret")
    with TestClient(app) as client:
        res = client.post("/auth/supabase", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


def test_demo_auth_can_be_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_DEMO_AUTH", False)
    with TestClient(app) as client:
        res = client.post("/auth/demo")
    assert res.status_code == 403
