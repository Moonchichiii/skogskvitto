from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.billing.services import (
    FREE_RECEIPT_LIMIT,
    PLAN_FREE,
    PLAN_PILOT,
    PLAN_PREMIUM,
    PLAN_TRIAL,
    get_feature_gates_sync,
)
from apps.core.decorators import login_required_view
from apps.receipts.models import Receipt


@login_required_view
def profile(request: HttpRequest) -> HttpResponse:
    user = request.user
    gates = get_feature_gates_sync(user)
    user_plan = str(gates.get("user_plan", PLAN_FREE))
    receipt_count = Receipt.objects.filter(owner=user).count()

    plan_labels = {
        PLAN_FREE: "Gratis",
        PLAN_TRIAL: "Trial",
        PLAN_PREMIUM: "Premium",
        PLAN_PILOT: "Testpilot",
    }
    plan_descriptions = {
        PLAN_FREE: "Du kan testa scanning och förhandsvisning.",
        PLAN_TRIAL: "Du testar SkogsKvitto. Export och nedladdning kr?ver betalplan.",
        PLAN_PREMIUM: "Export och nedladdning ?r aktiverat.",
        PLAN_PILOT: "Testpilotl?ge ?r aktiverat f?r feedback och utveckling.",
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
