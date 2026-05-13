from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@login_required
@require_GET
def index(request: HttpRequest) -> HttpResponse:
    return render(request, "core/index.html")
