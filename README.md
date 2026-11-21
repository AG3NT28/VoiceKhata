# Voice Khata

> AI-Powered Digital Voice Ledger for Local Kirana Stores

## Overview

Voice Khata converts the traditional handwritten *Khata* (credit ledger) used by Indian kirana store owners into an AI-powered voice-driven digital ledger. The shopkeeper simply speaks transactions in Hindi, English, or code-mixed Hinglish, and the system records, calculates balances, answers queries, and corrects errors - all through voice.

## Problem Statement

Traditional bookkeeping in small retail shops involves handwritten registers, manual balance calculations, searching for customer names, and correcting mistakes - all while serving customers. This becomes error-prone and time-consuming.

Voice Khata solves this by letting the shopkeeper speak naturally (for example: Ramesh ka 340 rupaye udhaar likho) and the AI handles transcription, understanding, validation, storage, and voice confirmation.

## Key Features

- Voice-based credit entry (udhaar)
- Payment recording
- Customer identification with disambiguation
- Outstanding balance calculation
- Voice queries (balance, daily summary)
- Spoken transaction correction with audit trail
- Multilingual / code-mixed (Hindi + English) support
- Real-time voice responses (< 2s TTFA)
- Daily business summary
- SQLite stock / inventory with audit logs
- Passwordless shop email login
- Customer IDs from name + phone (seeded IDs for voice adds)

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vite vanilla JS (+ optional React prototype) |
| Audio | MediaRecorder + Web Audio API, native WebSocket |
| Backend | Python 3.11 + FastAPI + Uvicorn (async) |
| ORM | SQLAlchemy 2.0 async |
| Database (dev) | SQLite (aiosqlite) |
| Validation | Pydantic v2 |
| Speech-to-Text | Gnani Prisma |
| Language Model | OpenAI-compatible LLM (structured JSON output) |
| Text-to-Speech | Gnani Timbre |
| Auth | JWT + passwordless shop email |
| Testing | pytest + pytest-asyncio + httpx |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20 LTS
- Git
- A microphone
- Gnani / LLM API keys as needed

### Backend Setup

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # fill in your API keys
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env   # optional Supabase / API base
npm run dev
```

Open http://localhost:5173 for the UI and http://127.0.0.1:8000/docs for the API.

## Environment Variables

See `backend/.env.example` and `frontend/.env.example`. Real `.env` files are gitignored.

## Testing

```bash
cd backend
pytest tests/ -v
```

## License

MIT
