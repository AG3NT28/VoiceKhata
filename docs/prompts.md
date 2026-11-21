# LLM Prompts

See backend/app/ai/prompts.py (to be created in Phase 4).

## Intents

ADD_CUSTOMER, ADD_CREDIT, RECORD_PAYMENT, CHECK_BALANCE, DAILY_SUMMARY, CORRECT_LAST, CLARIFY

## Rules

- Amounts converted to paise (integer).
- Relative dates kept as date_expr; backend resolves.
- Customer names preserved as spoken.
- Clarify on ambiguity or missing amount.
- Never hallucinate; output only JSON.
