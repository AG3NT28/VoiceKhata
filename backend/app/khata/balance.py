from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.khata.ledger import compute_balance

async def get_balance(db: AsyncSession, customer_id: UUID) -> int:
    return await compute_balance(db, customer_id)
