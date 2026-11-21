import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Transaction, TxnStatus, TxnType
from app.khata.ledger import add_credit, record_payment

async def correct_transaction(
    db: AsyncSession,
    original: Transaction,
    new_amount_paise: int | None = None,
    new_type: TxnType | None = None,
    actor: str = "shopkeeper",
) -> Transaction:
    """Reverse original and create corrected entry (supersedes original)."""
    # Mark original as reversed
    original.status = TxnStatus.reversed
    await db.commit()

    # Create corrected transaction
    corrected_type = new_type or original.type
    corrected_amount = new_amount_paise if new_amount_paise is not None else original.amount_paise

    if corrected_type == TxnType.credit:
        new_txn = await add_credit(
            db=db,
            shop_id=original.shop_id,
            customer_id=original.customer_id,
            amount_paise=corrected_amount,
            txn_date=original.txn_date,
            transcript=f"correction of {original.id}",
        )
    else:
        new_txn = await record_payment(
            db=db,
            shop_id=original.shop_id,
            customer_id=original.customer_id,
            amount_paise=corrected_amount,
            txn_date=original.txn_date,
            transcript=f"correction of {original.id}",
        )

    new_txn.supersedes = original.id
    original.reversed_by = new_txn.id
    await db.commit()
    await db.refresh(new_txn)
    await db.refresh(original)
    return new_txn

async def void_transaction(db: AsyncSession, original: Transaction, actor: str = 'shopkeeper') -> Transaction:
    original.status = TxnStatus.voided
    await db.commit()
    await db.refresh(original)
    return original
