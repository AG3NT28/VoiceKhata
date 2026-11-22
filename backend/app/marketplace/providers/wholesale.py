"""Independent wholesaler / distributor / brand-authorized imported catalogues."""
from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.marketplace.models import MarketplaceListing, MarketplaceProvider, SupplierProfile
from app.marketplace.providers.base import MarketplaceProviderAdapter, ProviderProduct, ProviderStatus


class IndependentWholesaleProvider(MarketplaceProviderAdapter):
    code = "independent_wholesale"
    name = "Independent Wholesalers"
    category = "wholesale"

    def __init__(self, db: AsyncSession | None = None, shop_id=None):
        self.db = db
        self.shop_id = shop_id

    def get_provider_status(self) -> ProviderStatus:
        return ProviderStatus(
            code=self.code,
            name=self.name,
            category=self.category,
            status="IMPORT_READY",
            enabled=True,
            auth_notes="Uses shopkeeper-imported CSV/Excel catalogues. Not live marketplace scrapes.",
            live_data=False,
            redirect_capable=True,
        )

    async def search_products(self, query: str, *, parsed: Any = None) -> list[ProviderProduct]:
        if self.db is None:
            return []
        provider = (
            await self.db.execute(
                select(MarketplaceProvider).where(MarketplaceProvider.code == self.code)
            )
        ).scalar_one_or_none()
        if not provider:
            return []

        q = select(MarketplaceListing).where(
            MarketplaceListing.provider_id == provider.id,
            MarketplaceListing.price_source == "imported",
        )
        if self.shop_id is not None:
            q = q.where(
                or_(
                    MarketplaceListing.shop_id == self.shop_id,
                    MarketplaceListing.shop_id.is_(None),
                )
            )
        tokens = []
        if parsed is not None:
            tokens = [t for t in [parsed.brand, parsed.product_name, parsed.variant] if t]
        if not tokens:
            tokens = [w for w in (query or "").split() if len(w) > 2]
        if tokens:
            clauses = []
            for token in tokens[:6]:
                like = f"%{token}%"
                clauses.append(MarketplaceListing.title.ilike(like))
                clauses.append(MarketplaceListing.brand.ilike(like))
            q = q.where(or_(*clauses))

        rows = (await self.db.execute(q.limit(50))).scalars().all()
        out: list[ProviderProduct] = []
        for row in rows:
            supplier_name = None
            if row.supplier_id:
                supplier = await self.db.get(SupplierProfile, row.supplier_id)
                supplier_name = supplier.name if supplier else None
            out.append(
                ProviderProduct(
                    external_id=row.external_product_id,
                    title=row.title,
                    brand=row.brand,
                    package_quantity=row.package_quantity,
                    unit=row.unit,
                    moq=row.moq,
                    case_size=row.case_size,
                    base_price_paise=row.base_price_paise,
                    gst_percent=row.gst_percent,
                    delivery_charges_paise=row.delivery_charges_paise,
                    discount_paise=row.discount_paise,
                    platform_fee_paise=row.platform_fee_paise,
                    stock_status=row.stock_status,
                    delivery_estimate_days=row.delivery_estimate_days,
                    product_url=row.product_url,
                    price_source="imported",
                    supplier_name=supplier_name,
                )
            )
        return out
