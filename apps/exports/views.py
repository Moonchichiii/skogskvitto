from __future__ import annotations

import logging
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpRequest
from django.http.response import HttpResponseBadRequest, HttpResponseBase, HttpResponseForbidden

from apps.billing.services import FEATURE_EXCEL_DOWNLOAD, can_use_feature_sync
from apps.exports.services import build_excel
from apps.receipts.selectors import receipts_for_year, user_receipts

logger = logging.getLogger(__name__)


@login_required
def export_excel(request: HttpRequest) -> HttpResponseBase:
    decision = can_use_feature_sync(request.user, FEATURE_EXCEL_DOWNLOAD)
    if not decision.allowed:
        logger.info(
            "exports.export_excel.denied",
            extra={"user_id": request.user.pk, "reason": decision.reason},
        )
        return HttpResponseForbidden("Export och nedladdning ingår i betalplanen.")

    year_raw = request.GET.get("year", "")
    if year_raw:
        if not year_raw.isdigit():
            return HttpResponseBadRequest("Ogiltigt år.")
        year = int(year_raw)
        receipts = list(receipts_for_year(request.user, year))
        filename = f"SkogsKvitto_Inkomstar_{year}.xlsx"
    else:
        receipts = list(user_receipts(request.user).order_by("-date", "-created_at"))
        year = None
        filename = f"SkogsKvitto_Alla_Kvitton_{date.today().isoformat()}.xlsx"

    if not receipts:
        logger.info(
            "exports.export_excel.empty",
            extra={"user_id": request.user.pk, "year": year},
        )
        return HttpResponseBadRequest(
            "Inga kvitton att exportera. Scanna minst ett kvitto först."
        )

    buf = build_excel(receipts)
    logger.info(
        "exports.export_excel.success",
        extra={
            "user_id": request.user.pk,
            "year": year,
            "receipt_count": len(receipts),
        },
    )
    return FileResponse(
        buf,
        as_attachment=True,
        filename=filename,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

