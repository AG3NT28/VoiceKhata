"""Voice command orchestrator: transcript -> intent -> ledger action -> reply."""
from __future__ import annotations

import re
import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.extraction import ExtractedIntent
from app.ai.fallback import parse_text
from app.ai.llm import extract_intent
from app.config import settings
from app.database.models import Customer, Item, ItemStatus, Transaction, TxnStatus, TxnType
from app.khata.corrections import correct_transaction
from app.khata.customers import create_customer, find_customer_by_code, find_customers_by_name
from app.khata.ledger import add_credit, compute_balance, record_payment
from app.utils.dates import today_in_tz
from app.utils.paise import paise_to_rupees, rupees_to_paise

_CODE_RE = re.compile(r"\bC\d{3,}\b", re.IGNORECASE)

DEFAULT_CLARIFY = "Samajh nahi aaya. Jaise boliye: 'Ramesh ka 340 rupaye udhaar'."


# ---------------------------------------------------------------------------
# Reply localisation (Hindi / English / Telugu / Kannada / Tamil)
# ---------------------------------------------------------------------------
_REPLIES: dict[str, dict[str, str]] = {
    "hi": {
        "empty": "Kuch sunai nahi diya. Dobara boliye.",
        "ask_name": "Customer ka naam kya hai?",
        "already_exists": "{name} pehle se hai, code {code}.",
        "multi_customer": "Do customer mile - {name}. Kaunsa?",
        "new_customer": "Naya customer {name} ban gaya, temporary ID {code}. Phone number form me daalne par ID update ho jayegi.",
        "ask_amount": "Kitne rupaye? Amount dobara boliye.",
        "ask_customer": "Kiska khata? Customer ka naam boliye.",
        "code_not_found": "Is code se koi customer nahi mila. Code check karke phir try karein.",
        "amount_positive": "Amount zero se zyada hona chahiye.",
        "credit_done": "{name} ka {amount} udhaar likh diya. Ab total baaki {balance}.",
        "payment_done": "{name} se {amount} jama ho gaya. Ab baaki {balance}.",
        "balance": "{name} ({code}) ka baaki {balance} hai.",
        "top_dues": "Kiska? Top baaki: {listing}.",
        "daily_summary": "Aaj {credit} udhaar diya, {payment} jama hua, {count} entry hui.",
        "khata_summary": "Khata summary: {count} customers pe total {total} baaki. Top: {top}.",
        "inventory_empty": "Inventory empty hai. Stock tab se items add karein.",
        "stock_summary": "Stock summary: {items} items, {low} low stock. Kam: {low_line}.",
        "no_last_entry": "Koi pichhli entry nahi mili jo correct kar sakun.",
        "corrected": "Theek kar diya. Pehle {old}, ab {new}. {name} ka baaki {balance}.",
        "default_clarify": DEFAULT_CLARIFY,
        "no_due": "koi due nahi",
        "no_khata": "koi khata nahi",
        "all_ok": "sab theek",
    },
    "en": {
        "empty": "I didn't hear anything. Please say that again.",
        "ask_name": "What is the customer's name?",
        "already_exists": "{name} already exists, code {code}.",
        "multi_customer": "Two customers match - {name}. Which one?",
        "new_customer": "New customer {name} created, temporary ID {code}. Add a phone number in the form to update the ID.",
        "ask_amount": "How much? Please say the amount again.",
        "ask_customer": "Whose account? Please say the customer's name.",
        "code_not_found": "No customer found with that code. Check the code and try again.",
        "amount_positive": "The amount must be greater than zero.",
        "credit_done": "Recorded {amount} credit for {name}. Total due is now {balance}.",
        "payment_done": "Received {amount} from {name}. Remaining due is {balance}.",
        "balance": "{name} ({code}) has {balance} due.",
        "top_dues": "Whose? Top dues: {listing}.",
        "daily_summary": "Today: {credit} credit given, {payment} received, {count} entries.",
        "khata_summary": "Khata summary: {count} customers owe {total} in total. Top: {top}.",
        "inventory_empty": "Inventory is empty. Add items from the Stock tab.",
        "stock_summary": "Stock summary: {items} items, {low} low stock. Low: {low_line}.",
        "no_last_entry": "No previous entry found to correct.",
        "corrected": "Corrected. Before {old}, now {new}. {name} has {balance} due.",
        "default_clarify": "I didn't understand. Try: 'Ramesh 340 udhaar'.",
        "no_due": "no dues",
        "no_khata": "no khata",
        "all_ok": "all good",
    },
    "te": {
        "empty": "ఏమీ వినిపించలేదు. మళ్లీ చెప్పండి.",
        "ask_name": "కస్టమర్ పేరు ఏమిటి?",
        "already_exists": "{name} ఇప్పటికే ఉన్నారు, కోడ్ {code}.",
        "multi_customer": "ఇద్దరు కస్టమర్లు దొరికారు - {name}. ఎవరు?",
        "new_customer": "కొత్త కస్టమర్ {name} సృష్టించబడింది, తాత్కాలిక ID {code}. ఫోన్ నంబర్ ఫారంలో ఇస్తే ID అప్‌డేట్ అవుతుంది.",
        "ask_amount": "ఎంత డబ్బు? మొత్తం మళ్లీ చెప్పండి.",
        "ask_customer": "ఎవరి ఖాతా? కస్టమర్ పేరు చెప్పండి.",
        "code_not_found": "ఈ కోడ్‌తో కస్టమర్ దొరకలేదు. కోడ్ తనిఖీ చేసి మళ్లీ ప్రయత్నించండి.",
        "amount_positive": "మొత్తం సున్నా కంటే ఎక్కువ ఉండాలి.",
        "credit_done": "{name} కు {amount} అప్పు నమోదు చేయబడింది. ఇప్పుడు మొత్తం బాకీ {balance}.",
        "payment_done": "{name} నుండి {amount} జమ అయింది. ఇప్పుడు బాకీ {balance}.",
        "balance": "{name} ({code}) బాకీ {balance}.",
        "top_dues": "ఎవరు? ఎక్కువ బాకీ: {listing}.",
        "daily_summary": "ఈరోజు {credit} అప్పు ఇచ్చారు, {payment} జమ అయింది, {count} ఎంట్రీలు.",
        "khata_summary": "ఖాతా సారాంశం: {count} కస్టమర్లపై మొత్తం {total} బాకీ. టాప్: {top}.",
        "inventory_empty": "నిల్వ ఖాళీగా ఉంది. స్టాక్ ట్యాబ్ నుండి వస్తువులు జోడించండి.",
        "stock_summary": "నిల్వ సారాంశం: {items} వస్తువులు, {low} తక్కువ నిల్వ. తక్కువ: {low_line}.",
        "no_last_entry": "సరిచేయడానికి మునుపటి ఎంట్రీ కనబడలేదు.",
        "corrected": "సరిచేయబడింది. ముందు {old}, ఇప్పుడు {new}. {name} బాకీ {balance}.",
        "default_clarify": "అర్థం కాలేదు. ఇలా చెప్పండి: 'రమేష్ కు 340 అప్పు రాయు'.",
        "no_due": "బాకీ లేదు",
        "no_khata": "ఖాతా లేదు",
        "all_ok": "అన్నీ బాగున్నాయి",
    },
    "kn": {
        "empty": "ಏನೂ ಕೇಳಿಸಲಿಲ್ಲ. ಮತ್ತೆ ಹೇಳಿ.",
        "ask_name": "ಗ್ರಾಹಕರ ಹೆಸರು ಏನು?",
        "already_exists": "{name} ಈಗಾಗಲೇ ಇದ್ದಾರೆ, ಕೋಡ್ {code}.",
        "multi_customer": "ಇಬ್ಬರು ಗ್ರಾಹಕರು ಸಿಕ್ಕರು - {name}. ಯಾರು?",
        "new_customer": "ಹೊಸ ಗ್ರಾಹಕ {name} ರಚಿಸಲಾಗಿದೆ, ತಾತ್ಕಾಲಿಕ ID {code}. ಫೋನ್ ಸಂಖ್ಯೆ ಫಾರಂನಲ್ಲಿ ಹಾಕಿದರೆ ID ಅಪ್‌ಡೇಟ್ ಆಗುತ್ತದೆ.",
        "ask_amount": "ಎಷ್ಟು ಹಣ? ಮೊತ್ತವನ್ನು ಮತ್ತೆ ಹೇಳಿ.",
        "ask_customer": "ಯಾರ ಖಾತೆ? ಗ್ರಾಹಕರ ಹೆಸರು ಹೇಳಿ.",
        "code_not_found": "ಈ ಕೋಡ್‌ನಿಂದ ಗ್ರಾಹಕರು ಸಿಗಲಿಲ್ಲ. ಕೋಡ್ ಪರಿಶೀಲಿಸಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
        "amount_positive": "ಮೊತ್ತವು ಸೊನ್ನೆಗಿಂತ ಹೆಚ್ಚಿರಬೇಕು.",
        "credit_done": "{name} ಅವರಿಗೆ {amount} ಸಾಲ ದಾಖಲಿಸಲಾಗಿದೆ. ಈಗ ಒಟ್ಟು ಬಾಕಿ {balance}.",
        "payment_done": "{name} ರಿಂದ {amount} ಜಮಾ ಆಗಿದೆ. ಈಗ ಬಾಕಿ {balance}.",
        "balance": "{name} ({code}) ಬಾಕಿ {balance}.",
        "top_dues": "ಯಾರು? ಹೆಚ್ಚು ಬಾಕಿ: {listing}.",
        "daily_summary": "ಇಂದು {credit} ಸಾಲ ನೀಡಲಾಗಿದೆ, {payment} ಜಮಾ ಆಗಿದೆ, {count} ನಮೂದುಗಳು.",
        "khata_summary": "ಖಾತೆ ಸಾರಾಂಶ: {count} ಗ್ರಾಹಕರ ಮೇಲೆ ಒಟ್ಟು {total} ಬಾಕಿ. ಟಾಪ್: {top}.",
        "inventory_empty": "ಸ್ಟಾಕ್ ಖಾಲಿಯಿದೆ. ಸ್ಟಾಕ್ ಟ್ಯಾಬ್‌ನಿಂದ ವಸ್ತುಗಳನ್ನು ಸೇರಿಸಿ.",
        "stock_summary": "ಸ್ಟಾಕ್ ಸಾರಾಂಶ: {items} ವಸ್ತುಗಳು, {low} ಕಡಿಮೆ ಸ್ಟಾಕ್. ಕಡಿಮೆ: {low_line}.",
        "no_last_entry": "ಸರಿಪಡಿಸಲು ಹಿಂದಿನ ನಮೂದು ಸಿಗಲಿಲ್ಲ.",
        "corrected": "ಸರಿಪಡಿಸಲಾಗಿದೆ. ಮೊದಲು {old}, ಈಗ {new}. {name} ಬಾಕಿ {balance}.",
        "default_clarify": "ಅರ್ಥವಾಗಲಿಲ್ಲ. ಹೀಗೆ ಹೇಳಿ: 'ರಮೇಶ್ ಗೆ 340 ಸಾಲ ಬರೆ'.",
        "no_due": "ಬಾಕಿ ಇಲ್ಲ",
        "no_khata": "ಖಾತೆ ಇಲ್ಲ",
        "all_ok": "ಎಲ್ಲ ಸರಿ",
    },
    "ta": {
        "empty": "எதுவும் கேட்கவில்லை. மீண்டும் சொல்லுங்கள்.",
        "ask_name": "வாடிக்கையாளர் பெயர் என்ன?",
        "already_exists": "{name} ஏற்கனவே உள்ளார், குறியீடு {code}.",
        "multi_customer": "இரண்டு வாடிக்கையாளர்கள் கிடைத்தனர் - {name}. யார்?",
        "new_customer": "புதிய வாடிக்கையாளர் {name} உருவாக்கப்பட்டார், தற்காலிக ID {code}. தொலைபேசி எண்ணை படிவத்தில் சேர்த்தால் ID புதுப்பிக்கப்படும்.",
        "ask_amount": "எவ்வளவு பணம்? தொகையை மீண்டும் சொல்லுங்கள்.",
        "ask_customer": "யாருடைய கணக்கு? வாடிக்கையாளர் பெயரைச் சொல்லுங்கள்.",
        "code_not_found": "இந்தக் குறியீட்டில் வாடிக்கையாளர் கிடைக்கவில்லை. குறியீட்டைச் சரிபார்த்து மீண்டும் முயற்சிக்கவும்.",
        "amount_positive": "தொகை பூஜ்ஜியத்தை விட அதிகமாக இருக்க வேண்டும்.",
        "credit_done": "{name} க்கு {amount} கடன் பதிவு செய்யப்பட்டது. இப்போது மொத்த நிலுவை {balance}.",
        "payment_done": "{name} இடமிருந்து {amount} செலுத்தப்பட்டது. இப்போது நிலுவை {balance}.",
        "balance": "{name} ({code}) நிலுவை {balance}.",
        "top_dues": "யார்? அதிக நிலுவை: {listing}.",
        "daily_summary": "இன்று {credit} கடன் கொடுக்கப்பட்டது, {payment} வசூலானது, {count} பதிவுகள்.",
        "khata_summary": "கணக்கு சுருக்கம்: {count} வாடிக்கையாளர்களிடம் மொத்தம் {total} நிலுவை. முதல்: {top}.",
        "inventory_empty": "இருப்பு காலியாக உள்ளது. இருப்பு தாவலில் பொருட்களைச் சேர்க்கவும்.",
        "stock_summary": "இருப்பு சுருக்கம்: {items} பொருட்கள், {low} குறைந்த இருப்பு. குறைவு: {low_line}.",
        "no_last_entry": "திருத்த முந்தைய பதிவு கிடைக்கவில்லை.",
        "corrected": "திருத்தப்பட்டது. முன்பு {old}, இப்போது {new}. {name} நிலுவை {balance}.",
        "default_clarify": "புரியவில்லை. இப்படிச் சொல்லுங்கள்: 'ரமேஷ் க்கு 340 கடன் எழுது'.",
        "no_due": "நிலுவை இல்லை",
        "no_khata": "கணக்கு இல்லை",
        "all_ok": "எல்லாம் சரி",
    },
}

# Script ranges let us detect the language even when the STT returns native script.
_SCRIPT_LANGUAGES = (
    ("te", "\u0c00", "\u0c7f"),  # Telugu
    ("kn", "\u0c80", "\u0cff"),  # Kannada
    ("ta", "\u0b80", "\u0bff"),  # Tamil
)

# Distinctive transliterated words (ambiguous words like "appu"/"baaki" are skipped).
_TRANSLIT_MARKERS = {
    "ta": {
        "kadan", "kadanam", "ezhuthu", "kuduthen", "kuduthuten", "vaanginen",
        "evvalavu", "kattiten", "onnu", "moonu", "naalu", "aindhu", "ezhu",
        "ettu", "onbadhu", "pathu", "latcham", "aayiram", "kanakku",
    },
    "kn": {
        "baree", "kotte", "kottidini", "padede", "eshtu", "madida", "ondu",
        "eradu", "mooru", "naalku", "ombattu", "hattu", "nooru", "savira",
        "ivattu", "graahaka", "paavathi",
    },
    "te": {
        "raayu", "ichchanu", "theesukunnaanu", "entha", "chesadu", "okati",
        "rendu", "moodu", "naalugu", "enimidi", "tommidi", "padi", "vandha",
        "veyyi", "laksha", "rupayalu", "ivvala", "chellimpu",
    },
}


def detect_language(text: str) -> str:
    """Best-effort language of a transcript: te / kn / ta / hi (default)."""
    if not text:
        return "hi"
    for lang, start, end in _SCRIPT_LANGUAGES:
        if any(start <= ch <= end for ch in text):
            return lang
    tokens = set(re.findall(r"[^\W\d_]+", text.lower(), re.UNICODE))
    for lang in ("ta", "kn", "te"):
        if tokens & _TRANSLIT_MARKERS[lang]:
            return lang
    return "hi"


def _say(lang: str, key: str, **kwargs) -> str:
    table = _REPLIES.get(lang, _REPLIES["hi"])
    template = table.get(key) or _REPLIES["hi"].get(key, key)
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


def _money(paise: int) -> str:
    rupees = paise / 100
    if rupees == int(rupees):
        return f"₹{int(rupees)}"
    return f"₹{rupees:.2f}"


async def understand(transcript: str) -> tuple[ExtractedIntent, str]:
    """Run the LLM when configured, otherwise the deterministic parser."""
    if settings.LLM_API_KEY:
        try:
            return await extract_intent(transcript), "llm"
        except Exception:
            return parse_text(transcript), "fallback (LLM unavailable)"
    return parse_text(transcript), "fallback (no LLM key)"


async def _customer_payload(db: AsyncSession, customer: Customer) -> dict:
    balance = await compute_balance(db, customer.id)
    return {
        "id": str(customer.id),
        "name": customer.name,
        "code": customer.customer_code,
        "balance_paise": balance,
        "balance_rupees": paise_to_rupees(balance),
    }


async def _resolve(db: AsyncSession, shop_id: uuid.UUID, name: str | None, transcript: str = ""):
    """Resolve by customer code (C0001) first, then by name."""
    haystack = f"{name or ''} {transcript or ''}"
    code_match = _CODE_RE.search(haystack)
    if code_match:
        by_code = await find_customer_by_code(db, shop_id, code_match.group(0))
        if by_code:
            return by_code, []
    if name and re.fullmatch(r"C\d{3,}", name.strip(), flags=re.IGNORECASE):
        by_code = await find_customer_by_code(db, shop_id, name.strip())
        if by_code:
            return by_code, []
        return None, []
    if not name:
        return None, []
    matches = await find_customers_by_name(db, shop_id, name)
    if len(matches) == 1:
        return matches[0], []
    return None, matches


async def demo_state(db: AsyncSession, shop_id: uuid.UUID) -> dict:
    """Snapshot used by the prototype UI."""
    result = await db.execute(select(Customer).where(Customer.shop_id == shop_id).order_by(Customer.name))
    customers = []
    for customer in result.scalars().all():
        customers.append(await _customer_payload(db, customer))

    today = today_in_tz()
    summary = await _summary(db, shop_id, today)
    recent = await db.execute(
        select(Transaction, Customer)
        .join(Customer, Transaction.customer_id == Customer.id)
        .where(Transaction.shop_id == shop_id)
        .order_by(Transaction.created_at.desc())
        .limit(8)
    )
    recent_items = [
        {
            "id": str(txn.id),
            "customer": customer.name,
            "type": txn.type.value,
            "amount_rupees": paise_to_rupees(txn.amount_paise),
            "status": txn.status.value,
            "created_at": txn.created_at.isoformat(),
        }
        for txn, customer in recent.all()
    ]
    return {"customers": customers, "summary": summary, "recent": recent_items}


async def _summary(db: AsyncSession, shop_id: uuid.UUID, target: date) -> dict:
    result = await db.execute(
        select(Transaction.type, func.sum(Transaction.amount_paise), func.count())
        .where(
            Transaction.shop_id == shop_id,
            Transaction.txn_date == target,
            Transaction.status == TxnStatus.active,
        )
        .group_by(Transaction.type)
    )
    credit = payment = count = 0
    for txn_type, amount, rows in result.all():
        if txn_type == TxnType.credit:
            credit = amount or 0
        else:
            payment = amount or 0
        count += rows
    return {
        "date": target.isoformat(),
        "total_credit_paise": credit,
        "total_payment_paise": payment,
        "net_paise": credit - payment,
        "transaction_count": count,
    }


async def handle_transcript(db: AsyncSession, shop_id: uuid.UUID, transcript: str) -> dict:
    """Execute one voice command end to end."""
    transcript = (transcript or "").strip()
    lang = detect_language(transcript)
    if not transcript:
        return {
            "transcript": "",
            "intent": "CLARIFY",
            "confidence": 0.0,
            "entities": {},
            "engine": "none",
            "reply_text": _say(lang, "empty"),
            "needs_clarification": True,
            "options": [],
        }

    intent_obj, engine = await understand(transcript)
    intent = intent_obj.intent
    entities = intent_obj.entities or {}
    name = (entities.get("customer_name") or entities.get("name") or "").strip() or None
    # LLM may return amount_paise or amount_rupees — accept both
    if entities.get("amount_paise") is not None:
        try:
            amount = float(entities["amount_paise"]) / 100.0
        except (TypeError, ValueError):
            amount = entities.get("amount_rupees", entities.get("amount"))
    else:
        amount = entities.get("amount_rupees", entities.get("amount"))

    result = {
        "transcript": transcript,
        "intent": intent,
        "confidence": intent_obj.confidence,
        "entities": entities,
        "engine": engine,
        "language": lang,
        "needs_clarification": False,
        "options": [],
        "customer": None,
        "transaction": None,
        "summary": None,
    }

    # ---- ADD_CUSTOMER ------------------------------------------------------
    if intent == "ADD_CUSTOMER":
        if not name:
            result.update(
                needs_clarification=True,
                reply_text=_say(lang, "ask_name"),
            )
            return result
        existing, matches = await _resolve(db, shop_id, name, transcript)
        if existing:
            result["customer"] = await _customer_payload(db, existing)
            result["reply_text"] = _say(lang, "already_exists", name=existing.name, code=existing.customer_code)
            return result
        if matches:
            result.update(
                needs_clarification=True,
                reply_text=_say(lang, "multi_customer", name=name),
                options=[c.name for c in matches],
            )
            return result
        customer = await create_customer(db, shop_id, name)  # provisional code (name3 + seed) until phone is added
        result["customer"] = await _customer_payload(db, customer)
        result["reply_text"] = _say(lang, "new_customer", name=customer.name, code=customer.customer_code)
        return result

    # ---- ADD_CREDIT / RECORD_PAYMENT --------------------------------------
    if intent in ("ADD_CREDIT", "RECORD_PAYMENT"):
        # Hard guards from edge-case invariants (never guess / never commit invalid)
        if entities.get("negation"):
            result.update(
                needs_clarification=True,
                reply_text=intent_obj.clarification_question
                or "Negation mili — payment/credit commit nahi kiya. Confirm karke boliye.",
            )
            return result
        if amount is None:
            result.update(
                needs_clarification=True,
                reply_text=intent_obj.clarification_question or _say(lang, "ask_amount"),
            )
            return result
        if not name:
            result.update(
                needs_clarification=True,
                reply_text=intent_obj.clarification_question or _say(lang, "ask_customer"),
            )
            return result

        customer, matches = await _resolve(db, shop_id, name, transcript)
        if matches:
            result.update(
                needs_clarification=True,
                reply_text=_say(lang, "multi_customer", name=name) + " " + ", ".join(c.name for c in matches),
                options=[c.name for c in matches],
            )
            return result
        if customer is None:
            # Don't auto-create when the utterance looked like a code lookup.
            if _CODE_RE.search(f"{name or ''} {transcript}"):
                result.update(
                    needs_clarification=True,
                    reply_text=_say(lang, "code_not_found"),
                )
                return result
            customer = await create_customer(db, shop_id, name)
            result["entities"]["customer_created"] = True

        amount_paise = rupees_to_paise(float(amount))
        if amount_paise <= 0:
            result.update(needs_clarification=True, reply_text=intent_obj.clarification_question or _say(lang, "amount_positive"))
            return result

        txn_date = today_in_tz()
        if intent == "ADD_CREDIT":
            txn = await add_credit(
                db, shop_id, customer.id, amount_paise, txn_date,
                transcript=transcript, confidence=intent_obj.confidence,
            )
        else:
            txn = await record_payment(
                db, shop_id, customer.id, amount_paise, txn_date,
                transcript=transcript, confidence=intent_obj.confidence,
            )

        payload = await _customer_payload(db, customer)
        result["customer"] = payload
        result["transaction"] = {
            "id": str(txn.id),
            "type": txn.type.value,
            "amount_paise": txn.amount_paise,
            "amount_rupees": paise_to_rupees(txn.amount_paise),
            "status": txn.status.value,
        }
        if intent == "ADD_CREDIT":
            result["reply_text"] = _say(
                lang, "credit_done",
                name=customer.name,
                amount=_money(amount_paise),
                balance=_money(payload["balance_paise"]),
            )
        else:
            result["reply_text"] = _say(
                lang, "payment_done",
                name=customer.name,
                amount=_money(amount_paise),
                balance=_money(payload["balance_paise"]),
            )
        return result

    # ---- CHECK_BALANCE -----------------------------------------------------
    if intent == "CHECK_BALANCE":
        customer, matches = await _resolve(db, shop_id, name, transcript)
        if matches:
            result.update(
                needs_clarification=True,
                reply_text=_say(lang, "multi_customer", name=name) + " " + ", ".join(c.name for c in matches),
                options=[c.name for c in matches],
            )
            return result
        if customer:
            payload = await _customer_payload(db, customer)
            result["customer"] = payload
            result["reply_text"] = _say(
                lang, "balance",
                name=customer.name,
                code=customer.customer_code,
                balance=_money(payload["balance_paise"]),
            )
            return result
        snapshot = await demo_state(db, shop_id)
        top = sorted(snapshot["customers"], key=lambda c: c["balance_paise"], reverse=True)[:3]
        listing = ", ".join(f"{c['name']} {_money(c['balance_paise'])}" for c in top) or _say(lang, "no_khata")
        result["reply_text"] = _say(lang, "top_dues", listing=listing)
        result["needs_clarification"] = True
        return result

    # ---- DAILY_SUMMARY -----------------------------------------------------
    if intent == "DAILY_SUMMARY":
        summary = await _summary(db, shop_id, today_in_tz())
        result["summary"] = summary
        result["reply_text"] = _say(
            lang, "daily_summary",
            credit=_money(summary["total_credit_paise"]),
            payment=_money(summary["total_payment_paise"]),
            count=summary["transaction_count"],
        )
        return result

    # ---- KHATA_SUMMARY -----------------------------------------------------
    if intent == "KHATA_SUMMARY":
        snapshot = await demo_state(db, shop_id)
        customers = snapshot["customers"]
        owed = [c for c in customers if c["balance_paise"] > 0]
        total_due = sum(c["balance_paise"] for c in owed)
        top = sorted(owed, key=lambda c: c["balance_paise"], reverse=True)[:3]
        top_line = ", ".join(f"{c['name']} {_money(c['balance_paise'])}" for c in top) or _say(lang, "no_due")
        result["summary"] = {"total_due_paise": total_due, "customers_with_dues": len(owed)}
        result["reply_text"] = _say(
            lang, "khata_summary",
            count=len(owed),
            total=_money(total_due),
            top=top_line,
        )
        return result

    # ---- STOCK_SUMMARY -----------------------------------------------------
    if intent == "STOCK_SUMMARY":
        inv = await db.execute(
            select(Item).where(
                Item.shop_id == shop_id,
                Item.status == ItemStatus.active.value,
            )
        )
        items = list(inv.scalars().all())
        low = [i for i in items if i.quantity <= i.minimum_quantity]
        if not items:
            result["reply_text"] = _say(lang, "inventory_empty")
            return result
        low_line = ", ".join(f"{i.name} {i.quantity}" for i in low[:4]) or _say(lang, "all_ok")
        result["reply_text"] = _say(
            lang, "stock_summary",
            items=len(items),
            low=len(low),
            low_line=low_line,
        )
        return result

    # ---- FIND_WHOLESALE -----------------------------------------------------
    if intent == "FIND_WHOLESALE":
        from app.marketplace.orchestrator import search_marketplace

        query = (entities.get("query") or transcript).strip()
        if entities.get("brand") or entities.get("product"):
            bits = [
                str(entities["brand"]) if entities.get("brand") else "",
                str(entities["product"]) if entities.get("product") else "",
                query,
            ]
            query = " ".join(b for b in bits if b).strip() or query
        search = await search_marketplace(
            db,
            shop_id=shop_id,
            query=query,
            purchase_type=entities.get("purchase_type") or "wholesale",
        )
        offers = search.offers[:3]
        result["marketplace"] = search.model_dump(mode="json")
        if not offers:
            result["reply_text"] = (
                "Koi wholesale offer nahi mila. Marketplace tab me search karke dekhiye."
            )
            return result
        lines = []
        for idx, offer in enumerate(offers, start=1):
            unit = offer.effective_unit_rupees
            unit_txt = f"₹{unit:.2f}/{offer.unit}" if unit is not None else "price TBD"
            lines.append(f"{idx}) {offer.supplier_name or offer.provider_name}: {unit_txt}")
        best = offers[0]
        result["reply_text"] = (
            f"{len(offers)} wholesale offers mile. "
            f"Sabse sasta unit rate: {best.supplier_name or best.provider_name}. "
            + " ".join(lines)
            + " Marketplace tab me open karke supplier pe ja sakte ho. Final price supplier site pe confirm karein."
        )
        return result

    # ---- CORRECT_LAST ------------------------------------------------------
    if intent == "CORRECT_LAST":
        customer, _ = await _resolve(db, shop_id, name, transcript)
        stmt = select(Transaction).where(
            Transaction.shop_id == shop_id, Transaction.status == TxnStatus.active
        )
        if customer:
            stmt = stmt.where(Transaction.customer_id == customer.id)
        stmt = stmt.order_by(Transaction.created_at.desc()).limit(1)
        last = (await db.execute(stmt)).scalars().first()
        if not last:
            result["reply_text"] = _say(lang, "no_last_entry")
            return result

        owner = await db.get(Customer, last.customer_id)
        new_amount = rupees_to_paise(float(amount)) if amount is not None else last.amount_paise
        corrected = await correct_transaction(db, last, new_amount_paise=new_amount)
        payload = await _customer_payload(db, owner)
        result["customer"] = payload
        result["transaction"] = {
            "id": str(corrected.id),
            "type": corrected.type.value,
            "amount_paise": corrected.amount_paise,
            "amount_rupees": paise_to_rupees(corrected.amount_paise),
            "status": corrected.status.value,
            "supersedes": str(last.id),
        }
        result["reply_text"] = _say(
            lang, "corrected",
            old=_money(last.amount_paise),
            new=_money(corrected.amount_paise),
            name=owner.name,
            balance=_money(payload["balance_paise"]),
        )
        return result

    # ---- CLARIFY -----------------------------------------------------------
    result["needs_clarification"] = True
    result["reply_text"] = intent_obj.clarification_question or _say(lang, "default_clarify")
    return result
