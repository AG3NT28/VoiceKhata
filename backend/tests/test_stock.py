"""Stock API smoke tests against shared SQLite DB."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _auth_headers(client: AsyncClient) -> dict:
    res = await client.post("/auth/demo")
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_stock_list_and_summary(client):
    headers = await _auth_headers(client)
    listed = await client.get("/stock", headers=headers)
    assert listed.status_code == 200
    assert isinstance(listed.json(), list)

    summary = await client.get("/stock/summary", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert "total_items" in body
    assert "by_category" in body


@pytest.mark.asyncio
async def test_stock_add_remove_adjust(client):
    headers = await _auth_headers(client)
    created = await client.post(
        "/stock",
        headers=headers,
        json={
            "name": "Test Atta Pack",
            "category": "groceries",
            "quantity": 10,
            "unit_price_paise": 5000,
            "minimum_quantity": 3,
        },
    )
    assert created.status_code == 201
    item = created.json()
    item_id = item["id"]
    assert item["quantity"] == 10
    assert item["unit_price_rupees"] == 50.0

    added = await client.post(
        f"/stock/{item_id}/add",
        headers=headers,
        json={"quantity": 5, "reason": "restock"},
    )
    assert added.status_code == 200
    assert added.json()["quantity"] == 15

    removed = await client.post(
        f"/stock/{item_id}/remove",
        headers=headers,
        json={"quantity": 4, "reason": "sold"},
    )
    assert removed.status_code == 200
    assert removed.json()["quantity"] == 11

    short = await client.post(
        f"/stock/{item_id}/remove",
        headers=headers,
        json={"quantity": 100, "reason": "sold"},
    )
    assert short.status_code == 400

    adjusted = await client.post(
        f"/stock/{item_id}/adjust",
        headers=headers,
        json={"delta": -2, "reason": "damage"},
    )
    assert adjusted.status_code == 200
    assert adjusted.json()["quantity"] == 9

    logs = await client.get(f"/stock/{item_id}/log", headers=headers)
    assert logs.status_code == 200
    assert len(logs.json()) >= 3
