import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.db import get_db
from app.schemas import EmailLoginRequest, LoginRequest, RegisterShopRequest, TokenResponse
from app.security.auth import (
    create_access_token,
    login_shop,
    register_shop,
    security_scheme,
    verify_supabase_access_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(raw: str) -> str:
    email = (raw or "").strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Enter a valid shop email")
    return email


async def _issue_demo_shop_token(
    db: AsyncSession,
    email: str | None = None,
    *,
    reset: bool = False,
) -> TokenResponse:
    from datetime import datetime

    from app.api.inventory import seed_inventory_if_empty
    from app.api.voice import get_demo_shop
    from app.database.models import ShopLoginState
    from app.khata.shop_reset import reset_shop_data
    from app.stock.service import seed_stock_if_empty

    shop = await get_demo_shop(db)
    shop_reset = False
    if email:
        state = await db.get(ShopLoginState, shop.id)
        previous = ((state.active_email if state else "") or "").strip().lower()
        if reset or previous != email:
            await reset_shop_data(db, shop.id)
            shop_reset = True
            if state is None:
                state = ShopLoginState(shop_id=shop.id, active_email=email)
                db.add(state)
            else:
                state.active_email = email
                state.updated_at = datetime.utcnow()
            await db.commit()
            await seed_inventory_if_empty(db, shop)
            await seed_stock_if_empty(db, shop.id)
            from app.marketplace.seed import seed_default_stars, seed_marketplace

            await seed_marketplace(db, shop_id=shop.id)
            await seed_default_stars(db, shop.id)

    claims = {"sub": str(shop.id), "shop": shop.name}
    if email:
        claims["email"] = email
    token = create_access_token(claims)
    return TokenResponse(
        access_token=token,
        shop_id=shop.id,
        shop_name=shop.name,
        email=email,
        shop_reset=shop_reset,
    )


@router.post("/register-shop", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterShopRequest, db: AsyncSession = Depends(get_db)):
    shop, token = await register_shop(db, payload.name, payload.password, payload.timezone)
    return TokenResponse(access_token=token, shop_id=shop.id, shop_name=shop.name)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    shop, token = await login_shop(db, payload.shop_id, payload.password)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    return TokenResponse(access_token=token, shop_id=shop.id, shop_name=shop.name)


@router.post("/email", response_model=TokenResponse)
async def email_login(payload: EmailLoginRequest, db: AsyncSession = Depends(get_db)):
    """Passwordless shop access. A new/different email wipes shared demo shop data."""
    email = _normalize_email(payload.email)
    return await _issue_demo_shop_token(db, email, reset=payload.reset)


@router.post("/demo", response_model=TokenResponse)
async def demo_login(db: AsyncSession = Depends(get_db)):
    """Dev-only: issue a JWT for the seeded demo shop without an email."""
    if not settings.ALLOW_DEMO_AUTH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo auth is disabled. Sign in with shop email.",
        )
    return await _issue_demo_shop_token(db)


@router.post("/supabase", response_model=TokenResponse)
async def supabase_exchange(
    creds: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Verify a Supabase access token, then issue the shared demo-shop VoiceKhata JWT."""
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Supabase token")

    claims = await verify_supabase_access_token(creds.credentials)
    from app.api.voice import get_demo_shop

    shop = await get_demo_shop(db)
    token = create_access_token(
        {
            "sub": str(shop.id),
            "shop": shop.name,
            "supabase_sub": claims.get("sub"),
            "email": claims.get("email"),
        }
    )
    return TokenResponse(access_token=token, shop_id=shop.id, shop_name=shop.name)
