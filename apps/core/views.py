from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.receipts import selectors

OVERVIEW_THUMB_COUNT = 5
OVERVIEW_THUMB_SIZE = 120
PRELOAD_COUNT = 18
PRELOAD_SIZE = 240


def _thumbnail_url(public_id: str, *, size: int) -> str:
    cloud_name = str(getattr(settings, "CLOUDINARY_CLOUD_NAME", "")).strip()
    clean = (public_id or "").strip().lstrip("/")
    if not cloud_name or not clean:
        return ""
    transformation = f"f_auto,q_auto:eco,c_fill,g_auto,w_{size},h_{size}"
    return f"https://res.cloudinary.com/{cloud_name}/image/upload/{transformation}/{quote(clean, safe='/')}"


def home(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "core/home.html")


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """Authenticated landing — overview tiles + recent thumbnails + year summary."""
    user = request.user
    year = selectors.current_year()

    recent = selectors.latest_receipts(user, limit=PRELOAD_COUNT)
    public_ids = [r.cloudinary_public_id for r in recent if r.cloudinary_public_id]

    recent_thumbs = [
        url
        for url in (
            _thumbnail_url(pid, size=OVERVIEW_THUMB_SIZE)
            for pid in public_ids[:OVERVIEW_THUMB_COUNT]
        )
        if url
    ]
    preload_thumbs = [
        url
        for url in (_thumbnail_url(pid, size=PRELOAD_SIZE) for pid in public_ids)
        if url
    ]

    receipt_count = selectors.user_receipts(user).count()
    totals = selectors.year_totals(user, year)

    tax_year_count = selectors.user_tax_years(user).count()

    first_name = (user.first_name or "").strip()

    return render(
        request,
        "core/dashboard.html",
        {
            "first_name": first_name,
            "recent_thumbs": recent_thumbs,
            "preload_thumbs": preload_thumbs,
            "receipt_count": receipt_count,
            "receipt_count_year": totals["count"],
            "remaining": max(receipt_count - OVERVIEW_THUMB_COUNT, 0),
            "tax_year_count": tax_year_count,
            "year": year,
            "total_year": totals["total"],
            "vat_year": totals["vat"],
        },
    )
