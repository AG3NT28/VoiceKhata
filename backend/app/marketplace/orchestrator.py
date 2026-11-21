"""Concurrent marketplace search, match, land, and rank."""
from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.marketplace.cache import cache_clear, cache_get, cache_set
from app.marketplace.models import MarketplaceListing, MarketplaceProvider, SearchHistory
from app.marketplace.price_engine import calculate_landed_cost, rank_offers
from app.marketplace.product_matcher import score_match
from app.marketplace.product_parser import parse_product_query
from app.marketplace.providers.demo_catalogue import DemoCatalogueProvider
from app.marketplace.providers.wholesale import IndependentWholesaleProvider
from app.marketplace.providers import all_providers, providers_by_code
from app.marketplace.schemas import (
    OfferOut,
    ProductParseResult,
    ProviderStatusOut,
    RankedBuckets,
    SearchResponse,
)

PROVIDER_TIMEOUT_SEC = 4.0


def _paise_to_rupees(paise: int | None) -> float | None:
    if paise is None:
        return None
    return round(paise / 100.0, 2)


async def _run_provider(adapter, query: str, parsed: ProductParseResult) -> tuple[str, list, Any]:
    try:
        products = await asyncio.wait_for(
            adapter.search_products(query, parsed=parsed),
            timeout=PROVIDER_TIMEOUT_SEC,
        )
        return adapter.code, products or [], adapter.get_provider_status()
    except Exception as exc:
        status = adapter.get_provider_status()
        status.status = "ERROR"
        status.auth_notes = f"{status.auth_notes or ''} | {exc}"[:400]
        return adapter.code, [], status


def _offer_from_product(
    product,
    *,
    offer_id: UUID,
    provider_code: str,
    provider_name: str,
    parsed: ProductParseResult,
    listing_id: UUID | None = None,
) -> OfferOut | None:
    match = score_match(
        parsed,
        title=product.title,
        brand=product.brand,
        variant=getattr(product, "variant", None),
        package_quantity=product.package_quantity,
        unit=product.unit,
        barcode=getattr(product, "barcode", None),
    )
    if match.confidence < 0.25 and parsed.product_name.lower() not in (product.title or "").lower():
        # still allow broad demo hits when query tokens overlap title
        pass
    if match.confidence < 0.2:
        return None

    landed = calculate_landed_cost(
        base_price_paise=product.base_price_paise,
        package_quantity=product.package_quantity,
        moq=product.moq,
        case_size=product.case_size,
        requested_quantity=parsed.requested_quantity,
        gst_percent=product.gst_percent,
        delivery_charges_paise=product.delivery_charges_paise,
        discount_paise=product.discount_paise,
        platform_fee_paise=product.platform_fee_paise,
    )
    return OfferOut(
        offer_id=listing_id or offer_id,
        product_id=None,
        provider_code=provider_code,
        provider_name=provider_name,
        supplier_name=product.supplier_name,
        title=product.title,
        brand=product.brand,
        package_quantity=product.package_quantity,
        unit=product.unit,
        moq=product.moq,
        case_size=product.case_size,
        base_price_paise=product.base_price_paise,
        base_price_rupees=_paise_to_rupees(product.base_price_paise) or 0.0,
        gst_percent=product.gst_percent,
        delivery_charges_paise=product.delivery_charges_paise,
        delivery_charges_rupees=_paise_to_rupees(product.delivery_charges_paise),
        discount_paise=product.discount_paise,
        platform_fee_paise=product.platform_fee_paise,
        landed_cost_paise=landed.landed_cost_paise,
        landed_cost_rupees=_paise_to_rupees(landed.landed_cost_paise),
        effective_unit_paise=landed.effective_unit_paise,
        effective_unit_rupees=_paise_to_rupees(landed.effective_unit_paise),
        comparable_quantity=landed.comparable_quantity,
        stock_status=product.stock_status,
        delivery_estimate_days=product.delivery_estimate_days,
        price_source=product.price_source,
        price_complete=landed.price_complete,
        match_confidence=match.confidence,
        last_updated=datetime.utcnow(),
        has_redirect=bool(product.product_url),
    )


async def search_marketplace(
    db: AsyncSession,
    *,
    shop_id: UUID,
    query: str,
    purchase_type: str | None = "wholesale",
    provider_filter: list[str] | None = None,
) -> SearchResponse:
    cache_key = f"mkt:{shop_id}:{query}:{purchase_type}:{','.join(provider_filter or [])}"
    cached = cache_get(cache_key)
    if cached:
        try:
            return SearchResponse.model_validate(cached)
        except Exception:
            cache_clear()

    parsed = parse_product_query(query, purchase_type)

    # Split DB-backed vs stub providers. AsyncSession is not safe for concurrent use,
    # so DB adapters run sequentially; stubs can gather.
    db_adapters = []
    stub_adapters = []
    by_code = providers_by_code()
    codes = provider_filter or list(by_code.keys())
    for code in codes:
        if code == "demo_catalogue":
            db_adapters.append(DemoCatalogueProvider(db))
        elif code == "independent_wholesale":
            db_adapters.append(IndependentWholesaleProvider(db, shop_id))
        elif code in by_code:
            stub_adapters.append(by_code[code])

    results = []
    for adapter in db_adapters:
        results.append(await _run_provider(adapter, query, parsed))
    if stub_adapters:
        stub_results = await asyncio.gather(
            *[_run_provider(a, query, parsed) for a in stub_adapters],
            return_exceptions=True,
        )
        for item in stub_results:
            if isinstance(item, Exception):
                continue
            results.append(item)

    # Map external ids to persisted listing ids when available
    listing_map: dict[tuple[str, str], UUID] = {}
    listing_rows = (
        await db.execute(select(MarketplaceListing, MarketplaceProvider).join(MarketplaceProvider))
    ).all()
    for listing, provider in listing_rows:
        if listing.shop_id is None or listing.shop_id == shop_id:
            listing_map[(provider.code, listing.external_product_id)] = listing.id

    offers: list[OfferOut] = []
    provider_statuses: list[ProviderStatusOut] = []
    for code, products, status in results:
        provider_statuses.append(
            ProviderStatusOut(
                code=status.code,
                name=status.name,
                category=status.category,
                status=status.status,
                enabled=status.enabled,
                auth_notes=status.auth_notes,
                live_data=status.live_data,
                redirect_capable=status.redirect_capable,
            )
        )
        for product in products:
            listing_id = listing_map.get((code, product.external_id))
            offer_id = listing_id or uuid4()
            # Enrich supplier name from DB when available
            if listing_id and not product.supplier_name:
                listing = await db.get(MarketplaceListing, listing_id)
                if listing and listing.supplier_id:
                    from app.marketplace.models import SupplierProfile

                    supplier = await db.get(SupplierProfile, listing.supplier_id)
                    if supplier:
                        product.supplier_name = supplier.name
            offer = _offer_from_product(
                product,
                offer_id=offer_id,
                provider_code=code,
                provider_name=status.name,
                parsed=parsed,
                listing_id=listing_id,
            )
            if offer:
                offers.append(offer)

    offers.sort(key=lambda o: (0 if o.price_complete else 1, o.effective_unit_paise or 10**18))
    ranked_raw = rank_offers([o.model_dump() for o in offers])
    rankings = RankedBuckets(
        lowest_unit_price=[OfferOut.model_validate(x) for x in ranked_raw["lowest_unit_price"]],
        best_bulk_deal=[OfferOut.model_validate(x) for x in ranked_raw["best_bulk_deal"]],
        fastest_delivery=[OfferOut.model_validate(x) for x in ranked_raw["fastest_delivery"]],
    )

    db.add(
        SearchHistory(
            shop_id=shop_id,
            query_text=query,
            parsed_json=parsed.model_dump_json(),
            result_count=len(offers),
        )
    )
    await db.commit()

    response = SearchResponse(
        query=query,
        parsed=parsed,
        offers=offers,
        rankings=rankings,
        providers_queried=provider_statuses,
    )
    cache_set(cache_key, response.model_dump(mode="json"))
    return response


async def get_offer(db: AsyncSession, offer_id: UUID, shop_id: UUID) -> MarketplaceListing | None:
    listing = await db.get(MarketplaceListing, offer_id)
    if not listing:
        return None
    if listing.shop_id is not None and listing.shop_id != shop_id:
        return None
    return listing
