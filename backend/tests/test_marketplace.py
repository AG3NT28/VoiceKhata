"""Marketplace unit + API smoke tests (demonstration data only)."""
from __future__ import annotations

import io

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.marketplace.price_engine import calculate_landed_cost, required_order_units
from app.marketplace.product_matcher import score_match
from app.marketplace.product_parser import parse_product_query
from app.marketplace.redirect_service import is_safe_redirect
from app.marketplace.schemas import ProductParseResult


def test_parse_fortune_oil():
    parsed = parse_product_query("Find 10 kg Fortune sunflower oil at wholesale price.")
    assert parsed.brand == "Fortune"
    assert parsed.variant == "Sunflower"
    assert parsed.requested_quantity == 10
    assert parsed.unit == "kg"
    assert parsed.purchase_type == "wholesale"


def test_variant_mismatch_not_equivalent():
    parsed = ProductParseResult(
        product_name="Sunflower Oil",
        brand="Fortune",
        variant="Sunflower",
        requested_quantity=1,
        unit="l",
    )
    bad = score_match(
        parsed,
        title="Fortune Groundnut Oil 1L",
        brand="Fortune",
        variant="Groundnut",
        package_quantity=1,
        unit="l",
    )
    assert bad.confidence == 0.0
    assert bad.reason == "variant_mismatch"


def test_moq_and_case_rounding():
    assert required_order_units(10, 5, moq=10, case_size=5) == 10
    # ceil(6/5)=2 packs, then round up to case_size 4
    assert required_order_units(6, 5, moq=1, case_size=4) == 4


def test_landed_cost_and_effective_unit():
    result = calculate_landed_cost(
        base_price_paise=10000,
        package_quantity=1,
        moq=12,
        case_size=12,
        requested_quantity=10,
        gst_percent=5,
        delivery_charges_paise=2000,
        discount_paise=0,
        platform_fee_paise=100,
    )
    assert result.order_units == 12
    assert result.price_complete is True
    assert result.gst_paise == 6000  # 5% of 120000
    assert result.landed_cost_paise == 120000 + 6000 + 2000 + 100
    assert result.effective_unit_paise == int(round(result.landed_cost_paise / 12))


def test_incomplete_when_gst_unknown():
    result = calculate_landed_cost(
        base_price_paise=10000,
        package_quantity=1,
        requested_quantity=1,
        gst_percent=None,
        delivery_charges_paise=500,
    )
    assert result.price_complete is False
    assert "gst_unknown" in result.notes


def test_redirect_domain_guard():
    assert is_safe_redirect("https://example.com/demo/x", "demo_catalogue", "example.com")
    assert not is_safe_redirect("https://evil.example/phish", "jumbotail", "jumbotail.com")
    assert not is_safe_redirect("javascript:alert(1)", "demo_catalogue", "example.com")


async def _ensure_tables():
    from app.database.db import engine
    from app.database.models import Base
    import app.marketplace.models  # noqa: F401
    from app.marketplace.seed import seed_marketplace
    from app.database.db import SessionLocal

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        await seed_marketplace(db)


@pytest.mark.asyncio
async def test_marketplace_search_api():
    await _ensure_tables()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth = await client.post("/auth/email", json={"email": "mkt-test@shop.test"})
        assert auth.status_code == 200
        token = auth.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        providers = await client.get("/api/marketplace/providers", headers=headers)
        assert providers.status_code == 200
        codes = {p["code"] for p in providers.json()}
        assert "demo_catalogue" in codes
        assert "jumbotail" in codes

        search = await client.post(
            "/api/marketplace/search",
            headers=headers,
            json={"query": "Fortune sunflower oil wholesale", "purchase_type": "wholesale"},
        )
        assert search.status_code == 200
        body = search.json()
        assert body["parsed"]["brand"] == "Fortune"
        assert any(o["price_source"] == "demonstration" for o in body["offers"])
        # groundnut must not dominate sunflower search top if matched
        titles = " ".join(o["title"].lower() for o in body["offers"])
        assert "sunflower" in titles

        # unauthorized without token
        bare = await client.get("/api/marketplace/providers")
        assert bare.status_code == 401


@pytest.mark.asyncio
async def test_catalogue_import_csv():
    await _ensure_tables()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth = await client.post("/auth/email", json={"email": "mkt-import@shop.test"})
        token = auth.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        csv_body = (
            "product_name,brand,sku,package_size,unit,wholesale_price,moq,gst_percent,delivery_charges,stock\n"
            "Local Atta 5kg,LocalBrand,LOC-ATTA-5,5,kg,240,10,5,100,in_stock\n"
            ",BadRow,,,,\n"
        ).encode()
        files = {"file": ("catalogue.csv", io.BytesIO(csv_body), "text/csv")}
        data = {"supplier_name": "Test Wholesaler"}
        resp = await client.post(
            "/api/marketplace/suppliers/import",
            headers=headers,
            files=files,
            data=data,
        )
        assert resp.status_code == 200
        report = resp.json()
        assert report["imported"] >= 1
        assert report["rejected"] >= 1
