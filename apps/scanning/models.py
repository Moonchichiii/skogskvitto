from __future__ import annotations

from django.conf import settings
from django.db import models


class ReceiptScanJob(models.Model):
    """Temporary scan job — represents one in-flight receipt extraction.

    Lifecycle: pending -> queued -> processing -> review_ready -> confirmed
    (or failed at any point).

    Confirmed jobs are linked to a permanent Receipt via confirmed_receipt.
    Unconfirmed jobs are disposable: they hold the Cloudinary upload and
    the AI preview data until the user confirms or discards.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        REVIEW_READY = "review_ready", "Review ready"
        CONFIRMED = "confirmed", "Confirmed"
        FAILED = "failed", "Failed"

    class Provider(models.TextChoices):
        OPENAI = "openai", "OpenAI"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="receipt_scan_jobs",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
    )
    cloudinary_public_id = models.CharField(max_length=255)
    cloudinary_secure_url = models.URLField(max_length=1024)
    preview_data = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=512, blank=True)
    confirmed_receipt = models.ForeignKey(
        "receipts.Receipt",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scan_jobs",
    )
    ai_provider = models.CharField(
        max_length=32,
        choices=Provider.choices,
        default=Provider.OPENAI,
    )
    queued_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status", "-created_at"]),
            models.Index(fields=["status", "queued_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ScanJob #{self.pk} ({self.status})"

    @property
    def is_terminal(self) -> bool:
        return self.status in {self.Status.CONFIRMED, self.Status.FAILED}

    @property
    def is_in_progress(self) -> bool:
        return self.status in {
            self.Status.PENDING,
            self.Status.QUEUED,
            self.Status.PROCESSING,
        }
