"""Customer disambiguation helpers."""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.khata.customers import find_customer_by_code, find_customers_by_name

async def resolve_customer(db: AsyncSession, shop_id: UUID, identifier: str):
    """
    Returns (customer, candidates, needs_clarification).
    - If identifier looks like a code (starts with C + digits), match by code.
    - Else match by name; if multiple, return candidates for clarification.
    """
    ident = identifier.strip()
    if ident.upper().startswith("C") and ident[1:].isdigit():
        cust = await find_customer_by_code(db, shop_id, ident)
        if cust:
            return cust, [], False
        return None, [], True

    matches = await find_customers_by_name(db, shop_id, ident)
    if len(matches) == 0:
        return None, [], True
    if len(matches) == 1:
        return matches[0], [], False
    return None, matches, True
