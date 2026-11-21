"""REST API for SQLite stock / inventory (prefix /stock)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.security.auth import get_current_shop_id
from app.stock import service as stock_service
from app.utils.paise import rupees_to_paise

router = APIRouter(prefix="/stock", tags=["stock"])


class StockItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    category: str | None = Field(None, max_length=60)
    quantity: int = Field(0, ge=0)
    unit_price_paise: int | None = Field(None, ge=0)
    unit_price_rupees: float | None = Field(None, ge=0)
    minimum_quantity: int = Field(5, ge=0)
    supplier: str | None = Field(None, max_length=120)
    barcode: str | None = Field(None, max_length=64)
    notes: str | None = None


class StockQtyBody(BaseModel):
    quantity: int = Field(..., gt=0)
    reason: str | None = Field(None, max_length=200)


class StockAdjustBody(BaseModel):
    delta: int = Field(...)
    reason: str | None = Field(None, max_length=200)


class StockItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    shop_id: UUID
    name: str
    category: str | None = None
    quantity: int
    unit_price_paise: int
    unit_price_rupees: float
    minimum_quantity: int
    supplier: str | None = None
    barcode: str | None = None
    notes: str | None = None
    status: str
    low_stock: bool
    last_restocked: datetime | None = None
    created_at: datetime
    updated_at: datetime


class StockLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    item_id: UUID
    type: str
    quantity: int
    reason: str | None = None
    reference_id: UUID | None = None
    created_at: datetime


class StockSummaryResponse(BaseModel):
    total_items: int
    total_quantity: int
    low_stock_count: int
    by_category: dict


def _price_paise(payload: StockItemCreate) -> int:
    if payload.unit_price_paise is not None:
        return payload.unit_price_paise
    if payload.unit_price_rupees is not None:
        return rupees_to_paise(payload.unit_price_rupees)
    return 0


@router.post("", response_model=StockItemResponse, status_code=201)
async def create_stock_item(
    payload: StockItemCreate,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    item = await stock_service.create_item(
        db,
        shop_id,
        name=payload.name,
        category=payload.category,
        quantity=payload.quantity,
        unit_price_paise=_price_paise(payload),
        minimum_quantity=payload.minimum_quantity,
        supplier=payload.supplier,
        barcode=payload.barcode,
        notes=payload.notes,
    )
    return stock_service.item_to_dict(item)


@router.get("", response_model=list[StockItemResponse])
async def list_stock(
    category: str | None = Query(None),
    search: str | None = Query(None),
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    items = await stock_service.list_items(db, shop_id, category=category, search=search)
    return [stock_service.item_to_dict(i) for i in items]


@router.get("/summary", response_model=StockSummaryResponse)
async def get_stock_summary(
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    return await stock_service.stock_summary(db, shop_id)


@router.get("/{item_id}", response_model=StockItemResponse)
async def get_stock_item(
    item_id: UUID,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    item = await stock_service.get_item(db, shop_id, item_id)
    return stock_service.item_to_dict(item)


@router.get("/{item_id}/log", response_model=list[StockLogResponse])
async def get_stock_log(
    item_id: UUID,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    logs = await stock_service.get_item_log(db, shop_id, item_id)
    return [
        {
            "id": log.id,
            "item_id": log.item_id,
            "type": log.type.value if hasattr(log.type, "value") else str(log.type),
            "quantity": log.quantity,
            "reason": log.reason,
            "reference_id": log.reference_id,
            "created_at": log.created_at,
        }
        for log in logs
    ]


@router.post("/{item_id}/add", response_model=StockItemResponse)
async def add_stock(
    item_id: UUID,
    payload: StockQtyBody,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    item = await stock_service.add_stock(
        db, shop_id, item_id, payload.quantity, payload.reason
    )
    return stock_service.item_to_dict(item)


@router.post("/{item_id}/remove", response_model=StockItemResponse)
async def remove_stock(
    item_id: UUID,
    payload: StockQtyBody,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    item = await stock_service.remove_stock(
        db, shop_id, item_id, payload.quantity, payload.reason
    )
    return stock_service.item_to_dict(item)


@router.post("/{item_id}/adjust", response_model=StockItemResponse)
async def adjust_stock(
    item_id: UUID,
    payload: StockAdjustBody,
    shop_id: UUID = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    item = await stock_service.adjust_stock(
        db, shop_id, item_id, payload.delta, payload.reason
    )
    return stock_service.item_to_dict(item)
