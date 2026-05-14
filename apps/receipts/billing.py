from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db.models import Q
from django.utils import timezone

from apps.receipts.models import Receipt, UserSubscription

logger = logging.getLogger(__name__)

FREE_RECEIPT_LIMIT: int = int(getattr(settings, "FREEMIUM_RECEIPT_LIMIT", 5))

STRIPE_API_BASE = "https://api.stripe.com/v1"
STRIPE_REQUEST_TIMEOUT = 30.0
STRIPE_SECRET_KEY: str = str(getattr(settings, "STRIPE_SECRET_KEY", ""))
STRIPE_PRICE_MONTHLY_ID: str = str(getattr(settings, "STRIPE_PRICE_MONTHLY_ID", ""))
STRIPE_PRICE_YEARLY_ID: str = str(getattr(settings, "STRIPE_PRICE_YEARLY_ID", ""))

PLAN_FREE = "free"
PLAN_TRIAL = "trial"
PLAN_PREMIUM = "premium"
PLAN_PILOT = "pilot"

FEATURE_RECEIPT_SCAN_PREVIEW = "receipt_scan_preview"
FEATURE_RECEIPT_CONFIRM_SAVE = "receipt_confirm_save"
FEATURE_EXCEL_PREVIEW = "excel_preview"
FEATURE_EXCEL_DOWNLOAD = "excel_download"
FEATURE_PDF_DOWNLOAD = "pdf_download"
FEATURE_YEARLY_REPORT_DOWNLOAD = "yearly_report_download"
FEATURE_DRIVING_LOG_EXPORT = "driving_log_export"

PREMIUM_FEATURES = {
    FEATURE_RECEIPT_CONFIRM_SAVE,
    FEATURE_EXCEL_DOWNLOAD,
    FEATURE_PDF_DOWNLOAD,
    FEATURE_YEARLY_REPORT_DOWNLOAD,
    FEATURE_DRIVING_LOG_EXPORT,
}

FREE_FEATURES = {
    FEATURE_RECEIPT_SCAN_PREVIEW,
    FEATURE_EXCEL_PREVIEW,
}


@dataclass(frozen=True, slots=True)
class AccessDecision:
    allowed: bool
    reason: str
    plan: str
    is_pilot_bypass: bool


def stripe_is_configured() -> bool:
    return bool(STRIPE_SECRET_KEY and STRIPE_PRICE_MONTHLY_ID and STRIPE_PRICE_YEARLY_ID)


async def stripe_request(
    method: str,
    endpoint: str,
    *,
    data: dict[str, str] | None = None,
    params: list[tuple[str, str | int | float | None]] | None = None,
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
    return mapping.get(plan) or None


async def user_has_active_subscription(user: AbstractBaseUser | AnonymousUser) -> bool:
    if not user.is_authenticated or user.pk is None:
        return False

    now = timezone.now()

    return await UserSubscription.objects.filter(
        user_id=user.pk,
        status=UserSubscription.STATUS_ACTIVE,
    ).filter(
        Q(current_period_end__isnull=True) | Q(current_period_end__gt=now)
    ).aexists()


async def user_has_trial_subscription(user: AbstractBaseUser | AnonymousUser) -> bool:
    if not user.is_authenticated or user.pk is None:
        return False

    now = timezone.now()

    return await UserSubscription.objects.filter(
        user_id=user.pk,
        status=UserSubscription.STATUS_TRIALING,
    ).filter(
        Q(current_period_end__isnull=True) | Q(current_period_end__gt=now)
    ).aexists()


async def is_pilot_user(user: AbstractBaseUser | AnonymousUser) -> bool:
    if not user.is_authenticated:
        return False

    return bool(getattr(user, "is_pilot", False))


async def get_user_plan(user: AbstractBaseUser | AnonymousUser) -> str:
    if await is_pilot_user(user):
        return PLAN_PILOT

    if await user_has_trial_subscription(user):
        return PLAN_TRIAL

    if await user_has_active_subscription(user):
        return PLAN_PREMIUM

    return PLAN_FREE


async def is_premium_user(user: AbstractBaseUser | AnonymousUser) -> bool:
    return (await get_user_plan(user)) in {PLAN_PREMIUM, PLAN_PILOT}


async def user_has_reached_free_limit(user: AbstractBaseUser | AnonymousUser) -> bool:
    if not user.is_authenticated or user.pk is None:
        return True

    if await is_pilot_user(user):
        return False

    if await user_has_active_subscription(user):
        return False

    receipt_count = await Receipt.objects.filter(owner_id=user.pk).acount()
    return receipt_count >= FREE_RECEIPT_LIMIT


def _log_pilot_bypass(user_id: int | None, feature: str, status: str) -> None:
    logger.info(
        "pilot_feature_bypass",
        extra={
            "status": status,
            "user_id": user_id,
            "feature": feature,
        },
    )


async def can_use_feature(
    user: AbstractBaseUser | AnonymousUser,
    feature: str,
) -> AccessDecision:
    if not user.is_authenticated:
        return AccessDecision(
            allowed=False,
            reason="Inloggning krävs för funktionen.",
            plan=PLAN_FREE,
            is_pilot_bypass=False,
        )

    plan = await get_user_plan(user)

    if feature in FREE_FEATURES:
        return AccessDecision(
            allowed=True,
            reason="Funktionen ingår i gratisnivån.",
            plan=plan,
            is_pilot_bypass=False,
        )

    if feature in PREMIUM_FEATURES:
        if plan == PLAN_PILOT:
            _log_pilot_bypass(getattr(user, "pk", None), feature, "allowed")
            return AccessDecision(
                allowed=True,
                reason="Pilotåtkomst aktiverad via server-side bypass.",
                plan=plan,
                is_pilot_bypass=True,
            )

        if plan == PLAN_PREMIUM:
            return AccessDecision(
                allowed=True,
                reason="Funktionen ingår i betalplanen.",
                plan=plan,
                is_pilot_bypass=False,
            )

        return AccessDecision(
            allowed=False,
            reason="Export och nedladdning ingår i betalplanen.",
            plan=plan,
            is_pilot_bypass=False,
        )

    return AccessDecision(
        allowed=False,
        reason="Funktionen är inte tillgänglig.",
        plan=plan,
        is_pilot_bypass=False,
    )


async def can_use_ai_scan(user: AbstractBaseUser | AnonymousUser) -> bool:
    return (await can_use_feature(user, FEATURE_RECEIPT_SCAN_PREVIEW)).allowed


async def can_export_excel(user: AbstractBaseUser | AnonymousUser) -> bool:
    return (await can_use_feature(user, FEATURE_EXCEL_DOWNLOAD)).allowed


async def can_use_korjournal(user: AbstractBaseUser | AnonymousUser) -> bool:
    return (await can_use_feature(user, FEATURE_DRIVING_LOG_EXPORT)).allowed


async def can_use_skogsinkomster(user: AbstractBaseUser | AnonymousUser) -> bool:
    return (await can_use_feature(user, FEATURE_YEARLY_REPORT_DOWNLOAD)).allowed


async def can_use_arsrapport(user: AbstractBaseUser | AnonymousUser) -> bool:
    return (await can_use_feature(user, FEATURE_YEARLY_REPORT_DOWNLOAD)).allowed


async def get_feature_gates(user: AbstractBaseUser | AnonymousUser) -> dict[str, bool | str]:
    plan = await get_user_plan(user)

    scan_preview = await can_use_feature(user, FEATURE_RECEIPT_SCAN_PREVIEW)
    confirm_save = await can_use_feature(user, FEATURE_RECEIPT_CONFIRM_SAVE)
    excel_download = await can_use_feature(user, FEATURE_EXCEL_DOWNLOAD)

    return {
        "user_plan": plan,
        "is_pilot": plan == PLAN_PILOT,
        "is_premium": plan in {PLAN_PREMIUM, PLAN_PILOT},
        "is_trial": plan == PLAN_TRIAL,
        "is_free": plan == PLAN_FREE,
        "can_ai_scan": scan_preview.allowed,
        "can_receipt_scan_preview": scan_preview.allowed,
        "can_receipt_confirm_save": confirm_save.allowed,
        "can_excel_export": excel_download.allowed,
        "can_excel_download": excel_download.allowed,
        "can_korjournal": await can_use_korjournal(user),
        "can_skogsinkomster": await can_use_skogsinkomster(user),
        "can_arsrapport": await can_use_arsrapport(user),
    }
