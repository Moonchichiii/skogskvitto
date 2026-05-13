from django.conf import settings
from django.http import HttpRequest


def legal_contact(_: HttpRequest) -> dict[str, str]:
    return {"privacy_contact": settings.PRIVACY_CONTACT}
