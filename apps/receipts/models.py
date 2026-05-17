from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def receipt_image_upload_path(_: "Receipt", filename: str) -> str:
    suffix = Path(filename).suffix.lower() or ".jpg"
    return f"receipts/{uuid4().hex}{suffix}"


class Receipt(models.Model):
    """Permanent ledger entry — the source of truth for accounting.

    A Receipt only exists after the user has explicitly confirmed an
    extracted scan preview. Math is strictly validated: amounts are
    non-negative and VAT cannot exceed total.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="receipts",
    )
    image = models.ImageField(upload_to=receipt_image_upload_path)
    cloudinary_public_id = models.CharField(max_length=255, blank=True)
    vendor = models.CharField(max_length=255, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    date = models.DateField(null=True, blank=True)
    category = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)
    source_scan_job_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ID of the scanning.ReceiptScanJob this Receipt was confirmed from.",
    )
    confirmed_at = models.DateTimeField(
        help_text="When the user confirmed the receipt. Required — receipts cannot exist unconfirmed.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "-date"]),
            models.Index(fields=["owner", "-created_at"]),
        ]
        ordering = ["-date", "-created_at"]

    def __str__(self) -> str:
        return self.vendor or f"Receipt #{self.pk}"

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
