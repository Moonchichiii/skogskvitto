import re
from datetime import date as date_cls
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, cast

import magic
from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from django.core.signing import BadSignature, Signer
from django.http import HttpRequest, HttpResponse
from django.http.response import HttpResponseForbidden
from django.template.loader import render_to_string
from ninja import File, Form, Router
from ninja.files import UploadedFile

from apps.core.models import User
from apps.receipts.billing import (
    FEATURE_RECEIPT_CONFIRM_SAVE,
    FEATURE_RECEIPT_SCAN_PREVIEW,
    can_use_feature,
)
from apps.receipts.models import Receipt, ReceiptScanJob
from apps.receipts.services import (
    SUPPORTED_IMAGE_MIME_TYPES,
    process_receipt_image,
    strip_exif_and_prepare_image,
)

router = Router(tags=["receipts"])

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
MAX_CORRECTION_TEXT_LENGTH = 300
SCAN_JOB_SIGNER = Signer(salt="receipt-scan-job")


def _parse_decimal(value: str) -> Decimal | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return Decimal(cleaned.replace(",", "."))
    except InvalidOperation:
        return None


def _parse_date(value: str) -> date_cls | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return date_cls.fromisoformat(cleaned)
    except ValueError:
        return None


def _render_fragment(template: str, context: dict[str, object], status: int = 200) -> HttpResponse:
    html = render_to_string(template, context)
    return HttpResponse(html, status=status)


def _detect_image_mime(upload: UploadedFile) -> str:
    head = upload.read(4096)
    upload.seek(0)
    return str(magic.from_buffer(head, mime=True))


def _require_authenticated_user(request: HttpRequest) -> HttpResponse | None:
    if request.user.is_authenticated:
        return None
    return HttpResponseForbidden("Inloggning krävs.")


def _build_preview_data(
    ai_data_vendor: str,
    ai_data_total_amount: Decimal | None,
    ai_data_vat_amount: Decimal | None,
    ai_data_date: date_cls | None,
    ai_data_category: str,
) -> dict[str, object]:
    return {
        "vendor": ai_data_vendor,
        "total_amount": str(ai_data_total_amount) if ai_data_total_amount is not None else "",
        "vat_amount": str(ai_data_vat_amount) if ai_data_vat_amount is not None else "",
        "date": ai_data_date.isoformat() if ai_data_date is not None else "",
        "category": ai_data_category,
        "note": "",
    }


def _suggest_correction(correction_text: str) -> dict[str, str]:
    lowered = correction_text.lower()
    suggestion: dict[str, str] = {}

    amount_match = re.search(r"(\d+(?:\s?\d{3})*[,.]\d{1,2})", correction_text)
    if amount_match:
        suggestion["total_amount"] = amount_match.group(1).replace(" ", "").replace(",", ".")
    if "drivmedel" in lowered:
        suggestion["category"] = "Drivmedel"
    elif "material" in lowered:
        suggestion["category"] = "Material"

    return suggestion


@router.post("/scan")
async def scan_receipt(request: HttpRequest, image: File[UploadedFile]) -> HttpResponse:
    authentication_error = _require_authenticated_user(request)
    if authentication_error is not None:
        return authentication_error
    user = cast(User, request.user)

    scan_decision = await can_use_feature(user, FEATURE_RECEIPT_SCAN_PREVIEW)
    if not scan_decision.allowed:
        return await sync_to_async(_render_fragment)(
            "receipts/partials/paywall.html",
            {"message": scan_decision.reason},
            403,
        )

    if image.size is None:
        return await sync_to_async(_render_fragment)(
            "receipts/partials/scan_error.html",
            {"error": "Kunde inte läsa filstorleken för uppladdningen."},
            400,
        )

    if image.size > MAX_UPLOAD_SIZE_BYTES:
        return await sync_to_async(_render_fragment)(
            "receipts/partials/scan_error.html",
            {"error": "Bilden är för stor. Max 10MB."},
            400,
        )

    detected_mime = await sync_to_async(_detect_image_mime)(image)
    if detected_mime not in SUPPORTED_IMAGE_MIME_TYPES:
        return await sync_to_async(_render_fragment)(
            "receipts/partials/scan_error.html",
            {"error": "Ogiltig filtyp. Endast JPG, PNG eller WEBP stöds."},
            400,
        )

    cleaned_file = await sync_to_async(strip_exif_and_prepare_image)(image, detected_mime)
    scan_job = await ReceiptScanJob.objects.acreate(
        user=user,
        image=cleaned_file,
        status=ReceiptScanJob.STATUS_RUNNING,
    )

    extension = Path(scan_job.image.name or "").suffix or ".jpg"
    tmp_path: Path | None = None
    try:
        with NamedTemporaryFile(suffix=extension, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            await sync_to_async(scan_job.image.open)("rb")
            file_bytes = await sync_to_async(scan_job.image.read)()
            tmp.write(file_bytes)
            await sync_to_async(scan_job.image.close)()
        ai_data = await process_receipt_image(tmp_path)
        scan_job.preview_data = _build_preview_data(
            ai_data.vendor,
            ai_data.total_amount,
            ai_data.vat_amount,
            ai_data.date,
            ai_data.category,
        )
        scan_job.status = ReceiptScanJob.STATUS_PREVIEW_READY
        scan_job.error_message = ""
    except Exception:
        scan_job.status = ReceiptScanJob.STATUS_FAILED
        scan_job.error_message = "Kunde inte analysera kvittot."
        await scan_job.asave(update_fields=["status", "error_message", "updated_at"])
        return await sync_to_async(_render_fragment)(
            "receipts/partials/scan_error.html",
            {"error": "Kunde inte analysera kvittot just nu. Försök igen."},
            502,
        )
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    await scan_job.asave(update_fields=["preview_data", "status", "error_message", "updated_at"])
    return await sync_to_async(_render_fragment)(
        "receipts/partials/scan_result_form.html",
        {
            "scan_job": scan_job,
            "preview": scan_job.preview_data,
            "signed_scan_job": SCAN_JOB_SIGNER.sign(str(scan_job.pk)),
        },
    )


@router.post("/save")
async def save_receipt(
    request: HttpRequest,
    signed_scan_job: Form[str],
    vendor: Form[str] = "",
    total_amount: Form[str] = "",
    vat_amount: Form[str] = "",
    date: Form[str] = "",
    category: Form[str] = "",
    note: Form[str] = "",
) -> HttpResponse:
    authentication_error = _require_authenticated_user(request)
    if authentication_error is not None:
        return authentication_error
    user = cast(User, request.user)

    try:
        scan_job_id = int(SCAN_JOB_SIGNER.unsign(signed_scan_job))
    except (BadSignature, ValueError):
        return HttpResponseForbidden("Ogiltig kvittosession.")

    try:
        scan_job = await ReceiptScanJob.objects.aget(pk=scan_job_id, user_id=user.id)
    except ReceiptScanJob.DoesNotExist:
        return HttpResponseForbidden("Skanningen saknas eller är inte tillgänglig.")

    if scan_job.status != ReceiptScanJob.STATUS_PREVIEW_READY:
        return HttpResponseForbidden("Skanningen är inte redo att sparas.")

    save_decision = await can_use_feature(user, FEATURE_RECEIPT_CONFIRM_SAVE)
    if not save_decision.allowed:
        return await sync_to_async(_render_fragment)(
            "receipts/partials/paywall.html",
            {"message": save_decision.reason},
            403,
        )

    preview = cast(dict[str, Any], scan_job.preview_data or {})
    receipt = Receipt(
        owner=user,
        vendor=vendor.strip() or str(preview.get("vendor", "")),
        total_amount=(
            _parse_decimal(total_amount)
            if total_amount.strip()
            else _parse_decimal(str(preview.get("total_amount", "")))
        ),
        vat_amount=(
            _parse_decimal(vat_amount)
            if vat_amount.strip()
            else _parse_decimal(str(preview.get("vat_amount", "")))
        ),
        date=_parse_date(date) if date.strip() else _parse_date(str(preview.get("date", ""))),
        category=category.strip() or str(preview.get("category", "")),
        note=note.strip() or str(preview.get("note", "")),
    )

    await sync_to_async(scan_job.image.open)("rb")
    file_bytes = await sync_to_async(scan_job.image.read)()
    await sync_to_async(scan_job.image.close)()
    extension = Path(scan_job.image.name or "").suffix or ".jpg"
    receipt.image.save(
        name=f"confirmed{extension}",
        content=ContentFile(file_bytes),
        save=False,
    )
    await receipt.asave()

    scan_job.confirmed_receipt = receipt
    scan_job.status = ReceiptScanJob.STATUS_CONFIRMED
    await scan_job.asave(update_fields=["confirmed_receipt", "status", "updated_at"])

    return await sync_to_async(_render_fragment)(
        "receipts/partials/scan_saved.html",
        {"receipt": receipt},
    )


@router.post("/correction-suggestion")
async def correction_suggestion(
    request: HttpRequest,
    signed_scan_job: Form[str],
    correction_text: Form[str],
) -> HttpResponse:
    authentication_error = _require_authenticated_user(request)
    if authentication_error is not None:
        return authentication_error
    user = cast(User, request.user)

    try:
        scan_job_id = int(SCAN_JOB_SIGNER.unsign(signed_scan_job))
    except (BadSignature, ValueError):
        return HttpResponseForbidden("Ogiltig kvittosession.")

    try:
        await ReceiptScanJob.objects.aget(pk=scan_job_id, user_id=user.id)
    except ReceiptScanJob.DoesNotExist:
        return HttpResponseForbidden("Skanningen saknas eller är inte tillgänglig.")

    suggestion = _suggest_correction(correction_text[:MAX_CORRECTION_TEXT_LENGTH])
    if not suggestion:
        return await sync_to_async(_render_fragment)(
            "receipts/partials/correction_suggestion.html",
            {"has_suggestion": False},
        )

    return await sync_to_async(_render_fragment)(
        "receipts/partials/correction_suggestion.html",
        {
            "has_suggestion": True,
            "message": "Jag hittade en möjlig korrigering.",
            "suggestion": suggestion,
        },
    )
