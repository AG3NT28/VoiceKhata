import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Customer, Shop
from app.utils.paise import *  # noqa

async def generate_customer_code(db: AsyncSession, shop_id: uuid.UUID) -> str:
    result = await db.execute(
        select(func.count()).select_from(Customer).where(Customer.shop_id == shop_id)
    )
    count = (result.scalar() or 0) + 1
    return f"C{count:04d}"

async def create_customer(db: AsyncSession, shop_id: uuid.UUID, name: str, phone: str | None = None) -> Customer:
    normalized = " ".join(name.strip().lower().split())
    code = await generate_customer_code(db, shop_id)
    customer = Customer(
        shop_id=shop_id,
        name=name.strip(),
        phone=phone,
        normalized_name=normalized,
        customer_code=code,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer

async def find_customer_by_code(db: AsyncSession, shop_id: uuid.UUID, code: str) -> Customer | None:
    result = await db.execute(
        select(Customer).where(Customer.shop_id == shop_id, Customer.customer_code == code.strip().upper())
    )
    return result.scalar_one_or_none()

async def find_customers_by_name(db: AsyncSession, shop_id: uuid.UUID, name: str) -> list[Customer]:
    normalized = " ".join(name.strip().lower().split())
    result = await db.execute(
        select(Customer).where(Customer.shop_id == shop_id, Customer.normalized_name == normalized)
    )
    return list(result.scalars().all())

async def list_customers(db: AsyncSession, shop_id: uuid.UUID, q: str = "") -> list[Customer]:
    stmt = select(Customer).where(Customer.shop_id == shop_id)
    if q:
        stmt = stmt.where(Customer.name.ilike(f"%{q}%"))
    result = await db.execute(stmt.order_by(Customer.name))
    return list(result.scalars().all())
