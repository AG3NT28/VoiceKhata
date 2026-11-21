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

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + TailwindCSS + Zustand |
| Audio | MediaRecorder + Web Audio API, native WebSocket |
| Backend | Python 3.11 + FastAPI + Uvicorn (async) |
| ORM | SQLAlchemy 2.0 async + Alembic |
| Database (dev) | SQLite (aiosqlite) |
| Database (prod) | PostgreSQL 16 (asyncpg) |
| Validation | Pydantic v2 |
| Speech-to-Text | Gnani Prisma v3.0 (streaming WebSocket) |
| Language Model | OpenAI-compatible LLM (structured JSON output) |
| Text-to-Speech | Gnani Timbre v3.0 (streaming) |
| Auth | JWT (python-jose) + bcrypt |
| Testing | pytest + pytest-asyncio + httpx |
| Deploy | Vercel (frontend), Render (backend), Neon (database) |

## Architecture

`
React Microphone -> WebSocket -> FastAPI Backend -> Gnani Prisma (STT) -> LLM (intent extraction) -> Ledger Service -> Database -> Gnani Timbre (TTS) -> WebSocket Audio -> React Player
`

The LLM never touches the database directly. It only returns structured JSON, which the backend validates before performing any financial operation.

## Database Design

- shops: id, name, timezone, created_at
- customers: id, shop_id, name, phone, normalized_name, status, created_at, updated_at (unique per shop + normalized name)
- transactions: id, shop_id, customer_id, type (credit/payment), amount_paise (integer), txn_date, status (active/reversed/voided), reversed_by, supersedes, idempotency_key (unique), raw_transcript, llm_confidence, created_at
- audit_log: id, shop_id, actor, action, entity_type, entity_id, payload (JSONB), created_at

Money is stored as integer paise (1 rupee = 100 paise) to avoid floating-point errors.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20 LTS
- Git
- A microphone
- Gnani Prisma v3.0 + Timbre v3.0 API credentials (from hackathon organizers)
- An LLM API key (Groq or OpenAI)

### Backend Setup

`ash
 cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # fill in your API keys
python init_db.py      # create tables
uvicorn app.main:app --reload --port 8000
`

### Frontend Setup

`ash
cd frontend
npm install
npm run dev
`

Open http://localhost:5173 for the UI and http://127.0.0.1:8000/docs for the API.

## Environment Variables

See backend/.env.example:

`
DATABASE_URL=sqlite+aiosqlite:///./voice_khata.db
JWT_SECRET=change-me
GNANI_API_KEY=your-gnani-key
GNANI_BASE_URL=https://api.gnani.ai
LLM_API_KEY=your-llm-key
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile
`

## Development Milestones

1. Setup (repo, venv, Vite, SQLite)
2. Database + Ledger engine + tests
3. REST API (customers, transactions, reports)
4. Frontend shell (dashboard, customer list, history)
5. LLM intent extraction
6. Gnani STT integration
7. Gnani TTS integration
8. WebSocket orchestrator
9. Barge-in + latency optimization
10. Advanced features (disambiguation, dates, corrections, daily summary)
11. Testing + polish
12. Deploy + demo

## Testing

`ash
cd backend
pytest tests/ -v
`

## Demo Script (3 minutes)

1. Intro
2. Add customer (Ramesh Kumar add karo)
3. Credit (Ramesh ka 340 udhaar)
4. Payment (Ramesh ne 200 diye)
5. Balance query (Ramesh ka kitna balance)
6. Ambiguity (two Rameshes -> clarification)
7. Correction (Nahi 340 nahi 430 tha)
8. Daily summary (Aaj kitna udhaar gaya)
9. Code-mixed (Ramesh ko 500 credit mein add karo)
10. Close with audit trail on dashboard

## License

MIT

## Contributing

Pull requests welcome. Please open an issue first for major changes.

## Author

AG3NT28
