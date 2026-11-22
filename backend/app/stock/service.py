"""CRUD + stock mutations with append-only StockLog audit trail."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Item, ItemStatus, StockLog, StockLogType


def item_to_dict(item: Item) -> dict:
    return {
        "id": item.id,
        "shop_id": item.shop_id,
        "name": item.name,
        "category": item.category,
        "quantity": item.quantity,
        "unit_price_paise": item.unit_price_paise,
        "unit_price_rupees": item.unit_price_paise / 100.0,
        "minimum_quantity": item.minimum_quantity,
        "supplier": item.supplier,
        "barcode": item.barcode,
        "notes": item.notes,
        "status": item.status,
        "low_stock": item.quantity <= item.minimum_quantity,
        "last_restocked": item.last_restocked,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


async def create_item(
    db: AsyncSession,
    shop_id: UUID,
    *,
    name: str,
    category: str | None = None,
    quantity: int = 0,
    unit_price_paise: int = 0,
    minimum_quantity: int = 5,
    supplier: str | None = None,
    barcode: str | None = None,
    notes: str | None = None,
) -> Item:
    existing = await db.execute(
        select(Item).where(
            Item.shop_id == shop_id,
            Item.name == name.strip(),
            Item.status == ItemStatus.active.value,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Item with this name already exists")

    item = Item(
        shop_id=shop_id,
        name=name.strip(),
        category=(category or "").strip() or None,
        quantity=max(0, int(quantity)),
        unit_price_paise=max(0, int(unit_price_paise)),
        minimum_quantity=max(0, int(minimum_quantity)),
        supplier=(supplier or "").strip() or None,
        barcode=(barcode or "").strip() or None,
        notes=(notes or "").strip() or None,
        status=ItemStatus.active.value,
        last_restocked=datetime.utcnow() if quantity > 0 else None,
    )
    db.add(item)
    await db.flush()

    if item.quantity > 0:
        db.add(
            StockLog(
                shop_id=shop_id,
                item_id=item.id,
                type=StockLogType.IN,
                quantity=item.quantity,
                reason="initial stock",
            )
        )

    await db.commit()
    await db.refresh(item)
    return item


async def list_items(
    db: AsyncSession,
    shop_id: UUID,
    *,
    category: str | None = None,
    search: str | None = None,
) -> list[Item]:
    stmt = select(Item).where(
        Item.shop_id == shop_id,
        Item.status == ItemStatus.active.value,
    )
    if category:
        stmt = stmt.where(Item.category == category.strip())
    if search:
        stmt = stmt.where(Item.name.ilike(f"%{search.strip()}%"))
    result = await db.execute(stmt.order_by(Item.name))
    return list(result.scalars().all())


async def get_item(db: AsyncSession, shop_id: UUID, item_id: UUID) -> Item:
    item = await db.get(Item, item_id)
    if not item or item.shop_id != shop_id or item.status != ItemStatus.active.value:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


async def stock_summary(db: AsyncSession, shop_id: UUID) -> dict:
    items = await list_items(db, shop_id)
    by_category: dict[str, dict] = {}
    for item in items:
        key = item.category or "uncategorized"
        bucket = by_category.setdefault(key, {"count": 0, "quantity": 0})
        bucket["count"] += 1
        bucket["quantity"] += item.quantity
    return {
        "total_items": len(items),
        "total_quantity": sum(i.quantity for i in items),
        "low_stock_count": sum(1 for i in items if i.quantity <= i.minimum_quantity),
        "by_category": by_category,
    }


async def get_item_log(db: AsyncSession, shop_id: UUID, item_id: UUID) -> list[StockLog]:
    await get_item(db, shop_id, item_id)
    result = await db.execute(
        select(StockLog)
        .where(StockLog.shop_id == shop_id, StockLog.item_id == item_id)
        .order_by(StockLog.created_at.desc())
    )
    return list(result.scalars().all())


async def add_stock(
    db: AsyncSession,
    shop_id: UUID,
    item_id: UUID,
    quantity: int,
    reason: str | None = None,
) -> Item:
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be positive")
    item = await get_item(db, shop_id, item_id)
    item.quantity += quantity
    item.last_restocked = datetime.utcnow()
    db.add(
        StockLog(
            shop_id=shop_id,
            item_id=item.id,
            type=StockLogType.IN,
            quantity=quantity,
            reason=reason or "restock",
        )
    )
    await db.commit()
    await db.refresh(item)
    return item


async def remove_stock(
    db: AsyncSession,
    shop_id: UUID,
    item_id: UUID,
    quantity: int,
    reason: str | None = None,
) -> Item:
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be positive")
    item = await get_item(db, shop_id, item_id)
    if item.quantity < quantity:
        raise HTTPException(status_code=400, detail="not enough stock")
    item.quantity -= quantity
    db.add(
        StockLog(
            shop_id=shop_id,
            item_id=item.id,
            type=StockLogType.OUT,
            quantity=-quantity,
            reason=reason or "sold",
        )
    )
    await db.commit()
    await db.refresh(item)
    return item


async def adjust_stock(
    db: AsyncSession,
    shop_id: UUID,
    item_id: UUID,
    delta: int,
    reason: str | None = None,
) -> Item:
    if delta == 0:
        raise HTTPException(status_code=400, detail="delta must be non-zero")
    item = await get_item(db, shop_id, item_id)
    item.quantity += delta  # may go below zero by design
    if delta > 0:
        item.last_restocked = datetime.utcnow()
    db.add(
        StockLog(
            shop_id=shop_id,
            item_id=item.id,
            type=StockLogType.ADJUST,
            quantity=delta,
            reason=reason or "adjust",
        )
    )
    await db.commit()
    await db.refresh(item)
    return item


PROVISION_STOCK_CATALOG = [
    # name, category, qty, unit_price_paise, minimum, supplier
    ("Fortune Sunflower Oil 1L", "edible_oils", 36, 15800, 12, "Oil Traders"),
    ("Fortune Sunflower Oil 5L", "edible_oils", 12, 72000, 4, "Oil Traders"),
    ("Saffola Gold Oil 1L", "edible_oils", 18, 21000, 8, "Oil Traders"),
    ("Aashirvaad Atta 5kg", "wheat_flour", 40, 28000, 10, "Grain Depot"),
    ("Aashirvaad Atta 10kg", "wheat_flour", 16, 54000, 5, "Grain Depot"),
    ("India Gate Basmati Rice 5kg", "rice", 20, 65000, 6, "Grain Depot"),
    ("Sona Masoori Rice 25kg", "rice", 8, 155000, 2, "Rice Mill"),
    ("Madhur Sugar 1kg", "sugar", 60, 4800, 20, "Wholesale Hub"),
    ("Tata Salt 1kg", "salt", 80, 3000, 24, "Wholesale Hub"),
    ("Toor Dal 1kg", "pulses", 45, 15500, 15, "Dal Mandi"),
    ("Moong Dal 1kg", "pulses", 30, 13500, 12, "Dal Mandi"),
    ("Chana Dal 1kg", "pulses", 28, 10500, 12, "Dal Mandi"),
    ("Everest Turmeric 200g", "spices", 48, 5600, 20, "Masala Mart"),
    ("MDH Garam Masala 100g", "spices", 36, 5100, 18, "Masala Mart"),
    ("Parle-G 800g", "biscuits", 40, 6000, 16, "FMCG Depot"),
    ("Tata Tea Gold 500g", "beverages", 24, 30000, 10, "FMCG Depot"),
    ("Amul Ghee 1L", "dairy", 10, 61000, 4, "Dairy Hub"),
    ("Amul Butter 500g", "dairy", 18, 30000, 8, "Dairy Hub"),
    ("Surf Excel 1kg", "cleaning", 22, 19800, 8, "Home Care Depot"),
    ("Harpic 1L", "cleaning", 16, 15500, 6, "Home Care Depot"),
    ("Lux Soap 3x150g", "personal_care", 30, 10200, 12, "Home Care Depot"),
]


async def seed_stock_if_empty(db: AsyncSession, shop_id: UUID) -> None:
    """Ensure generic provision-store stock rows exist (adds missing names)."""
    existing_names = {
        row[0]
        for row in (
            await db.execute(
                select(Item.name).where(
                    Item.shop_id == shop_id,
                    Item.status == ItemStatus.active.value,
                )
            )
        ).all()
    }
    for name, category, qty, price, minimum, supplier in PROVISION_STOCK_CATALOG:
        if name in existing_names:
            continue
        await create_item(
            db,
            shop_id,
            name=name,
            category=category,
            quantity=qty,
            unit_price_paise=price,
            minimum_quantity=minimum,
            supplier=supplier,
        )
