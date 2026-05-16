from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render


def home(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("scan")
    return render(request, "marketing/home.html")
