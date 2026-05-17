from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.billing.services import get_feature_gates_sync
from apps.receipts.models import Receipt


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    user = request.user
    year = date.today().year

    page_number_raw = request.GET.get("page", "1")
    page_number = int(page_number_raw) if page_number_raw.isdigit() else 1
    page_number = max(page_number, 1)
    page_size = 25

    base_queryset = Receipt.objects.filter(owner=user).order_by("-date", "-created_at")
    paginator = Paginator(base_queryset, page_size)
    page_obj = paginator.get_page(page_number)
    receipts = list(page_obj.object_list)

    aggregates = Receipt.objects.filter(owner=user, date__year=year).aggregate(
        total_year=Sum("total_amount"),
        vat_year=Sum("vat_amount"),
    )
    total_year = aggregates.get("total_year") or Decimal("0.00")
    vat_year = aggregates.get("vat_year") or Decimal("0.00")

    gates = get_feature_gates_sync(user)

    return render(
        request,
        "receipts/dashboard.html",
        {
            "receipts": receipts,
            "total_year": total_year,
            "vat_year": vat_year,
            "year": year,
            "gates": gates,
            "page_obj": page_obj,
        },
    )
