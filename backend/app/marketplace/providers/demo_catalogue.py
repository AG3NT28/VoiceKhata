"""Seeded provision-store wholesale catalogue — demonstration data only (no live APIs)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.marketplace.models import MarketplaceListing, MarketplaceProvider
from app.marketplace.providers.base import MarketplaceProviderAdapter, ProviderProduct, ProviderStatus


def _p(
    external_id: str,
    title: str,
    brand: str | None,
    package_quantity: float,
    unit: str,
    base_price_paise: int,
    *,
    variant: str | None = None,
    moq: int = 10,
    case_size: int = 1,
    gst_percent: float = 5.0,
    delivery_charges_paise: int = 10000,
    delivery_estimate_days: int = 2,
    supplier_name: str = "Kirana Wholesale Hub",
    category: str = "groceries",
) -> dict:
    return {
        "external_id": external_id,
        "title": title,
        "brand": brand,
        "variant": variant,
        "category": category,
        "package_quantity": package_quantity,
        "unit": unit,
        "moq": moq,
        "case_size": case_size,
        "base_price_paise": base_price_paise,
        "gst_percent": gst_percent,
        "delivery_charges_paise": delivery_charges_paise,
        "delivery_estimate_days": delivery_estimate_days,
        "product_url": f"https://example.com/demo/{external_id}",
        "supplier_name": supplier_name,
    }


# Rich kirana / provision-store seed — shown only via search, never as a default dump.
DEMO_PRODUCTS = [
    # Oils
    _p("demo-fortune-sf-1l", "Fortune Sunflower Oil 1L", "Fortune", 1, "l", 14500, variant="Sunflower", moq=12, case_size=12, supplier_name="Oil Traders Pune", category="edible_oils"),
    _p("demo-fortune-sf-5l", "Fortune Sunflower Oil 5L", "Fortune", 5, "l", 68000, variant="Sunflower", moq=4, case_size=4, supplier_name="Oil Traders Pune", category="edible_oils"),
    _p("demo-fortune-sf-15l", "Fortune Sunflower Oil 15L", "Fortune", 15, "l", 189000, variant="Sunflower", moq=2, case_size=2, delivery_charges_paise=25000, supplier_name="Oil Traders Pune", category="edible_oils"),
    _p("demo-fortune-gn-1l", "Fortune Groundnut Oil 1L", "Fortune", 1, "l", 17200, variant="Groundnut", moq=12, case_size=12, supplier_name="Oil Traders Pune", category="edible_oils"),
    _p("demo-saffola-gold-1l", "Saffola Gold Oil 1L", "Saffola", 1, "l", 19800, variant="Blended", moq=12, case_size=12, supplier_name="Oil Traders Pune", category="edible_oils"),
    _p("demo-dhara-mustard-1l", "Dhara Mustard Oil 1L", "Dhara", 1, "l", 16800, variant="Mustard", moq=12, case_size=12, supplier_name="Oil Traders Pune", category="edible_oils"),
    # Atta / flour
    _p("demo-aashirvaad-atta-5kg", "Aashirvaad Atta 5kg", "Aashirvaad", 5, "kg", 26500, moq=10, case_size=5, supplier_name="Grain Depot", category="wheat_flour"),
    _p("demo-aashirvaad-atta-10kg", "Aashirvaad Atta 10kg", "Aashirvaad", 10, "kg", 51000, moq=5, case_size=5, supplier_name="Grain Depot", category="wheat_flour"),
    _p("demo-aashirvaad-select-5kg", "Aashirvaad Select Atta 5kg", "Aashirvaad", 5, "kg", 29500, variant="Select", moq=8, case_size=4, supplier_name="Grain Depot", category="wheat_flour"),
    _p("demo-patajali-atta-5kg", "Patanjali Atta 5kg", "Patanjali", 5, "kg", 23000, moq=10, case_size=5, supplier_name="Grain Depot", category="wheat_flour"),
    # Rice
    _p("demo-india-gate-rice-5kg", "India Gate Basmati Rice 5kg", "India Gate", 5, "kg", 62000, variant="Basmati", moq=8, case_size=4, supplier_name="Grain Depot", category="rice"),
    _p("demo-india-gate-rice-1kg", "India Gate Basmati Rice 1kg", "India Gate", 1, "kg", 14500, variant="Basmati", moq=20, case_size=10, supplier_name="Grain Depot", category="rice"),
    _p("demo-sona-masoori-25kg", "Sona Masoori Rice 25kg", None, 25, "kg", 145000, variant="Sona Masoori", moq=2, case_size=1, delivery_charges_paise=30000, supplier_name="Rice Mill Nashik", category="rice"),
    _p("demo-kolam-rice-10kg", "Kolam Rice 10kg", None, 10, "kg", 52000, variant="Kolam", moq=5, case_size=5, supplier_name="Rice Mill Nashik", category="rice"),
    # Sugar / salt
    _p("demo-madhur-sugar-1kg", "Madhur Sugar 1kg", "Madhur", 1, "kg", 4600, moq=24, case_size=24, supplier_name="Kirana Wholesale Hub", category="sugar"),
    _p("demo-madhur-sugar-5kg", "Madhur Sugar 5kg", "Madhur", 5, "kg", 22000, moq=10, case_size=5, supplier_name="Kirana Wholesale Hub", category="sugar"),
    _p("demo-tata-salt-1kg", "Tata Salt 1kg", "Tata", 1, "kg", 2800, moq=24, case_size=24, delivery_estimate_days=1, supplier_name="Kirana Wholesale Hub", category="salt"),
    # Pulses
    _p("demo-toor-dal-1kg", "Toor Dal 1kg", None, 1, "kg", 14500, moq=20, case_size=10, supplier_name="Dal Mandi", category="pulses"),
    _p("demo-moong-dal-1kg", "Moong Dal 1kg", None, 1, "kg", 12800, moq=20, case_size=10, supplier_name="Dal Mandi", category="pulses"),
    _p("demo-chana-dal-1kg", "Chana Dal 1kg", None, 1, "kg", 9800, moq=20, case_size=10, supplier_name="Dal Mandi", category="pulses"),
    _p("demo-urad-dal-1kg", "Urad Dal 1kg", None, 1, "kg", 13200, moq=15, case_size=10, supplier_name="Dal Mandi", category="pulses"),
    # Spices
    _p("demo-everest-turmeric-200g", "Everest Turmeric Powder 200g", "Everest", 0.2, "kg", 5200, moq=24, case_size=24, supplier_name="Masala Mart", category="spices"),
    _p("demo-everest-chilli-200g", "Everest Red Chilli Powder 200g", "Everest", 0.2, "kg", 6100, moq=24, case_size=24, supplier_name="Masala Mart", category="spices"),
    _p("demo-mdh-garam-100g", "MDH Garam Masala 100g", "MDH", 0.1, "kg", 4800, moq=36, case_size=36, supplier_name="Masala Mart", category="spices"),
    # Packaged / biscuits / beverages
    _p("demo-parle-g-800g", "Parle-G Glucose Biscuits 800g", "Parle", 0.8, "kg", 5500, moq=20, case_size=20, supplier_name="FMCG Depot", category="biscuits"),
    _p("demo-britannia-goodday-600g", "Britannia Good Day 600g", "Britannia", 0.6, "kg", 7800, moq=16, case_size=16, supplier_name="FMCG Depot", category="biscuits"),
    _p("demo-tata-tea-500g", "Tata Tea Gold 500g", "Tata", 0.5, "kg", 28500, moq=12, case_size=12, supplier_name="FMCG Depot", category="beverages"),
    _p("demo-red-label-1kg", "Brooke Bond Red Label 1kg", "Brooke Bond", 1, "kg", 48000, moq=8, case_size=8, supplier_name="FMCG Depot", category="beverages"),
    _p("demo-nescafe-classic-200g", "Nescafe Classic 200g", "Nestle", 0.2, "kg", 42000, moq=12, case_size=12, supplier_name="FMCG Depot", category="beverages"),
    # Dairy
    _p("demo-amul-ghee-1l", "Amul Ghee 1L", "Amul", 1, "l", 58000, moq=6, case_size=6, gst_percent=12.0, supplier_name="Dairy Hub", category="dairy"),
    _p("demo-amul-butter-500g", "Amul Butter 500g", "Amul", 0.5, "kg", 28500, moq=12, case_size=12, gst_percent=12.0, supplier_name="Dairy Hub", category="dairy"),
    _p("demo-amul-milk-1l", "Amul Taaza Milk 1L", "Amul", 1, "l", 6200, moq=24, case_size=12, gst_percent=5.0, delivery_estimate_days=1, supplier_name="Dairy Hub", category="dairy"),
    # Personal care / cleaning
    _p("demo-lux-soap-3x150", "Lux Soap 3x150g", "Lux", 3, "pcs", 9500, moq=16, case_size=16, gst_percent=18.0, supplier_name="Home Care Depot", category="personal_care"),
    _p("demo-surf-excel-1kg", "Surf Excel Easy Wash 1kg", "Surf Excel", 1, "kg", 18500, moq=12, case_size=12, gst_percent=18.0, supplier_name="Home Care Depot", category="cleaning"),
    _p("demo-vim-bar-300g", "Vim Dishwash Bar 300g", "Vim", 0.3, "kg", 2800, moq=36, case_size=36, gst_percent=18.0, supplier_name="Home Care Depot", category="cleaning"),
    _p("demo-harpic-1l", "Harpic Power Plus 1L", "Harpic", 1, "l", 14500, moq=12, case_size=12, gst_percent=18.0, supplier_name="Home Care Depot", category="cleaning"),
    # Competing wholesale quotes (same SKU, different supplier) for fare compare
    _p("demo-fortune-sf-1l-b", "Fortune Sunflower Oil 1L", "Fortune", 1, "l", 13900, variant="Sunflower", moq=24, case_size=12, delivery_charges_paise=15000, delivery_estimate_days=3, supplier_name="City Cash & Carry", category="edible_oils"),
    _p("demo-aashirvaad-atta-5kg-b", "Aashirvaad Atta 5kg", "Aashirvaad", 5, "kg", 25500, moq=20, case_size=10, delivery_charges_paise=18000, delivery_estimate_days=2, supplier_name="City Cash & Carry", category="wheat_flour"),
    _p("demo-tata-salt-1kg-b", "Tata Salt 1kg", "Tata", 1, "kg", 2650, moq=48, case_size=24, delivery_charges_paise=8000, delivery_estimate_days=2, supplier_name="City Cash & Carry", category="salt"),
]


class DemoCatalogueProvider(MarketplaceProviderAdapter):
    code = "demo_catalogue"
    name = "VoiceKhata Provision Seed"
    category = "demonstration"

    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    def get_provider_status(self) -> ProviderStatus:
        return ProviderStatus(
            code=self.code,
            name=self.name,
            category=self.category,
            status="DEMONSTRATION",
            enabled=True,
            auth_notes="Seeded provision-store wholesale offers for local testing. Not live marketplace APIs.",
            live_data=False,
            redirect_capable=True,
        )

    async def search_products(self, query: str, *, parsed: Any = None) -> list[ProviderProduct]:
        # Require a real query — never dump the full catalogue on empty search.
        if not (query or "").strip():
            return []
        if self.db is not None:
            from_db = await self._search_db(query, parsed)
            if from_db:
                return from_db
        return self._search_memory(query, parsed)

    async def _search_db(self, query: str, parsed: Any) -> list[ProviderProduct]:
        provider = (
            await self.db.execute(
                select(MarketplaceProvider).where(MarketplaceProvider.code == self.code)
            )
        ).scalar_one_or_none()
        if not provider:
            return []

        q = select(MarketplaceListing).where(MarketplaceListing.provider_id == provider.id)
        tokens = []
        if parsed is not None:
            tokens = [t for t in [parsed.brand, parsed.variant, parsed.product_name, parsed.category] if t]
        if not tokens:
            tokens = [w for w in (query or "").split() if len(w) > 2]
        if not tokens:
            return []
        clauses = []
        for token in tokens[:8]:
            like = f"%{token}%"
            clauses.append(MarketplaceListing.title.ilike(like))
            clauses.append(MarketplaceListing.brand.ilike(like))
        q = q.where(or_(*clauses))
        rows = (await self.db.execute(q.limit(40))).scalars().all()
        return [self._to_product(row) for row in rows]

    def _search_memory(self, query: str, parsed: Any) -> list[ProviderProduct]:
        keys = []
        if parsed is not None:
            keys = [x.lower() for x in [parsed.brand, parsed.variant, parsed.product_name, parsed.category] if x]
        if not keys:
            keys = [w for w in (query or "").lower().split() if len(w) > 2]
        if not keys:
            return []
        out: list[ProviderProduct] = []
        for item in DEMO_PRODUCTS:
            blob = f"{item['title']} {item.get('brand') or ''} {item.get('variant') or ''} {item.get('category') or ''}".lower()
            if any(k in blob for k in keys):
                out.append(self._dict_to_product(item))
        return out

    def _dict_to_product(self, item: dict) -> ProviderProduct:
        return ProviderProduct(
            external_id=item["external_id"],
            title=item["title"],
            brand=item.get("brand"),
            variant=item.get("variant"),
            package_quantity=item["package_quantity"],
            unit=item["unit"],
            moq=item["moq"],
            case_size=item["case_size"],
            base_price_paise=item["base_price_paise"],
            gst_percent=item.get("gst_percent"),
            delivery_charges_paise=item.get("delivery_charges_paise"),
            delivery_estimate_days=item.get("delivery_estimate_days"),
            product_url=item.get("product_url"),
            price_source="demonstration",
            supplier_name=item.get("supplier_name"),
        )

    def _to_product(self, row: MarketplaceListing) -> ProviderProduct:
        return ProviderProduct(
            external_id=row.external_product_id,
            title=row.title,
            brand=row.brand,
            variant=None,
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
            price_source=row.price_source,
            supplier_name=None,
        )

    async def get_redirect_url(self, external_id: str) -> str | None:
        for item in DEMO_PRODUCTS:
            if item["external_id"] == external_id:
                return item.get("product_url")
        return None
