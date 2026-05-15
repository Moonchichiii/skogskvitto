from collections.abc import Awaitable, Callable
from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest
from django.http.response import HttpResponseBase

type AsyncView = Callable[[HttpRequest], Awaitable[HttpResponseBase]]

def login_required_async(view: AsyncView) -> AsyncView:
    @wraps(view)
    async def wrapped(request: HttpRequest) -> HttpResponseBase:
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        return await view(request)
    return wrapped