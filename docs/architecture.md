# Architecture

## Overview

Voice Khata is a real-time voice-driven digital ledger for kirana stores.

## Components

- Frontend (React + Vite): UI, microphone capture, WebSocket client, audio playback
- Backend (FastAPI): REST APIs, WebSocket orchestrator, business logic, DB access
- AI Layer: Gnani Prisma (STT), LLM (intent extraction), Gnani Timbre (TTS)
- Database: SQLite (dev) / PostgreSQL (prod)

## Data Flow

Browser Mic -> WebSocket -> FastAPI -> Gnani Prisma (STT) -> LLM (intent) -> Ledger Service -> DB -> Response -> Gnani Timbre (TTS) -> WebSocket -> Browser Player

## Key Principles

- LLM never touches the database; only returns structured JSON.
- Money stored as integer paise.
- No hard deletes on transactions; reverse + supersede with audit trail.
- Idempotency keys prevent duplicate charges.
