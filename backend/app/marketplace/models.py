"""Marketplace SQLAlchemy models (isolated from ledger tables)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import Base


class MarketplaceProvider(Base):
    __tablename__ = "marketplace_providers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40), default="wholesale")
    status: Mapped[str] = mapped_column(String(40), default="PARTNER_ACCESS_REQUIRED")
    auth_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_domains: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    listings: Mapped[list["MarketplaceListing"]] = relationship(back_populates="provider")


class CanonicalProduct(Base):
    __tablename__ = "marketplace_canonical_products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), index=True)
    brand: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    variant: Mapped[str | None] = mapped_column(String(80), nullable=True)
    package_quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit: Mapped[str] = mapped_column(String(20), default="kg")
    barcode: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    normalized_key: Mapped[str] = mapped_column(String(240), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    listings: Mapped[list["MarketplaceListing"]] = relationship(back_populates="canonical_product")


class SupplierProfile(Base):
    __tablename__ = "marketplace_suppliers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shops.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    provider_code: Mapped[str] = mapped_column(String(40), default="independent_wholesale")
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    contact: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    listings: Mapped[list["MarketplaceListing"]] = relationship(back_populates="supplier")


class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"
    __table_args__ = (
        UniqueConstraint("provider_id", "external_product_id", name="uq_provider_external_product"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shops.id"), nullable=True, index=True)
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("marketplace_providers.id"), index=True)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("marketplace_suppliers.id"), nullable=True, index=True
    )
    canonical_product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("marketplace_canonical_products.id"), nullable=True, index=True
    )
    external_product_id: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(240))
    brand: Mapped[str | None] = mapped_column(String(80), nullable=True)
    package_quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit: Mapped[str] = mapped_column(String(20), default="kg")
    moq: Mapped[int] = mapped_column(Integer, default=1)
    case_size: Mapped[int] = mapped_column(Integer, default=1)
    base_price_paise: Mapped[int] = mapped_column(BigInteger)
    gst_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivery_charges_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    discount_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    platform_fee_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    stock_status: Mapped[str] = mapped_column(String(40), default="in_stock")
    delivery_estimate_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_source: Mapped[str] = mapped_column(String(40), default="demonstration")
    # demonstration | imported | cached | live
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    provider: Mapped["MarketplaceProvider"] = relationship(back_populates="listings")
    supplier: Mapped["SupplierProfile | None"] = relationship(back_populates="listings")
    canonical_product: Mapped["CanonicalProduct | None"] = relationship(back_populates="listings")
    snapshots: Mapped[list["PriceSnapshot"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )


class PriceSnapshot(Base):
    __tablename__ = "marketplace_price_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("marketplace_listings.id"), index=True)
    base_price_paise: Mapped[int] = mapped_column(BigInteger)
    landed_cost_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    effective_unit_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source: Mapped[str] = mapped_column(String(40), default="demonstration")

    listing: Mapped["MarketplaceListing"] = relationship(back_populates="snapshots")


class SearchHistory(Base):
    __tablename__ = "marketplace_search_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), index=True)
    query_text: Mapped[str] = mapped_column(Text)
    parsed_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RedirectEvent(Base):
    __tablename__ = "marketplace_redirect_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("marketplace_listings.id"), index=True)
    destination_url: Mapped[str] = mapped_column(Text)
    provider_code: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StarredListing(Base):
    """Shopkeeper fare watchlist — monitor wholesale prices for starred stock."""
    __tablename__ = "marketplace_starred_listings"
    __table_args__ = (
        UniqueConstraint("shop_id", "listing_id", name="uq_shop_starred_listing"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("marketplace_listings.id"), index=True)
    starred_price_paise: Mapped[int] = mapped_column(BigInteger)
    note: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
