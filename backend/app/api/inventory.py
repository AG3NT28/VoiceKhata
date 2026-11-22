"""Inventory + mock wholesale quotes for provision-store MVP."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_db
from app.database.models import InventoryItem, Shop, WholesaleQuote
from app.schemas import (
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryItemUpdate,
    InventoryListResponse,
    InventoryQuotesResponse,
    WholesaleQuoteResponse,
)
from app.security.auth import get_current_shop_id
from app.utils.paise import rupees_to_paise

router = APIRouter(prefix="/inventory", tags=["inventory"])

SEED_CATALOG = [
    ("Fortune Sunflower Oil 1L", "L", 36, 12, 15800, {"demo_hub": 14500, "cash_carry": 13900, "local": 15200}),
    ("Aashirvaad Atta 5kg", "kg", 40, 10, 28000, {"demo_hub": 26500, "cash_carry": 25500, "local": 27500}),
    ("India Gate Basmati 5kg", "kg", 20, 6, 65000, {"demo_hub": 62000, "cash_carry": 63500, "local": 66000}),
    ("Madhur Sugar 1kg", "kg", 60, 20, 4800, {"demo_hub": 4600, "cash_carry": 4500, "local": 4900}),
    ("Tata Salt 1kg", "kg", 80, 24, 3000, {"demo_hub": 2800, "cash_carry": 2650, "local": 2900}),
    ("Toor Dal 1kg", "kg", 45, 15, 15500, {"demo_hub": 14500, "cash_carry": 14200, "local": 15000}),
    ("Tata Tea Gold 500g", "pcs", 24, 10, 30000, {"demo_hub": 28500, "cash_carry": 29000, "local": 31000}),
    ("Amul Ghee 1L", "L", 10, 4, 61000, {"demo_hub": 58000, "cash_carry": 59500, "local": 62000}),
    ("Surf Excel 1kg", "pcs", 22, 8, 19800, {"demo_hub": 18500, "cash_carry": 18200, "local": 19500}),
    ("Parle-G 800g", "pcs", 40, 16, 6000, {"demo_hub": 5500, "cash_carry": 5400, "local": 5800}),
]


def _item_response(item: InventoryItem) -> InventoryItemResponse:
    return InventoryItemResponse(
        id=item.id,
        shop_id=item.shop_id,
        name=item.name,
        sku=item.sku,
        unit=item.unit,
        quantity=item.quantity,
        reorder_level=item.reorder_level,
        unit_cost_paise=item.unit_cost_paise,
        unit_cost_rupees=item.unit_cost_paise / 100.0,
        low_stock=item.quantity <= item.reorder_level,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _quote_response(quote: WholesaleQuote) -> WholesaleQuoteResponse:
    return WholesaleQuoteResponse(
        id=quote.id,
        item_id=quote.item_id,
        source=quote.source,
        price_paise=quote.price_paise,
        price_rupees=quote.price_paise / 100.0,
        captured_at=quote.captured_at,
    )


async def seed_inventory_if_empty(db: AsyncSession, shop: Shop) -> None:
    """Ensure provision inventory rows exist (adds any missing names)."""
    existing_names = {
        row[0]
        for row in (
            await db.execute(
                select(InventoryItem.name).where(InventoryItem.shop_id == shop.id)
            )
        ).all()
    }
    for name, unit, qty, reorder, cost, quotes in SEED_CATALOG:
        if name in existing_names:
            continue
        item = InventoryItem(
            shop_id=shop.id,
            name=name,
            unit=unit,
            quantity=qty,
            reorder_level=reorder,
            unit_cost_paise=cost,
            sku=name.split()[0][:8].upper(),
        )
        db.add(item)
        await db.flush()
        for source, price in quotes.items():
            db.add(WholesaleQuote(item_id=item.id, source=source, price_paise=price))
    await db.commit()


@router.get("", response_model=InventoryListResponse)
async def list_inventory(
    q: str = Query(""),
    low_stock_only: bool = Query(False),
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InventoryItem).where(InventoryItem.shop_id == shop_id)
    if q:
        stmt = stmt.where(InventoryItem.name.ilike(f"%{q}%"))
    result = await db.execute(stmt.order_by(InventoryItem.name))
    items = list(result.scalars().all())
    low_stock_count = sum(1 for i in items if i.quantity <= i.reorder_level)
    if low_stock_only:
        items = [i for i in items if i.quantity <= i.reorder_level]
    return InventoryListResponse(
        items=[_item_response(i) for i in items],
        total=len(items),
        low_stock_count=low_stock_count,
    )


@router.post("", response_model=InventoryItemResponse, status_code=201)
async def create_item(
    payload: InventoryItemCreate,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(InventoryItem).where(
            InventoryItem.shop_id == shop_id,
            InventoryItem.name == payload.name.strip(),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Item with this name already exists")
    if payload.unit_cost_paise is not None:
        cost = payload.unit_cost_paise
    elif payload.unit_cost_rupees is not None:
        cost = rupees_to_paise(payload.unit_cost_rupees)
    else:
        cost = 0
    item = InventoryItem(
        shop_id=shop_id,
        name=payload.name.strip(),
        sku=payload.sku,
        unit=payload.unit or "pcs",
        quantity=payload.quantity,
        reorder_level=payload.reorder_level,
        unit_cost_paise=cost,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _item_response(item)


@router.get("/low-stock/summary")
async def low_stock_summary(
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(InventoryItem).where(InventoryItem.shop_id == shop_id))
    items = [i for i in result.scalars().all() if i.quantity <= i.reorder_level]
    return {
        "count": len(items),
        "items": [
            {
                "id": str(i.id),
                "name": i.name,
                "quantity": i.quantity,
                "reorder_level": i.reorder_level,
            }
            for i in items
        ],
    }


@router.patch("/{item_id}", response_model=InventoryItemResponse)
async def update_item(
    item_id: UUID,
    payload: InventoryItemUpdate,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(InventoryItem, item_id)
    if not item or item.shop_id != shop_id:
        raise HTTPException(status_code=404, detail="Item not found")
    if payload.name is not None:
        item.name = payload.name.strip()
    if payload.sku is not None:
        item.sku = payload.sku
    if payload.unit is not None:
        item.unit = payload.unit
    if payload.quantity is not None:
        item.quantity = payload.quantity
    if payload.reorder_level is not None:
        item.reorder_level = payload.reorder_level
    if payload.unit_cost_paise is not None:
        item.unit_cost_paise = payload.unit_cost_paise
    elif payload.unit_cost_rupees is not None:
        item.unit_cost_paise = rupees_to_paise(payload.unit_cost_rupees)
    await db.commit()
    await db.refresh(item)
    return _item_response(item)


@router.get("/{item_id}/quotes", response_model=InventoryQuotesResponse)
async def item_quotes(
    item_id: UUID,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(InventoryItem, item_id)
    if not item or item.shop_id != shop_id:
        raise HTTPException(status_code=404, detail="Item not found")
    result = await db.execute(
        select(WholesaleQuote).where(WholesaleQuote.item_id == item_id).order_by(WholesaleQuote.price_paise)
    )
    quotes = list(result.scalars().all())
    best = quotes[0] if quotes else None
    return InventoryQuotesResponse(
        item=_item_response(item),
        quotes=[_quote_response(q) for q in quotes],
        best_source=best.source if best else None,
        best_price_rupees=(best.price_paise / 100.0) if best else None,
    )
