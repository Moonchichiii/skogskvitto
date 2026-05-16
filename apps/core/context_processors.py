from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def legal_contact(_: HttpRequest) -> dict[str, str]:
    return {"privacy_contact": settings.PRIVACY_CONTACT}


def _cloudinary_image_url(
    public_id: str,
    *,
    width: int,
    height: int,
    quality: str = "auto:good",
) -> str:
    cloud_name = settings.CLOUDINARY_CLOUD_NAME.strip()
    clean_public_id = public_id.strip().removeprefix("/")

    if not cloud_name or not clean_public_id:
        return ""

    return (
        f"https://res.cloudinary.com/{cloud_name}/image/upload/"
        f"f_auto,q_{quality},c_fill,g_auto,w_{width},h_{height}/"
        f"{clean_public_id}"
    )


def public_assets(_: HttpRequest) -> dict[str, dict[str, str]]:
    hero_public_id = settings.MARKETING_HERO_IMAGE_PUBLIC_ID

    return {
        "marketing_hero_image": {
            "small": _cloudinary_image_url(
                hero_public_id,
                width=640,
                height=760,
                quality="auto:eco",
            ),
            "medium": _cloudinary_image_url(
                hero_public_id,
                width=960,
                height=820,
                quality="auto:good",
            ),
            "large": _cloudinary_image_url(
                hero_public_id,
                width=1280,
                height=980,
                quality="auto:good",
            ),
        }
    }