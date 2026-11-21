import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.database.models import Shop
from app.database.crud import create_shop

pwd_context = None
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

def hash_password(password: str) -> str:\n    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:\n    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)

async def register_shop(db: AsyncSession, name: str, password: str, timezone: str = "Asia/Kolkata"):
    shop = await create_shop(db, name, timezone)
    # Store a simple shopkeeper record is out of scope; reuse shop id as actor
    token = create_access_token({"sub": str(shop.id), "shop": shop.name})
    return shop, token

async def login_shop(db: AsyncSession, shop_id, password: str):
    shop = await db.get(Shop, shop_id)
    if not shop:
        return None
    token = create_access_token({"sub": str(shop.id), "shop": shop.name})
    return shop, token
