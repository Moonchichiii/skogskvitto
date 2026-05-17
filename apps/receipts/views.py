from __future__ import annotations

import logging
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.http.response import HttpResponseBase
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.billing.services import get_feature_gates_sync
from apps.receipts import selectors, services
from apps.receipts.models import TaxYear

logger = logging.getLogger(__name__)

RECEIPTS_PAGE_SIZE = 24
THUMB_SIZE = 240


def _thumbnail_url(public_id: str, *, size: int) -> str:
    cloud_name = str(getattr(settings, "CLOUDINARY_CLOUD_NAME", "")).strip()
    clean = (public_id or "").strip().lstrip("/")
    if not cloud_name or not clean:
        return ""
    transformation = f"f_auto,q_auto:eco,c_fill,g_auto,w_{size},h_{size}"
    return f"https://res.cloudinary.com/{cloud_name}/image/upload/{transformation}/{quote(clean, safe='/')}"


def _parse_year_filter(raw: str | None, available_years: list[int]) -> int | None:
    """Validate ?year= query param against the user's actual years."""
    if not raw:
        return None
    if not raw.isdigit():
        return None
    candidate = int(raw)
    return candidate if candidate in available_years else None


# -----------------------------------------------------------------------------
# Receipts collection — /kvitton/
# -----------------------------------------------------------------------------


@login_required
def receipts_list(request: HttpRequest) -> HttpResponse:
    """All receipts for the user, filterable by year."""
    user = request.user

    # Build the list of years that actually have receipts (for the filter)
    available_years = list(
        selectors.user_tax_years(user)
        .values_list("year", flat=True)
        .order_by("-year")
    )

    selected_year = _parse_year_filter(request.GET.get("year"), available_years)

    queryset = selectors.user_receipts(user).order_by("-date", "-created_at")
    if selected_year is not None:
        queryset = queryset.filter(date__year=selected_year)

    page_number_raw = request.GET.get("page", "1")
    page_number = int(page_number_raw) if page_number_raw.isdigit() else 1
    page_number = max(page_number, 1)

    paginator = Paginator(queryset, RECEIPTS_PAGE_SIZE)
    page_obj = paginator.get_page(page_number)

    receipts_with_thumbs = [
        (receipt, _thumbnail_url(receipt.cloudinary_public_id, size=THUMB_SIZE))
        for receipt in page_obj.object_list
    ]

    return render(
        request,
        "receipts/receipts_list.html",
        {
            "receipts_with_thumbs": receipts_with_thumbs,
            "available_years": available_years,
            "selected_year": selected_year,
            "page_obj": page_obj,
            "gates": get_feature_gates_sync(user),
        },
    )


# -----------------------------------------------------------------------------
# Tax years list — /inkomstar/
# -----------------------------------------------------------------------------


@login_required
def tax_year_list(request: HttpRequest) -> HttpResponse:
    """List of all tax years for the user, with totals and lock status."""
    tax_years = list(selectors.tax_years_with_totals(request.user))

    return render(
        request,
        "receipts/tax_year_list.html",
        {
            "tax_years": tax_years,
            "gates": get_feature_gates_sync(request.user),
        },
    )


# -----------------------------------------------------------------------------
# Tax year detail — /inkomstar/<year>/
# -----------------------------------------------------------------------------


@login_required
def tax_year_detail(request: HttpRequest, year: int) -> HttpResponse:
    """A single tax year — receipts grid + lock/unlock + export buttons."""
    tax_year = get_object_or_404(TaxYear, owner=request.user, year=year)

    receipts = list(tax_year.receipts.order_by("-date", "-created_at"))
    receipts_with_thumbs = [
        (receipt, _thumbnail_url(receipt.cloudinary_public_id, size=THUMB_SIZE))
        for receipt in receipts
    ]

    totals = selectors.year_totals(request.user, year)

    return render(
        request,
        "receipts/tax_year_detail.html",
        {
            "tax_year": tax_year,
            "receipts_with_thumbs": receipts_with_thumbs,
            "total_year": totals["total"],
            "vat_year": totals["vat"],
            "receipt_count": totals["count"],
            "gates": get_feature_gates_sync(request.user),
        },
    )


# -----------------------------------------------------------------------------
# Lock / unlock — POST endpoints
# -----------------------------------------------------------------------------


@login_required
@require_POST
def tax_year_lock(request: HttpRequest, year: int) -> HttpResponseBase:
    tax_year = get_object_or_404(TaxYear, owner=request.user, year=year)
    services.lock_tax_year(tax_year=tax_year)
    
    logger.info(
        "receipts.tax_year_lock",
        extra={"user_id": request.user.pk, "year": year},
    )
    
    messages.success(
        request,
        f"Inkomstår {year} är nu låst. Befintliga kvitton kan inte ändras.",
    )
    return HttpResponseRedirect(reverse("tax_year_detail", kwargs={"year": year}))


@login_required
@require_POST
def tax_year_unlock(request: HttpRequest, year: int) -> HttpResponseBase:
    tax_year = get_object_or_404(TaxYear, owner=request.user, year=year)
    services.unlock_tax_year(tax_year=tax_year)
    
    logger.info(
        "receipts.tax_year_unlock",
        extra={"user_id": request.user.pk, "year": year},
    )
    
    messages.info(
        request,
        f"Inkomstår {year} är upplåst. Kvitton kan nu redigeras igen.",
    )
    return HttpResponseRedirect(reverse("tax_year_detail", kwargs={"year": year}))
