from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.customers import router as customers_router
from app.api.transactions import router as transactions_router
from app.api.reports import router as reports_router

app = FastAPI(title='Voice Khata', version='0.1.0')

app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(transactions_router)
app.include_router(reports_router)

@app.get('/health')
async def health():
    return {'status': 'ok', 'service': 'voice-khata'}

@app.get('/')
async def root():
    return {'message': 'Voice Khata Backend Running'}
