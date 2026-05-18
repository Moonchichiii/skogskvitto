from __future__ import annotations

import logging
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.receipts.models import TaxYear

logger = logging.getLogger(__name__)


@transaction.atomic
def get_or_create_tax_year(
    *,
    owner: AbstractBaseUser,
    year: int,
    property_obj=None,
) -> TaxYear:
    """Return or create a TaxYear for this property+year.

    For backward compatibility, if property_obj is None, falls back to the
    user's default property. New code should always pass property_obj.
    """
    if property_obj is None:
        from apps.properties.services import get_or_create_default_property

        property_obj = get_or_create_default_property(owner)

    tax_year, _created = TaxYear.objects.get_or_create(
        property=property_obj,
        year=year,
        defaults={
            "owner": owner,
            "status": TaxYear.Status.OPEN,
        },
    )
    return tax_year


@transaction.atomic
def allocate_ordinal_number(*, property_obj, tax_year) -> int:
    """Allocate the next ordinal_number for (property, tax_year) atomically.

    Uses SELECT FOR UPDATE to serialize concurrent allocators. The unique
    constraint is the safety net. Numbers may have gaps over time when
    receipts are deleted — this is intentional, gaps don't matter for
    bookkeeping (the accountant sees what's there in order).
    """
    from apps.receipts.models import Receipt

    last = (
        Receipt.objects.select_for_update()
        .filter(property=property_obj, tax_year=tax_year)
        .aggregate(max_n=models.Max("ordinal_number"))
    )
    return (last["max_n"] or 0) + 1


@transaction.atomic
def update_receipt(
    *,
    receipt: "Receipt",
    vendor: str,
    total_amount: "Decimal",
    vat_amount: "Decimal",
    date: "date_type",
    category: str,
    note: str,
) -> "Receipt":
    """Update a receipt's editable fields.

    Raises:
        ValidationError: if the receipt's tax_year is locked, or values invalid.
    """
    assert_receipt_editable(receipt)

    receipt.vendor = vendor
    receipt.total_amount = total_amount
    receipt.vat_amount = vat_amount
    receipt.date = date  # may trigger tax_year recompute in save()
    receipt.category = category
    receipt.note = note
    receipt.full_clean()
    receipt.save()

    logger.info(
        "receipts.update_receipt",
        extra={"user_id": receipt.owner_id, "receipt_id": receipt.pk},
    )
    return receipt


@transaction.atomic
def delete_receipt(*, receipt: "Receipt") -> dict:
    """Hard-delete a receipt. The ordinal_number is not reused.

    Returns a small dict with metadata so the view can show a confirmation
    toast like "Nr:5 raderat".
    """
    assert_receipt_editable(receipt)

    metadata = {
        "ordinal_number": receipt.ordinal_number,
        "vendor": receipt.vendor,
        "tax_year": receipt.tax_year.year if receipt.tax_year_id else None,
    }
    receipt_id = receipt.pk

    receipt.delete()

    logger.info(
        "receipts.delete_receipt",
        extra={
            "user_id": receipt.owner_id,
            "receipt_id": receipt_id,
            **metadata,
        },
    )
    return metadata


def assert_receipt_editable(receipt: "Receipt") -> None:
    """Raise ValidationError if this receipt is in a locked tax year."""
    if receipt.tax_year_id and receipt.tax_year.is_locked:
        raise ValidationError(
            f"Inkomstår {receipt.tax_year.year} är låst. "
            "Lås upp året innan du redigerar kvittot."
        )


@transaction.atomic
def lock_tax_year(*, tax_year: TaxYear) -> TaxYear:
    """Lock a tax year. Idempotent — locking an already-locked year is a no-op."""
    if tax_year.is_locked:
        return tax_year

    tax_year.status = TaxYear.Status.LOCKED
    tax_year.locked_at = timezone.now()
    tax_year.save(update_fields=["status", "locked_at", "updated_at"])
    return tax_year


@transaction.atomic
def unlock_tax_year(*, tax_year: TaxYear) -> TaxYear:
    """Unlock a tax year. Idempotent — unlocking an already-open year is a no-op."""
    if tax_year.is_open:
        return tax_year

    tax_year.status = TaxYear.Status.OPEN
    tax_year.locked_at = None
    tax_year.save(update_fields=["status", "locked_at", "updated_at"])
    return tax_year
