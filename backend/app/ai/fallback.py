"""Deterministic Hinglish intent parser.

Used when no LLM key is configured, or when the LLM call fails. It is
deliberately simple and rule-based: good enough for a live prototype demo,
never a replacement for the LLM path.
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
_MULTIPLIERS = {"sau": 100, "hundred": 100, "hazaar": 1000, "hajar": 1000, "thousand": 1000, "lakh": 100000}

_NUMBER_WORDS = set(_UNITS) | set(_MULTIPLIERS)

# --- intent keywords --------------------------------------------------------
_CORRECT_WORDS = {"galat", "galti", "correction", "correct", "sudhar", "sudharo", "badlo", "change", "wapas"}
_PAYMENT_WORDS = {
    "diya", "diye", "di", "jama", "jamaa", "jamaa", "payment", "pay", "paid",
    "chuka", "chukaya", "chukaaya", "wapas", "return", "de", "dene", "aaya", "aaye",
}
_CREDIT_WORDS = {
    "udhaar", "udhar", "udhaari", "likho", "likh", "likha", "chadha", "chadhao",
    "le", "liya", "gaya", "gaye", "credit", "khata", "khate", "due", "baaki",
}
_BALANCE_WORDS = {"balance", "baaki", "baki", "hisaab", "hisab", "kitna", "kitne", "bacha", "bachega"}
_SUMMARY_WORDS = {"summary", "report", "total", "aaj", "din", "hisab", "hisaab"}
_STOCK_WORDS = {"stock", "inventory", "maal", "samaan", "stash", "store"}
_KHATA_WORDS = {"khata", "ledger", "udhaar", "dues", "baaki"}
_ADD_CUSTOMER_WORDS = {"naya", "nayi", "new", "banao", "banado", "add", "kholo", "khata"}
_NAME_MARKERS = {"ka", "ko", "ne", "se", "ki", "ke"}
_STOPWORDS = (
    _NUMBER_WORDS
    | _CORRECT_WORDS
    | _PAYMENT_WORDS
    | _CREDIT_WORDS
    | _BALANCE_WORDS
    | _SUMMARY_WORDS
    | _ADD_CUSTOMER_WORDS
    | {"rupaye", "rupee", "rupees", "rs", "ka", "ko", "ne", "se", "ki", "ke", "hai", "tha", "the",
       "nahi", "nahin", "abhi", "mera", "mere", "uska", "uske", "ka", "aur", "please", "plz", "kar",
       "karo", "karna", "hain", "ho", "gaya", "gayi", "wala", "wali", "aaj", "kal", "customer",
       "customers", "banda", "aadmi"}
)


def parse_number(text: str) -> int | None:
    """Extract the first amount from digits or Hindi/English number words."""
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
    digits = re.findall(r"\d[\d,]*", text)
    if len(digits) >= 2:
        try:
            return int(digits[-1].replace(",", ""))
        except ValueError:
            pass
    return parse_number(text)


def _normalise(text: str) -> str:
    return " ".join(text.lower().replace("₹", " ").split())


def _extract_name(text: str) -> str | None:
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    # Strategy 1: name immediately before a marker word (ka/ko/ne/se/ke/ki)
    for i, token in enumerate(tokens):
        if token in _NAME_MARKERS and i > 0:
            candidate = tokens[i - 1]
            if candidate not in _STOPWORDS and len(candidate) > 1:
                return candidate.capitalize()
    # Strategy 2: name immediately after a marker ("ka Ramesh")
    for i, token in enumerate(tokens):
        if token in _NAME_MARKERS and i + 1 < len(tokens):
            candidate = tokens[i + 1]
            if candidate not in _STOPWORDS and len(candidate) > 1:
                return candidate.capitalize()
    # Strategy 3: first meaningful non-keyword, non-number word
    for token in tokens:
        if token not in _STOPWORDS and token not in _NUMBER_WORDS and len(token) > 1:
            return token.capitalize()
    return None


def _is_add_customer_utterance(tokens: set[str], amount: int | None) -> bool:
    """True for 'add customer X', 'X add karo', 'naya khata X', etc. (no credit amount)."""
    add_verbs = {"add", "banao", "banado", "kholo", "register", "create"}
    new_words = {"naya", "nayi", "new"}
    customer_words = {"customer", "customers", "khata"}
    # Explicit new-customer phrasing always wins (even if a number slipped in).
    if (tokens & new_words) and (tokens & (customer_words | add_verbs | {"khata"})):
        return True
    # Without an amount, add/banao/kholo means register a customer, not credit.
    if amount is None and (tokens & add_verbs):
        return True
    if amount is None and (tokens & customer_words) and (tokens & (add_verbs | new_words)):
        return True
    return False


def parse_text(text: str) -> ExtractedIntent:
    """Parse a Hinglish utterance into a structured intent."""
    norm = _normalise(text)
    tokens = set(re.findall(r"[a-zA-Z]+", norm))
    amount = parse_number(norm)
    name = _extract_name(text)

    # Correction: "nahi 340 nahi 430 tha", "galat likha", "correction"
    if (tokens & _CORRECT_WORDS) or ("nahi" in tokens and "tha" in tokens):
        return ExtractedIntent(
            intent="CORRECT_LAST",
            confidence=0.8,
            entities={"customer_name": name, "amount_rupees": parse_corrected_number(norm)},
        )

    if _is_add_customer_utterance(tokens, amount):
        return ExtractedIntent(
            intent="ADD_CUSTOMER",
            confidence=0.9,
            entities={"customer_name": name, "name": name},
        )

    if tokens & _BALANCE_WORDS and not (tokens & _PAYMENT_WORDS):
        if name or "kitna" in tokens or "balance" in tokens:
            return ExtractedIntent(intent="CHECK_BALANCE", confidence=0.85, entities={"customer_name": name})

    if tokens & _STOCK_WORDS and (tokens & _SUMMARY_WORDS or "kitna" in tokens or "low" in tokens or "kam" in tokens):
        return ExtractedIntent(intent="STOCK_SUMMARY", confidence=0.9, entities={})

    if tokens & _KHATA_WORDS and (tokens & _SUMMARY_WORDS or "summary" in tokens):
        return ExtractedIntent(intent="KHATA_SUMMARY", confidence=0.9, entities={})

    if tokens & _SUMMARY_WORDS and not name and amount is None:
        return ExtractedIntent(intent="DAILY_SUMMARY", confidence=0.85, entities={})

    if tokens & _PAYMENT_WORDS:
        if amount is None:
            return ExtractedIntent(
                intent="CLARIFY",
                confidence=0.4,
                entities={"customer_name": name},
                clarification_needed=True,
                clarification_question=f"Kitne rupaye {name or ''} se aaye? Amount dobara boliye.".strip(),
            )
        return ExtractedIntent(
            intent="RECORD_PAYMENT",
            confidence=0.9,
            entities={"customer_name": name, "amount_rupees": amount},
        )

    if amount is not None and (tokens & _CREDIT_WORDS or name):
        return ExtractedIntent(
            intent="ADD_CREDIT",
            confidence=0.9,
            entities={"customer_name": name, "amount_rupees": amount},
        )

    if amount is not None:
        return ExtractedIntent(
            intent="ADD_CREDIT",
            confidence=0.6,
            entities={"customer_name": name, "amount_rupees": amount},
        )

    if name and not amount:
        return ExtractedIntent(
            intent="CLARIFY",
            confidence=0.5,
            entities={"customer_name": name},
            clarification_needed=True,
            clarification_question=f"{name} ka kitne rupaye? Amount boliye.",
            clarification_options=[],
        )

    return ExtractedIntent(
        intent="CLARIFY",
        confidence=0.2,
        entities={},
        clarification_needed=True,
        clarification_question="Samajh nahi aaya. Dobara boliye - jaise 'Ramesh ka 340 rupaye udhaar'.",
        clarification_options=[],
    )
