from __future__ import annotations

import logging

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.billing.services import get_user_billing_summary

logger = logging.getLogger(__name__)


@login_required
def profile(request: HttpRequest) -> HttpResponse:
    """User profile hub.

    Owns: display name, email display, links to allauth's email/password
    pages, link to delete-account flow.

    Consumes (read-only): a single immutable billing summary DTO.
    """

    user = request.user
    billing_summary = get_user_billing_summary(user)

    return render(
        request,
        "accounts/profile.html",
        {
            "billing_summary": billing_summary,
            "full_name": user.get_full_name().strip(),
            "email": user.email,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def delete_account(request: HttpRequest) -> HttpResponse:
    """Self-service account deletion.

    GET: render confirmation form.
    POST: require user to retype their own email, then delete + logout.

    Cascade deletes Receipts, ReceiptScanJobs and UserSubscription via the
    FK definitions in each respective app. Stripe-side cancellation is NOT
    performed here — see note at the end of the response.
    """

    if request.method == "POST":
        confirm = request.POST.get("confirm_email", "").strip().lower()
        if confirm != request.user.email.lower():
            logger.warning(
                "accounts.delete_account.email_mismatch",
                extra={"user_id": request.user.pk},
            )
            return render(
                request,
                "accounts/delete_confirm.html",
                {"error": "E-postadressen matchade inte. Kontot raderades inte."},
                status=400,
            )

        user = request.user
        user_id = user.pk
        user_email = user.email
        logout(request)
        user.delete()
        logger.info(
            "accounts.delete_account.deleted",
            extra={"user_id": user_id, "email": user_email},
        )
        return redirect("home")

    return render(request, "accounts/delete_confirm.html", {})
