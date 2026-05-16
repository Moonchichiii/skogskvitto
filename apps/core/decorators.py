from collections.abc import Callable
from functools import wraps
from typing import Concatenate, ParamSpec, TypeVar, cast

from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest
from django.http.response import HttpResponseBase

P = ParamSpec("P")
R = TypeVar("R", bound=HttpResponseBase)


def login_required_view(
    view_func: Callable[Concatenate[HttpRequest, P], R],
) -> Callable[Concatenate[HttpRequest, P], HttpResponseBase]:
    @wraps(view_func)
    def wrapped(
        request: HttpRequest,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> HttpResponseBase:
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        return cast(HttpResponseBase, view_func(request, *args, **kwargs))

    return wrapped
