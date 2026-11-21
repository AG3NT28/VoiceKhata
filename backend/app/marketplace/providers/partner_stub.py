"""Shared stub for providers without authorized API access."""
from __future__ import annotations

from typing import Any

from app.marketplace.providers.base import MarketplaceProviderAdapter, ProviderProduct, ProviderStatus


class PartnerAccessStub(MarketplaceProviderAdapter):
    code = "stub"
    name = "Stub"
    category = "wholesale"
    notes = (
        "No public product-search API is assumed. "
        "Partner onboarding / credentials required before live catalogue access."
    )

    async def search_products(self, query: str, *, parsed: Any = None) -> list[ProviderProduct]:
        return []

    def get_provider_status(self) -> ProviderStatus:
        return ProviderStatus(
            code=self.code,
            name=self.name,
            category=self.category,
            status="PARTNER_ACCESS_REQUIRED",
            enabled=True,
            auth_notes=self.notes,
            live_data=False,
            redirect_capable=False,
        )
