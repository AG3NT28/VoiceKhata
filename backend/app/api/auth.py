from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.database.models import Shop
from app.schemas import RegisterShopRequest, LoginRequest, TokenResponse
from app.security.auth import register_shop, login_shop, hash_password

router = APIRouter(prefix="/auth", tags=["auth"])

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
