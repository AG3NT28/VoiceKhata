"""Deterministic Hinglish intent parser trained against edge-case dataset.

Used when no LLM key is configured, or when the LLM call fails. Rules encode
the labelled Voice Khata training examples / invariants (no guessed amount,
direction, or customer; refuse future/negated payments).
"""
from __future__ import annotations

import re

from app.ai.extraction import ExtractedIntent

# --- number words -----------------------------------------------------------
_UNITS = {
    "shunya": 0, "zero": 0,
    "ek": 1, "one": 1,
    "do": 2, "two": 2,
    "teen": 3, "three": 3,
    "char": 4, "chaar": 4, "four": 4,
    "paanch": 5, "panch": 5, "five": 5,
    "chhah": 6, "chhe": 6, "che": 6, "six": 6,
    "saat": 7, "seven": 7,
    "aath": 8, "eight": 8,
    "nau": 9, "nine": 9,
    "das": 10, "ten": 10,
    "gyarah": 11, "eleven": 11,
    "barah": 12, "twelve": 12,
    "terah": 13, "thirteen": 13,
    "chaudah": 14, "fourteen": 14,
    "pandrah": 15, "fifteen": 15,
    "solah": 16, "sixteen": 16,
    "satrah": 17, "seventeen": 17,
    "atharah": 18, "eighteen": 18,
    "unnis": 19, "nineteen": 19,
    "bees": 20, "twenty": 20,
    "tees": 30, "thirty": 30,
    "chalis": 40, "forty": 40,
    "pachaas": 50, "pachas": 50, "fifty": 50,
    "saath": 60, "sixty": 60,
    "sattar": 70, "seventy": 70,
    "assi": 80, "eighty": 80,
    "nabbe": 90, "ninety": 90,
}
_MULTIPLIERS = {
    "sau": 100, "hundred": 100,
    "hazaar": 1000, "hajar": 1000, "thousand": 1000,
    "lakh": 100000, "k": 1000,
}
_NUMBER_WORDS = set(_UNITS) | set(_MULTIPLIERS) | {"and"}

_CORRECT_WORDS = {"galat", "galti", "correction", "correct", "sudhar", "sudharo", "badlo", "change"}
_PAYMENT_WORDS = {
    "diya", "diye", "di", "jama", "jamaa", "payment", "pay", "paid",
    "chuka", "chukaya", "chukaaya", "aaya", "aaye",
}
_CREDIT_WORDS = {
    "udhaar", "udhar", "udhaari", "chadha", "chadhao",
    "credit", "due",
}
_WEAK_WRITE_WORDS = {"likho", "likh", "likha", "daalo", "daal", "add"}
_BALANCE_WORDS = {"balance", "baaki", "baki", "hisaab", "hisab", "kitna", "kitne", "bacha", "bachega", "total", "batao"}
_SUMMARY_WORDS = {"summary", "report", "total", "aaj", "din"}
_STOCK_WORDS = {"stock", "inventory", "maal", "samaan", "stash", "store"}
_WHOLESALE_WORDS = {
    "wholesale", "thok", "थोक", "supplier", "jumbotail", "udaan", "ondc",
    "bulk", "carton", "moq", "bazaar", "market", "rate", "rates", "deal",
}
_FIND_WORDS = {"find", "search", "khojo", "dhundo", "compare", "sasta", "cheapest"}
_KHATA_WORDS = {"khata", "ledger", "udhaar", "dues", "baaki"}
_ADD_CUSTOMER_WORDS = {"naya", "nayi", "new", "banao", "banado", "add", "kholo", "khata"}
_FUTURE_WORDS = {"dega", "denge", "dengi", "karega", "karenge", "hoga", "tomorrow", "will"}
_CANCEL_WORDS = {"mat", "cancel", "rok", "roko", "hatado", "hatao", "undo"}
_NEGATION = {"nahi", "nahin", "na", "not", "never"}
_NAME_MARKERS = {"ka", "ko", "ne", "se", "ki", "ke"}
_STOPWORDS = (
    _NUMBER_WORDS
    | _CORRECT_WORDS
    | _PAYMENT_WORDS
    | _CREDIT_WORDS
    | _WEAK_WRITE_WORDS
    | _BALANCE_WORDS
    | _SUMMARY_WORDS
    | _ADD_CUSTOMER_WORDS
    | _FUTURE_WORDS
    | _CANCEL_WORDS
    | _NEGATION
    | {"rupaye", "rupee", "rupees", "rs", "ka", "ko", "ne", "se", "ki", "ke", "hai", "tha", "the",
       "abhi", "mera", "mere", "uska", "uske", "aur", "please", "plz", "kar",
       "karo", "karna", "hain", "ho", "gaya", "gayi", "wala", "wali", "aaj", "kal", "customer",
       "customers", "banda", "aadmi", "maine", "usne", "same", "entry", "dobara", "bhej", "raha",
       "hoon", "mein", "wapas", "liye", "liya", "le", "de", "dene", "return"}
)


def parse_number(text: str) -> int | None:
    """Extract amount in rupees from digits, 2.5K style, or number words."""
    # Compact forms: 2.5K / 2.5k / 1,200
    compact = re.search(r"(\d+(?:\.\d+)?)\s*([kK])\b", text)
    if compact:
        return int(float(compact.group(1)) * 1000)
    digits = re.search(r"\d[\d,]*", text)
    if digits:
        try:
            return int(digits.group(0).replace(",", ""))
        except ValueError:
            pass

    total = 0
    current = 0
    found = False
    for token in re.findall(r"[a-zA-Z]+", text.lower()):
        if token in {"and"}:
            continue
        if token in _UNITS:
            current += _UNITS[token]
            found = True
        elif token in _MULTIPLIERS:
            mult = _MULTIPLIERS[token]
            current = (current or 1) * mult
            if mult >= 1000:
                total += current
                current = 0
            found = True
    value = total + current
    return value if found and value > 0 else None


def parse_corrected_number(text: str) -> int | None:
    """For corrections the *last* amount spoken is the intended one."""
    compact = re.findall(r"(\d+(?:\.\d+)?)\s*[kK]\b", text)
    if len(compact) >= 2:
        return int(float(compact[-1]) * 1000)
    digits = re.findall(r"\d[\d,]*", text)
    if len(digits) >= 2:
        try:
            return int(digits[-1].replace(",", ""))
        except ValueError:
            pass
    # "340 nahi 430"
    m = re.search(r"(\d[\d,]*)\s*(?:nahi|nahin|not)\s*(\d[\d,]*)", text.lower())
    if m:
        return int(m.group(2).replace(",", ""))
    return parse_number(text)


def _normalise(text: str) -> str:
    return " ".join(text.lower().replace("₹", " ").split())


def _extract_name(text: str) -> str | None:
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    for i, token in enumerate(tokens):
        if token in _NAME_MARKERS and i > 0:
            candidate = tokens[i - 1]
            if candidate not in _STOPWORDS and len(candidate) > 1:
                return candidate.capitalize()
    for i, token in enumerate(tokens):
        if token in _NAME_MARKERS and i + 1 < len(tokens):
            candidate = tokens[i + 1]
            if candidate not in _STOPWORDS and len(candidate) > 1:
                return candidate.capitalize()
    for token in tokens:
        if token not in _STOPWORDS and token not in _NUMBER_WORDS and len(token) > 1:
            return token.capitalize()
    return None


def _is_add_customer_utterance(tokens: set[str], amount: int | None) -> bool:
    add_verbs = {"add", "banao", "banado", "kholo", "register", "create"}
    new_words = {"naya", "nayi", "new"}
    customer_words = {"customer", "customers", "khata"}
    if (tokens & new_words) and (tokens & (customer_words | add_verbs)):
        return True
    if amount is None and (tokens & add_verbs) and not (tokens & (_CREDIT_WORDS | _PAYMENT_WORDS | {"udhaar"})):
        # "mat add karo" is cancel, not add-customer
        if tokens & _CANCEL_WORDS or tokens & _NEGATION:
            return False
        return True
    if amount is None and (tokens & customer_words) and (tokens & (add_verbs | new_words)):
        return True
    return False


def _clarify(name: str | None, amount: int | None, question: str, *, confidence: float = 0.5) -> ExtractedIntent:
    entities: dict = {}
    if name:
        entities["customer_name"] = name
    if amount is not None:
        entities["amount_rupees"] = amount
        entities["amount_paise"] = int(amount) * 100
    return ExtractedIntent(
        intent="CLARIFY",
        confidence=confidence,
        entities=entities,
        clarification_needed=True,
        clarification_question=question,
        clarification_options=[],
    )


def parse_text(text: str) -> ExtractedIntent:
    """Parse a Hinglish utterance into a structured intent."""
    norm = _normalise(text)
    tokens = set(re.findall(r"[a-zA-Z]+", norm))
    amount = parse_number(norm)
    name = _extract_name(text)

    # Cancel / abort pending commit
    if (tokens & _CANCEL_WORDS and tokens & (_NEGATION | {"add", "karo"})) or norm.strip() in {
        "nahi mat add karo",
        "mat add karo",
        "cancel",
    }:
        return _clarify(None, None, "Theek hai, kuch commit nahi kiya.", confidence=0.9)

    # Negated payment: "300 nahi diye"
    if (tokens & _NEGATION) and (tokens & _PAYMENT_WORDS) and "tha" not in tokens:
        return _clarify(name, amount, "Payment record nahi kiya. Confirm karke boliye.", confidence=0.85)

    # Dispute balance review (before generic "galat" correction)
    if ("galat" in tokens or "galti" in tokens) and (tokens & {"balance", "baaki", "baki", "hisaab", "total"}):
        return ExtractedIntent(
            intent="CHECK_BALANCE",
            confidence=0.85,
            entities={"customer_name": name},
            clarification_needed=False,
        )

    # Daily credit total: "Aaj kitna udhaar gaya"
    if ("aaj" in tokens or "today" in tokens) and ("udhaar" in tokens or "udhar" in tokens) and (
        "kitna" in tokens or "kitne" in tokens or "gaya" in tokens or "total" in tokens
    ):
        return ExtractedIntent(intent="DAILY_SUMMARY", confidence=0.9, entities={})

    # Correction: "nahi 340 nahi 430", "500 nahi 550 tha" (amount correction, not balance dispute)
    if re.search(r"\d\s*(?:nahi|nahin|not)\s*\d", norm) or (
        ("nahi" in tokens and "tha" in tokens) and amount is not None
    ) or ((tokens & _CORRECT_WORDS) and amount is not None):
        corrected = parse_corrected_number(norm)
        entities = {"customer_name": name, "field": "amount"}
        if corrected is not None:
            entities["amount_rupees"] = corrected
            entities["amount_paise"] = corrected * 100
            entities["new_value"] = corrected * 100
        return ExtractedIntent(intent="CORRECT_LAST", confidence=0.85, entities=entities)

    # Future promise — do not record payment
    if tokens & _FUTURE_WORDS:
        return _clarify(
            name,
            amount,
            "Ye future promise lag raha hai. Abhi payment record nahi karunga. Confirm karein?",
            confidence=0.9,
        )

    if _is_add_customer_utterance(tokens, amount):
        return ExtractedIntent(
            intent="ADD_CUSTOMER",
            confidence=0.9,
            entities={"customer_name": name, "name": name},
        )

    # Multi-customer same utterance → clarify allocation
    joined = " " + norm + " "
    if " aur " in joined and amount is not None and (tokens & (_PAYMENT_WORDS | _CREDIT_WORDS | _WEAK_WRITE_WORDS)):
        return _clarify(
            name,
            amount,
            "Do customers ka zikr hai. Alag-alag amount confirm karein.",
            confidence=0.75,
        )

    # Ambiguous direction: "Maine X se liye"
    if "maine" in tokens and ("se" in tokens) and amount is not None:
        return _clarify(
            name,
            amount,
            "Credit hai ya payment? Clear boliye.",
            confidence=0.7,
            )

    # Refund / adjustment wording
    if "wapas" in tokens and amount is not None:
        return _clarify(
            name,
            amount,
            "Refund / adjustment confirm karein — payment nahi samjha.",
            confidence=0.75,
        )

    if tokens & _BALANCE_WORDS and not (tokens & _PAYMENT_WORDS):
        if name or "kitna" in tokens or "balance" in tokens or "total" in tokens or "batao" in tokens:
            return ExtractedIntent(intent="CHECK_BALANCE", confidence=0.85, entities={"customer_name": name})

    if tokens & _STOCK_WORDS and (tokens & _SUMMARY_WORDS or "kitna" in tokens or "low" in tokens or "kam" in tokens):
        return ExtractedIntent(intent="STOCK_SUMMARY", confidence=0.9, entities={})

    if (tokens & _WHOLESALE_WORDS) or (
        (tokens & _FIND_WORDS)
        and any(w in norm for w in ("oil", "atta", "rice", "sugar", "dal", "tel", "chawal", "chini", "kg", "litre"))
    ):
        return ExtractedIntent(
            intent="FIND_WHOLESALE",
            confidence=0.9,
            entities={"query": text.strip(), "purchase_type": "wholesale"},
        )

    if tokens & _KHATA_WORDS and (tokens & _SUMMARY_WORDS or "summary" in tokens):
        return ExtractedIntent(intent="KHATA_SUMMARY", confidence=0.9, entities={})

    if (tokens & {"aaj", "udhaar"} and ("kitna" in tokens or "gaya" in tokens)) or (
        tokens & _SUMMARY_WORDS and not name and amount is None and "batao" not in tokens
    ):
        return ExtractedIntent(intent="DAILY_SUMMARY", confidence=0.85, entities={})

    # Zero / invalid amount
    if amount == 0:
        return _clarify(name, 0, "Amount zero nahi ho sakta. Sahi amount boliye.", confidence=0.9)

    # Strong payment
    if tokens & _PAYMENT_WORDS:
        if amount is None:
            return _clarify(name, None, f"Kitne rupaye {name or ''} se aaye? Amount boliye.".strip())
        if not name:
            return _clarify(None, amount, "Kis customer ne payment diya? Naam boliye.")
        return ExtractedIntent(
            intent="RECORD_PAYMENT",
            confidence=0.9,
            entities={"customer_name": name, "amount_rupees": amount, "amount_paise": amount * 100},
        )

    # Strong credit (udhaar/credit) — amount required
    if tokens & _CREDIT_WORDS:
        if amount is None:
            return _clarify(name, None, f"{name or 'Customer'} ka kitne rupaye udhaar? Amount boliye.")
        if not name:
            return _clarify(None, amount, "Kiska udhaar? Customer naam boliye.")
        return ExtractedIntent(
            intent="ADD_CREDIT",
            confidence=0.9,
            entities={"customer_name": name, "amount_rupees": amount, "amount_paise": amount * 100},
        )

    # Weak write verb without clear credit/payment → ask direction (TR005)
    if amount is not None and (tokens & _WEAK_WRITE_WORDS):
        return _clarify(
            name,
            amount,
            "Credit (udhaar) ya payment? Clear boliye.",
            confidence=0.65,
        )

    if amount is not None and name:
        # Amount + name but no direction words → clarify (safer than guessing)
        return _clarify(
            name,
            amount,
            "Credit ya payment? Clear boliye.",
            confidence=0.55,
        )

    if amount is not None and not name:
        return _clarify(None, amount, "Kis customer ke liye? Naam boliye.")

    if name and not amount:
        return _clarify(name, None, f"{name} ka kitne rupaye? Amount boliye.")

    return _clarify(
        None,
        None,
        "Samajh nahi aaya. Dobara boliye — jaise 'Ramesh ka 340 rupaye udhaar'.",
        confidence=0.2,
    )
