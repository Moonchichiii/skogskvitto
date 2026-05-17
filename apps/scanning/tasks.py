from __future__ import annotations

import logging

from apps.scanning.models import ReceiptScanJob
from apps.scanning.services import mark_failed, mark_processing

logger = logging.getLogger(__name__)


def process_receipt_scan_job(job_id: int) -> None:
    """Worker entrypoint for an async scan job.

    NOTE: This is the placeholder shell for the future RQ worker. Wiring to
    Redis/RQ happens in a later pass once integrations.openai_client and
    integrations.cloudinary clients are fully fleshed out.

    Expected flow once wired:
      1. Load ReceiptScanJob by id (within the user-scoped queryset).
      2. mark_processing(job)
      3. Fetch image bytes from Cloudinary using cloudinary_secure_url.
      4. Call apps.integrations.openai_client.extract_receipt_fields_from_bytes.
      5. Build a ReceiptScanResult, sanitize text fields, mark_review_ready.
      6. On any exception: mark_failed(job, error_message=...).
    """

    job = ReceiptScanJob.objects.filter(pk=job_id).first()
    if job is None:
        logger.warning("scanning.tasks.job_not_found", extra={"job_id": job_id})
        return

    try:
        mark_processing(job)
        # TODO: Wire OpenAI extraction + Cloudinary fetch in Pass 02.
        raise NotImplementedError("Scan worker is not yet wired to integrations.")
    except NotImplementedError:
        mark_failed(job, error_message="Worker not yet implemented.")
        raise
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("scanning.tasks.unexpected_failure", extra={"job_id": job_id})
        mark_failed(job, error_message=str(exc))
        raise
