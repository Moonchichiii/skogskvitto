from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from apps.billing.services import get_feature_gates_sync
from apps.scanning import services
from apps.scanning.forms import parse_confirm_form
from apps.scanning.models import ReceiptScanJob

logger = logging.getLogger(__name__)


def _compute_net_preview(data: dict | object) -> str:
    """Best-effort net = total - vat preview string for the review form.

    Returns an empty string when either side can't be parsed — the field stays
    blank rather than showing 0.00 (less misleading).
    """
    from decimal import Decimal, InvalidOperation

    def _to_decimal(raw: object) -> Decimal | None:
        s = str(raw or "").replace(",", ".").strip()
        if not s:
            return None
        try:
            return Decimal(s)
        except InvalidOperation:
            return None

    # Support both QueryDict (.get) and plain dict
    get = data.get if hasattr(data, "get") else lambda k, d=None: d
    total = _to_decimal(get("total_amount"))
    vat = _to_decimal(get("vat_amount"))

    if total is None:
        return ""
    if vat is None:
        vat = Decimal("0.00")

    net = total - vat
    return f"{net:.2f}"


# ---------------------------------------------------------------------------
# Page view — /scan/
# ---------------------------------------------------------------------------


@ensure_csrf_cookie
@login_required
def scan(request: HttpRequest) -> HttpResponse:
    gates = get_feature_gates_sync(request.user)
    return render(request, "scanning/scan.html", {"gates": gates})


# ---------------------------------------------------------------------------
# Sign — /scanning/sign/ (POST)
# ---------------------------------------------------------------------------


@login_required
@require_POST
def sign_upload(request: HttpRequest) -> HttpResponse:
    """Return a signed payload for direct-to-Cloudinary upload."""
    try:
        sig = services.issue_upload_signature(user=request.user)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(sig.model_dump())


# ---------------------------------------------------------------------------
# Intake — /scanning/job/<id>/intake/ (POST, HTMX)
# ---------------------------------------------------------------------------


@login_required
@require_POST
def intake(request: HttpRequest, job_id: int) -> HttpResponse:
    """Record the Cloudinary upload result and enqueue OCR.

    Returns an HTMX-driven 'pending' fragment that polls the status endpoint.
    """
    job = get_object_or_404(ReceiptScanJob, pk=job_id, user=request.user)

    reported_public_id = (request.POST.get("public_id") or "").strip()
    reported_secure_url = (request.POST.get("secure_url") or "").strip()

    try:
        services.record_intake(
            job=job,
            reported_public_id=reported_public_id,
            reported_secure_url=reported_secure_url,
        )
    except ValidationError as exc:
        logger.warning(
            "scanning.intake.validation_failed",
            extra={
                "job_id": job.pk,
                "user_id": request.user.pk,
                "error": str(exc),
            },
        )
        return render(
            request,
            "scanning/partials/scan_error.html",
            {
                "error": (
                    exc.messages[0]
                    if exc.messages
                    else "Ogiltig uppladdning."
                )
            },
            status=400,
        )

    return render(
        request,
        "scanning/partials/scan_pending.html",
        {"job": job},
    )


# ---------------------------------------------------------------------------
# Status — /scanning/job/<id>/status/ (GET, HTMX polling)
# ---------------------------------------------------------------------------


@login_required
def status(request: HttpRequest, job_id: int) -> HttpResponse:
    """Polled by the pending fragment. Returns the next state's HTML."""
    job = get_object_or_404(ReceiptScanJob, pk=job_id, user=request.user)

    if job.status in (
        ReceiptScanJob.Status.PENDING,
        ReceiptScanJob.Status.QUEUED,
        ReceiptScanJob.Status.PROCESSING,
    ):
        return render(
            request, "scanning/partials/scan_pending.html", {"job": job}
        )

    if job.status == ReceiptScanJob.Status.REVIEW_READY:
        preview = dict(job.preview_data or {})
        # Compute net from preview total/vat so user sees it before save
        net_preview = _compute_net_preview(preview)
        return render(
            request,
            "scanning/partials/scan_result_form.html",
            {
                "job": job,
                "preview": preview,
                "net_preview": net_preview,
                "errors": {},
                "failed": False,
            },
        )

    if job.status == ReceiptScanJob.Status.FAILED:
        return render(
            request,
            "scanning/partials/scan_result_form.html",
            {
                "job": job,
                "preview": {},
                "net_preview": "",
                "errors": {},
                "failed": True,
                "error_message": job.error_message
                or "AI-tolkningen misslyckades.",
            },
        )

    if job.status == ReceiptScanJob.Status.CONFIRMED:
        return render(
            request,
            "scanning/partials/scan_saved.html",
            {"receipt": job.confirmed_receipt},
        )

    return HttpResponseBadRequest("Okänt skanningstillstånd.")


# ---------------------------------------------------------------------------
# Confirm — /scanning/job/<id>/confirm/ (POST, HTMX)
# ---------------------------------------------------------------------------


@login_required
@require_POST
def confirm(request: HttpRequest, job_id: int) -> HttpResponse:
    """Create a Receipt from the reviewed scan."""
    job = get_object_or_404(ReceiptScanJob, pk=job_id, user=request.user)

    cleaned, errors = parse_confirm_form(request.POST)
    if errors or cleaned is None:
        return render(
            request,
            "scanning/partials/scan_result_form.html",
            {
                "job": job,
                "preview": request.POST,
                "net_preview": _compute_net_preview(request.POST),
                "errors": errors,
                "failed": job.status == ReceiptScanJob.Status.FAILED,
                "error_message": job.error_message,
            },
            status=400,
        )

    try:
        job, receipt = services.confirm_scan(
            job=job,
            vendor=cleaned.vendor,
            total_amount=cleaned.total_amount,
            vat_amount=cleaned.vat_amount,
            date=cleaned.date,
            category=cleaned.category,
            note=cleaned.note,
        )
    except ValidationError as exc:
        messages = (
            list(exc.message_dict.values())
            if hasattr(exc, "message_dict")
            else exc.messages
        )
        flat = "; ".join(str(m) for m in messages) or "Ogiltig data."
        return render(
            request,
            "scanning/partials/scan_result_form.html",
            {
                "job": job,
                "preview": request.POST,
                "net_preview": _compute_net_preview(request.POST),
                "errors": {"form": flat},
                "failed": job.status == ReceiptScanJob.Status.FAILED,
            },
            status=400,
        )

    return render(
        request,
        "scanning/partials/scan_saved.html",
        {"receipt": receipt},
    )
