# API Documentation

See /docs (Swagger) when backend is running: http://127.0.0.1:8000/docs

## REST Endpoints

- POST /auth/login
- POST /auth/register-shop
- POST /auth/demo  (issues a JWT for the seeded demo shop; used by the UI)
- GET /customers?q=&status=
- POST /customers
- GET /customers/{id}
- PATCH /customers/{id}
- GET /customers/{id}/balance
- GET /customers/{id}/transactions?from=&to=&limit=
- POST /transactions (idempotency-key header)
- POST /transactions/{id}/reverse
- GET /reports/daily?date=
- GET /reports/summary?from=&to=

## WebSocket

Endpoint: /ws/voice

Client -> Server: start_session, audio_chunk, end_utterance, barge_in
Server -> Client: transcript_partial, transcript_final, intent, clarification, confirmation, audio_chunk, error, metrics
