from __future__ import annotations

from datetime import datetime

import httpx
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseBadRequest, HttpResponseRedirect
from django.http.response import HttpResponseBase
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from apps.billing.models import UserSubscription
from apps.billing.services import (
    is_premium_user_sync,
    plan_to_price_id,
    stripe_is_configured,
    stripe_request_sync,
)


@login_required
def start_checkout(request: HttpRequest) -> HttpResponseBase:
    user = request.user

    if not stripe_is_configured():
        return HttpResponseBadRequest(
            "Stripe-konfiguration saknas. Kontrollera STRIPE_SECRET_KEY, "
            "STRIPE_PRICE_MONTHLY_ID och STRIPE_PRICE_YEARLY_ID."
        )

    if is_premium_user_sync(user):
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
        checkout_session = stripe_request_sync(
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


@login_required
def billing_success(request: HttpRequest) -> HttpResponseBase:
    user = request.user

    if not stripe_is_configured():
        return HttpResponseBadRequest(
            "Stripe-konfiguration saknas. Kontrollera STRIPE_SECRET_KEY, "
            "STRIPE_PRICE_MONTHLY_ID och STRIPE_PRICE_YEARLY_ID."
        )

    session_id = request.GET.get("session_id", "")
    if not session_id:
        return HttpResponseBadRequest("Checkout-session saknas.")

    try:
        checkout_session = stripe_request_sync(
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

    current_period_end = None
    current_period_end_raw = subscription.get("current_period_end")
    if isinstance(current_period_end_raw, int):
        current_period_end = datetime.fromtimestamp(
            current_period_end_raw,
            tz=timezone.get_current_timezone(),
        )

    interval = UserSubscription.Interval.MONTH
    items = subscription.get("items")
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
                        if stripe_interval == UserSubscription.Interval.YEAR:
                            interval = UserSubscription.Interval.YEAR

    user_subscription, created = UserSubscription.objects.get_or_create(
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
        user_subscription.save(
            update_fields=[
                "stripe_customer_id",
                "stripe_subscription_id",
                "status",
                "plan_interval",
                "current_period_end",
                "updated_at",
            ]
        )

    return redirect("dashboard")


@login_required
def billing_cancel(_: HttpRequest) -> HttpResponseBase:
    return redirect("scan")

