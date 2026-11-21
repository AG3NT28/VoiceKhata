"""Reset shared demo-shop operational data for a fresh email login."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    AuditLog,
    Customer,
    InventoryItem,
    Item,
    StockLog,
    Transaction,
    WholesaleQuote,
)
from app.marketplace.models import MarketplaceListing, RedirectEvent, SearchHistory, StarredListing


async def reset_shop_data(db: AsyncSession, shop_id: UUID) -> None:
    """Wipe ledger + stock for a shop so a new email starts clean."""
    # Marketplace shop-scoped watches / imports / history
    await db.execute(delete(StarredListing).where(StarredListing.shop_id == shop_id))
    await db.execute(delete(RedirectEvent).where(RedirectEvent.shop_id == shop_id))
    await db.execute(delete(SearchHistory).where(SearchHistory.shop_id == shop_id))
    await db.execute(delete(MarketplaceListing).where(MarketplaceListing.shop_id == shop_id))

    # Quotes → inventory items
    inv_ids = (
        await db.execute(select(InventoryItem.id).where(InventoryItem.shop_id == shop_id))
    ).scalars().all()
    if inv_ids:
        await db.execute(delete(WholesaleQuote).where(WholesaleQuote.item_id.in_(inv_ids)))
    await db.execute(delete(InventoryItem).where(InventoryItem.shop_id == shop_id))

    # Stock logs → items
    await db.execute(delete(StockLog).where(StockLog.shop_id == shop_id))
    await db.execute(delete(Item).where(Item.shop_id == shop_id))

    # Transactions before customers (FK)
    await db.execute(delete(Transaction).where(Transaction.shop_id == shop_id))
    await db.execute(delete(Customer).where(Customer.shop_id == shop_id))
    await db.execute(delete(AuditLog).where(AuditLog.shop_id == shop_id))
    await db.commit()
