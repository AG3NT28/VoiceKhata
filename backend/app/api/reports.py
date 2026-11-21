from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.db import get_db
from app.database.models import Transaction, TxnType, TxnStatus
from app.schemas import DailySummaryResponse
from app.security.auth import get_current_shop_id
from uuid import UUID

router = APIRouter(prefix='/reports', tags=['reports'])

@router.get('/daily', response_model=DailySummaryResponse)
async def daily_summary(date: date = Query(None), shop_id: UUID = Depends(get_current_shop_id), db: AsyncSession = Depends(get_db)):
    target = date or __import__('datetime').date.today()
    result = await db.execute(select(Transaction.type, func.sum(Transaction.amount_paise), func.count()).where(Transaction.shop_id == shop_id, Transaction.txn_date == target, Transaction.status == TxnStatus.active).group_by(Transaction.type))
    credit = payment = count = 0
    for t, amt, c in result.all():
        if t == TxnType.credit: credit = amt or 0
        else: payment = amt or 0
        count += c
    cust_result = await db.execute(select(func.count(func.distinct(Transaction.customer_id))).where(Transaction.shop_id == shop_id, Transaction.txn_date == target, Transaction.status == TxnStatus.active))
    customers_served = cust_result.scalar() or 0
    return DailySummaryResponse(date=target, total_credit_paise=credit, total_payment_paise=payment, net_paise=credit-payment, transaction_count=count, customers_served=customers_served)
