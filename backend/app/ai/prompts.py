"""LLM system prompt + few-shots seeded from the edge-case training dataset."""
from __future__ import annotations

from app.ai.dataset import core_invariants, few_shot_from_dataset

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
- FIND_WHOLESALE: search wholesale / marketplace offers (entities.query = product phrase)
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
]

def _merge_few_shots() -> list[tuple[str, dict]]:
    seen: set[str] = set()
    out: list[tuple[str, dict]] = []
    for transcript, payload in list(_BASE_FEW_SHOTS) + few_shot_from_dataset(25):
        key = transcript.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append((transcript, payload))
    return out


FEW_SHOT_EXAMPLES = _merge_few_shots()
