"""Evaluate fallback parser against Voice Khata edge-case training examples."""
from __future__ import annotations

import pytest

from app.ai.dataset import (
    NO_COMMIT_DECISIONS,
    expected_amount_paise,
    map_intent,
    training_examples,
)
from app.ai.fallback import parse_number, parse_text


def _actual_amount_paise(entities: dict) -> int | None:
    if entities.get("amount_paise") is not None:
        return int(entities["amount_paise"])
    if entities.get("amount_rupees") is not None:
        return int(float(entities["amount_rupees"]) * 100)
    if entities.get("new_value") is not None:
        # new_value stored as paise for corrections
        val = int(entities["new_value"])
        return val if val >= 100 or entities.get("field") == "amount" else val * 100
    return None


def test_number_edge_forms():
    assert parse_number("2.5K credit") == 2500
    assert parse_number("one hundred and fifty rupees") == 150
    assert parse_number("paanch sau") == 500


@pytest.mark.parametrize("ex", training_examples(), ids=lambda e: e["example_id"])
def test_training_example_intent_and_slots(ex):
    predicted = parse_text(ex["transcript"])
    expected_intent = map_intent(ex["intent"])
    decision = ex.get("decision") or ""

    # Intent family must match after dataset→runtime mapping
    if decision in NO_COMMIT_DECISIONS and expected_intent not in {
        "CHECK_BALANCE",
        "DAILY_SUMMARY",
        "CORRECT_LAST",
    }:
        assert predicted.intent == "CLARIFY", (
            f"{ex['example_id']}: expected CLARIFY for decision={decision}, got {predicted.intent}"
        )
    else:
        assert predicted.intent == expected_intent, (
            f"{ex['example_id']}: intent {predicted.intent} != {expected_intent} for '{ex['transcript']}'"
        )

    # Amount slot (when labelled and not a multi-txn batch)
    want_amt = expected_amount_paise(ex.get("entities"))
    if want_amt is not None and "transactions" not in (ex.get("entities") or {}):
        got_amt = _actual_amount_paise(predicted.entities or {})
        if want_amt == 0:
            assert got_amt in {0, None} or predicted.intent == "CLARIFY"
        else:
            assert got_amt == want_amt, (
                f"{ex['example_id']}: amount {got_amt} != {want_amt} for '{ex['transcript']}'"
            )

    # Customer name when labelled as a single customer
    want_name = (ex.get("entities") or {}).get("customer_name")
    if want_name and predicted.intent != "CLARIFY":
        got_name = (predicted.entities or {}).get("customer_name")
        assert got_name == want_name, f"{ex['example_id']}: name {got_name} != {want_name}"

    # No-commit decisions must not look like a confident write
    if decision in {"DO_NOT_RECORD_PAYMENT", "CANCEL_NO_COMMIT", "REJECT_INVALID_AMOUNT"}:
        assert predicted.intent in {"CLARIFY", "CHECK_BALANCE"}
        assert predicted.clarification_needed or predicted.intent == "CHECK_BALANCE"
