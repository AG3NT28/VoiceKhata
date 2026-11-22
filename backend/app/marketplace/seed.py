"""Seed marketplace providers, provision catalogue, and default starred fares."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.marketplace.models import (
    MarketplaceListing,
    MarketplaceProvider,
    StarredListing,
    SupplierProfile,
)
from app.marketplace.providers.demo_catalogue import DEMO_PRODUCTS

PROVIDER_SEED = [
    ("demo_catalogue", "VoiceKhata Provision Seed", "demonstration", "DEMONSTRATION",
     "Seeded provision-store wholesale offers. Not live APIs.", "example.com"),
    ("independent_wholesale", "Independent Wholesalers", "wholesale", "IMPORT_READY",
     "CSV/Excel imported supplier catalogues.", ""),
    ("jumbotail", "Jumbotail", "b2b_wholesale", "PARTNER_ACCESS_REQUIRED",
     "Partner API credentials required.", "jumbotail.com"),
    ("wishbee", "Wishbee", "b2b_wholesale", "PARTNER_ACCESS_REQUIRED",
     "Partner credentials required.", "wishbee.in,wishbee.com"),
    ("udaan", "Udaan", "b2b_wholesale", "PARTNER_ACCESS_REQUIRED",
     "Partner integration required.", "udaan.com"),
    ("ondc", "ONDC RET10", "open_commerce", "PARTNER_ACCESS_REQUIRED",
     "ONDC network participant onboarding required.", "ondc.org"),
    ("blinkit", "Blinkit", "quick_commerce", "PARTNER_ACCESS_REQUIRED",
     "Official partner API required — no scraping.", "blinkit.com"),
    ("bigbasket", "BigBasket", "quick_commerce", "PARTNER_ACCESS_REQUIRED",
     "Partner/affiliate access required.", "bigbasket.com"),
    ("jiomart", "JioMart", "quick_commerce", "PARTNER_ACCESS_REQUIRED",
     "Partner API required.", "jiomart.com"),
]

# Default watchlist SKUs so Market home has starred fares to monitor
DEFAULT_STAR_EXTERNAL_IDS = [
    "demo-fortune-sf-1l",
    "demo-aashirvaad-atta-5kg",
    "demo-tata-salt-1kg",
    "demo-toor-dal-1kg",
    "demo-tata-tea-500g",
    "demo-amul-ghee-1l",
]


async def seed_marketplace(db: AsyncSession, shop_id=None) -> None:
    providers: dict[str, MarketplaceProvider] = {}
    for code, name, category, status, notes, domains in PROVIDER_SEED:
        row = (
            await db.execute(select(MarketplaceProvider).where(MarketplaceProvider.code == code))
        ).scalar_one_or_none()
        if row is None:
            row = MarketplaceProvider(
                code=code,
                name=name,
                category=category,
                status=status,
                auth_notes=notes,
                approved_domains=domains,
                enabled=True,
            )
            db.add(row)
            await db.flush()
        else:
            row.name = name
            row.auth_notes = notes
        providers[code] = row

    demo = providers["demo_catalogue"]
    suppliers: dict[str, SupplierProfile] = {}
    listing_by_external: dict[str, MarketplaceListing] = {}

    for item in DEMO_PRODUCTS:
        supplier_name = item.get("supplier_name") or "Kirana Wholesale Hub"
        if supplier_name not in suppliers:
            existing_sup = (
                await db.execute(
                    select(SupplierProfile).where(
                        SupplierProfile.name == supplier_name,
                        SupplierProfile.provider_code == "demo_catalogue",
                    )
                )
            ).scalar_one_or_none()
            if existing_sup is None:
                existing_sup = SupplierProfile(
                    name=supplier_name,
                    provider_code="demo_catalogue",
                    city="Pune",
                )
                db.add(existing_sup)
                await db.flush()
            suppliers[supplier_name] = existing_sup

        existing = (
            await db.execute(
                select(MarketplaceListing).where(
                    MarketplaceListing.provider_id == demo.id,
                    MarketplaceListing.external_product_id == item["external_id"],
                )
            )
        ).scalar_one_or_none()
        if existing:
            # Keep catalogue prices fresh for fare monitoring demos
            existing.base_price_paise = item["base_price_paise"]
            existing.gst_percent = item.get("gst_percent")
            existing.delivery_charges_paise = item.get("delivery_charges_paise")
            existing.moq = item["moq"]
            existing.case_size = item["case_size"]
            existing.supplier_id = suppliers[supplier_name].id
            listing_by_external[item["external_id"]] = existing
            continue
        listing = MarketplaceListing(
            provider_id=demo.id,
            supplier_id=suppliers[supplier_name].id,
            external_product_id=item["external_id"],
            title=item["title"],
            brand=item.get("brand"),
            package_quantity=item["package_quantity"],
            unit=item["unit"],
            moq=item["moq"],
            case_size=item["case_size"],
            base_price_paise=item["base_price_paise"],
            gst_percent=item.get("gst_percent"),
            delivery_charges_paise=item.get("delivery_charges_paise"),
            stock_status="in_stock",
            delivery_estimate_days=item.get("delivery_estimate_days"),
            product_url=item.get("product_url"),
            price_source="demonstration",
        )
        db.add(listing)
        await db.flush()
        listing_by_external[item["external_id"]] = listing

    await db.commit()

    if shop_id is not None:
        await seed_default_stars(db, shop_id, listing_by_external)


async def seed_default_stars(db: AsyncSession, shop_id, listing_by_external: dict | None = None) -> None:
    """Star a few provision staples so Market home shows fare watches."""
    if listing_by_external is None:
        demo = (
            await db.execute(
                select(MarketplaceProvider).where(MarketplaceProvider.code == "demo_catalogue")
            )
        ).scalar_one_or_none()
        if not demo:
            return
        listing_by_external = {}
        rows = (
            await db.execute(
                select(MarketplaceListing).where(MarketplaceListing.provider_id == demo.id)
            )
        ).scalars().all()
        for row in rows:
            listing_by_external[row.external_product_id] = row

    for external_id in DEFAULT_STAR_EXTERNAL_IDS:
        listing = listing_by_external.get(external_id)
        if not listing:
            continue
        exists = (
            await db.execute(
                select(StarredListing).where(
                    StarredListing.shop_id == shop_id,
                    StarredListing.listing_id == listing.id,
                )
            )
        ).scalar_one_or_none()
        if exists:
            continue
        db.add(
            StarredListing(
                shop_id=shop_id,
                listing_id=listing.id,
                starred_price_paise=listing.base_price_paise,
                note="Seeded fare watch",
            )
        )
    await db.commit()
