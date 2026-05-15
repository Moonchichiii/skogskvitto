import io
from collections.abc import Awaitable, Callable
from datetime import date, datetime
from decimal import Decimal
from functools import wraps
from typing import cast

import httpx
from asgiref.sync import sync_to_async
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import FileResponse, HttpRequest, HttpResponseBadRequest, HttpResponseRedirect
from django.http.response import HttpResponseBase, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.core.models import User
from apps.billing.services import (
    FEATURE_EXCEL_DOWNLOAD,
    can_use_feature,
    get_feature_gates,
    is_premium_user,
    plan_to_price_id,
    stripe_is_configured,
    stripe_request,
)
from apps.exports.services import build_excel
from apps.receipts.models import Receipt, UserSubscription

type AsyncView = Callable[[HttpRequest], Awaitable[HttpResponseBase]]


def login_required_async(view: AsyncView) -> AsyncView:
    @wraps(view)
    async def wrapped(request: HttpRequest) -> HttpResponseBase:
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        return await view(request)

    return wrapped


@login_required_async
async def scan(request: HttpRequest) -> HttpResponseBase:
    user = cast(User, request.user)
    gates = await get_feature_gates(user)
    return render(request, "receipts/scan.html", {"gates": gates})


@login_required_async
async def dashboard(request: HttpRequest) -> HttpResponseBase:
    user = cast(User, request.user)
    year = date.today().year
    page_number_raw = request.GET.get("page", "1")
    page_number = int(page_number_raw) if page_number_raw.isdigit() else 1
    page_number = max(page_number, 1)
    page_size = 25

    base_queryset = Receipt.objects.filter(owner=user).order_by("-date", "-created_at")
    receipt_count = await base_queryset.acount()
    paginator = await sync_to_async(Paginator)(range(receipt_count), page_size)
    page_obj = paginator.get_page(page_number)

    offset = (page_obj.number - 1) * page_size
    receipts = [r async for r in base_queryset[offset : offset + page_size]]
    aggregates = await Receipt.objects.filter(owner=user, date__year=year).aaggregate(
        total_year=Sum("total_amount"),
        vat_year=Sum("vat_amount"),
    )
    total_year = cast(Decimal | None, aggregates.get("total_year")) or Decimal(0)
    vat_year = cast(Decimal | None, aggregates.get("vat_year")) or Decimal(0)

    gates = await get_feature_gates(user)

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


@login_required_async
async def export_excel(request: HttpRequest) -> HttpResponseBase:
    user = cast(User, request.user)
    decision = await can_use_feature(user, FEATURE_EXCEL_DOWNLOAD)
    if not decision.allowed:
        return HttpResponseForbidden("Export och nedladdning ingår i betalplanen.")

    receipts = [
        r async for r in Receipt.objects.filter(owner=user).order_by("-date", "-created_at")
    ]

    buf: io.BytesIO = await sync_to_async(build_excel)(receipts)
    filename = f"SkogsKvitto_Export_{date.today().isoformat()}.xlsx"
    return FileResponse(
        buf,
        as_attachment=True,
        filename=filename,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@login_required_async
async def start_checkout(request: HttpRequest) -> HttpResponseBase:
    user = cast(User, request.user)
    if not stripe_is_configured():
        return HttpResponseBadRequest(
            "Stripe-konfiguration saknas. Kontrollera STRIPE_SECRET_KEY, "
            "STRIPE_PRICE_MONTHLY_ID och STRIPE_PRICE_YEARLY_ID."
        )

    if await is_premium_user(user):
        return redirect("dashboard")

    plan = request.GET.get("plan", "yearly")
    if plan not in {"monthly", "yearly"}:
        return HttpResponseBadRequest("Ogiltig betalningsplan.")

    price_id = plan_to_price_id(plan)
    if price_id is None:
        return HttpResponseBadRequest("Ogiltig betalningsplan.")

    success_base_url = request.build_absolute_uri(reverse("billing_success"))
    success_url = f"{success_base_url}?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = request.build_absolute_uri(reverse("billing_cancel"))

    try:
        checkout_session = await stripe_request(
            "POST",
            "/checkout/sessions",
            data={
                "mode": "subscription",
                "line_items[0][price]": price_id,
                "line_items[0][quantity]": "1",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "allow_promotion_codes": "true",
                "client_reference_id": str(user.id),
                "customer_email": user.email,
            },
        )
    except httpx.HTTPError:
        return HttpResponseBadRequest("Kunde inte starta betalning just nu.")

    checkout_url = checkout_session.get("url")
    if not isinstance(checkout_url, str) or not checkout_url:
        return HttpResponseBadRequest("Stripe returnerade ingen checkout-länk.")

    return HttpResponseRedirect(checkout_url)


@login_required_async
async def billing_success(request: HttpRequest) -> HttpResponseBase:
    user = cast(User, request.user)
    if not stripe_is_configured():
        return HttpResponseBadRequest(
            "Stripe-konfiguration saknas. Kontrollera STRIPE_SECRET_KEY, "
            "STRIPE_PRICE_MONTHLY_ID och STRIPE_PRICE_YEARLY_ID."
        )

    session_id = request.GET.get("session_id", "")
    if not session_id:
        return HttpResponseBadRequest("Checkout-session saknas.")

    try:
        checkout_session = await stripe_request(
            "GET",
            f"/checkout/sessions/{session_id}",
            params=[("expand[]", "subscription")],
        )
    except httpx.HTTPError:
        return HttpResponseBadRequest("Kunde inte verifiera betalningen.")

    if checkout_session.get("mode") != "subscription":
        return HttpResponseBadRequest("Ogiltig checkout-session.")

    if checkout_session.get("status") != "complete":
        return HttpResponseBadRequest("Betalningen är inte slutförd.")

    if str(checkout_session.get("client_reference_id", "")) != str(user.id):
        return HttpResponseBadRequest("Checkout-session tillhör inte aktuell användare.")

    subscription = checkout_session.get("subscription")
    if not isinstance(subscription, dict):
        return HttpResponseBadRequest("Saknar abonnemangsdata från Stripe.")

    subscription_id = subscription.get("id")
    status = subscription.get("status")
    if not isinstance(subscription_id, str) or not isinstance(status, str):
        return HttpResponseBadRequest("Ogiltig abonnemangsdata från Stripe.")

    customer_id = checkout_session.get("customer")
    if not isinstance(customer_id, str):
        customer_id = ""

    current_period_end_raw = subscription.get("current_period_end")
    current_period_end = None
    if isinstance(current_period_end_raw, int):
        current_period_end = datetime.fromtimestamp(
            current_period_end_raw,
            tz=timezone.get_current_timezone(),
        )

    items = subscription.get("items")
    interval = UserSubscription.INTERVAL_MONTH
    if isinstance(items, dict):
        data = items.get("data")
        if isinstance(data, list) and data:
            first_item = data[0]
            if isinstance(first_item, dict):
                price = first_item.get("price")
                if isinstance(price, dict):
                    recurring = price.get("recurring")
                    if isinstance(recurring, dict):
                        stripe_interval = recurring.get("interval")
                        if stripe_interval == UserSubscription.INTERVAL_YEAR:
                            interval = UserSubscription.INTERVAL_YEAR

    user_subscription, created = await UserSubscription.objects.aget_or_create(
        user=user,
        defaults={
            "stripe_subscription_id": subscription_id,
            "stripe_customer_id": customer_id,
            "status": status,
            "plan_interval": interval,
            "current_period_end": current_period_end,
        },
    )
    if not created:
        user_subscription.stripe_customer_id = customer_id
        user_subscription.stripe_subscription_id = subscription_id
        user_subscription.status = status
        user_subscription.plan_interval = interval
        user_subscription.current_period_end = current_period_end
        await user_subscription.asave(
            update_fields=[
                "stripe_customer_id",
                "stripe_subscription_id",
                "status",
                "plan_interval",
                "current_period_end",
            ]
        )

    return redirect("dashboard")


@login_required_async
async def billing_cancel(_: HttpRequest) -> HttpResponseBase:
    return redirect("scan")
