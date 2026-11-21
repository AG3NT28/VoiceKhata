"""Idempotency helpers."""
import uuid
import hashlib

def make_idempotency_key(shop_id, customer_id, txn_type, amount_paise, txn_date, transcript=None) -> str:
    base = f"{shop_id}|{customer_id}|{txn_type}|{amount_paise}|{txn_date}|{transcript or ''}"
    return hashlib.sha256(base.encode()).hexdigest()[:64]

def new_client_key() -> str:
    return str(uuid.uuid4())
