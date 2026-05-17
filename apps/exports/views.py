from __future__ import annotations

from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpRequest
from django.http.response import HttpResponseBase, HttpResponseForbidden

from apps.billing.services import FEATURE_EXCEL_DOWNLOAD, can_use_feature_sync
from apps.exports.services import build_excel
from apps.receipts.models import Receipt


@login_required
def export_excel(request: HttpRequest) -> HttpResponseBase:
    decision = can_use_feature_sync(request.user, FEATURE_EXCEL_DOWNLOAD)
    if not decision.allowed:
        return HttpResponseForbidden("Export och nedladdning ingår i betalplanen.")

    receipts = list(
        Receipt.objects.filter(owner=request.user).order_by("-date", "-created_at")
    )

    buf = build_excel(receipts)
    filename = f"SkogsKvitto_Export_{date.today().isoformat()}.xlsx"

    return FileResponse(
        buf,
        as_attachment=True,
        filename=filename,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

