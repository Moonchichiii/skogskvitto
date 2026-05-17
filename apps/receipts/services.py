from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.receipts.models import TaxYear


@transaction.atomic
def get_or_create_tax_year(*, owner: AbstractBaseUser, year: int) -> TaxYear:
    """Idempotent fetch-or-create of a TaxYear for the given user/year.

    Used by Receipt.save() to ensure every receipt has a parent TaxYear.
    Race-safe via the unique constraint on (owner, year).
    """
    tax_year, _ = TaxYear.objects.get_or_create(
        owner=owner,
        year=year,
        defaults={"status": TaxYear.Status.OPEN},
    )
    return tax_year


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


def assert_receipt_editable(*, tax_year: TaxYear) -> None:
    """Guard for receipt edit/delete operations.

    Raises ValidationError if the parent tax year is locked. Note: NEW
    receipts are always allowed even if the year is locked (only existing
    ones are frozen).
    """
    if tax_year.is_locked:
        raise ValidationError(
            f"Inkomståret {tax_year.year} är låst. "
            "Lås upp inkomståret innan du redigerar eller raderar kvitton."
        )
