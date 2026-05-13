from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.receipts.billing import get_feature_gates


async def index(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    gates = await get_feature_gates(request.user)
    return render(request, "core/index.html", {"gates": gates})
