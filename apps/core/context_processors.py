from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def legal_contact(_: HttpRequest) -> dict[str, str]:
    return {
        "privacy_contact": settings.PRIVACY_CONTACT,
        "support_contact": settings.SUPPORT_CONTACT,
    }


def _cloudinary_image_url(public_id: str, *, width: int, height: int, quality: str) -> str:
    cloud_name = str(getattr(settings, "CLOUDINARY_CLOUD_NAME", "")).strip()
    clean_public_id = public_id.strip().lstrip("/")

    if not cloud_name or not clean_public_id:
        return ""

    transformation = f"f_auto,q_auto:{quality},c_fill,g_auto,w_{width},h_{height}"
    return f"https://res.cloudinary.com/{cloud_name}/image/upload/{transformation}/{clean_public_id}"


def public_assets(_: HttpRequest) -> dict[str, object]:
    hero_public_id = str(getattr(settings, "MARKETING_HERO_IMAGE_PUBLIC_ID", "")).strip()

    return {
        "marketing_hero_image": {
            "small": _cloudinary_image_url(hero_public_id, width=640, height=620, quality="eco"),
            "medium": _cloudinary_image_url(hero_public_id, width=960, height=820, quality="good"),
            "large": _cloudinary_image_url(hero_public_id, width=1280, height=980, quality="good"),
        }
    }


def site_meta(_: HttpRequest) -> dict[str, str]:
    """SEO defaults — overridable per page via {% block %} in base.html."""
    return {
        "site_name": "SkogsKvitto",
        "site_url": str(getattr(settings, "SITE_URL", "https://skogskvitto.se")),
        "default_og_image": str(getattr(settings, "DEFAULT_OG_IMAGE", "")),
    }
