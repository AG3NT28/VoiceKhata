"""Voice command orchestrator: transcript -> intent -> ledger action -> reply."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.extraction import ExtractedIntent
from app.ai.fallback import parse_text
from app.ai.llm import extract_intent
from app.config import settings
from app.database.models import Customer, Transaction, TxnStatus, TxnType
from app.khata.corrections import correct_transaction
from app.khata.customers import create_customer, find_customers_by_name
from app.khata.ledger import add_credit, compute_balance, record_payment
from app.utils.dates import today_in_tz
from app.utils.paise import paise_to_rupees, rupees_to_paise

DEFAULT_CLARIFY = "Samajh nahi aaya. Jaise boliye: 'Ramesh ka 340 rupaye udhaar'."


def _money(paise: int) -> str:
    rupees = paise / 100
    if rupees == int(rupees):
        return f"₹{int(rupees)}"
    return f"₹{rupees:.2f}"


async def understand(transcript: str) -> tuple[ExtractedIntent, str]:
    """Run the LLM when configured, otherwise the deterministic parser."""
    if settings.LLM_API_KEY:
        try:
            return await extract_intent(transcript), "llm"
        except Exception:
            return parse_text(transcript), "fallback (LLM unavailable)"
    return parse_text(transcript), "fallback (no LLM key)"


async def _customer_payload(db: AsyncSession, customer: Customer) -> dict:
    balance = await compute_balance(db, customer.id)
    return {
        "id": str(customer.id),
        "name": customer.name,
        "code": customer.customer_code,
        "balance_paise": balance,
        "balance_rupees": paise_to_rupees(balance),
    }


async def _resolve(db: AsyncSession, shop_id: uuid.UUID, name: str | None):
    if not name:
        return None, []
    matches = await find_customers_by_name(db, shop_id, name)
    if len(matches) == 1:
        return matches[0], []
    return None, matches


async def demo_state(db: AsyncSession, shop_id: uuid.UUID) -> dict:
    """Snapshot used by the prototype UI."""
    result = await db.execute(select(Customer).where(Customer.shop_id == shop_id).order_by(Customer.name))
    customers = []
    for customer in result.scalars().all():
        customers.append(await _customer_payload(db, customer))

    today = today_in_tz()
    summary = await _summary(db, shop_id, today)
    recent = await db.execute(
        select(Transaction, Customer)
        .join(Customer, Transaction.customer_id == Customer.id)
        .where(Transaction.shop_id == shop_id)
        .order_by(Transaction.created_at.desc())
        .limit(8)
    )
    recent_items = [
        {
            "id": str(txn.id),
            "customer": customer.name,
            "type": txn.type.value,
            "amount_rupees": paise_to_rupees(txn.amount_paise),
            "status": txn.status.value,
            "created_at": txn.created_at.isoformat(),
        }
        for txn, customer in recent.all()
    ]
    return {"customers": customers, "summary": summary, "recent": recent_items}


async def _summary(db: AsyncSession, shop_id: uuid.UUID, target: date) -> dict:
    result = await db.execute(
        select(Transaction.type, func.sum(Transaction.amount_paise), func.count())
        .where(
            Transaction.shop_id == shop_id,
            Transaction.txn_date == target,
            Transaction.status == TxnStatus.active,
        )
        .group_by(Transaction.type)
    )
    credit = payment = count = 0
    for txn_type, amount, rows in result.all():
        if txn_type == TxnType.credit:
            credit = amount or 0
        else:
            payment = amount or 0
        count += rows
    return {
        "date": target.isoformat(),
        "total_credit_paise": credit,
        "total_payment_paise": payment,
        "net_paise": credit - payment,
        "transaction_count": count,
    }


async def handle_transcript(db: AsyncSession, shop_id: uuid.UUID, transcript: str) -> dict:
    """Execute one voice command end to end."""
    transcript = (transcript or "").strip()
    if not transcript:
        return {
            "transcript": "",
            "intent": "CLARIFY",
            "confidence": 0.0,
            "entities": {},
            "engine": "none",
            "reply_text": "Kuch sunai nahi diya. Dobara boliye.",
            "needs_clarification": True,
            "options": [],
        }

    intent_obj, engine = await understand(transcript)
    intent = intent_obj.intent
    entities = intent_obj.entities or {}
    name = (entities.get("customer_name") or entities.get("name") or "").strip() or None
    amount = entities.get("amount_rupees", entities.get("amount"))

    result = {
        "transcript": transcript,
        "intent": intent,
        "confidence": intent_obj.confidence,
        "entities": entities,
        "engine": engine,
        "needs_clarification": False,
        "options": [],
        "customer": None,
        "transaction": None,
        "summary": None,
    }

    # ---- ADD_CUSTOMER ------------------------------------------------------
    if intent == "ADD_CUSTOMER":
        if not name:
            result.update(
                needs_clarification=True,
                reply_text="Customer ka naam kya hai?",
            )
            return result
        existing, matches = await _resolve(db, shop_id, name)
        if existing:
            result["customer"] = await _customer_payload(db, existing)
            result["reply_text"] = f"{existing.name} pehle se hai, code {existing.customer_code}."
            return result
        customer = await create_customer(db, shop_id, name)
        result["customer"] = await _customer_payload(db, customer)
        result["reply_text"] = f"Naya customer {customer.name} ban gaya, code {customer.customer_code}."
        return result

    # ---- ADD_CREDIT / RECORD_PAYMENT --------------------------------------
    if intent in ("ADD_CREDIT", "RECORD_PAYMENT"):
        if amount is None:
            result.update(
                needs_clarification=True,
                reply_text="Kitne rupaye? Amount dobara boliye.",
            )
            return result
        if not name:
            result.update(
                needs_clarification=True,
                reply_text="Kiska khata? Customer ka naam boliye.",
            )
            return result

        customer, matches = await _resolve(db, shop_id, name)
        if matches:
            result.update(
                needs_clarification=True,
                reply_text=f"Do customer mile - {name}. Kaunsa? " + ", ".join(c.name for c in matches),
                options=[c.name for c in matches],
            )
            return result
        if customer is None:
            customer = await create_customer(db, shop_id, name)
            result["entities"]["customer_created"] = True

        amount_paise = rupees_to_paise(float(amount))
        if amount_paise <= 0:
            result.update(needs_clarification=True, reply_text="Amount zero se zyada hona chahiye.")
            return result

        txn_date = today_in_tz()
        if intent == "ADD_CREDIT":
            txn = await add_credit(
                db, shop_id, customer.id, amount_paise, txn_date,
                transcript=transcript, confidence=intent_obj.confidence,
            )
        else:
            txn = await record_payment(
                db, shop_id, customer.id, amount_paise, txn_date,
                transcript=transcript, confidence=intent_obj.confidence,
            )

        payload = await _customer_payload(db, customer)
        result["customer"] = payload
        result["transaction"] = {
            "id": str(txn.id),
            "type": txn.type.value,
            "amount_paise": txn.amount_paise,
            "amount_rupees": paise_to_rupees(txn.amount_paise),
            "status": txn.status.value,
        }
        if intent == "ADD_CREDIT":
            result["reply_text"] = (
                f"{customer.name} ka {_money(amount_paise)} udhaar likh diya. "
                f"Ab total baaki {_money(payload['balance_paise'])}."
            )
        else:
            result["reply_text"] = (
                f"{customer.name} se {_money(amount_paise)} jama ho gaya. "
                f"Ab baaki {_money(payload['balance_paise'])}."
            )
        return result

    # ---- CHECK_BALANCE -----------------------------------------------------
    if intent == "CHECK_BALANCE":
        customer, matches = await _resolve(db, shop_id, name)
        if matches:
            result.update(
                needs_clarification=True,
                reply_text=f"Do customer mile - {name}. Kaunsa? " + ", ".join(c.name for c in matches),
                options=[c.name for c in matches],
            )
            return result
        if customer:
            payload = await _customer_payload(db, customer)
            result["customer"] = payload
            result["reply_text"] = (
                f"{customer.name} ({customer.customer_code}) ka baaki {_money(payload['balance_paise'])} hai."
            )
            return result
        snapshot = await demo_state(db, shop_id)
        top = sorted(snapshot["customers"], key=lambda c: c["balance_paise"], reverse=True)[:3]
        listing = ", ".join(f"{c['name']} {_money(c['balance_paise'])}" for c in top) or "koi khata nahi"
        result["reply_text"] = f"Kiska? Top baaki: {listing}."
        result["needs_clarification"] = True
        return result

    # ---- DAILY_SUMMARY -----------------------------------------------------
    if intent == "DAILY_SUMMARY":
        summary = await _summary(db, shop_id, today_in_tz())
        result["summary"] = summary
        result["reply_text"] = (
            f"Aaj {_money(summary['total_credit_paise'])} udhaar diya, "
            f"{_money(summary['total_payment_paise'])} jama hua, "
            f"{summary['transaction_count']} entry hui."
        )
        return result

    # ---- CORRECT_LAST ------------------------------------------------------
    if intent == "CORRECT_LAST":
        customer, _ = await _resolve(db, shop_id, name)
        stmt = select(Transaction).where(
            Transaction.shop_id == shop_id, Transaction.status == TxnStatus.active
        )
        if customer:
            stmt = stmt.where(Transaction.customer_id == customer.id)
        stmt = stmt.order_by(Transaction.created_at.desc()).limit(1)
        last = (await db.execute(stmt)).scalars().first()
        if not last:
            result["reply_text"] = "Koi pichhli entry nahi mili jo correct kar sakun."
            return result

        owner = await db.get(Customer, last.customer_id)
        new_amount = rupees_to_paise(float(amount)) if amount is not None else last.amount_paise
        corrected = await correct_transaction(db, last, new_amount_paise=new_amount)
        payload = await _customer_payload(db, owner)
        result["customer"] = payload
        result["transaction"] = {
            "id": str(corrected.id),
            "type": corrected.type.value,
            "amount_paise": corrected.amount_paise,
            "amount_rupees": paise_to_rupees(corrected.amount_paise),
            "status": corrected.status.value,
            "supersedes": str(last.id),
        }
        result["reply_text"] = (
            f"Theek kar diya. Pehle {_money(last.amount_paise)}, ab {_money(corrected.amount_paise)}. "
            f"{owner.name} ka baaki {_money(payload['balance_paise'])}."
        )
        return result

    # ---- CLARIFY -----------------------------------------------------------
    result["needs_clarification"] = True
    result["reply_text"] = intent_obj.clarification_question or DEFAULT_CLARIFY
    return result
