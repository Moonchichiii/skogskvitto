from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import models


def receipt_image_upload_path(_: "Receipt", filename: str) -> str:
    suffix = Path(filename).suffix.lower() or ".jpg"
    return f"receipts/{uuid4().hex}{suffix}"


def receipt_scan_job_upload_path(_: "ReceiptScanJob", filename: str) -> str:
    suffix = Path(filename).suffix.lower() or ".jpg"
    return f"receipt-scan-jobs/{uuid4().hex}{suffix}"


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
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
        ]

    def __str__(self) -> str:
        return self.vendor or f"Receipt #{self.pk}"


class ReceiptScanJob(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_PREVIEW_READY = "preview_ready"
    STATUS_CONFIRMED = "confirmed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_PREVIEW_READY, "Preview ready"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_FAILED, "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="receipt_scan_jobs",
    )
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PENDING)
    image = models.ImageField(upload_to=receipt_scan_job_upload_path)
    preview_data = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    confirmed_receipt = models.ForeignKey(
        "Receipt",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scan_jobs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"ScanJob #{self.pk} ({self.status})"


class UserSubscription(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_TRIALING = "trialing"
    STATUS_CANCELED = "canceled"
    STATUS_INCOMPLETE = "incomplete"
    STATUS_INCOMPLETE_EXPIRED = "incomplete_expired"
    STATUS_UNPAID = "unpaid"
    STATUS_PAST_DUE = "past_due"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_TRIALING, "Trialing"),
        (STATUS_CANCELED, "Canceled"),
        (STATUS_INCOMPLETE, "Incomplete"),
        (STATUS_INCOMPLETE_EXPIRED, "Incomplete expired"),
        (STATUS_UNPAID, "Unpaid"),
        (STATUS_PAST_DUE, "Past due"),
    ]

    INTERVAL_MONTH = "month"
    INTERVAL_YEAR = "year"
    INTERVAL_CHOICES = [(INTERVAL_MONTH, "Month"), (INTERVAL_YEAR, "Year")]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES)
    plan_interval = models.CharField(
        max_length=16,
        choices=INTERVAL_CHOICES,
        default=INTERVAL_MONTH,
    )
    current_period_end = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Subscription for {self.user} ({self.status})"
