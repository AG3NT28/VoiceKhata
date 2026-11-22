"""Load Voice Khata edge-case / training dataset for prompts + evaluation."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "voice_khata_edge_cases_dataset.json"

# Map dataset intent labels → runtime ExtractedIntent intents.
INTENT_MAP = {
    "ADD_CUSTOMER": "ADD_CUSTOMER",
    "ADD_CREDIT": "ADD_CREDIT",
    "RECORD_PAYMENT": "RECORD_PAYMENT",
    "CHECK_BALANCE": "CHECK_BALANCE",
    "GET_DAILY_SUMMARY": "DAILY_SUMMARY",
    "GET_DAILY_CREDIT_TOTAL": "DAILY_SUMMARY",
    "CORRECT_TRANSACTION": "CORRECT_LAST",
    "CORRECT_PENDING_TRANSACTION": "CORRECT_LAST",
    "CANCEL_PENDING_TRANSACTION": "CLARIFY",
    "FUTURE_PAYMENT_PROMISE": "CLARIFY",
    "REFUND_OR_ADJUSTMENT": "CLARIFY",
    "UNKNOWN_OR_CLARIFY": "CLARIFY",
    "UNKNOWN_TRANSACTION_DIRECTION": "CLARIFY",
    "AMBIGUOUS_PAYMENT_ALLOCATION": "CLARIFY",
    "AMBIGUOUS_FINANCIAL_DIRECTION": "CLARIFY",
    "NEGATED_PAYMENT": "CLARIFY",
    "BATCH_ADD_CREDIT": "CLARIFY",
    "DISPUTE_OR_REVIEW_BALANCE": "CHECK_BALANCE",
    "PAYMENT_MISSING_CUSTOMER": "CLARIFY",
    "RECORD_PAYMENT_OR_CLARIFY": "RECORD_PAYMENT",
}

# Decisions that must NOT commit money.
NO_COMMIT_DECISIONS = {
    "ASK_CLARIFICATION",
    "CANCEL_NO_COMMIT",
    "REJECT_INVALID_AMOUNT",
    "DO_NOT_RECORD_PAYMENT",
    "ASK_CUSTOMER",
    "USE_CONTEXT_ONLY_IF_UNAMBIGUOUS_OTHERWISE_ASK",
}


@lru_cache(maxsize=1)
def load_dataset() -> dict:
    if not DATA_PATH.exists():
        return {}
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def training_examples() -> list[dict]:
    return list(load_dataset().get("training_examples") or [])


def core_invariants() -> list[dict]:
    return list(load_dataset().get("core_invariants") or [])


def map_intent(label: str) -> str:
    return INTENT_MAP.get(label, "CLARIFY")


def expected_amount_paise(entities: dict | None) -> int | None:
    if not entities:
        return None
    if entities.get("new_amount_paise") is not None:
        return int(entities["new_amount_paise"])
    if entities.get("amount_paise") is not None:
        return int(entities["amount_paise"])
    return None


def example_to_few_shot(ex: dict) -> tuple[str, dict]:
    """Convert a labelled training row into an LLM few-shot pair."""
    intent = map_intent(ex.get("intent") or "UNKNOWN_OR_CLARIFY")
    entities = dict(ex.get("entities") or {})
    decision = ex.get("decision") or ""
    clarify = decision in NO_COMMIT_DECISIONS or intent == "CLARIFY"
    if clarify and intent not in {"CHECK_BALANCE", "DAILY_SUMMARY", "CORRECT_LAST"}:
        intent = "CLARIFY"

    out_entities: dict = {}
    if entities.get("customer_name"):
        out_entities["customer_name"] = entities["customer_name"]
        out_entities["name"] = entities["customer_name"]
    if entities.get("amount_paise") is not None:
        out_entities["amount_paise"] = entities["amount_paise"]
    if entities.get("new_amount_paise") is not None:
        out_entities["amount_paise"] = entities["new_amount_paise"]
        out_entities["new_value"] = entities["new_amount_paise"]
        out_entities["field"] = "amount"
    if entities.get("date_expression"):
        out_entities["date_expr"] = str(entities["date_expression"]).lower()
    if entities.get("negation"):
        out_entities["negation"] = True

    question = ex.get("expected_clarification")
    payload = {
        "intent": intent,
        "confidence": 0.55 if clarify and intent == "CLARIFY" else 0.95,
        "entities": out_entities,
        "clarification_needed": bool(clarify and intent == "CLARIFY"),
        "clarification_question": question if clarify else None,
        "clarification_options": [],
    }
    return ex["transcript"], payload


def few_shot_from_dataset(limit: int = 20) -> list[tuple[str, dict]]:
    shots: list[tuple[str, dict]] = []
    for ex in training_examples():
        if ex.get("split") not in {None, "train", "seed", "all"}:
            # still include all labelled rows — dataset marks them train
            pass
        shots.append(example_to_few_shot(ex))
        if len(shots) >= limit:
            break
    return shots
