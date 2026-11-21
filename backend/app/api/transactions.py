from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.db import get_db
from app.database.models import Transaction, Customer, TxnStatus
from app.khata.ledger import add_credit, record_payment, compute_balance
from app.khata.customers import find_customer_by_code
from app.schemas import TransactionCreate, TransactionResponse, BalanceResponse
from app.security.auth import get_current_shop_id
from app.utils.paise import rupees_to_paise

router = APIRouter(prefix='/transactions', tags=['transactions'])
def _to_response(t):
    return TransactionResponse(
        id=t.id, shop_id=t.shop_id, customer_id=t.customer_id, type=t.type.value,
        amount_paise=t.amount_paise, amount_rupees=t.amount_paise / 100.0,
        txn_date=t.txn_date, status=t.status.value, idempotency_key=t.idempotency_key,
        raw_transcript=t.raw_transcript, llm_confidence=t.llm_confidence, created_at=t.created_at,
    )
@router.post('', response_model=TransactionResponse, status_code=201)
async def create_transaction(payload: TransactionCreate, shop_id: UUID = Depends(get_current_shop_id), db: AsyncSession = Depends(get_db)):
    customer = None
    if payload.customer_id:
        customer = await db.get(Customer, payload.customer_id)
    elif payload.customer_code:
        customer = await find_customer_by_code(db, shop_id, payload.customer_code)
    if not customer or customer.shop_id != shop_id:
        raise HTTPException(status_code=404, detail='Customer not found')
    if payload.amount_paise is not None:
        amount_paise = payload.amount_paise
    elif payload.amount_rupees is not None:
        amount_paise = rupees_to_paise(payload.amount_rupees)
    else:
        raise HTTPException(status_code=422, detail='amount_rupees or amount_paise required')
    if amount_paise <= 0:
        raise HTTPException(status_code=422, detail='Amount must be positive')
    txn_date = payload.txn_date or date.today()
    if payload.type == 'credit':
        txn = await add_credit(db, shop_id, customer.id, amount_paise, txn_date, idempotency_key=payload.idempotency_key, transcript=payload.transcript, confidence=payload.confidence)
    else:
        txn = await record_payment(db, shop_id, customer.id, amount_paise, txn_date, idempotency_key=payload.idempotency_key, transcript=payload.transcript, confidence=payload.confidence)
    return _to_response(txn)

@router.get('/{transaction_id}', response_model=TransactionResponse)
async def get_transaction(transaction_id: UUID, shop_id: UUID = Depends(get_current_shop_id), db: AsyncSession = Depends(get_db)):
    txn = await db.get(Transaction, transaction_id)
    if not txn or txn.shop_id != shop_id:
        raise HTTPException(status_code=404, detail='Transaction not found')
    return _to_response(txn)

@router.post('/{transaction_id}/reverse', response_model=TransactionResponse)
async def reverse_transaction(transaction_id: UUID, shop_id: UUID = Depends(get_current_shop_id), db: AsyncSession = Depends(get_db)):
    from app.khata.corrections import void_transaction
    txn = await db.get(Transaction, transaction_id)
    if not txn or txn.shop_id != shop_id:
        raise HTTPException(status_code=404, detail='Transaction not found')
    if txn.status != TxnStatus.active:
        raise HTTPException(status_code=400, detail='Only active transactions can be reversed')
    corrected = await void_transaction(db, txn)
    return _to_response(corrected)

@router.get('', response_model=list[TransactionResponse])
async def list_transactions_endpoint(customer_id: UUID = Query(None), limit: int = Query(50, ge=1, le=200), shop_id: UUID = Depends(get_current_shop_id), db: AsyncSession = Depends(get_db)):
    from app.khata.ledger import list_transactions as _lt
    if not customer_id:
        raise HTTPException(status_code=422, detail='customer_id required')
    cust = await db.get(Customer, customer_id)
    if not cust or cust.shop_id != shop_id:
        raise HTTPException(status_code=404, detail='Customer not found')
    txns = await _lt(db, customer_id, limit=limit)
    return [_to_response(t) for t in txns]
