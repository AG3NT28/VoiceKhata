"""Pydantic schemas for marketplace API."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProductParseResult(BaseModel):
    product_name: str
    brand: Optional[str] = None
    variant: Optional[str] = None
    category: Optional[str] = None
    requested_quantity: float = 1.0
    unit: str = "kg"
    purchase_type: str = "wholesale"
    barcode: Optional[str] = None
    raw_query: str = ""


class ProviderStatusOut(BaseModel):
    code: str
    name: str
    category: str
    status: str
    enabled: bool
    auth_notes: Optional[str] = None
    live_data: bool = False
    redirect_capable: bool = False


class OfferOut(BaseModel):
    offer_id: UUID
    product_id: Optional[UUID] = None
    provider_code: str
    provider_name: str
    supplier_name: Optional[str] = None
    title: str
    brand: Optional[str] = None
    package_quantity: float
    unit: str
    moq: int
    case_size: int
    base_price_paise: int
    base_price_rupees: float
    gst_percent: Optional[float] = None
    delivery_charges_paise: Optional[int] = None
    delivery_charges_rupees: Optional[float] = None
    discount_paise: int = 0
    platform_fee_paise: int = 0
    landed_cost_paise: Optional[int] = None
    landed_cost_rupees: Optional[float] = None
    effective_unit_paise: Optional[int] = None
    effective_unit_rupees: Optional[float] = None
    comparable_quantity: float
    stock_status: str
    delivery_estimate_days: Optional[int] = None
    price_source: str
    price_complete: bool
    match_confidence: float = 0.0
    last_updated: datetime
    has_redirect: bool = False
    notice: str = "Confirm final price, availability and delivery on the supplier platform."


class RankedBuckets(BaseModel):
    lowest_unit_price: list[OfferOut] = Field(default_factory=list)
    best_bulk_deal: list[OfferOut] = Field(default_factory=list)
    fastest_delivery: list[OfferOut] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    purchase_type: Optional[str] = "wholesale"
    providers: Optional[list[str]] = None


class SearchResponse(BaseModel):
    query: str
    parsed: ProductParseResult
    offers: list[OfferOut]
    rankings: RankedBuckets
    providers_queried: list[ProviderStatusOut]
    data_disclaimer: str = (
        "Results may include demonstration or imported catalogue data. "
        "Live marketplace prices require partner API access."
    )


class CompareRequest(BaseModel):
    offer_ids: list[UUID] = Field(..., min_length=1, max_length=20)


class CompareResponse(BaseModel):
    offers: list[OfferOut]
    rankings: RankedBuckets


class RedirectResponse(BaseModel):
    offer_id: UUID
    destination_url: str
    provider_code: str
    recorded: bool
    notice: str


class ImportReport(BaseModel):
    imported: int
    rejected: int
    errors: list[dict[str, Any]] = Field(default_factory=list)


class HistoryItem(BaseModel):
    id: UUID
    query_text: str
    result_count: int
    created_at: datetime


class HistoryResponse(BaseModel):
    items: list[HistoryItem]


class StarredOfferOut(BaseModel):
    star_id: UUID
    offer_id: UUID
    title: str
    brand: Optional[str] = None
    supplier_name: Optional[str] = None
    package_quantity: float
    unit: str
    starred_price_paise: int
    starred_price_rupees: float
    current_price_paise: int
    current_price_rupees: float
    delta_paise: int
    delta_rupees: float
    price_source: str
    stock_status: str
    last_updated: datetime
    note: Optional[str] = None


class StarToggleResponse(BaseModel):
    offer_id: UUID
    starred: bool
    star: Optional[StarredOfferOut] = None


class ProductDetailResponse(BaseModel):
    product_id: UUID
    name: str
    brand: Optional[str]
    category: Optional[str]
    variant: Optional[str]
    package_quantity: float
    unit: str
    offers: list[OfferOut]
