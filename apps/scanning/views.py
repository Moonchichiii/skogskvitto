from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.billing.services import get_feature_gates_sync


@login_required
def scan(request: HttpRequest) -> HttpResponse:
    gates = get_feature_gates_sync(request.user)
    return render(request, "scanning/scan.html", {"gates": gates})
