from datetime import date as date_cls
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import NamedTemporaryFile

import magic
from asgiref.sync import sync_to_async
from django.core.signing import BadSignature, Signer
from django.http import HttpRequest, HttpResponse
from django.http.response import HttpResponseForbidden
from django.template.loader import render_to_string
from ninja import File, Form, Router
from ninja.files import UploadedFile

from apps.receipts.models import Receipt
from apps.receipts.services import (
    SUPPORTED_IMAGE_MIME_TYPES,
    process_receipt_image,
    strip_exif_and_prepare_image,
)

router = Router(tags=["receipts"])

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
RECEIPT_SIGNER = Signer(salt="receipt-save")


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


@router.post("/scan")
async def scan_receipt(request: HttpRequest, image: File[UploadedFile]) -> HttpResponse:
    authentication_error = _require_authenticated_user(request)
    if authentication_error is not None:
        return authentication_error

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
    receipt = await Receipt.objects.acreate(owner=request.user, image=cleaned_file)

    extension = Path(receipt.image.name or "").suffix or ".jpg"
    tmp_path: Path | None = None
    try:
        with NamedTemporaryFile(suffix=extension, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            await sync_to_async(receipt.image.open)("rb")
            file_bytes = await sync_to_async(receipt.image.read)()
            tmp.write(file_bytes)
            await sync_to_async(receipt.image.close)()
        ai_data = await process_receipt_image(tmp_path)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    receipt.vendor = ai_data.vendor
    receipt.total_amount = ai_data.total_amount
    receipt.vat_amount = ai_data.vat_amount
    receipt.date = ai_data.date
    receipt.category = ai_data.category
    await receipt.asave(
        update_fields=["vendor", "total_amount", "vat_amount", "date", "category"],
    )

    return await sync_to_async(_render_fragment)(
        "receipts/partials/scan_result_form.html",
        {"receipt": receipt, "signed_receipt": RECEIPT_SIGNER.sign(str(receipt.pk))},
    )


@router.post("/save")
async def save_receipt(
    request: HttpRequest,
    signed_receipt: Form[str],
    vendor: Form[str] = "",
    total_amount: Form[str] = "",
    vat_amount: Form[str] = "",
    date: Form[str] = "",
    category: Form[str] = "",
) -> HttpResponse:
    authentication_error = _require_authenticated_user(request)
    if authentication_error is not None:
        return authentication_error

    try:
        receipt_id = int(RECEIPT_SIGNER.unsign(signed_receipt))
    except (BadSignature, ValueError):
        return HttpResponseForbidden("Ogiltig kvittosession.")

    try:
        receipt = await Receipt.objects.aget(pk=receipt_id)
    except Receipt.DoesNotExist:
        return HttpResponseForbidden("Kvitto saknas eller är inte tillgängligt.")
    if receipt.owner_id != request.user.id:
        return HttpResponseForbidden("Du saknar behörighet för detta kvitto.")

    receipt.vendor = vendor.strip()
    receipt.total_amount = _parse_decimal(total_amount)
    receipt.vat_amount = _parse_decimal(vat_amount)
    receipt.date = _parse_date(date)
    receipt.category = category.strip()
    await receipt.asave(update_fields=["vendor", "total_amount", "vat_amount", "date", "category"])

    return await sync_to_async(_render_fragment)(
        "receipts/partials/scan_saved.html",
        {"receipt": receipt},
    )
