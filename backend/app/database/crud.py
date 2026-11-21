from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Shop, Customer, Transaction

async def create_shop(db: AsyncSession, name: str, timezone: str = "Asia/Kolkata") -> Shop:
    shop = Shop(name=name, timezone=timezone)
    db.add(shop)
    await db.commit()
    await db.refresh(shop)
    return shop

async def get_shop(db: AsyncSession, shop_id):
    return await db.get(Shop, shop_id)
