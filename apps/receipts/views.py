import io
from collections.abc import Awaitable, Callable
from datetime import date
from decimal import Decimal
from functools import wraps

from asgiref.sync import sync_to_async
from django.contrib.auth.views import redirect_to_login
from django.http import FileResponse, HttpRequest
from django.http.response import HttpResponseBase
from django.shortcuts import render

from apps.receipts.exports import build_excel
from apps.receipts.models import Receipt

type AsyncView = Callable[[HttpRequest], Awaitable[HttpResponseBase]]


def login_required_async(view: AsyncView) -> AsyncView:
    @wraps(view)
    async def wrapped(request: HttpRequest) -> HttpResponseBase:
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        return await view(request)

    return wrapped


@login_required_async
async def dashboard(request: HttpRequest) -> HttpResponseBase:
    year = date.today().year
    receipts = [
        r
        async for r in Receipt.objects.filter(owner=request.user).order_by(
            "-date", "-created_at"
        )
    ]

    year_receipts = [r for r in receipts if r.date and r.date.year == year]
    total_year = sum((r.total_amount or Decimal(0) for r in year_receipts), Decimal(0))
    vat_year = sum((r.vat_amount or Decimal(0) for r in year_receipts), Decimal(0))

    return render(
        request,
        "receipts/dashboard.html",
        {"receipts": receipts, "total_year": total_year, "vat_year": vat_year, "year": year},
    )


@login_required_async
async def export_excel(request: HttpRequest) -> HttpResponseBase:
    receipts = [
        r
        async for r in Receipt.objects.filter(owner=request.user).order_by(
            "-date", "-created_at"
        )
    ]

    buf: io.BytesIO = await sync_to_async(build_excel)(receipts)
    filename = f"SkogsKvitto_Export_{date.today().isoformat()}.xlsx"
    return FileResponse(
        buf,
        as_attachment=True,
        filename=filename,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
