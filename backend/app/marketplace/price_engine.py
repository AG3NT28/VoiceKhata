"""Landed-cost and effective unit-price calculations."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LandedCostResult:
    order_units: int
    comparable_quantity: float
    product_cost_paise: int
    gst_paise: int | None
    delivery_paise: int | None
    platform_fee_paise: int
    discount_paise: int
    landed_cost_paise: int | None
    effective_unit_paise: int | None
    price_complete: bool
    notes: list[str]


def required_order_units(requested_quantity: float, package_quantity: float, moq: int, case_size: int) -> int:
    """How many sellable packs are needed to meet requested qty and MOQ/case rules."""
    pack = package_quantity if package_quantity > 0 else 1.0
    packs_needed = max(1, int((requested_quantity + pack - 1e-9) // pack))
    if requested_quantity > packs_needed * pack:
        packs_needed += 1
    # ceil division for exact
    import math

    packs_needed = max(1, math.ceil(requested_quantity / pack))
    packs_needed = max(packs_needed, max(1, moq or 1))
    case = max(1, case_size or 1)
    if packs_needed % case != 0:
        packs_needed = ((packs_needed + case - 1) // case) * case
    return packs_needed


def calculate_landed_cost(
    *,
    base_price_paise: int,
    package_quantity: float,
    moq: int = 1,
    case_size: int = 1,
    requested_quantity: float = 1.0,
    gst_percent: float | None = None,
    delivery_charges_paise: int | None = None,
    discount_paise: int = 0,
    platform_fee_paise: int = 0,
    bulk_tiers: list[tuple[int, float]] | None = None,
) -> LandedCostResult:
    """
    Total landed cost = product + GST + delivery + platform fee - discounts.
    Effective unit cost = landed / comparable quantity (in listing unit).
    """
    notes: list[str] = []
    units = required_order_units(requested_quantity, package_quantity, moq, case_size)
    unit_price = base_price_paise

    # Quantity-based pricing tiers: (min_units, price_paise_per_pack)
    if bulk_tiers:
        for min_units, tier_price in sorted(bulk_tiers, key=lambda x: x[0], reverse=True):
            if units >= min_units:
                unit_price = int(tier_price)
                notes.append(f"bulk_tier>={min_units}")
                break

    product_cost = unit_price * units - max(0, discount_paise)
    product_cost = max(0, product_cost)

    gst_paise: int | None
    if gst_percent is None:
        gst_paise = None
        notes.append("gst_unknown")
    else:
        gst_paise = int(round(product_cost * (gst_percent / 100.0)))

    delivery = delivery_charges_paise
    if delivery is None:
        notes.append("delivery_unknown")

    complete = gst_paise is not None and delivery is not None
    partial_sum = product_cost + (gst_paise or 0) + (delivery or 0) + max(0, platform_fee_paise)
    landed = partial_sum if complete else partial_sum  # still compute estimate
    comparable_qty = units * (package_quantity if package_quantity > 0 else 1.0)
    effective = int(round(landed / comparable_qty)) if comparable_qty > 0 else None

    return LandedCostResult(
        order_units=units,
        comparable_quantity=comparable_qty,
        product_cost_paise=product_cost,
        gst_paise=gst_paise,
        delivery_paise=delivery,
        platform_fee_paise=max(0, platform_fee_paise),
        discount_paise=max(0, discount_paise),
        landed_cost_paise=landed,
        effective_unit_paise=effective,
        price_complete=complete,
        notes=notes,
    )


def rank_offers(offers: list[dict]) -> dict[str, list[dict]]:
    """Rank into three buckets. Incomplete prices never win 'lowest' alone without flag."""
    priced = [o for o in offers if o.get("effective_unit_paise") is not None]
    lowest = sorted(
        priced,
        key=lambda o: (
            0 if o.get("price_complete") else 1,
            o.get("effective_unit_paise") or 10**18,
            o.get("moq") or 1,
        ),
    )[:5]

    bulk = sorted(
        priced,
        key=lambda o: (
            -(o.get("comparable_quantity") or 0),
            o.get("effective_unit_paise") or 10**18,
        ),
    )[:5]

    fast = sorted(
        [o for o in offers if o.get("delivery_estimate_days") is not None],
        key=lambda o: (o.get("delivery_estimate_days") or 999, o.get("effective_unit_paise") or 10**18),
    )[:5]

    return {
        "lowest_unit_price": lowest,
        "best_bulk_deal": bulk,
        "fastest_delivery": fast,
    }
