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


def _supabase_api_key() -> str:
    return (
        (settings.SUPABASE_ANON_KEY or "").strip()
        or (settings.SUPABASE_PUBLISHABLE_KEY or "").strip()
        or (settings.SUPABASE_SECRET_KEY or "").strip()
    )


async def verify_supabase_access_token(token: str) -> dict:
    """Validate a Supabase Auth access token via JWT secret or Auth API."""
    jwt_secret = (settings.SUPABASE_JWT_SECRET or "").strip()
    if jwt_secret:
        try:
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Supabase token: {exc}",
            ) from exc
        if not payload.get("sub"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Supabase token")
        return payload

    base_url = (settings.SUPABASE_URL or "").strip().rstrip("/")
    api_key = _supabase_api_key()
    if not base_url or not api_key or "YOUR_PROJECT" in base_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase auth is not configured (set SUPABASE_URL and API key, or SUPABASE_JWT_SECRET)",
        )

    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{base_url}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": api_key,
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach Supabase Auth: {exc}",
        ) from exc

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Supabase session",
        )
    data = resp.json() if resp.content else {}
    user_id = data.get("id") or data.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Supabase user")
    return {
        "sub": user_id,
        "email": data.get("email"),
        "role": data.get("role") or "authenticated",
    }
