"""Price-comparison JSONL → Gnani keyterms + FIND_WHOLESALE NLU."""
from __future__ import annotations

import pytest

from app.ai.fallback import parse_text
from app.ai.price_dataset import (
    DATA_PATH,
    build_query_from_entities,
    few_shot_from_price_dataset,
    gnani_keyterms,
    gnani_keyterms_json,
    load_price_examples,
    map_price_intent,
    training_summary,
)


def test_dataset_file_present():
    assert DATA_PATH.exists(), f"missing {DATA_PATH}"
    rows = load_price_examples()
    assert len(rows) >= 50


def test_training_summary_and_keyterms():
    summary = training_summary()
    assert summary["examples"] >= 50
    assert summary["keyterms"] >= 20
    assert "FIND_WHOLESALE" in summary["runtime_intents"]
    terms = gnani_keyterms(50)
    assert any("atta" in t.lower() or "आटा" in t for t in terms)
    raw = gnani_keyterms_json(20)
    assert raw.startswith("[") and "udhaar" in raw


def test_gnani_keyterms_never_exceed_api_limit():
    import json

    terms = gnani_keyterms(200)
    assert len(terms) <= 200
    assert all(" " not in t for t in terms), "multi-word keyterms inflate Gnani token count"
    payload = json.loads(gnani_keyterms_json(500))
    assert len(payload) <= 200


def test_few_shots_map_to_find_wholesale():
    shots = few_shot_from_price_dataset(12)
    assert len(shots) >= 5
    for spoken, payload in shots:
        assert spoken
        assert payload["intent"] in {"FIND_WHOLESALE", "CLARIFY"}
        if payload["intent"] == "FIND_WHOLESALE":
            assert payload["entities"].get("query")


def test_build_query_from_entities():
    q = build_query_from_entities(
        {"brand": "Tata", "product": "नमक", "quantity": 1, "unit": "kg"},
        "fallback",
    )
    assert "Tata" in q and "नमक" in q


@pytest.mark.parametrize(
    "utterance",
    [
        "Fortune sunflower oil wholesale rates",
        "मुझे एक किलो अरहर दाल का सबसे सस्ता रेट बताओ।",
        "आशिरवाद आटा दस किलो वाला किस ऐप पे सस्ता है?",
        "compare Maggi prices across marketplaces",
        "Surf Excel detergent cheapest wholesale",
    ],
)
def test_fallback_routes_price_compare(utterance):
    got = parse_text(utterance)
    assert got.intent == "FIND_WHOLESALE", f"{utterance!r} -> {got.intent}"


def test_price_examples_intent_mapping_sample():
    rows = load_price_examples()
    mapped = {map_price_intent(r) for r in rows[:40]}
    assert "FIND_WHOLESALE" in mapped
