import io
from collections.abc import Awaitable, Callable
from datetime import date
from decimal import Decimal
from functools import wraps

import httpx
from asgiref.sync import sync_to_async
from django.contrib.auth.views import redirect_to_login
from django.http import FileResponse, HttpRequest, HttpResponseBadRequest, HttpResponseRedirect
from django.http.response import HttpResponseForbidden
from django.http.response import HttpResponseBase
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.receipts.billing import (
    can_export_excel,
    can_use_korjournal,
    get_user_plan,
    is_premium_user,
    plan_to_price_id,
    stripe_request,
    stripe_is_configured,
    user_has_active_subscription,
)
from apps.receipts.exports import build_excel
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

    has_premium_access = await is_premium_user(request.user)

    return render(
        request,
        "receipts/dashboard.html",
        {
            "receipts": receipts,
            "total_year": total_year,
            "vat_year": vat_year,
            "year": year,
            "has_active_subscription": has_premium_access,
            "user_plan": await get_user_plan(request.user),
            "can_use_korjournal": await can_use_korjournal(request.user),
        },
    )


@login_required_async
async def export_excel(request: HttpRequest) -> HttpResponseBase:
    if not await can_export_excel(request.user):
        return HttpResponseForbidden("Export till Excel kräver Premium eller pilotåtkomst.")

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


@login_required_async
async def start_checkout(request: HttpRequest) -> HttpResponseBase:
    if not stripe_is_configured():
        return HttpResponseBadRequest(
            "Stripe-konfiguration saknas. Kontrollera STRIPE_SECRET_KEY, "
            "STRIPE_PRICE_MONTHLY_ID och STRIPE_PRICE_YEARLY_ID."
        )

    if await is_premium_user(request.user):
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
                "client_reference_id": str(request.user.id),
                "customer_email": request.user.email,
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

    if str(checkout_session.get("client_reference_id", "")) != str(request.user.id):
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
        current_period_end = timezone.datetime.fromtimestamp(
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
        user=request.user,
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
    return redirect("index")
