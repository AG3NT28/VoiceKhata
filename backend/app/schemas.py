from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

# ---------- Auth ----------
class RegisterShopRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=4)
    timezone: str = "Asia/Kolkata"

class LoginRequest(BaseModel):
    shop_id: UUID
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    shop_id: UUID
    shop_name: str

# ---------- Customer ----------
class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    phone: Optional[str] = Field(None, max_length=20)

class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    phone: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = Field(None, pattern="^(active|archived)$")

class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    shop_id: UUID
    name: str
    phone: Optional[str]
    customer_code: str
    normalized_name: str
    status: str
    created_at: datetime
    updated_at: datetime

class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]
    total: int
    limit: int
    offset: int

# ---------- Transaction ----------
class TransactionCreate(BaseModel):
    customer_id: Optional[UUID] = None
    customer_code: Optional[str] = None
    type: str = Field(..., pattern="^(credit|payment)$")
    amount_rupees: Optional[float] = Field(None, gt=0)
    amount_paise: Optional[int] = Field(None, gt=0)
    txn_date: Optional[date] = None
    idempotency_key: Optional[str] = None
    transcript: Optional[str] = None
    confidence: Optional[float] = None

class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    shop_id: UUID
    customer_id: UUID
    type: str
    amount_paise: int
    amount_rupees: float
    txn_date: date
    status: str
    idempotency_key: str
    raw_transcript: Optional[str]
    llm_confidence: Optional[float]
    created_at: datetime

class BalanceResponse(BaseModel):
    customer_id: UUID
    customer_code: str
    customer_name: str
    balance_paise: int
    balance_rupees: float

class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int

# ---------- Reports ----------
class DailySummaryResponse(BaseModel):
    date: date
    total_credit_paise: int
    total_payment_paise: int
    net_paise: int
    transaction_count: int
    customers_served: int
