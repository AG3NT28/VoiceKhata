"""Customer helpers — unique codes: first 3 name letters + 2 phone digits."""
from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Customer

_PHONE_DIGITS = re.compile(r"\D+")


def name_prefix(name: str) -> str:
    """First 3 letters of the name (A–Z / unicode letters), padded with X if short."""
    letters = "".join(ch for ch in (name or "") if ch.isalpha())
    if not letters:
        prefix = "CUS"
    else:
        prefix = letters[:3]
    prefix = prefix.upper() if prefix.isascii() else prefix
    if len(prefix) < 3:
        prefix = (prefix + "XXX")[:3]
    return prefix


def phone_suffix(phone: str | None) -> str | None:
    """Last 2 digits of the phone, or None if not enough digits."""
    if not phone:
        return None
    digits = _PHONE_DIGITS.sub("", str(phone))
    if len(digits) < 2:
        return None
    return digits[-2:]


def is_provisional_code(code: str, name: str) -> bool:
    """True when code looks like a seeded placeholder for this name prefix."""
    prefix = name_prefix(name)
    return bool(re.fullmatch(rf"{re.escape(prefix)}\d{{2}}", (code or "").upper() if prefix.isascii() else (code or "")))


async def _code_taken(
    db: AsyncSession,
    shop_id: uuid.UUID,
    code: str,
    *,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    stmt = select(Customer.id).where(
        Customer.shop_id == shop_id,
        Customer.customer_code == code,
    )
    if exclude_id is not None:
        stmt = stmt.where(Customer.id != exclude_id)
    result = await db.execute(stmt.limit(1))
    return result.scalar_one_or_none() is not None


async def _allocate_unique(
    db: AsyncSession,
    shop_id: uuid.UUID,
    base: str,
    *,
    exclude_id: uuid.UUID | None = None,
) -> str:
    base = (base or "CUS00")[:18]
    if not await _code_taken(db, shop_id, base, exclude_id=exclude_id):
        return base
    for i in range(1, 1000):
        candidate = f"{base}{i}"[:20]
        if not await _code_taken(db, shop_id, candidate, exclude_id=exclude_id):
            return candidate
    # Extremely unlikely fallback
    return f"{base}{uuid.uuid4().hex[:4]}"[:20]


async def generate_customer_code(
    db: AsyncSession,
    shop_id: uuid.UUID,
    name: str,
    phone: str | None = None,
    *,
    exclude_id: uuid.UUID | None = None,
) -> str:
    """
    Final ID: first 3 letters of name + last 2 phone digits (e.g. RAM99).
    No phone (voice): seeded provisional ID name3 + 00/01/… (e.g. RAM00).
    """
    prefix = name_prefix(name)
    suffix = phone_suffix(phone)
    if suffix:
        return await _allocate_unique(db, shop_id, f"{prefix}{suffix}", exclude_id=exclude_id)

    # Seeded provisional codes for voice / phone-less creates
    for i in range(100):
        candidate = f"{prefix}{i:02d}"
        if not await _code_taken(db, shop_id, candidate, exclude_id=exclude_id):
            return candidate
    return await _allocate_unique(db, shop_id, f"{prefix}XX", exclude_id=exclude_id)


async def create_customer(
    db: AsyncSession,
    shop_id: uuid.UUID,
    name: str,
    phone: str | None = None,
) -> Customer:
    cleaned_name = (name or "").strip() or "Customer"
    cleaned_phone = (phone or "").strip() or None
    normalized = " ".join(cleaned_name.lower().split())
    code = await generate_customer_code(db, shop_id, cleaned_name, cleaned_phone)
    customer = Customer(
        shop_id=shop_id,
        name=cleaned_name,
        phone=cleaned_phone,
        normalized_name=normalized,
        customer_code=code,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


async def refresh_customer_code(db: AsyncSession, customer: Customer) -> Customer:
    """Recompute customer_code from current name + phone (used after phone is filled in)."""
    new_code = await generate_customer_code(
        db,
        customer.shop_id,
        customer.name,
        customer.phone,
        exclude_id=customer.id,
    )
    if new_code != customer.customer_code:
        customer.customer_code = new_code
    return customer


async def find_customer_by_code(db: AsyncSession, shop_id: uuid.UUID, code: str) -> Customer | None:
    raw = (code or "").strip()
    if not raw:
        return None
    candidates = [raw]
    if raw.isascii():
        candidates.append(raw.upper())
    result = await db.execute(
        select(Customer).where(
            Customer.shop_id == shop_id,
            Customer.customer_code.in_(list(dict.fromkeys(candidates))),
        )
    )
    return result.scalars().first()


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
