import base64
import json
import logging
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from decouple import config
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image
from pydantic import BaseModel, Field, ValidationError

OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
OPENAI_MODEL = config("OPENAI_MODEL", default="gpt-4.1-mini")
logger = logging.getLogger(__name__)


class ReceiptScanResult(BaseModel):
    vendor: str = Field(default="")
    total_amount: Decimal | None = Field(default=None)
    vat_amount: Decimal | None = Field(default=None)
    date: date | None = Field(default=None)
    category: str = Field(default="")


SUPPORTED_IMAGE_MIME_TYPES = {
    "image/jpeg": ("JPEG", ".jpg"),
    "image/png": ("PNG", ".png"),
    "image/webp": ("WEBP", ".webp"),
}
EXTENSION_TO_MIME = {ext: mime for mime, (_, ext) in SUPPORTED_IMAGE_MIME_TYPES.items()}
Image.MAX_IMAGE_PIXELS = 20_000_000


def strip_exif_and_prepare_image(uploaded_file: UploadedFile, detected_mime: str) -> ContentFile:
    image = Image.open(uploaded_file)
    image_format, extension = SUPPORTED_IMAGE_MIME_TYPES[detected_mime]
    if image_format == "JPEG":
        image = image.convert("RGB")

    output = BytesIO()
    image.save(output, format=image_format)
    output.seek(0)
    return ContentFile(output.read(), name=f"upload{extension}")


def _extract_json_payload(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]).strip()
    return json.loads(cleaned)


async def process_receipt_image(file_path: Path) -> ReceiptScanResult:
    if not OPENAI_API_KEY:
        return ReceiptScanResult()

    image_bytes = file_path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    mime_type = EXTENSION_TO_MIME.get(file_path.suffix.lower(), "image/jpeg")
    data_uri = f"data:{mime_type};base64,{encoded}"

    instruction = (
        "Extract receipt data and return strict JSON with keys: "
        "vendor, total_amount, vat_amount, date, category. "
        "Use ISO date format YYYY-MM-DD and numbers for amounts."
    )
    payload = {
        "model": OPENAI_MODEL,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "You only return strict JSON, no markdown, no prose.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": instruction},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            },
        ],
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )
    response.raise_for_status()
    completion = response.json()
    content = completion["choices"][0]["message"]["content"]

    try:
        parsed = _extract_json_payload(content)
        return ReceiptScanResult.model_validate(parsed)
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValidationError):
        logger.warning("Failed to parse OpenAI receipt response", exc_info=True)
        return ReceiptScanResult()
