import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.models import Base, Shop
from app.database.db import SessionLocal
from app.khata.customers import create_customer, find_customers_by_name
from app.khata.ledger import add_credit, record_payment, compute_balance
from app.khata.corrections import correct_transaction
from app.utils.paise import rupees_to_paise, paise_to_rupees

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session() as s:
        # create a shop
        shop = Shop(name="Test Shop", timezone="Asia/Kolkata")
        s.add(shop)
        await s.commit()
        await s.refresh(shop)
        s._shop_id = shop.id
        yield s
    await engine.dispose()

@pytest.mark.asyncio
async def test_paise_conversion():
    assert rupees_to_paise(340.50) == 34050
    assert paise_to_rupees(34050) == 340.50

@pytest.mark.asyncio
async def test_create_customer_and_credit_payment_balance(db):
    shop_id = db._shop_id
    cust = await create_customer(db, shop_id, "Ramesh Kumar", "9999999999")
    assert cust.customer_code == "RAM99"
    assert cust.name == "Ramesh Kumar"

    credit = await add_credit(db, shop_id, cust.id, rupees_to_paise(340), __import__("datetime").date.today())
    assert credit.type.value == "credit"
    assert credit.amount_paise == 34000

    payment = await record_payment(db, shop_id, cust.id, rupees_to_paise(200), __import__("datetime").date.today())
    assert payment.type.value == "payment"

    bal = await compute_balance(db, cust.id)
    assert bal == rupees_to_paise(140)

@pytest.mark.asyncio
async def test_idempotency(db):
    shop_id = db._shop_id
    cust = await create_customer(db, shop_id, "Suresh")
    key = "test-key-123"
    t1 = await add_credit(db, shop_id, cust.id, 50000, __import__("datetime").date.today(), idempotency_key=key)
    t2 = await add_credit(db, shop_id, cust.id, 50000, __import__("datetime").date.today(), idempotency_key=key)
    assert t1.id == t2.id

@pytest.mark.asyncio
async def test_correction(db):
    shop_id = db._shop_id
    cust = await create_customer(db, shop_id, "Mahesh")
    original = await add_credit(db, shop_id, cust.id, 34000, __import__("datetime").date.today())
    corrected = await correct_transaction(db, original, new_amount_paise=43000)
    assert corrected.amount_paise == 43000
    assert corrected.supersedes == original.id
    await db.refresh(original)
    assert original.status.value == "reversed"
    assert original.reversed_by == corrected.id
    bal = await compute_balance(db, cust.id)
    assert bal == 43000

@pytest.mark.asyncio
async def test_disambiguation_multiple_same_name(db):
    shop_id = db._shop_id
    await create_customer(db, shop_id, "Ramesh Kumar")
    await create_customer(db, shop_id, "Ramesh Gowda")
    matches = await find_customers_by_name(db, shop_id, "Ramesh Kumar")
    # only exact normalized match
    assert len(matches) == 1
    all_ramesh = await find_customers_by_name(db, shop_id, "Ramesh")
    # different normalized names, so no exact match for just "Ramesh"
    assert len(all_ramesh) == 0
