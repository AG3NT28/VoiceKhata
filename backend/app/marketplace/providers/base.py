"""Common provider adapter interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderProduct:
    external_id: str
    title: str
    brand: str | None = None
    variant: str | None = None
    package_quantity: float = 1.0
    unit: str = "kg"
    moq: int = 1
    case_size: int = 1
    base_price_paise: int = 0
    gst_percent: float | None = None
    delivery_charges_paise: int | None = None
    discount_paise: int = 0
    platform_fee_paise: int = 0
    stock_status: str = "in_stock"
    delivery_estimate_days: int | None = None
    product_url: str | None = None
    price_source: str = "demonstration"
    supplier_name: str | None = None
    barcode: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderStatus:
    code: str
    name: str
    category: str
    status: str  # LIVE | PARTNER_ACCESS_REQUIRED | DISABLED | ERROR
    enabled: bool = True
    auth_notes: str | None = None
    live_data: bool = False
    redirect_capable: bool = False


class MarketplaceProviderAdapter(ABC):
    code: str = "base"
    name: str = "Base"
    category: str = "wholesale"

    @abstractmethod
    async def search_products(self, query: str, *, parsed: Any = None) -> list[ProviderProduct]:
        ...

    async def get_product_details(self, external_id: str) -> ProviderProduct | None:
        return None

    async def get_redirect_url(self, external_id: str) -> str | None:
        return None

    def get_provider_status(self) -> ProviderStatus:
        return ProviderStatus(
            code=self.code,
            name=self.name,
            category=self.category,
            status="PARTNER_ACCESS_REQUIRED",
            enabled=True,
            auth_notes="Official partner credentials required. No public product API assumed.",
            live_data=False,
            redirect_capable=False,
        )
