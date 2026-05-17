"""Scanning domain services.

Owns the lifecycle of ReceiptScanJob: signing direct uploads, recording the
upload result, kicking off async OCR, and confirming the final Receipt.

The OCR pipeline itself lives in apps.scanning.tasks (RQ worker entry point)
and uses apps.integrations.openai_client + apps.integrations.cloudinary_client.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from datetime import date as date_type
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from pydantic import BaseModel, Field

from apps.integrations import cloudinary_client
from apps.scanning.models import ReceiptScanJob

logger = logging.getLogger(__name__)

PERSONAL_NUMBER_PATTERN = re.compile(r"\b\d{6,8}[-+]?\d{4}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+46|0)\d{7,12}\b")
EMAIL_PATTERN = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")

MAX_PENDING_JOBS_PER_USER = 10


class ReceiptScanResult(BaseModel):
    """Validated, sanitized output of a single receipt extraction."""

    vendor: str = Field(default="")
    total_amount: Decimal | None = Field(default=None)
    vat_amount: Decimal | None = Field(default=None)
    date: date_type | None = Field(default=None)
    category: str = Field(default="")
    note: str = Field(default="")


def sanitize_text(value: str) -> str:
    """Strip personal numbers, phone numbers and emails from OCR output."""
    sanitized = PERSONAL_NUMBER_PATTERN.sub("[redacted]", value)
    sanitized = PHONE_PATTERN.sub("[redacted]", sanitized)
    sanitized = EMAIL_PATTERN.sub("[redacted]", sanitized)
    return sanitized.strip()


# ---------------------------------------------------------------------------
# Signing — Step 1 of the upload flow
# ---------------------------------------------------------------------------


class UploadSignature(BaseModel):
    """Payload returned by the sign endpoint for direct-to-Cloudinary upload."""

    job_id: int
    cloud_name: str
    api_key: str
    timestamp: int
    signature: str
    public_id: str
    folder: str


@transaction.atomic
def issue_upload_signature(*, user: AbstractBaseUser) -> UploadSignature:
    """Create a PENDING ReceiptScanJob and return a signed upload payload.

    The signature commits the client to uploading with exactly the public_id
    and folder we specify, so users can't pollute each other's spaces.

    Raises:
        ValueError: if Cloudinary isn't configured or the user has too many
                    pending jobs.
    """
    if not cloudinary_client.is_configured():
        raise ValueError("Cloudinary är inte konfigurerat.")

    pending_count = ReceiptScanJob.objects.filter(
        user=user,
        status__in=[
            ReceiptScanJob.Status.PENDING,
            ReceiptScanJob.Status.QUEUED,
            ReceiptScanJob.Status.PROCESSING,
        ],
    ).count()
    if pending_count >= MAX_PENDING_JOBS_PER_USER:
        raise ValueError(
            "Du har för många skanningar pågående just nu. Vänta tills någon "
            "är klar innan du startar en ny."
        )

    folder = f"skogskvitto/scans/user_{user.pk}"
    public_id = f"{folder}/{uuid.uuid4().hex}"
    timestamp = int(time.time())

    sign_params: dict[str, str | int] = {
        "folder": folder,
        "public_id": public_id,
        "timestamp": timestamp,
    }
    signature = cloudinary_client.sign_upload_params(sign_params)

    job = ReceiptScanJob.objects.create(
        user=user,
        cloudinary_public_id=public_id,
        cloudinary_secure_url="",
        status=ReceiptScanJob.Status.PENDING,
    )

    logger.info(
        "scanning.issue_upload_signature",
        extra={"user_id": user.pk, "job_id": job.pk, "public_id": public_id},
    )

    return UploadSignature(
        job_id=job.pk,
        cloud_name=cloudinary_client.cloud_name(),
        api_key=cloudinary_client.api_key(),
        timestamp=timestamp,
        signature=signature,
        public_id=public_id,
        folder=folder,
    )


# ---------------------------------------------------------------------------
# Intake — Step 2 of the upload flow
# ---------------------------------------------------------------------------


@transaction.atomic
def record_intake(
    *,
    job: ReceiptScanJob,
    reported_public_id: str,
    reported_secure_url: str,
) -> ReceiptScanJob:
    """Verify the Cloudinary upload result and enqueue the OCR task.

    Raises:
        ValidationError: if the reported public_id doesn't match the one we signed,
                         or the job is in a terminal state.
    """
    if job.is_terminal:
        raise ValidationError("Skanningen är redan avslutad.")

    if reported_public_id != job.cloudinary_public_id:
        logger.warning(
            "scanning.record_intake.public_id_mismatch",
            extra={
                "job_id": job.pk,
                "expected": job.cloudinary_public_id,
                "got": reported_public_id,
            },
        )
        raise ValidationError("Uppladdningens identifierare matchar inte signaturen.")

    if not reported_secure_url.startswith("https://res.cloudinary.com/"):
        raise ValidationError("Ogiltig Cloudinary-URL.")

    job.cloudinary_secure_url = reported_secure_url
    job.status = ReceiptScanJob.Status.QUEUED
    job.queued_at = timezone.now()
    job.save(
        update_fields=["cloudinary_secure_url", "status", "queued_at", "updated_at"]
    )

    # Import here to avoid a circular import at module load time:
    # tasks → models → services → tasks.
    from apps.scanning.tasks import enqueue_scan_job

    enqueue_scan_job(job.pk)

    logger.info(
        "scanning.record_intake.queued",
        extra={"user_id": job.user_id, "job_id": job.pk},
    )
    return job


# ---------------------------------------------------------------------------
# Status lifecycle — used by the RQ worker
# ---------------------------------------------------------------------------


def mark_processing(job: ReceiptScanJob) -> None:
    job.status = ReceiptScanJob.Status.PROCESSING
    job.save(update_fields=["status", "updated_at"])


def mark_review_ready(job: ReceiptScanJob, *, preview: ReceiptScanResult) -> None:
    job.status = ReceiptScanJob.Status.REVIEW_READY
    job.preview_data = preview.model_dump(mode="json")
    job.processed_at = timezone.now()
    job.error_message = ""
    job.save(
        update_fields=[
            "status",
            "preview_data",
            "processed_at",
            "error_message",
            "updated_at",
        ]
    )


def mark_failed(job: ReceiptScanJob, *, error_message: str) -> None:
    job.status = ReceiptScanJob.Status.FAILED
    job.error_message = error_message[:512]
    job.processed_at = timezone.now()
    job.save(
        update_fields=["status", "error_message", "processed_at", "updated_at"]
    )
    logger.warning(
        "scanning.mark_failed",
        extra={"job_id": job.pk, "user_id": job.user_id, "error": error_message},
    )


# ---------------------------------------------------------------------------
# Preview-data parsing — turns AI dict into typed result
# ---------------------------------------------------------------------------


def build_scan_result(raw: dict[str, Any]) -> ReceiptScanResult:
    """Convert a raw OpenAI dict into a sanitized ReceiptScanResult."""
    from datetime import datetime
    from decimal import InvalidOperation

    def _decimal(value: Any) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value).replace(",", ".").strip())
        except InvalidOperation:
            return None

    def _date(value: Any) -> date_type | None:
        if not value:
            return None
        try:
            return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    def _str(value: Any) -> str:
        return sanitize_text(str(value or "").strip())

    return ReceiptScanResult(
        vendor=_str(raw.get("vendor")),
        total_amount=_decimal(raw.get("total_amount")),
        vat_amount=_decimal(raw.get("vat_amount")),
        date=_date(raw.get("date")),
        category=_str(raw.get("category")),
        note=_str(raw.get("note")),
    )


# ---------------------------------------------------------------------------
# Confirmation — turn ScanJob into Receipt
# ---------------------------------------------------------------------------


@transaction.atomic
def confirm_scan(
    *,
    job: ReceiptScanJob,
    vendor: str,
    total_amount: Decimal,
    vat_amount: Decimal,
    date: date_type,
    category: str,
    note: str,
) -> "tuple[ReceiptScanJob, object]":
    """Create the permanent Receipt from a reviewed ScanJob.

    Idempotent: if the job is already CONFIRMED, returns the existing
    (job, receipt) tuple.

    Raises:
        ValidationError: if the job has no upload, or amounts are invalid.
    """
    from apps.receipts.models import Receipt

    if job.status == ReceiptScanJob.Status.CONFIRMED and job.confirmed_receipt_id:
        return job, job.confirmed_receipt

    if not job.cloudinary_secure_url or not job.cloudinary_public_id:
        raise ValidationError("Bilden är inte uppladdad. Försök igen.")

    receipt = Receipt(
        owner=job.user,
        cloudinary_public_id=job.cloudinary_public_id,
        cloudinary_secure_url=job.cloudinary_secure_url,
        vendor=vendor,
        total_amount=total_amount,
        vat_amount=vat_amount,
        date=date,
        category=category,
        note=note,
        source_scan_job_id=job.pk,
        confirmed_at=timezone.now(),
    )
    receipt.full_clean()
    receipt.save()

    job.confirmed_receipt = receipt
    job.status = ReceiptScanJob.Status.CONFIRMED
    job.save(update_fields=["confirmed_receipt", "status", "updated_at"])

    logger.info(
        "scanning.confirm_scan",
        extra={
            "user_id": job.user_id,
            "job_id": job.pk,
            "receipt_id": receipt.pk,
            "tax_year": receipt.tax_year.year if receipt.tax_year else None,
        },
    )
    return job, receipt

