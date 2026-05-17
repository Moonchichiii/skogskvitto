"""Form-style parsing helpers for the scan-confirm view.

Not a Django ModelForm — Receipt has too many auto-derived fields. This is a
hand-rolled validator that turns raw POST strings into typed values, returning
either a clean dict or a dict of error messages keyed by field.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type, datetime
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True, slots=True)
class ConfirmFormData:
    vendor: str
    total_amount: Decimal
    vat_amount: Decimal
    date: date_type
    category: str
    note: str


def _parse_decimal(raw: str) -> Decimal | None:
    cleaned = (raw or "").replace(",", ".").replace(" ", "").strip()
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _parse_date(raw: str) -> date_type | None:
    cleaned = (raw or "").strip()
    if not cleaned:
        return None
    try:
        return datetime.strptime(cleaned, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_confirm_form(post_data: dict[str, str]) -> tuple[ConfirmFormData | None, dict[str, str]]:
    errors: dict[str, str] = {}

    vendor = (post_data.get("vendor") or "").strip()[:255]

    total_amount = _parse_decimal(post_data.get("total_amount", ""))
    if total_amount is None:
        errors["total_amount"] = "Ange ett giltigt belopp."
    elif total_amount < Decimal("0"):
        errors["total_amount"] = "Belopp måste vara noll eller positivt."

    vat_amount = _parse_decimal(post_data.get("vat_amount", ""))
    if vat_amount is None:
        vat_amount = Decimal("0.00")
    elif vat_amount < Decimal("0"):
        errors["vat_amount"] = "Moms måste vara noll eller positiv."

    if total_amount is not None and vat_amount is not None and vat_amount > total_amount:
        errors["vat_amount"] = "Moms kan inte överstiga totalbelopp."

    parsed_date = _parse_date(post_data.get("date", ""))
    if parsed_date is None:
        errors["date"] = "Ange ett giltigt datum (YYYY-MM-DD)."

    category = (post_data.get("category") or "").strip()[:100]
    note = (post_data.get("note") or "").strip()

    if errors:
        return None, errors

    assert total_amount is not None
    assert parsed_date is not None

    return ConfirmFormData(
        vendor=vendor,
        total_amount=total_amount,
        vat_amount=vat_amount,
        date=parsed_date,
        category=category,
        note=note,
    ), {}
