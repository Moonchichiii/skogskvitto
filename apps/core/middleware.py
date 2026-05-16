from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

LOCAL_DEV_HOSTS = {
    "localhost:8000",
    "localhost:8001",
    "127.0.0.1:8000",
    "127.0.0.1:8001",
}


class LocalNullOriginMiddleware:
    """
    Local development only.

    Some local browser flows can send Origin: null on localhost POSTs.
    This removes only that local null Origin before Django's CSRF check.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if (
            settings.DEBUG
            and request.META.get("HTTP_ORIGIN") == "null"
            and request.get_host() in LOCAL_DEV_HOSTS
        ):
            request.META.pop("HTTP_ORIGIN", None)

        return self.get_response(request)
