from __future__ import annotations

import logging
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.http.response import HttpResponseBase
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST, require_http_methods

from apps.billing.services import get_feature_gates_sync
from apps.receipts import selectors, services
from apps.receipts.forms import parse_edit_form
from apps.receipts.models import Receipt, TaxYear

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
    return HttpResponseRedirect(
        reverse("tax_year_detail", kwargs={"year": year})
    )


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
    return HttpResponseRedirect(
        reverse("tax_year_detail", kwargs={"year": year})
    )


# -----------------------------------------------------------------------------
# Receipt CRUD — /kvitton/<id>/...
# -----------------------------------------------------------------------------


@login_required
def receipt_detail(request: HttpRequest, receipt_id: int) -> HttpResponse:
    """Read-only detail view for a single receipt."""
    receipt = get_object_or_404(
        Receipt.objects.select_related("tax_year", "property"),
        pk=receipt_id,
        owner=request.user,
    )
    return render(
        request,
        "receipts/receipt_detail.html",
        {
            "receipt": receipt,
            "is_locked": (
                receipt.tax_year.is_locked if receipt.tax_year_id else False
            ),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def receipt_edit(request: HttpRequest, receipt_id: int) -> HttpResponse:
    """Edit view for a single receipt. Blocked when tax_year is locked."""
    receipt = get_object_or_404(
        Receipt.objects.select_related("tax_year", "property"),
        pk=receipt_id,
        owner=request.user,
    )

    if receipt.tax_year_id and receipt.tax_year.is_locked:
        return render(
            request,
            "receipts/receipt_edit_locked.html",
            {"receipt": receipt},
            status=403,
        )

    if request.method == "POST":
        cleaned, errors = parse_edit_form(request.POST)
        if errors or cleaned is None:
            return render(
                request,
                "receipts/receipt_edit.html",
                {
                    "receipt": receipt,
                    "form_values": request.POST,
                    "errors": errors,
                },
                status=400,
            )

        try:
            services.update_receipt(
                receipt=receipt,
                vendor=cleaned.vendor,
                total_amount=cleaned.total_amount,
                vat_amount=cleaned.vat_amount,
                date=cleaned.date,
                category=cleaned.category,
                note=cleaned.note,
            )
        except ValidationError as exc:
            err_messages = (
                list(exc.message_dict.values())
                if hasattr(exc, "message_dict")
                else exc.messages
            )
            flat = "; ".join(str(m) for m in err_messages) or "Ogiltig data."
            return render(
                request,
                "receipts/receipt_edit.html",
                {
                    "receipt": receipt,
                    "form_values": request.POST,
                    "errors": {"form": flat},
                },
                status=400,
            )

        return redirect("receipt_detail", receipt_id=receipt.pk)

    # GET — show form pre-filled with current values
    return render(
        request,
        "receipts/receipt_edit.html",
        {
            "receipt": receipt,
            "form_values": {
                "vendor": receipt.vendor,
                "total_amount": f"{receipt.total_amount:.2f}",
                "vat_amount": f"{receipt.vat_amount:.2f}",
                "date": receipt.date.isoformat() if receipt.date else "",
                "category": receipt.category,
                "note": receipt.note,
            },
            "errors": {},
        },
    )


@login_required
@require_POST
def receipt_delete(request: HttpRequest, receipt_id: int) -> HttpResponse:
    """Hard-delete a receipt. Requires POST."""
    receipt = get_object_or_404(
        Receipt.objects.select_related("tax_year"),
        pk=receipt_id,
        owner=request.user,
    )

    try:
        metadata = services.delete_receipt(receipt=receipt)
    except ValidationError as exc:
        return render(
            request,
            "receipts/receipt_detail.html",
            {
                "receipt": receipt,
                "is_locked": True,
                "error": (
                    str(exc.messages[0])
                    if exc.messages
                    else "Kunde inte radera."
                ),
            },
            status=403,
        )

    tax_year = metadata.get("tax_year")
    if tax_year:
        return redirect("tax_year_detail", year=tax_year)
    return redirect("receipts_list")
