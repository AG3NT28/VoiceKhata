"""Provider adapters. Live connectors require partner credentials."""
from __future__ import annotations

from app.marketplace.providers.base import MarketplaceProviderAdapter
from app.marketplace.providers.bigbasket import BigBasketProvider
from app.marketplace.providers.blinkit import BlinkitProvider
from app.marketplace.providers.demo_catalogue import DemoCatalogueProvider
from app.marketplace.providers.jiomart import JioMartProvider
from app.marketplace.providers.jumbotail import JumbotailProvider
from app.marketplace.providers.ondc import OndcProvider
from app.marketplace.providers.udaan import UdaanProvider
from app.marketplace.providers.wholesale import IndependentWholesaleProvider
from app.marketplace.providers.wishbee import WishbeeProvider


def all_providers() -> list[MarketplaceProviderAdapter]:
    return [
        DemoCatalogueProvider(),
        IndependentWholesaleProvider(),
        JumbotailProvider(),
        WishbeeProvider(),
        UdaanProvider(),
        OndcProvider(),
        BlinkitProvider(),
        BigBasketProvider(),
        JioMartProvider(),
    ]


def providers_by_code() -> dict[str, MarketplaceProviderAdapter]:
    return {p.code: p for p in all_providers()}
