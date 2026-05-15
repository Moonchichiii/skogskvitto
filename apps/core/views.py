from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.receipts.billing import (
    FREE_RECEIPT_LIMIT,
    PLAN_FREE,
    PLAN_PILOT,
    PLAN_PREMIUM,
    PLAN_TRIAL,
    get_feature_gates,
)
from apps.receipts.models import Receipt


async def _get_receipt_count(user_id: int | None) -> int:
    if user_id is None:
        return 0

    return await Receipt.objects.filter(owner_id=user_id).acount()


async def profile(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())

    user = request.user
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
        PLAN_FREE: "Du kan testa scanning och förhandsvisning.",
        PLAN_TRIAL: "Du testar SkogsKvitto. Export och nedladdning kräver betalplan.",
        PLAN_PREMIUM: "Export och nedladdning är aktiverat.",
        PLAN_PILOT: "Testpilotläge är aktiverat för feedback och utveckling.",
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
                user_plan,
                "Du kan testa scanning och förhandsvisning.",
            ),
            "full_name": full_name,
            "receipt_count": receipt_count,
            "free_receipt_limit": FREE_RECEIPT_LIMIT,
            "export_enabled": export_enabled,
            "is_testpilot": bool(gates.get("is_pilot", False)),
        },
    )
