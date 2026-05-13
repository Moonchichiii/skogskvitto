from pathlib import Path

import magic
from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from ninja import File, Router
from ninja.files import UploadedFile

from receipts.models import Receipt
from receipts.services import (
    SUPPORTED_IMAGE_MIME_TYPES,
    process_receipt_image,
    strip_exif_and_prepare_image,
)

router = Router(tags=["receipts"])

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024


def _render_fragment(template: str, context: dict[str, object], status: int = 200) -> HttpResponse:
    html = render_to_string(template, context)
    return HttpResponse(html, status=status)


def _detect_image_mime(upload: UploadedFile) -> str:
    head = upload.read(4096)
    upload.seek(0)
    return str(magic.from_buffer(head, mime=True))


@router.post("/scan")
async def scan_receipt(request: HttpRequest, image: UploadedFile = File(...)) -> HttpResponse:
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
    owner = request.user if request.user.is_authenticated else None
    receipt = await Receipt.objects.acreate(owner=owner, image=cleaned_file)

    ai_data = await process_receipt_image(Path(receipt.image.path))
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
        {"receipt": receipt},
    )
