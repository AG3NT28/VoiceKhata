import uuid
import enum
from datetime import datetime, date
from sqlalchemy import (
    String, BigInteger, Date, DateTime, Enum, ForeignKey, UniqueConstraint, Text,
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

class Shop(Base):
    __tablename__ = "shops"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    timezone: Mapped[str] = mapped_column(String(40), default="Asia/Kolkata")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customers: Mapped[list["Customer"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="shop", cascade="all, delete-orphan")

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
