"""Deterministic-first product matching with fuzzy fallback."""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.marketplace.schemas import ProductParseResult


def normalize_key(brand: str | None, name: str, variant: str | None, qty: float, unit: str) -> str:
    parts = [
        (brand or "").strip().lower(),
        re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip(),
        (variant or "").strip().lower(),
        f"{qty:g}",
        (unit or "").strip().lower(),
    ]
    return "|".join(parts)


def _tokens(text: str) -> set[str]:
    return {t for t in re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split() if t}


@dataclass
class MatchScore:
    confidence: float
    reason: str


def score_match(
    parsed: ProductParseResult,
    *,
    title: str,
    brand: str | None,
    variant: str | None,
    package_quantity: float,
    unit: str,
    barcode: str | None = None,
) -> MatchScore:
    if parsed.barcode and barcode and parsed.barcode == barcode:
        return MatchScore(1.0, "barcode")

    score = 0.0
    reasons: list[str] = []

    # Variant must not collide (sunflower vs groundnut)
    if parsed.variant and variant:
        if parsed.variant.strip().lower() != variant.strip().lower():
            return MatchScore(0.0, "variant_mismatch")
        score += 0.25
        reasons.append("variant")
    elif parsed.variant:
        if parsed.variant.lower() not in (title or "").lower():
            return MatchScore(0.05, "variant_missing")
        score += 0.15
        reasons.append("variant_in_title")

    if parsed.brand and brand:
        if parsed.brand.strip().lower() == brand.strip().lower():
            score += 0.3
            reasons.append("brand")
        else:
            return MatchScore(0.0, "brand_mismatch")
    elif parsed.brand and parsed.brand.lower() in (title or "").lower():
        score += 0.2
        reasons.append("brand_in_title")

    # Quantity / unit — soft preference, not hard fail (different pack sizes OK)
    if unit and parsed.unit and unit.lower() == parsed.unit.lower():
        score += 0.1
        reasons.append("unit")
    if package_quantity and parsed.requested_quantity:
        # prefer same pack size
        if abs(package_quantity - parsed.requested_quantity) < 1e-6:
            score += 0.15
            reasons.append("pack_qty")

    name_tokens = _tokens(parsed.product_name)
    title_tokens = _tokens(title)
    if name_tokens and title_tokens:
        overlap = len(name_tokens & title_tokens) / max(len(name_tokens), 1)
        score += 0.3 * overlap
        if overlap >= 0.5:
            reasons.append("name_overlap")

    # Drop very weak matches
    confidence = round(min(score, 1.0), 3)
    if confidence < 0.25:
        return MatchScore(confidence, "weak")
    return MatchScore(confidence, ",".join(reasons) or "fuzzy")
