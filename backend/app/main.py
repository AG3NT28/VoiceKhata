from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.customers import router as customers_router
from app.api.inventory import router as inventory_router, seed_inventory_if_empty
from app.api.reports import router as reports_router
from app.api.stock import router as stock_router
from app.api.transactions import router as transactions_router
from app.api.voice import get_demo_shop, router as voice_router
from app.database.db import SessionLocal, engine
from app.database.models import Base
from app.stock.service import seed_stock_if_empty
from app.voice.websocket import router as ws_router


from app.voice.stt import close_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        shop = await get_demo_shop(db)
        await seed_inventory_if_empty(db, shop)
        await seed_stock_if_empty(db, shop.id)
    yield
    await close_client()


app = FastAPI(title='Voice Khata', version='0.2.0', lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=False, allow_methods=['*'], allow_headers=['*'])

app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(transactions_router)
app.include_router(reports_router)
app.include_router(inventory_router)
app.include_router(stock_router)
app.include_router(voice_router)
app.include_router(ws_router)

# Built SPA lives in backend/static in production (see Dockerfile).
STATIC_DIR = Path(__file__).resolve().parents[1] / 'static'


@app.get('/health')
async def health():
    return {'status': 'ok', 'service': 'voice-khata'}


@app.get('/')
async def root():
    index = STATIC_DIR / 'index.html'
    if index.is_file():
        return FileResponse(index)
    return {'message': 'Voice Khata Backend Running'}


# Serve the compiled frontend when it is present. API routes above win because
# they are registered first; this catch-all only handles SPA paths.
if STATIC_DIR.is_dir():
    assets = STATIC_DIR / 'assets'
    if assets.is_dir():
        app.mount('/assets', StaticFiles(directory=assets), name='assets')

    @app.get('/{full_path:path}')
    async def spa_fallback(full_path: str):
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / 'index.html')
