import uuid
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Transaction, TxnType, TxnStatus, Customer
from app.utils.idempotency import make_idempotency_key

async def compute_balance(db: AsyncSession, customer_id: uuid.UUID) -> int:
    """Return outstanding balance in paise."""
    from sqlalchemy import func
    result = await db.execute(
        select(Transaction.type, func.sum(Transaction.amount_paise))
        .where(Transaction.customer_id == customer_id, Transaction.status == TxnStatus.active)
        .group_by(Transaction.type)
    )
    credit = payment = 0
    for t, amt in result.all():
        if t == TxnType.credit:
            credit = amt or 0
        else:
            payment = amt or 0
    return credit - payment

async def _get_or_create_by_key(db: AsyncSession, idempotency_key: str):
    result = await db.execute(select(Transaction).where(Transaction.idempotency_key == idempotency_key))
    return result.scalar_one_or_none()

async def add_credit(
    db: AsyncSession,
    shop_id: uuid.UUID,
    customer_id: uuid.UUID,
    amount_paise: int,
    txn_date: date,
    idempotency_key: str | None = None,
    transcript: str | None = None,
    confidence: float | None = None,
    created_by: uuid.UUID | None = None,
) -> Transaction:
    if not idempotency_key:
        idempotency_key = make_idempotency_key(shop_id, customer_id, "credit", amount_paise, txn_date, transcript)
    existing = await _get_or_create_by_key(db, idempotency_key)
    if existing:
        return existing
    txn = Transaction(
        shop_id=shop_id,
        customer_id=customer_id,
        type=TxnType.credit,
        amount_paise=amount_paise,
        txn_date=txn_date,
        idempotency_key=idempotency_key,
        raw_transcript=transcript,
        llm_confidence=confidence,
        created_by=created_by,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return txn

async def record_payment(
    db: AsyncSession,
    shop_id: uuid.UUID,
    customer_id: uuid.UUID,
    amount_paise: int,
    txn_date: date,
    idempotency_key: str | None = None,
    transcript: str | None = None,
    confidence: float | None = None,
    created_by: uuid.UUID | None = None,
) -> Transaction:
    if not idempotency_key:
        idempotency_key = make_idempotency_key(shop_id, customer_id, "payment", amount_paise, txn_date, transcript)
    existing = await _get_or_create_by_key(db, idempotency_key)
    if existing:
        return existing
    txn = Transaction(
        shop_id=shop_id,
        customer_id=customer_id,
        type=TxnType.payment,
        amount_paise=amount_paise,
        txn_date=txn_date,
        idempotency_key=idempotency_key,
        raw_transcript=transcript,
        llm_confidence=confidence,
        created_by=created_by,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return txn

async def list_transactions(db: AsyncSession, customer_id: uuid.UUID, limit: int = 50):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.customer_id == customer_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
