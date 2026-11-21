"""Parse multilingual / code-mixed wholesale product queries."""
from __future__ import annotations

import re

from app.marketplace.schemas import ProductParseResult

_QTY_RE = re.compile(
    r"(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>kg|kgs|किलो|किलो그램|g|gm|grams|l|ltr|litre|liter|ml|pcs|packet|pkt|dozen)?",
    re.IGNORECASE,
)

_BRANDS = [
    "fortune", "aashirvaad", "ashirvad", "tata", "india gate", "fortune", "saffola",
    "dhara", "gemini", "patanjali", "amul", "britannia", "parle", "maggi", "nestle",
    "dabur", "himalaya", "surf excel", "rin", "vim", "harpic", "dettol",
]

_CATEGORY_HINTS = {
    "oil": "edible_oils",
    "tel": "edible_oils",
    "atta": "wheat_flour",
    "flour": "wheat_flour",
    "rice": "rice",
    "chawal": "rice",
    "sugar": "sugar",
    "chini": "sugar",
    "dal": "pulses",
    "pulse": "pulses",
    "masala": "spices",
    "spice": "spices",
    "biscuit": "biscuits",
    "tea": "beverages",
    "chai": "beverages",
    "milk": "dairy",
    "doodh": "dairy",
    "soap": "personal_care",
    "detergent": "cleaning",
}

_UNIT_MAP = {
    "kgs": "kg",
    "किलो": "kg",
    "किलोграм": "kg",
    "gm": "g",
    "grams": "g",
    "ltr": "l",
    "litre": "l",
    "liter": "l",
    "packet": "pcs",
    "pkt": "pcs",
    "dozen": "pcs",
}

_VARIANT_WORDS = {
    "sunflower": "Sunflower",
    "groundnut": "Groundnut",
    "mustard": "Mustard",
    "soyabean": "Soyabean",
    "basmati": "Basmati",
    "sona masoori": "Sona Masoori",
}


def _detect_brand(text: str) -> str | None:
    lower = text.lower()
    for brand in sorted(_BRANDS, key=len, reverse=True):
        if brand in lower:
            return brand.title() if brand != "aashirvaad" else "Aashirvaad"
    return None


def _detect_category(text: str) -> str | None:
    lower = text.lower()
    for hint, cat in _CATEGORY_HINTS.items():
        if hint in lower:
            return cat
    return None


def _detect_variant(text: str) -> str | None:
    lower = text.lower()
    for key, label in _VARIANT_WORDS.items():
        if key in lower:
            return label
    return None


def _clean_product_name(text: str, brand: str | None, qty: float | None, unit: str | None) -> str:
    cleaned = text
    for token in ("find", "search", "wholesale", "price", "rates", "rate", "at", "of", "for",
                  "खोजो", "खरीदो", "थोक", "भाव", "दाम", "किंमत"):
        cleaned = re.sub(rf"\b{re.escape(token)}\b", " ", cleaned, flags=re.IGNORECASE)
    if brand:
        cleaned = re.sub(re.escape(brand), " ", cleaned, flags=re.IGNORECASE)
    if qty is not None:
        cleaned = re.sub(rf"\b{re.escape(str(int(qty) if qty == int(qty) else qty))}\b", " ", cleaned)
    if unit:
        cleaned = re.sub(rf"\b{re.escape(unit)}\b", " ", cleaned, flags=re.IGNORECASE)
        for raw, mapped in _UNIT_MAP.items():
            if mapped == unit:
                cleaned = re.sub(rf"\b{re.escape(raw)}\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,")
    return cleaned.title() if cleaned else "Product"


def parse_product_query(query: str, purchase_type: str | None = None) -> ProductParseResult:
    raw = (query or "").strip()
    lower = raw.lower()
    qty = 1.0
    unit = "kg"
    m = _QTY_RE.search(raw)
    if m:
        qty = float(m.group("qty"))
        raw_unit = (m.group("unit") or "kg").lower()
        unit = _UNIT_MAP.get(raw_unit, raw_unit)

    brand = _detect_brand(raw)
    variant = _detect_variant(raw)
    category = _detect_category(raw)
    product_name = _clean_product_name(raw, brand, qty, unit)
    if variant and variant.lower() not in product_name.lower():
        product_name = f"{variant} {product_name}".strip()

    ptype = (purchase_type or "").strip().lower()
    if not ptype:
        ptype = "wholesale" if any(w in lower for w in ("wholesale", "थोक", "bulk", "carton")) else "retail"

    return ProductParseResult(
        product_name=product_name or "Product",
        brand=brand,
        variant=variant,
        category=category,
        requested_quantity=qty,
        unit=unit,
        purchase_type=ptype,
        raw_query=raw,
    )
