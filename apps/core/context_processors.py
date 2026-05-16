from django.conf import settings
from django.http import HttpRequest


def legal_contact(_: HttpRequest) -> dict[str, str]:
    return {"privacy_contact": settings.PRIVACY_CONTACT}


def public_assets(_: HttpRequest) -> dict[str, object]:
    cloud_name = settings.CLOUDINARY_CLOUD_NAME
    hero_public_id = settings.MARKETING_HERO_IMAGE_PUBLIC_ID

    if not cloud_name or not hero_public_id:
        return {
            "marketing_hero_image": {},
        }

    base_url = f"https://res.cloudinary.com/{cloud_name}/image/upload"

    return {
        "marketing_hero_image": {
            "small": (
                f"{base_url}/f_auto,q_auto:eco,c_fill,g_auto,"
                f"w_640,h_620/{hero_public_id}"
            ),
            "medium": (
                f"{base_url}/f_auto,q_auto:eco,c_fill,g_auto,"
                f"w_960,h_820/{hero_public_id}"
            ),
            "large": (
                f"{base_url}/f_auto,q_auto:eco,c_fill,g_auto,"
                f"w_1280,h_980/{hero_public_id}"
            ),
        }
    }
