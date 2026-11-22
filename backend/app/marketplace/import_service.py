"""Authorized supplier catalogue CSV/Excel import."""
from __future__ import annotations

import csv
import io
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.marketplace.models import MarketplaceListing, MarketplaceProvider, SupplierProfile
from app.marketplace.schemas import ImportReport

REQUIRED_COLUMNS = {"product_name", "wholesale_price"}


def _to_paise(value: Any) -> int:
    text = str(value).strip().replace(",", "").replace("₹", "")
    if not text:
        raise ValueError("empty price")
    return int(round(float(text) * 100))


def _parse_rows(raw: bytes, filename: str) -> list[dict[str, str]]:
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xls")):
        try:
            import openpyxl
        except ImportError as exc:
            raise ValueError("Excel import requires openpyxl. Upload CSV instead.") from exc
        wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(h or "").strip().lower() for h in next(rows_iter)]
        out = []
        for row in rows_iter:
            item = {headers[i]: ("" if row[i] is None else str(row[i]).strip()) for i in range(len(headers))}
            if any(item.values()):
                out.append(item)
        return out

    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return [{(k or "").strip().lower(): (v or "").strip() for k, v in row.items()} for row in reader]


async def import_supplier_catalogue(
    db: AsyncSession,
    *,
    shop_id: UUID,
    raw: bytes,
    filename: str,
    supplier_name: str = "Imported Supplier",
) -> ImportReport:
    try:
        rows = _parse_rows(raw, filename)
    except Exception as exc:
        return ImportReport(imported=0, rejected=0, errors=[{"row": 0, "error": str(exc)}])

    if not rows:
        return ImportReport(imported=0, rejected=0, errors=[{"row": 0, "error": "No rows found"}])

    headers = set(rows[0].keys())
    # accept aliases
    alias = {
        "product": "product_name",
        "name": "product_name",
        "title": "product_name",
        "price": "wholesale_price",
        "price_rupees": "wholesale_price",
        "mrp": "wholesale_price",
        "qty": "package_size",
        "package": "package_size",
        "gst": "gst_percent",
        "delivery": "delivery_charges",
        "sku_id": "sku",
    }
    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        norm = dict(row)
        for src, dst in alias.items():
            if src in norm and dst not in norm:
                norm[dst] = norm[src]
        normalized_rows.append(norm)
    headers = set(normalized_rows[0].keys())
    if not REQUIRED_COLUMNS.issubset(headers):
        return ImportReport(
            imported=0,
            rejected=0,
            errors=[{"row": 0, "error": f"Missing columns: {sorted(REQUIRED_COLUMNS - headers)}"}],
        )

    provider = (
        await db.execute(
            select(MarketplaceProvider).where(MarketplaceProvider.code == "independent_wholesale")
        )
    ).scalar_one_or_none()
    if provider is None:
        provider = MarketplaceProvider(
            code="independent_wholesale",
            name="Independent Wholesalers",
            category="wholesale",
            status="IMPORT_READY",
            auth_notes="Imported catalogues",
        )
        db.add(provider)
        await db.flush()

    supplier = SupplierProfile(
        shop_id=shop_id,
        name=supplier_name or "Imported Supplier",
        provider_code="independent_wholesale",
    )
    db.add(supplier)
    await db.flush()

    imported = 0
    rejected = 0
    errors: list[dict[str, Any]] = []

    for idx, row in enumerate(normalized_rows, start=2):
        try:
            name = row.get("product_name") or ""
            if not name:
                raise ValueError("product_name required")
            price_paise = _to_paise(row.get("wholesale_price"))
            package_size = float(row.get("package_size") or row.get("package_quantity") or 1)
            unit = (row.get("unit") or "kg").lower()
            moq = int(float(row.get("moq") or 1))
            gst = float(row["gst_percent"]) if row.get("gst_percent") else None
            delivery = _to_paise(row["delivery_charges"]) if row.get("delivery_charges") else None
            sku = row.get("sku") or f"imp-{uuid4().hex[:10]}"
            stock = row.get("stock") or row.get("stock_availability") or "in_stock"
            url = row.get("product_url") or row.get("url") or None

            listing = MarketplaceListing(
                shop_id=shop_id,
                provider_id=provider.id,
                supplier_id=supplier.id,
                external_product_id=sku,
                title=name,
                brand=row.get("brand") or None,
                package_quantity=package_size,
                unit=unit,
                moq=moq,
                case_size=int(float(row.get("case_size") or 1)),
                base_price_paise=price_paise,
                gst_percent=gst,
                delivery_charges_paise=delivery,
                stock_status=stock,
                product_url=url,
                price_source="imported",
            )
            db.add(listing)
            imported += 1
        except Exception as exc:
            rejected += 1
            errors.append({"row": idx, "error": str(exc)})

    await db.commit()
    return ImportReport(imported=imported, rejected=rejected, errors=errors[:50])
