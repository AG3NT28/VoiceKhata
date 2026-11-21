"""Prototype-facing voice API: audio in, ledger action out."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.database.models import Shop, Transaction, TxnStatus
from app.khata.customers import create_customer, find_customers_by_name
from app.khata.ledger import add_credit, record_payment
from app.utils.dates import today_in_tz
from app.voice.pipeline import demo_state, handle_transcript
from app.voice.stt import STTError, transcribe_detailed
from app.voice.tts import TTSError, synthesize

router = APIRouter(prefix="/voice", tags=["voice"])

DEMO_SHOP_NAME = "Demo Kirana Store"


class TextCommand(BaseModel):
    text: str


class SpeakRequest(BaseModel):
    text: str
    language: str = "hi-en"


async def get_demo_shop(db: AsyncSession) -> Shop:
    """Single-shop demo tenant so the prototype needs no login."""
    result = await db.execute(select(Shop).where(Shop.name == DEMO_SHOP_NAME))
    shop = result.scalar_one_or_none()
    if shop:
        return shop

    shop = Shop(name=DEMO_SHOP_NAME)
    db.add(shop)
    await db.commit()
    await db.refresh(shop)

    # Seed a small, believable ledger so the UI is not empty on first load.
    ramesh = await create_customer(db, shop.id, "Ramesh")
    suresh = await create_customer(db, shop.id, "Suresh")
    await create_customer(db, shop.id, "Sunita")
    await add_credit(db, shop.id, ramesh.id, 34000, today_in_tz(), transcript="seed: Ramesh 340 udhaar")
    await add_credit(db, shop.id, suresh.id, 125000, today_in_tz(), transcript="seed: Suresh 1250 udhaar")
    await record_payment(db, shop.id, ramesh.id, 10000, today_in_tz(), transcript="seed: Ramesh 100 jama")
    return shop


@router.post("/transcribe")
async def transcribe_only(audio: UploadFile = File(...), language_code: str = Form("hi-IN,en-IN")):
    data = await audio.read()
    try:
        return await transcribe_detailed(data, audio.filename or "audio.wav", language_code=language_code)
    except STTError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/command")
async def voice_command(
    audio: UploadFile = File(...),
    language_code: str = Form("hi-IN,en-IN"),
    db: AsyncSession = Depends(get_db),
):
    shop = await get_demo_shop(db)
    data = await audio.read()
    try:
        stt = await transcribe_detailed(data, audio.filename or "audio.wav", language_code=language_code)
    except STTError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    result = await handle_transcript(db, shop.id, stt["transcript"])
    result["stt"] = stt
    return result


@router.post("/text")
async def text_command(payload: TextCommand, db: AsyncSession = Depends(get_db)):
    shop = await get_demo_shop(db)
    return await handle_transcript(db, shop.id, payload.text)


@router.get("/state")
async def state(db: AsyncSession = Depends(get_db)):
    shop = await get_demo_shop(db)
    snapshot = await demo_state(db, shop.id)
    snapshot["shop"] = {"id": str(shop.id), "name": shop.name}
    return snapshot


@router.post("/undo")
async def undo_last(db: AsyncSession = Depends(get_db)):
    shop = await get_demo_shop(db)
    stmt = select(Transaction).where(
        Transaction.shop_id == shop.id, Transaction.status == TxnStatus.active
    ).order_by(Transaction.created_at.desc()).limit(1)
    last = (await db.execute(stmt)).scalars().first()
    if not last:
        return {"ok": False, "reply_text": "Koi entry nahi jo undo kar sakun."}
    from app.khata.corrections import void_transaction
    await void_transaction(db, last)
    return {
        "ok": True,
        "reply_text": "Undo ho gaya: %s Rs%.0f hata diya." % (last.type.value, last.amount_paise / 100),
        "transaction_id": str(last.id),
    }


@router.post("/speak")
async def speak_text(payload: SpeakRequest):
    try:
        audio = await synthesize(payload.text, language=payload.language)
    except TTSError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    if audio is None:
        raise HTTPException(status_code=503, detail="Gnani TTS not configured (set GNANI_API_KEY).")
    return Response(content=audio, media_type="audio/wav")
