import io
from datetime import date
from decimal import Decimal

from asgiref.sync import sync_to_async
from django.http import FileResponse, HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render

from apps.receipts.exports import build_excel
from apps.receipts.models import Receipt


async def dashboard(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("/")

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


async def export_excel(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

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
