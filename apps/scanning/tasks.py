"""RQ worker entrypoints for the scanning pipeline.

When REDIS_URL is set, `enqueue_scan_job` schedules `process_receipt_scan_job`
on the `scanning` queue. When REDIS_URL is empty (dev without Redis), django-rq
runs synchronously thanks to ASYNC=False in RQ_QUEUES.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
import django_rq

from apps.integrations import cloudinary_client
from apps.integrations.openai_client import extract_receipt_fields_from_bytes
from apps.scanning.models import ReceiptScanJob
from apps.scanning.services import (
    build_scan_result,
    mark_failed,
    mark_processing,
    mark_review_ready,
)

logger = logging.getLogger(__name__)


def enqueue_scan_job(job_id: int) -> None:
    """Enqueue an OCR job on the 'scanning' queue."""
    queue = django_rq.get_queue("scanning")
    queue.enqueue(process_receipt_scan_job, job_id)


def process_receipt_scan_job(job_id: int) -> None:
    """Worker entrypoint — runs the OCR pipeline for a single ScanJob.

    Flow:
      1. Load job (user-scoped query not needed here — we trust the ID)
      2. Mark PROCESSING
      3. Fetch image from Cloudinary
      4. Call OpenAI extraction
      5. Build ReceiptScanResult, sanitize, mark REVIEW_READY
      6. On any failure → mark FAILED (user can still manually fill the form)
    """
    job = ReceiptScanJob.objects.filter(pk=job_id).first()
    if job is None:
        logger.warning("scanning.tasks.job_not_found", extra={"job_id": job_id})
        return

    if job.is_terminal:
        logger.info(
            "scanning.tasks.skip_terminal_job",
            extra={"job_id": job_id, "status": job.status},
        )
        return

    try:
        mark_processing(job)

        # 1. Fetch image bytes
        try:
            image_bytes, suffix = cloudinary_client.fetch_image_bytes(
                job.cloudinary_secure_url
            )
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(
                "scanning.tasks.fetch_failed",
                extra={"job_id": job_id, "error": str(exc)},
            )
            mark_failed(job, error_message="Kunde inte hämta bilden från Cloudinary.")
            return

        # 2. Call OpenAI (async function — run in fresh event loop)
        try:
            raw = asyncio.run(extract_receipt_fields_from_bytes(image_bytes, suffix))
        except httpx.HTTPError as exc:
            logger.warning(
                "scanning.tasks.openai_failed",
                extra={"job_id": job_id, "error": str(exc)},
            )
            mark_failed(
                job,
                error_message="AI-tolkningen misslyckades. Fyll i uppgifterna manuellt nedan.",
            )
            return

        # 3. Build typed result + mark ready
        preview = build_scan_result(raw)
        mark_review_ready(job, preview=preview)
        logger.info(
            "scanning.tasks.review_ready",
            extra={"job_id": job_id, "user_id": job.user_id},
        )

    except Exception as exc:  # pragma: no cover — defensive catch-all
        logger.exception(
            "scanning.tasks.unexpected_failure",
            extra={"job_id": job_id},
        )
        mark_failed(job, error_message=str(exc))
        raise
