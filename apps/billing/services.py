from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db.models import Q
from django.utils import timezone

from apps.billing.models import UserSubscription
from apps.receipts.models import Receipt

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

# NEW — labels live where the business logic lives, not duplicated per consumer
PLAN_LABELS: dict[str, str] = {
    PLAN_FREE: "Gratis",
    PLAN_TRIAL: "Trial",
    PLAN_PREMIUM: "Premium",
    PLAN_PILOT: "Särskild åtkomst",
}

PLAN_DESCRIPTIONS: dict[str, str] = {
    PLAN_FREE: "Du kan testa scanning och förhandsvisning.",
    PLAN_TRIAL: "Du testar SkogsKvitto. Export och nedladdning kräver betalplan.",
    PLAN_PREMIUM: "Export och nedladdning är aktiverat.",
    PLAN_PILOT: "Särskild åtkomst är aktiverad.",
}

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


# NEW — public read-only DTO for cross-app consumers (e.g. accounts.profile view)
@dataclass(frozen=True, slots=True)
class UserBillingSummary:
    plan: str
    plan_label: str
    plan_description: str
    is_free: bool
    is_trial: bool
    is_premium: bool
    is_pilot: bool
    receipt_count: int
    free_receipt_limit: int
    export_enabled: bool


def stripe_is_configured() -> bool:
    return bool(STRIPE_SECRET_KEY and STRIPE_PRICE_MONTHLY_ID and STRIPE_PRICE_YEARLY_ID)


def stripe_request_sync(
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

    with httpx.Client(timeout=STRIPE_REQUEST_TIMEOUT) as client:
        response = client.request(
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


async def stripe_request(
    method: str,
    endpoint: str,
    *,
    data: dict[str, str] | None = None,
    params: list[tuple[str, str | int | float | None]] | None = None,
) -> dict[str, object]:
    return await sync_to_async(stripe_request_sync, thread_sensitive=True)(
        method,
        endpoint,
        data=data,
        params=params,
    )


def plan_to_price_id(plan: str) -> str | None:
    mapping = {
        "monthly": STRIPE_PRICE_MONTHLY_ID,
        "yearly": STRIPE_PRICE_YEARLY_ID,
    }
    return mapping.get(plan) or None


def is_pilot_user_sync(user: AbstractBaseUser | AnonymousUser) -> bool:
    if not user.is_authenticated:
        return False

    return bool(getattr(user, "is_pilot", False))


def user_has_active_subscription_sync(user: AbstractBaseUser | AnonymousUser) -> bool:
    if not user.is_authenticated or user.pk is None:
        return False

    now = timezone.now()

    return (
        UserSubscription.objects.filter(
            user_id=user.pk,
            status=UserSubscription.Status.ACTIVE,
        )
        .filter(Q(current_period_end__isnull=True) | Q(current_period_end__gt=now))
        .exists()
    )


def user_has_trial_subscription_sync(user: AbstractBaseUser | AnonymousUser) -> bool:
    if not user.is_authenticated or user.pk is None:
        return False

    now = timezone.now()

    return (
        UserSubscription.objects.filter(
            user_id=user.pk,
            status=UserSubscription.Status.TRIALING,
        )
        .filter(Q(current_period_end__isnull=True) | Q(current_period_end__gt=now))
        .exists()
    )


def get_user_plan_sync(user: AbstractBaseUser | AnonymousUser) -> str:
    if is_pilot_user_sync(user):
        return PLAN_PILOT

    if user_has_trial_subscription_sync(user):
        return PLAN_TRIAL

    if user_has_active_subscription_sync(user):
        return PLAN_PREMIUM

    return PLAN_FREE


def is_premium_user_sync(user: AbstractBaseUser | AnonymousUser) -> bool:
    return get_user_plan_sync(user) in {PLAN_PREMIUM, PLAN_PILOT}


def user_has_reached_free_limit_sync(user: AbstractBaseUser | AnonymousUser) -> bool:
    if not user.is_authenticated or user.pk is None:
        return True

    if is_pilot_user_sync(user):
        return False

    if user_has_active_subscription_sync(user):
        return False

    return Receipt.objects.filter(owner_id=user.pk).count() >= FREE_RECEIPT_LIMIT


def _log_pilot_bypass(user_id: int | None, feature: str, status: str) -> None:
    logger.info(
        "pilot_feature_bypass",
        extra={
            "status": status,
            "user_id": user_id,
            "feature": feature,
        },
    )


def can_use_feature_sync(
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

    plan = get_user_plan_sync(user)

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
                reason="Särskild åtkomst aktiverad via server-side bypass.",
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


def get_feature_gates_sync(user: AbstractBaseUser | AnonymousUser) -> dict[str, bool | str]:
    plan = get_user_plan_sync(user)

    scan_preview = can_use_feature_sync(user, FEATURE_RECEIPT_SCAN_PREVIEW)
    confirm_save = can_use_feature_sync(user, FEATURE_RECEIPT_CONFIRM_SAVE)
    excel_download = can_use_feature_sync(user, FEATURE_EXCEL_DOWNLOAD)
    driving_log = can_use_feature_sync(user, FEATURE_DRIVING_LOG_EXPORT)
    yearly_report = can_use_feature_sync(user, FEATURE_YEARLY_REPORT_DOWNLOAD)

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
        "can_korjournal": driving_log.allowed,
        "can_skogsinkomster": yearly_report.allowed,
        "can_arsrapport": yearly_report.allowed,
    }


# NEW — single public function consumed by apps/accounts/views.py
def get_user_billing_summary(user: AbstractBaseUser | AnonymousUser) -> UserBillingSummary:
    """Return an immutable summary of the user's billing state.

    This is the ONLY billing API that cross-app consumers (e.g. the profile
    view in accounts) should use. It pre-computes all labels and flags so
    callers never need to know about plan constants or feature names.
    """

    plan = get_user_plan_sync(user)

    if user.is_authenticated and user.pk is not None:
        receipt_count = Receipt.objects.filter(owner_id=user.pk).count()
    else:
        receipt_count = 0

    export_decision = can_use_feature_sync(user, FEATURE_EXCEL_DOWNLOAD)

    return UserBillingSummary(
        plan=plan,
        plan_label=PLAN_LABELS.get(plan, PLAN_LABELS[PLAN_FREE]),
        plan_description=PLAN_DESCRIPTIONS.get(plan, PLAN_DESCRIPTIONS[PLAN_FREE]),
        is_free=plan == PLAN_FREE,
        is_trial=plan == PLAN_TRIAL,
        is_premium=plan in {PLAN_PREMIUM, PLAN_PILOT},
        is_pilot=plan == PLAN_PILOT,
        receipt_count=receipt_count,
        free_receipt_limit=FREE_RECEIPT_LIMIT,
        export_enabled=export_decision.allowed,
    )


async def is_pilot_user(user: AbstractBaseUser | AnonymousUser) -> bool:
    return await sync_to_async(is_pilot_user_sync, thread_sensitive=True)(user)


async def user_has_active_subscription(user: AbstractBaseUser | AnonymousUser) -> bool:
    return await sync_to_async(user_has_active_subscription_sync, thread_sensitive=True)(user)


async def user_has_trial_subscription(user: AbstractBaseUser | AnonymousUser) -> bool:
    return await sync_to_async(user_has_trial_subscription_sync, thread_sensitive=True)(user)


async def get_user_plan(user: AbstractBaseUser | AnonymousUser) -> str:
    return await sync_to_async(get_user_plan_sync, thread_sensitive=True)(user)


async def is_premium_user(user: AbstractBaseUser | AnonymousUser) -> bool:
    return await sync_to_async(is_premium_user_sync, thread_sensitive=True)(user)


async def user_has_reached_free_limit(user: AbstractBaseUser | AnonymousUser) -> bool:
    return await sync_to_async(user_has_reached_free_limit_sync, thread_sensitive=True)(user)


async def can_use_feature(
    user: AbstractBaseUser | AnonymousUser,
    feature: str,
) -> AccessDecision:
    return await sync_to_async(can_use_feature_sync, thread_sensitive=True)(user, feature)


async def get_feature_gates(user: AbstractBaseUser | AnonymousUser) -> dict[str, bool | str]:
    return await sync_to_async(get_feature_gates_sync, thread_sensitive=True)(user)
