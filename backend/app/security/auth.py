import bcrypt
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database.models import Shop
from app.database.crud import create_shop

ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

security_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)

async def register_shop(db: AsyncSession, name: str, password: str, timezone: str = 'Asia/Kolkata'):
    shop = await create_shop(db, name, timezone)
    token = create_access_token({'sub': str(shop.id), 'shop': shop.name})
    return shop, token

async def login_shop(db: AsyncSession, shop_id, password: str):
    shop = await db.get(Shop, shop_id)
    if not shop:
        return None
    token = create_access_token({'sub': str(shop.id), 'shop': shop.name})
    return shop, token

async def get_current_shop_id(creds: HTTPAuthorizationCredentials = Depends(security_scheme)) -> UUID:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing token')
    try:
        payload = jwt.decode(creds.credentials, settings.JWT_SECRET, algorithms=['HS256'])
        return UUID(payload['sub'])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')
