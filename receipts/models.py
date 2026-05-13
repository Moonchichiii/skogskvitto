from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import models


def receipt_image_upload_path(_: "Receipt", filename: str) -> str:
    suffix = Path(filename).suffix.lower() or ".jpg"
    return f"receipts/{uuid4().hex}{suffix}"


class Receipt(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="receipts",
        null=True,
        blank=True,
    )
    image = models.ImageField(upload_to=receipt_image_upload_path)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    vendor = models.CharField(max_length=255, blank=True)
    date = models.DateField(null=True, blank=True)
    category = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.vendor or f"Receipt #{self.pk}"
