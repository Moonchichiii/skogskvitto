from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any, cast

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_TIMEOUT_SECONDS = 45.0

EXTENSION_TO_MIME: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _api_key() -> str:
    return str(getattr(settings, "OPENAI_API_KEY", "") or "")


def _model() -> str:
    return str(getattr(settings, "OPENAI_MODEL", "gpt-4.1-mini") or "gpt-4.1-mini")


def is_configured() -> bool:
    return bool(_api_key())


def _encode_image(image_bytes: bytes, suffix: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    mime_type = EXTENSION_TO_MIME.get(suffix.lower(), "image/jpeg")
    return f"data:{mime_type};base64,{encoded}"


def _extract_json_payload(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]).strip()

    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        msg = "OpenAI response payload must be a JSON object."
        raise TypeError(msg)

    return cast(dict[str, Any], payload)


async def extract_receipt_fields_from_path(file_path: Path) -> dict[str, Any]:
    """Send a receipt image to OpenAI and return the raw extracted JSON dict.

    This is a dumb pipe. No Django models, no domain logic. The caller is
    responsible for validating and persisting the result.
    """

    if not is_configured():
        return {}

    image_bytes = file_path.read_bytes()
    return await extract_receipt_fields_from_bytes(image_bytes, file_path.suffix)


async def extract_receipt_fields_from_bytes(image_bytes: bytes, suffix: str) -> dict[str, Any]:
    if not is_configured():
        return {}

    data_uri = _encode_image(image_bytes, suffix)

    instruction = (
        "Extract receipt data and return strict JSON with keys: "
        "vendor, total_amount, vat_amount, date, category. "
        "Use ISO date format YYYY-MM-DD and numbers for amounts."
    )

    payload: dict[str, Any] = {
        "model": _model(),
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

    headers = {"Authorization": f"Bearer {_api_key()}"}

    async with httpx.AsyncClient(timeout=OPENAI_TIMEOUT_SECONDS) as client:
        response = await client.post(OPENAI_API_URL, headers=headers, json=payload)

    response.raise_for_status()
    completion = response.json()

    try:
        content = completion["choices"][0]["message"]["content"]
        return _extract_json_payload(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        logger.warning("openai_client.parse_failed", exc_info=True)
        return {}
