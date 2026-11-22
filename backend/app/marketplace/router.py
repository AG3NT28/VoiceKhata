"""Marketplace HTTP API under /api/marketplace."""
from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.marketplace.import_service import import_supplier_catalogue
from app.marketplace.models import (
    CanonicalProduct,
    MarketplaceListing,
    MarketplaceProvider,
    RedirectEvent,
    SearchHistory,
    StarredListing,
    SupplierProfile,
)
from app.marketplace.orchestrator import get_offer, search_marketplace
from app.marketplace.price_engine import calculate_landed_cost, rank_offers
from app.marketplace.product_parser import parse_product_query
from app.marketplace.providers import all_providers
from app.marketplace.redirect_service import is_safe_redirect
from app.marketplace.schemas import (
    CompareRequest,
    CompareResponse,
    HistoryItem,
    HistoryResponse,
    ImportReport,
    OfferOut,
    ProductDetailResponse,
    ProviderStatusOut,
    RankedBuckets,
    RedirectResponse,
    SearchRequest,
    SearchResponse,
    StarredOfferOut,
    StarToggleResponse,
)
from app.security.auth import get_current_shop_id

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


def _listing_to_offer(listing: MarketplaceListing, provider: MarketplaceProvider, requested_qty: float = 1.0) -> OfferOut:
    landed = calculate_landed_cost(
        base_price_paise=listing.base_price_paise,
        package_quantity=listing.package_quantity,
        moq=listing.moq,
        case_size=listing.case_size,
        requested_quantity=requested_qty,
        gst_percent=listing.gst_percent,
        delivery_charges_paise=listing.delivery_charges_paise,
        discount_paise=listing.discount_paise,
        platform_fee_paise=listing.platform_fee_paise,
    )
    return OfferOut(
        offer_id=listing.id,
        product_id=listing.canonical_product_id,
        provider_code=provider.code,
        provider_name=provider.name,
        title=listing.title,
        brand=listing.brand,
        package_quantity=listing.package_quantity,
        unit=listing.unit,
        moq=listing.moq,
        case_size=listing.case_size,
        base_price_paise=listing.base_price_paise,
        base_price_rupees=listing.base_price_paise / 100.0,
        gst_percent=listing.gst_percent,
        delivery_charges_paise=listing.delivery_charges_paise,
        delivery_charges_rupees=(listing.delivery_charges_paise / 100.0) if listing.delivery_charges_paise is not None else None,
        discount_paise=listing.discount_paise,
        platform_fee_paise=listing.platform_fee_paise,
        landed_cost_paise=landed.landed_cost_paise,
        landed_cost_rupees=(landed.landed_cost_paise or 0) / 100.0 if landed.landed_cost_paise is not None else None,
        effective_unit_paise=landed.effective_unit_paise,
        effective_unit_rupees=(landed.effective_unit_paise or 0) / 100.0 if landed.effective_unit_paise is not None else None,
        comparable_quantity=landed.comparable_quantity,
        stock_status=listing.stock_status,
        delivery_estimate_days=listing.delivery_estimate_days,
        price_source=listing.price_source,
        price_complete=landed.price_complete,
        match_confidence=1.0,
        last_updated=listing.last_updated,
        has_redirect=bool(listing.product_url),
    )


@router.get("/providers", response_model=list[ProviderStatusOut])
async def list_providers(
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(MarketplaceProvider).order_by(MarketplaceProvider.name))).scalars().all()
    if rows:
        return [
            ProviderStatusOut(
                code=r.code,
                name=r.name,
                category=r.category,
                status=r.status,
                enabled=r.enabled,
                auth_notes=r.auth_notes,
                live_data=r.status == "LIVE",
                redirect_capable=bool(r.approved_domains) or r.code in ("demo_catalogue", "independent_wholesale"),
            )
            for r in rows
        ]
    return [
        ProviderStatusOut(
            code=p.code,
            name=p.name,
            category=p.category,
            status=p.get_provider_status().status,
            enabled=True,
            auth_notes=p.get_provider_status().auth_notes,
            live_data=p.get_provider_status().live_data,
            redirect_capable=p.get_provider_status().redirect_capable,
        )
        for p in all_providers()
    ]


@router.post("/search", response_model=SearchResponse)
async def search(
    payload: SearchRequest,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    return await search_marketplace(
        db,
        shop_id=shop_id,
        query=payload.query,
        purchase_type=payload.purchase_type,
        provider_filter=payload.providers,
    )


@router.get("/products/{product_id}", response_model=ProductDetailResponse)
async def product_detail(
    product_id: UUID,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(CanonicalProduct, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    listings = (
        await db.execute(
            select(MarketplaceListing, MarketplaceProvider)
            .join(MarketplaceProvider)
            .where(MarketplaceListing.canonical_product_id == product_id)
        )
    ).all()
    offers = [_listing_to_offer(listing, provider) for listing, provider in listings]
    return ProductDetailResponse(
        product_id=product.id,
        name=product.name,
        brand=product.brand,
        category=product.category,
        variant=product.variant,
        package_quantity=product.package_quantity,
        unit=product.unit,
        offers=offers,
    )


@router.get("/offers/{offer_id}", response_model=OfferOut)
async def offer_detail(
    offer_id: UUID,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    listing = await get_offer(db, offer_id, shop_id)
    if not listing:
        raise HTTPException(404, "Offer not found")
    provider = await db.get(MarketplaceProvider, listing.provider_id)
    if not provider:
        raise HTTPException(404, "Provider missing")
    return _listing_to_offer(listing, provider)


@router.post("/compare", response_model=CompareResponse)
async def compare(
    payload: CompareRequest,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    offers: list[OfferOut] = []
    for oid in payload.offer_ids:
        listing = await get_offer(db, oid, shop_id)
        if not listing:
            continue
        provider = await db.get(MarketplaceProvider, listing.provider_id)
        if provider:
            offers.append(_listing_to_offer(listing, provider))
    ranked = rank_offers([o.model_dump() for o in offers])
    return CompareResponse(
        offers=offers,
        rankings=RankedBuckets(
            lowest_unit_price=[OfferOut.model_validate(x) for x in ranked["lowest_unit_price"]],
            best_bulk_deal=[OfferOut.model_validate(x) for x in ranked["best_bulk_deal"]],
            fastest_delivery=[OfferOut.model_validate(x) for x in ranked["fastest_delivery"]],
        ),
    )


@router.post("/redirect/{offer_id}", response_model=RedirectResponse)
async def redirect_offer(
    offer_id: UUID,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    listing = await get_offer(db, offer_id, shop_id)
    if not listing:
        raise HTTPException(404, "Offer not found")
    provider = await db.get(MarketplaceProvider, listing.provider_id)
    if not provider:
        raise HTTPException(404, "Provider missing")
    url = listing.product_url
    if not url or not is_safe_redirect(url, provider.code, provider.approved_domains):
        raise HTTPException(
            400,
            "No authorized redirect URL for this offer. Confirm on the supplier platform manually.",
        )
    db.add(
        RedirectEvent(
            shop_id=shop_id,
            listing_id=listing.id,
            destination_url=url,
            provider_code=provider.code,
        )
    )
    await db.commit()
    return RedirectResponse(
        offer_id=listing.id,
        destination_url=url,
        provider_code=provider.code,
        recorded=True,
        notice="Confirm final price, availability and delivery on the supplier platform.",
    )


@router.get("/history", response_model=HistoryResponse)
async def history(
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(SearchHistory)
            .where(SearchHistory.shop_id == shop_id)
            .order_by(SearchHistory.created_at.desc())
            .limit(30)
        )
    ).scalars().all()
    return HistoryResponse(
        items=[
            HistoryItem(
                id=r.id,
                query_text=r.query_text,
                result_count=r.result_count,
                created_at=r.created_at,
            )
            for r in rows
        ]
    )


@router.post("/suppliers/import", response_model=ImportReport)
async def import_catalogue(
    file: UploadFile = File(...),
    supplier_name: str = Form("Imported Supplier"),
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Empty file")
    return await import_supplier_catalogue(
        db,
        shop_id=shop_id,
        raw=raw,
        filename=file.filename or "catalogue.csv",
        supplier_name=supplier_name,
    )


@router.post("/parse")
async def parse_only(payload: SearchRequest, shop_id: UUID = Depends(get_current_shop_id)):
    """Debug/helper: product intelligence extraction only."""
    return parse_product_query(payload.query, payload.purchase_type)


def _star_out(star: StarredListing, listing: MarketplaceListing, supplier_name: str | None) -> StarredOfferOut:
    delta = listing.base_price_paise - star.starred_price_paise
    return StarredOfferOut(
        star_id=star.id,
        offer_id=listing.id,
        title=listing.title,
        brand=listing.brand,
        supplier_name=supplier_name,
        package_quantity=listing.package_quantity,
        unit=listing.unit,
        starred_price_paise=star.starred_price_paise,
        starred_price_rupees=star.starred_price_paise / 100.0,
        current_price_paise=listing.base_price_paise,
        current_price_rupees=listing.base_price_paise / 100.0,
        delta_paise=delta,
        delta_rupees=delta / 100.0,
        price_source=listing.price_source,
        stock_status=listing.stock_status,
        last_updated=listing.last_updated,
        note=star.note,
    )


@router.get("/stars", response_model=list[StarredOfferOut])
async def list_stars(
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    """Starred stock for fare monitoring on the marketplace home."""
    from app.marketplace.seed import seed_default_stars

    rows = (
        await db.execute(
            select(StarredListing).where(StarredListing.shop_id == shop_id).order_by(StarredListing.created_at.desc())
        )
    ).scalars().all()
    if not rows:
        await seed_default_stars(db, shop_id)
        rows = (
            await db.execute(
                select(StarredListing).where(StarredListing.shop_id == shop_id).order_by(StarredListing.created_at.desc())
            )
        ).scalars().all()

    out: list[StarredOfferOut] = []
    for star in rows:
        listing = await db.get(MarketplaceListing, star.listing_id)
        if not listing:
            continue
        supplier_name = None
        if listing.supplier_id:
            supplier = await db.get(SupplierProfile, listing.supplier_id)
            supplier_name = supplier.name if supplier else None
        out.append(_star_out(star, listing, supplier_name))
    return out


@router.post("/stars/{offer_id}", response_model=StarToggleResponse)
async def star_offer(
    offer_id: UUID,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    listing = await get_offer(db, offer_id, shop_id)
    if not listing:
        # Demo listings are global (shop_id null) — allow starring those too
        listing = await db.get(MarketplaceListing, offer_id)
        if not listing or (listing.shop_id is not None and listing.shop_id != shop_id):
            raise HTTPException(404, "Offer not found")

    existing = (
        await db.execute(
            select(StarredListing).where(
                StarredListing.shop_id == shop_id,
                StarredListing.listing_id == listing.id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        supplier_name = None
        if listing.supplier_id:
            supplier = await db.get(SupplierProfile, listing.supplier_id)
            supplier_name = supplier.name if supplier else None
        return StarToggleResponse(offer_id=listing.id, starred=True, star=_star_out(existing, listing, supplier_name))

    star = StarredListing(
        shop_id=shop_id,
        listing_id=listing.id,
        starred_price_paise=listing.base_price_paise,
    )
    db.add(star)
    await db.commit()
    await db.refresh(star)
    supplier_name = None
    if listing.supplier_id:
        supplier = await db.get(SupplierProfile, listing.supplier_id)
        supplier_name = supplier.name if supplier else None
    return StarToggleResponse(offer_id=listing.id, starred=True, star=_star_out(star, listing, supplier_name))


@router.delete("/stars/{offer_id}", response_model=StarToggleResponse)
async def unstar_offer(
    offer_id: UUID,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    existing = (
        await db.execute(
            select(StarredListing).where(
                StarredListing.shop_id == shop_id,
                StarredListing.listing_id == offer_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.commit()
    return StarToggleResponse(offer_id=offer_id, starred=False, star=None)
