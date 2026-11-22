"""Price-comparison multilingual training set for Gnani STT bias + NLU.

Gnani Prisma does not accept offline fine-tunes. Training here means:
1. keyterms + topic bias on every STT request (ASR)
2. few-shots / fallback rules for compare_prices → FIND_WHOLESALE (NLU)
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "voicekhata_price_comparison_multilingual.jsonl"
)

# Dataset intent → runtime intent
INTENT_MAP = {
    "compare_prices": "FIND_WHOLESALE",
    "compare_with_expiry_filter": "FIND_WHOLESALE",
    "set_price_type": "FIND_WHOLESALE",
    "ask_price_inclusions": "FIND_WHOLESALE",
}

_LEDGER_KEYTERMS = [
    "udhaar", "khata", "rupaye", "baaki", "jama", "payment", "balance",
    "likho", "diye", "customer", "sau", "hazaar", "lakh", "credit",
]

_COMPARE_KEYTERMS = [
    "compare", "wholesale", "sasta", "rate", "price", "marketplace",
    "udaan", "jumbotail", "wishbee", "ondc", "blinkit", "jiomart",
    "atta", "dal", "chini", "tel", "oil", "rice", "namak", "detergent",
    "sunflower", "aashirvaad", "tata", "maggi", "britannia", "nescafe",
    "surf excel", "ariel", "kohinoor", "biscuits", "coffee",
    "सस्ता", "रेट", "दाम", "तुलना", "थोक", "आटा", "दाल", "चीनी", "नमक", "तेल",
    "ధర", "తక్కువ", "పిండి", "పప్పు",
    "விலை", "குறைந்த", "பருப்பு",
    "ಬೆಲೆ", "ಕಡಿಮೆ", "ಬೇಳೆ",
]


@lru_cache(maxsize=1)
def load_price_examples() -> list[dict]:
    if not DATA_PATH.exists():
        return []
    rows: list[dict] = []
    for line in DATA_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def map_price_intent(row: dict) -> str:
    if row.get("needs_clarification"):
        return "CLARIFY"
    return INTENT_MAP.get(row.get("intent") or "", "FIND_WHOLESALE")


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v not in (None, "")]
    return [value]


def build_query_from_entities(entities: dict | None, fallback: str = "") -> str:
    entities = entities or {}
    parts: list[str] = []
    brand = entities.get("brand")
    if isinstance(brand, str) and brand:
        parts.append(brand)
    product = entities.get("product")
    if isinstance(product, str) and product:
        parts.append(product)
    qty = entities.get("quantity")
    unit = entities.get("unit") or ""
    if isinstance(qty, list):
        # multi pack — use largest pack for search seed
        try:
            qty = max(float(x) for x in qty)
        except Exception:
            qty = None
    if qty not in (None, ""):
        try:
            qn = float(qty)
            qtxt = str(int(qn)) if qn == int(qn) else str(qn)
            parts.append(f"{qtxt}{unit}".strip() if unit else qtxt)
        except Exception:
            pass
    price_type = entities.get("price_type")
    if price_type:
        parts.append(str(price_type))
    query = " ".join(parts).strip()
    return query or (fallback or "").strip()


def example_to_few_shot(row: dict) -> tuple[str, dict]:
    intent = map_price_intent(row)
    entities = dict(row.get("entities") or {})
    spoken = (row.get("spoken_text") or row.get("normalized_text") or "").strip()
    out_entities: dict = {
        "query": build_query_from_entities(entities, spoken),
        "purchase_type": "wholesale" if (entities.get("price_type") or "wholesale") == "wholesale" else (entities.get("price_type") or "wholesale"),
    }
    if entities.get("product"):
        out_entities["product"] = entities["product"]
    if entities.get("brand"):
        out_entities["brand"] = entities["brand"]
    if entities.get("quantity") is not None:
        out_entities["quantity"] = entities["quantity"]
    if entities.get("unit"):
        out_entities["unit"] = entities["unit"]
    if entities.get("marketplaces"):
        out_entities["marketplaces"] = entities["marketplaces"]

    clarify = intent == "CLARIFY"
    return spoken, {
        "intent": intent,
        "confidence": 0.6 if clarify else 0.93,
        "entities": out_entities if not clarify else {"query": spoken},
        "clarification_needed": clarify,
        "clarification_question": row.get("clarification_question") if clarify else None,
        "clarification_options": [],
    }


def few_shot_from_price_dataset(limit: int = 24) -> list[tuple[str, dict]]:
    shots: list[tuple[str, dict]] = []
    # Prefer non-clarify examples first, then clarify
    ordered = sorted(load_price_examples(), key=lambda r: bool(r.get("needs_clarification")))
    for row in ordered:
        shots.append(example_to_few_shot(row))
        if len(shots) >= limit:
            break
    return shots


def _collect_terms() -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    def add(term: str | None):
        if not term:
            return
        t = str(term).strip()
        if not t:
            return
        key = t.casefold()
        if key in seen:
            return
        seen.add(key)
        out.append(t)

    for term in _LEDGER_KEYTERMS + _COMPARE_KEYTERMS:
        add(term)

    for row in load_price_examples():
        entities = row.get("entities") or {}
        for brand in _as_list(entities.get("brand")):
            add(str(brand))
        for product in _as_list(entities.get("product")):
            add(str(product))
            # also first latin token if mixed
            for part in str(product).replace("/", " ").split():
                if part.isascii() and len(part) > 2:
                    add(part)
        for market in _as_list(entities.get("marketplaces")):
            add(str(market))
        # short phrases from normalized english-ish text
        norm = row.get("normalized_text") or ""
        for token in ["sunflower oil", "Good Day", "Surf Excel", "Aashirvaad", "Tata"]:
            if token.lower() in norm.lower():
                add(token)

    return out


def _flatten_keyterm_tokens(terms: list[str]) -> list[str]:
    """Split phrases into single tokens — Gnani counts each whitespace piece."""
    seen: set[str] = set()
    out: list[str] = []
    for term in terms:
        for part in str(term).replace(",", " ").split():
            token = part.strip()
            if len(token) < 2:
                continue
            key = token.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(token)
    return out


@lru_cache(maxsize=1)
def gnani_keyterms(limit: int = 200) -> list[str]:
    """Up to `limit` single-token keyterms (Gnani Prisma max = 200)."""
    max_n = max(1, min(200, int(limit)))
    return _flatten_keyterm_tokens(_collect_terms())[:max_n]


def gnani_keyterms_json(limit: int = 200) -> str:
    return json.dumps(gnani_keyterms(limit)[:200], ensure_ascii=False)


def gnani_topic() -> str:
    return (
        "Indian kirana shopkeeper comparing wholesale grocery prices and pack sizes "
        "across B2B marketplaces like Udaan, Jumbotail, Wishbee and ONDC. "
        "Products include atta, dal, rice, sugar, salt, edible oil, biscuits, detergent, coffee."
    )


def training_summary() -> dict:
    rows = load_price_examples()
    by_lang: dict[str, int] = {}
    by_intent: dict[str, int] = {}
    for row in rows:
        by_lang[row.get("language") or "?"] = by_lang.get(row.get("language") or "?", 0) + 1
        mapped = map_price_intent(row)
        by_intent[mapped] = by_intent.get(mapped, 0) + 1
    return {
        "path": str(DATA_PATH),
        "examples": len(rows),
        "languages": by_lang,
        "runtime_intents": by_intent,
        "keyterms": len(gnani_keyterms()),
        "gnani_mode": "keyterms+topic (no offline fine-tune API)",
    }
