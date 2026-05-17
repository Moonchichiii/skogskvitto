from __future__ import annotations

import logging
import re
from datetime import date as date_type
from decimal import Decimal

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from django.utils import timezone
from pydantic import BaseModel, Field

from apps.scanning.models import ReceiptScanJob

logger = logging.getLogger(__name__)

PERSONAL_NUMBER_PATTERN = re.compile(r"\b\d{6,8}[-+]?\d{4}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+46|0)\d{7,12}\b")
EMAIL_PATTERN = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")


class ReceiptScanResult(BaseModel):
    """Validated, sanitized output of a single receipt extraction."""

    vendor: str = Field(default="")
    total_amount: Decimal | None = Field(default=None)
    vat_amount: Decimal | None = Field(default=None)
    date: date_type | None = Field(default=None)
    category: str = Field(default="")
    note: str = Field(default="")


def sanitize_text(value: str) -> str:
    sanitized = PERSONAL_NUMBER_PATTERN.sub("[redacted]", value)
    sanitized = PHONE_PATTERN.sub("[redacted]", sanitized)
    sanitized = EMAIL_PATTERN.sub("[redacted]", sanitized)
    return sanitized.strip()


@transaction.atomic
def create_scan_job(
    *,
    user: AbstractBaseUser,
    cloudinary_public_id: str,
    cloudinary_secure_url: str,
) -> ReceiptScanJob:
    """Create a new scan job after a direct-to-Cloudinary upload.

    The view layer is responsible for verifying the signed upload payload
    before calling this. Once created the job is queued for the async worker.
    """

    return ReceiptScanJob.objects.create(
        user=user,
        cloudinary_public_id=cloudinary_public_id,
        cloudinary_secure_url=cloudinary_secure_url,
        status=ReceiptScanJob.Status.PENDING,
    )


def mark_queued(job: ReceiptScanJob) -> None:
    job.status = ReceiptScanJob.Status.QUEUED
    job.queued_at = timezone.now()
    job.save(update_fields=["status", "queued_at", "updated_at"])


def mark_processing(job: ReceiptScanJob) -> None:
    job.status = ReceiptScanJob.Status.PROCESSING
    job.save(update_fields=["status", "updated_at"])


def mark_review_ready(job: ReceiptScanJob, *, preview: ReceiptScanResult) -> None:
    job.status = ReceiptScanJob.Status.REVIEW_READY
    job.preview_data = preview.model_dump(mode="json")
    job.processed_at = timezone.now()
    job.error_message = ""
    job.save(
        update_fields=["status", "preview_data", "processed_at", "error_message", "updated_at"]
    )


def mark_failed(job: ReceiptScanJob, *, error_message: str) -> None:
    job.status = ReceiptScanJob.Status.FAILED
    job.error_message = error_message[:512]
    job.processed_at = timezone.now()
    job.save(update_fields=["status", "error_message", "processed_at", "updated_at"])
