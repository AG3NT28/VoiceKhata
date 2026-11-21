from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database.db import get_db
from app.database.models import Customer, Shop
from app.khata.customers import (
    create_customer,
    find_customer_by_code,
    list_customers,
    refresh_customer_code,
)
from app.schemas import CustomerCreate, CustomerUpdate, CustomerResponse, CustomerListResponse, BalanceResponse
from app.security.auth import get_current_shop_id

router = APIRouter(prefix="/customers", tags=["customers"])

@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer_endpoint(
    payload: CustomerCreate,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    # Check duplicate normalized name
    from app.khata.customers import find_customers_by_name
    existing = await find_customers_by_name(db, shop_id, payload.name)
    if existing:
        raise HTTPException(status_code=409, detail="Customer with this name already exists")
    customer = await create_customer(db, shop_id, payload.name, payload.phone)
    return customer

@router.get("", response_model=CustomerListResponse)
async def list_customers_endpoint(
    q: str = Query("", description="Search by name"),
    status: str = Query("active", description="active | archived | all"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Customer).where(Customer.shop_id == shop_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            Customer.name.ilike(like)
            | Customer.phone.ilike(like)
            | Customer.customer_code.ilike(like)
        )
    if status != "all":
        stmt = stmt.where(Customer.status == status)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(Customer.name).offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return CustomerListResponse(items=items, total=total, limit=limit, offset=offset)

@router.get("/by-code/{code}", response_model=CustomerResponse)
async def get_customer_by_code(
    code: str,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    cust = await find_customer_by_code(db, shop_id, code)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    return cust

@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    cust = await db.get(Customer, customer_id)
    if not cust or cust.shop_id != shop_id:
        raise HTTPException(status_code=404, detail="Customer not found")
    return cust

@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    cust = await db.get(Customer, customer_id)
    if not cust or cust.shop_id != shop_id:
        raise HTTPException(status_code=404, detail="Customer not found")
    phone_updated = False
    if payload.name is not None:
        cust.name = payload.name.strip()
        cust.normalized_name = " ".join(payload.name.strip().lower().split())
    if payload.phone is not None:
        new_phone = payload.phone.strip() if payload.phone else None
        phone_updated = (new_phone or "") != (cust.phone or "")
        cust.phone = new_phone
    if payload.status is not None:
        cust.status = payload.status
    # When phone is filled/changed, upgrade provisional seeded ID → name3+phone2
    if phone_updated and cust.phone:
        await refresh_customer_code(db, cust)
    elif payload.name is not None and cust.phone:
        await refresh_customer_code(db, cust)
    await db.commit()
    await db.refresh(cust)
    return cust

@router.get('/{customer_id}/balance', response_model=BalanceResponse)
async def get_balance(customer_id: UUID, shop_id: UUID = Depends(get_current_shop_id), db: AsyncSession = Depends(get_db)):
    from app.khata.ledger import compute_balance
    cust = await db.get(Customer, customer_id)
    if not cust or cust.shop_id != shop_id:
        raise HTTPException(status_code=404, detail='Customer not found')
    bal = await compute_balance(db, customer_id)
    return BalanceResponse(customer_id=customer_id, customer_code=cust.customer_code, customer_name=cust.name, balance_paise=bal, balance_rupees=bal/100.0)
