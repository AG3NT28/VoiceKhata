"""Customer unique ID: name3 + phone2, with seeded provisional codes."""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base, Shop
from app.khata.customers import create_customer, name_prefix, phone_suffix, refresh_customer_code


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as s:
        shop = Shop(name="Code Shop", timezone="Asia/Kolkata")
        s.add(shop)
        await s.commit()
        await s.refresh(shop)
        s._shop_id = shop.id
        yield s
    await engine.dispose()


def test_name_and_phone_helpers():
    assert name_prefix("Ramesh Kumar") == "RAM"
    assert name_prefix("Al") == "ALX"
    assert phone_suffix("9876543210") == "10"
    assert phone_suffix("98") == "98"
    assert phone_suffix(None) is None
    assert phone_suffix("1") is None


@pytest.mark.asyncio
async def test_voice_gets_seeded_provisional_then_phone_upgrades(db):
    shop_id = db._shop_id
    first = await create_customer(db, shop_id, "Ramesh")
    assert first.customer_code == "RAM00"
    second = await create_customer(db, shop_id, "Ramesh Gowda")
    assert second.customer_code == "RAM01"

    first.phone = "9876543210"
    await refresh_customer_code(db, first)
    await db.commit()
    await db.refresh(first)
    assert first.customer_code == "RAM10"


@pytest.mark.asyncio
async def test_create_with_phone_uses_final_code(db):
    shop_id = db._shop_id
    cust = await create_customer(db, shop_id, "Priya Sharma", "9000012345")
    assert cust.customer_code == "PRI45"
