from typing import cast
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest
from django.http.response import HttpResponseBase
from django.shortcuts import render
from apps.billing.services import (
    FREE_RECEIPT_LIMIT,
    PLAN_FREE,
    PLAN_PILOT,
    PLAN_PREMIUM,
    PLAN_TRIAL,
    get_feature_gates,
)
from apps.core.models import User
from apps.receipts.models import Receipt

async def _get_receipt_count(user_id: int | None) -> int:
    if user_id is None:
        return 0
    return await Receipt.objects.filter(owner_id=user_id).acount()

async def profile(request: HttpRequest) -> HttpResponseBase:
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())

    user = cast(User, request.user)
    gates = await get_feature_gates(user)
    user_plan = str(gates.get("user_plan", PLAN_FREE))
    receipt_count = await _get_receipt_count(user.pk)

    plan_labels = {
        PLAN_FREE: "Gratis",
        PLAN_TRIAL: "Trial",
        PLAN_PREMIUM: "Premium",
        PLAN_PILOT: "Testpilot",
    }
    plan_descriptions = {
        PLAN_FREE: "Du kan testa scanning och fÃ¶rhandsvisning.",
        PLAN_TRIAL: "Du testar SkogsKvitto. Export och nedladdning krÃ¤ver betalplan.",
        PLAN_PREMIUM: "Export och nedladdning Ã¤r aktiverat.",
        PLAN_PILOT: "TestpilotlÃ¤ge Ã¤r aktiverat fÃ¶r feedback och utveckling.",
    }

    full_name = user.get_full_name().strip()
    export_enabled = bool(gates.get("can_excel_download", False))

    return render(
        request,
        "account/profile.html",
        {
            "user_plan": user_plan,
            "plan_label": plan_labels.get(user_plan, "Gratis"),
            "plan_description": plan_descriptions.get(
                user_plan, "Du kan testa scanning och fÃ¶rhandsvisning.",
            ),
            "full_name": full_name,
            "receipt_count": receipt_count,
            "free_receipt_limit": FREE_RECEIPT_LIMIT,
            "export_enabled": export_enabled,
            "is_testpilot": bool(gates.get("is_pilot", False)),
        },
    )