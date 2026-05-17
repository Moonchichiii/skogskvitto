"""Cloudinary client — dumb pipes for signing and fetching.

Provides:
  - sign_upload_params(): server-side signature for direct-to-Cloudinary uploads
  - fetch_image_bytes(): downloads a secure URL for downstream OCR

Does NOT touch Django models. Caller is responsible for orchestration.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from urllib.parse import urlparse

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

FETCH_TIMEOUT = 30.0
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


def api_secret() -> str:
    return str(getattr(settings, "CLOUDINARY_API_SECRET", "") or "")


def api_key() -> str:
    return str(getattr(settings, "CLOUDINARY_API_KEY", "") or "")


def cloud_name() -> str:
    return str(getattr(settings, "CLOUDINARY_CLOUD_NAME", "") or "")


def is_configured() -> bool:
    return bool(api_secret() and api_key() and cloud_name())


def sign_upload_params(params: dict[str, str | int]) -> str:
    """Cloudinary v1 signature: sorted key=value joined with '&', SHA-1 with secret appended."""
    sorted_pairs = sorted((k, str(v)) for k, v in params.items())
    to_sign = "&".join(f"{k}={v}" for k, v in sorted_pairs)
    return hashlib.sha1((to_sign + api_secret()).encode("utf-8")).hexdigest()


def fetch_image_bytes(secure_url: str) -> tuple[bytes, str]:
    """Download an image from Cloudinary and return (bytes, file_suffix).

    Raises:
        httpx.HTTPError: on any HTTP-level failure
        ValueError: if the image exceeds MAX_IMAGE_BYTES
    """
    with httpx.Client(timeout=FETCH_TIMEOUT) as client:
        response = client.get(secure_url)
    response.raise_for_status()

    if len(response.content) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"Bilden är för stor ({len(response.content)} byte, max {MAX_IMAGE_BYTES})"
        )

    path = urlparse(secure_url).path
    suffix = Path(path).suffix.lower() or ".jpg"

    return response.content, suffix
