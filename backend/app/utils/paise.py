"""Money helpers. All amounts stored as integer paise (1 rupee = 100 paise)."""

def rupees_to_paise(rupees: float) -> int:
    return int(round(rupees * 100))

def paise_to_rupees(paise: int) -> float:
    return paise / 100.0

def format_rupees(paise: int) -> str:
    return f"{paise / 100:.2f}"
