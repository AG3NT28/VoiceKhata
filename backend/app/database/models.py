from __future__ import annotations

import uuid
import enum
from datetime import datetime, date
from sqlalchemy import (
    String, BigInteger, Integer, Date, DateTime, Enum, ForeignKey, UniqueConstraint, Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class TxnType(str, enum.Enum):
    credit = "credit"
    payment = "payment"

class TxnStatus(str, enum.Enum):
    active = "active"
    reversed = "reversed"
    voided = "voided"

class CustomerStatus(str, enum.Enum):
    active = "active"
    archived = "archived"

class StockLogType(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUST = "ADJUST"

class ItemStatus(str, enum.Enum):
    active = "active"
    archived = "archived"

class Shop(Base):
    __tablename__ = "shops"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    timezone: Mapped[str] = mapped_column(String(40), default="Asia/Kolkata")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customers: Mapped[list["Customer"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    inventory_items: Mapped[list["InventoryItem"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    items: Mapped[list["Item"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    stock_logs: Mapped[list["StockLog"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    login_state: Mapped["ShopLoginState | None"] = relationship(
        back_populates="shop", uselist=False, cascade="all, delete-orphan"
    )


class ShopLoginState(Base):
    """Tracks which shop email currently owns the shared demo ledger."""
    __tablename__ = "shop_login_state"
    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), primary_key=True)
    active_email: Mapped[str] = mapped_column(String(254), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shop: Mapped["Shop"] = relationship(back_populates="login_state")

class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    normalized_name: Mapped[str] = mapped_column(String(120), index=True)
    customer_code: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), default=CustomerStatus.active.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shop: Mapped["Shop"] = relationship(back_populates="customers")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="customer")

    __table_args__ = (
        UniqueConstraint("shop_id", "normalized_name", name="uq_shop_customer_name"),
        UniqueConstraint("shop_id", "customer_code", name="uq_shop_customer_code"),
    )

class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    type: Mapped[TxnType] = mapped_column(Enum(TxnType))
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    txn_date: Mapped[date] = mapped_column(Date)
    status: Mapped[TxnStatus] = mapped_column(Enum(TxnStatus), default=TxnStatus.active)
    reversed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    supersedes: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    raw_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_confidence: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    shop: Mapped["Shop"] = relationship(back_populates="transactions")
    customer: Mapped["Customer"] = relationship(back_populates="transactions")

class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), index=True)
    actor: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    sku: Mapped[str | None] = mapped_column(String(40), nullable=True)
    unit: Mapped[str] = mapped_column(String(20), default="pcs")
    quantity: Mapped[int] = mapped_column(default=0)
    reorder_level: Mapped[int] = mapped_column(default=5)
    unit_cost_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shop: Mapped["Shop"] = relationship(back_populates="inventory_items")
    quotes: Mapped[list["WholesaleQuote"]] = relationship(back_populates="item", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("shop_id", "name", name="uq_shop_inventory_name"),
    )


class WholesaleQuote(Base):
    __tablename__ = "wholesale_quotes"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inventory_items.id"), index=True)
    source: Mapped[str] = mapped_column(String(40))  # jumbotail | flipkart | amazon | manual
    price_paise: Mapped[int] = mapped_column(BigInteger)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    item: Mapped["InventoryItem"] = relationship(back_populates="quotes")


class Item(Base):
    """Canonical stock product in shared SQLite DB (voice_khata.db)."""
    __tablename__ = "items"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    unit_price_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    minimum_quantity: Mapped[int] = mapped_column(Integer, default=5)
    supplier: Mapped[str | None] = mapped_column(String(120), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ItemStatus.active.value)
    last_restocked: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shop: Mapped["Shop"] = relationship(back_populates="items")
    logs: Mapped[list["StockLog"]] = relationship(back_populates="item", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("shop_id", "name", name="uq_shop_item_name"),
    )


class StockLog(Base):
    """Append-only audit trail for stock changes."""
    __tablename__ = "stock_logs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), index=True)
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("items.id"), index=True)
    type: Mapped[StockLogType] = mapped_column(Enum(StockLogType))
    quantity: Mapped[int] = mapped_column(Integer)  # signed delta
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    shop: Mapped["Shop"] = relationship(back_populates="stock_logs")
    item: Mapped["Item"] = relationship(back_populates="logs")
