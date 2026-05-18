from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


def receipt_image_upload_path(_: "Receipt", filename: str) -> str:
    suffix = Path(filename).suffix.lower() or ".jpg"
    return f"receipts/{uuid4().hex}{suffix}"


class TaxYear(models.Model):
    """A user's tax year — a container for receipts dated within that calendar year.

    Auto-created when a Receipt is saved for a year that doesn't yet have one.
    When locked, existing receipts in this year cannot be edited or deleted,
    but new receipts (e.g. late-arriving paper receipts being scanned) can
    still be added.
    """

    class Status(models.TextChoices):
        OPEN = "open", "Öppen"
        LOCKED = "locked", "Låst"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tax_years",
    )
    year = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.OPEN,
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "year"],
                name="unique_owner_year",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "-year"]),
        ]
        ordering = ["-year"]

    def __str__(self) -> str:
        return f"Inkomstår {self.year}"

    @property
    def is_locked(self) -> bool:
        return self.status == self.Status.LOCKED

    @property
    def is_open(self) -> bool:
        return self.status == self.Status.OPEN


class Receipt(models.Model):
    """Permanent ledger entry — the source of truth for accounting.

    Image storage lives in Cloudinary (cloudinary_public_id + cloudinary_secure_url).
    The legacy `image` ImageField is kept as an optional escape hatch for non-Cloudinary
    upload flows (e.g. admin or future bulk imports).

    Each receipt belongs to exactly one TaxYear, derived from `date`. The TaxYear is
    auto-created in Receipt.save() via the service layer.

    `net_amount` is auto-computed from `total_amount - vat_amount` on every save. It's
    stored (not just a property) so SQL aggregates can use it directly — exports group
    by category and sum nets without arithmetic in Python.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="receipts",
    )
    tax_year = models.ForeignKey(
        TaxYear,
        on_delete=models.PROTECT,
        related_name="receipts",
        null=True,
        blank=True,
        help_text="Auto-derived from `date`. Never set manually.",
    )
    image = models.ImageField(
        upload_to=receipt_image_upload_path,
        blank=True,
        null=True,
        help_text="Legacy local-storage path. Cloudinary-uploaded receipts leave this empty.",
    )
    cloudinary_public_id = models.CharField(max_length=255, blank=True)
    cloudinary_secure_url = models.URLField(max_length=1024, blank=True)
    vendor = models.CharField(max_length=255, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    net_amount = models.GeneratedField(
        expression=models.F("total_amount") - models.F("vat_amount"),
        output_field=models.DecimalField(max_digits=12, decimal_places=2),
        db_persist=True,
    )
    date = models.DateField(
        help_text="The receipt date — used to derive the TaxYear.",
    )
    category = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)
    source_scan_job_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ID of the scanning.ReceiptScanJob this Receipt was confirmed from.",
    )
    confirmed_at = models.DateTimeField(
        help_text="When the user confirmed the receipt. Required.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "-date"]),
            models.Index(fields=["owner", "-created_at"]),
            models.Index(fields=["tax_year", "-date"]),
        ]
        ordering = ["-date", "-created_at"]

    def __str__(self) -> str:
        return self.vendor or f"Receipt #{self.pk}"

    @property
    def declaration_year(self) -> int | None:
        """The year this receipt is declared (filed) — always inkomstår + 1."""
        if self.tax_year_id is None:
            return None
        return self.tax_year.year + 1

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}

        if self.total_amount is None or self.total_amount < Decimal("0"):
            errors["total_amount"] = "Totalbelopp måste vara noll eller positivt."

        if self.vat_amount is None or self.vat_amount < Decimal("0"):
            errors["vat_amount"] = "Moms måste vara noll eller positiv."

        if (
            self.total_amount is not None
            and self.vat_amount is not None
            and self.vat_amount > self.total_amount
        ):
            errors["vat_amount"] = "Moms kan inte överstiga totalbelopp."

        if errors:
            raise ValidationError(errors)

    @transaction.atomic
    def save(self, *args: Any, **kwargs: Any) -> None:
        from apps.receipts.services import get_or_create_tax_year

        if self.date and (
            self.tax_year_id is None or self.tax_year.year != self.date.year
        ):
            self.tax_year = get_or_create_tax_year(
                owner=self.owner, year=self.date.year
            )

        super().save(*args, **kwargs)
