"""LLM system prompt + few-shots seeded from the edge-case training dataset."""
from __future__ import annotations

from app.ai.dataset import core_invariants, few_shot_from_dataset
from app.ai.price_dataset import few_shot_from_price_dataset

_INVARIANT_LINES = "\n".join(
    f"- {inv.get('rule')}: {inv.get('description')}"
    for inv in core_invariants()[:12]
) or (
    "- No guessed amount/customer/direction\n"
    "- Clarify when uncertain\n"
    "- LLM is not source of truth"
)

SYSTEM_PROMPT = f'''You are the intent extractor for Voice Khata, a digital ledger for Indian kirana stores.
You NEVER modify data. You ONLY extract structured intent from the shopkeeper's speech.

Available intents:
- ADD_CUSTOMER: register customer with NO amount
- ADD_CREDIT: customer owes / udhaar (requires customer_name + amount_paise)
- RECORD_PAYMENT: customer paid (requires customer_name + amount_paise)
- CHECK_BALANCE: ask outstanding
- DAILY_SUMMARY / KHATA_SUMMARY / STOCK_SUMMARY: read-only summaries
- FIND_WHOLESALE: compare / search wholesale marketplace prices (entities.query, optional product/brand/quantity/unit)
- CORRECT_LAST: fix previous amount (entities.amount_paise = corrected value in paise)
- CLARIFY: missing/ambiguous info, future promise, negation, refund ambiguity, multi-customer

Core invariants (must obey):
{_INVARIANT_LINES}

Rules:
1. Amounts: integer paise (1 rupee = 100 paise). "paanch sau" → 50000; "2.5K" → 250000.
2. Dates: keep relative expressions as date_expr (aaj/kal/parso/today/yesterday/tomorrow).
3. Prefer entities.customer_name (also accept name). Never invent a customer.
4. If amount missing for credit/payment → CLARIFY. Never guess.
5. If direction unclear ("300 likho", "maine se liye") → CLARIFY with credit vs payment options.
6. Future promise ("dega", "kal dega") → CLARIFY; do NOT RECORD_PAYMENT.
7. Negated payment ("nahi diye") → CLARIFY; do not record.
8. Zero amount → CLARIFY / reject.
9. ADD_CUSTOMER only when registering with no credit amount.
10. Output ONLY valid JSON. No prose.

Multilingual input:
- The shopkeeper may speak Hindi, English, Telugu, Kannada, or Tamil — in native
  script or Latin transliteration. Parse all of them into the SAME schema.
- Telugu: appu/అప్పు = credit, ichchanu/ఇచ్చాను = gave, theesukunnaanu/తీసుకున్నాను = took,
  baaki/బాకీ = balance, raayu/రాయు = write, khata/ఖాతా = ledger, entha = how much.
- Kannada: appu/ಅಪ್ಪು = credit, kotte/ಕೊಟ್ಟೆ = gave, padede/ಪಡೆದೆ = received,
  baaki/ಬಾಕಿ = balance, baree/ಬರೆ = write, khate/ಖಾತೆ = ledger, eshtu = how much.
- Tamil: kadan/கடன் = credit, kuduthen/கொடுத்தேன் = gave, vaanginen/வாங்கினேன் = took,
  baaki/பாக்கி = balance, ezhuthu/எழுது = write, kanakku/கணக்கு = ledger, evvalavu = how much.
- Customer names may be native script or transliterated; keep them exactly as spoken.

Output schema:
{{"intent":"ADD_CREDIT","confidence":0.92,"entities":{{"customer_name":"Ramesh","amount_paise":34000,"date_expr":"aaj"}},"clarification_needed":false,"clarification_question":null,"clarification_options":[]}}
'''

# Seed few-shots: curated classics + dataset training rows
_BASE_FEW_SHOTS = [
    ('Ramesh ka 340 udhaar', {'intent': 'ADD_CREDIT', 'confidence': 0.95, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 34000, 'date_expr': 'aaj'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    ('Ramesh ne 200 diye', {'intent': 'RECORD_PAYMENT', 'confidence': 0.95, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 20000, 'date_expr': 'aaj'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    ('Ramesh ka kitna balance hai', {'intent': 'CHECK_BALANCE', 'confidence': 0.98, 'entities': {'customer_name': 'Ramesh'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    ('Aaj kitna udhaar gaya', {'intent': 'DAILY_SUMMARY', 'confidence': 0.97, 'entities': {}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    ('Ramesh ka 340 nahi 430', {'intent': 'CORRECT_LAST', 'confidence': 0.9, 'entities': {'customer_name': 'Ramesh', 'field': 'amount', 'amount_paise': 43000}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    ('Ramesh Kumar add karo', {'intent': 'ADD_CUSTOMER', 'confidence': 0.95, 'entities': {'customer_name': 'Ramesh Kumar', 'name': 'Ramesh Kumar'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    ('Ramesh ka 300 likho', {'intent': 'CLARIFY', 'confidence': 0.6, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 30000}, 'clarification_needed': True, 'clarification_question': 'Credit ya payment?', 'clarification_options': ['credit', 'payment']}),
    ('Ramesh kal 200 dega', {'intent': 'CLARIFY', 'confidence': 0.9, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 20000}, 'clarification_needed': True, 'clarification_question': 'Future promise — abhi payment record nahi karunga.', 'clarification_options': []}),
    ('Ramesh ne 300 nahi diye', {'intent': 'CLARIFY', 'confidence': 0.85, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 30000, 'negation': True}, 'clarification_needed': True, 'clarification_question': 'Payment record nahi kiya.', 'clarification_options': []}),
    ('Ramesh ko zero udhaar add karo', {'intent': 'CLARIFY', 'confidence': 0.9, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 0}, 'clarification_needed': True, 'clarification_question': 'Amount zero nahi ho sakta.', 'clarification_options': []}),
    ('Fortune sunflower oil wholesale rates', {'intent': 'FIND_WHOLESALE', 'confidence': 0.92, 'entities': {'query': 'Fortune sunflower oil wholesale rates', 'purchase_type': 'wholesale'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    # --- Telugu ---------------------------------------------------------------
    ('Ramesh ki 340 appu raayu', {'intent': 'ADD_CREDIT', 'confidence': 0.94, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 34000, 'date_expr': 'aaj'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    ('Ramesh ku 500 appu ichchanu', {'intent': 'ADD_CREDIT', 'confidence': 0.94, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 50000, 'date_expr': 'aaj'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    ('Ramesh 200 jama chesadu', {'intent': 'RECORD_PAYMENT', 'confidence': 0.93, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 20000, 'date_expr': 'aaj'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    ('Ramesh baaki entha', {'intent': 'CHECK_BALANCE', 'confidence': 0.96, 'entities': {'customer_name': 'Ramesh'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    # --- Kannada --------------------------------------------------------------
    ('Ramesh ge 250 appu baree', {'intent': 'ADD_CREDIT', 'confidence': 0.94, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 25000, 'date_expr': 'aaj'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    ('Ramesh ge 500 appu kotte', {'intent': 'ADD_CREDIT', 'confidence': 0.94, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 50000, 'date_expr': 'aaj'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    ('Ramesh 200 jama madida', {'intent': 'RECORD_PAYMENT', 'confidence': 0.93, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 20000, 'date_expr': 'aaj'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    ('Ramesh ge eshtu baaki', {'intent': 'CHECK_BALANCE', 'confidence': 0.96, 'entities': {'customer_name': 'Ramesh'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    # --- Tamil ---------------------------------------------------------------
    ('Ramesh kadan 300 ezhuthu', {'intent': 'ADD_CREDIT', 'confidence': 0.94, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 30000, 'date_expr': 'aaj'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    ('Ramesh ku 450 kadan kuduthen', {'intent': 'ADD_CREDIT', 'confidence': 0.94, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 45000, 'date_expr': 'aaj'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    ('Ramesh 200 kattiten', {'intent': 'RECORD_PAYMENT', 'confidence': 0.93, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 20000, 'date_expr': 'aaj'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
    ('Ramesh evvalavu baaki', {'intent': 'CHECK_BALANCE', 'confidence': 0.96, 'entities': {'customer_name': 'Ramesh'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}),
]

def _merge_few_shots() -> list[tuple[str, dict]]:
    seen: set[str] = set()
    out: list[tuple[str, dict]] = []
    # Ledger edge-cases + multilingual price-comparison training JSONL
    for transcript, payload in (
        list(_BASE_FEW_SHOTS)
        + few_shot_from_dataset(20)
        + few_shot_from_price_dataset(24)
    ):
        key = transcript.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append((transcript, payload))
    return out


FEW_SHOT_EXAMPLES = _merge_few_shots()
