from __future__ import annotations

import httpx
from decouple import config
from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Q
from django.utils import timezone

from apps.receipts.models import Receipt, UserSubscription

# Max antal gratis kvitton innan nästa skapande kräver prenumeration.
FREE_RECEIPT_LIMIT = config("FREEMIUM_RECEIPT_LIMIT", default=5, cast=int)
STRIPE_API_BASE = "https://api.stripe.com/v1"
STRIPE_REQUEST_TIMEOUT = 30.0
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_PRICE_MONTHLY_ID = config("STRIPE_PRICE_MONTHLY_ID", default="")
STRIPE_PRICE_YEARLY_ID = config("STRIPE_PRICE_YEARLY_ID", default="")

ACTIVE_SUBSCRIPTION_STATUSES = {
    UserSubscription.STATUS_ACTIVE,
    UserSubscription.STATUS_TRIALING,
}


def stripe_is_configured() -> bool:
    return bool(STRIPE_SECRET_KEY and STRIPE_PRICE_MONTHLY_ID and STRIPE_PRICE_YEARLY_ID)


async def stripe_request(
    method: str,
    endpoint: str,
    *,
    data: dict[str, str] | None = None,
    params: list[tuple[str, str]] | None = None,
) -> dict[str, object]:
    if not STRIPE_SECRET_KEY:
        msg = "Stripe secret key is missing."
        raise ValueError(msg)

    headers = {"Authorization": f"Bearer {STRIPE_SECRET_KEY}"}
    async with httpx.AsyncClient(timeout=STRIPE_REQUEST_TIMEOUT) as client:
        response = await client.request(
            method=method,
            url=f"{STRIPE_API_BASE}{endpoint}",
            data=data,
            params=params,
            headers=headers,
        )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        msg = "Invalid Stripe response payload."
        raise ValueError(msg)
    return payload


def plan_to_price_id(plan: str) -> str | None:
    mapping = {
        "monthly": STRIPE_PRICE_MONTHLY_ID,
        "yearly": STRIPE_PRICE_YEARLY_ID,
    }
    price_id = mapping.get(plan)
    if not price_id:
        return None
    return price_id


async def user_has_active_subscription(user: AbstractBaseUser) -> bool:
    now = timezone.now()
    return await UserSubscription.objects.filter(
        user=user,
        status__in=ACTIVE_SUBSCRIPTION_STATUSES,
    ).filter(Q(current_period_end__isnull=True) | Q(current_period_end__gt=now)).aexists()


async def user_has_reached_free_limit(user: AbstractBaseUser) -> bool:
    if await user_has_active_subscription(user):
        return False
    receipt_count = await Receipt.objects.filter(owner=user).acount()
    return receipt_count >= FREE_RECEIPT_LIMIT
