from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.models import AnonymousUser

from apps.core.models import User
from apps.receipts import billing


async def _return_false(_: Any) -> bool:
    return False


async def _return_true(_: Any) -> bool:
    return True


@pytest.mark.asyncio
async def test_free_user_lacks_premium_features(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "user_has_active_subscription", _return_false)
    monkeypatch.setattr(billing, "user_has_reached_free_limit", _return_true)
    user = User(username="free-user")

    assert await billing.get_user_plan(user) == billing.PLAN_FREE
    assert not await billing.is_premium_user(user)
    assert not await billing.can_export_excel(user)
    assert not await billing.can_use_korjournal(user)
    assert not await billing.can_use_ai_scan(user)
    assert not await billing.can_use_skogsinkomster(user)
    assert not await billing.can_use_arsrapport(user)


@pytest.mark.asyncio
async def test_premium_user_gets_premium_features(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "user_has_active_subscription", _return_true)
    user = User(username="premium-user")

    assert await billing.get_user_plan(user) == billing.PLAN_PREMIUM
    assert await billing.is_premium_user(user)
    assert await billing.can_export_excel(user)
    assert await billing.can_use_korjournal(user)
    assert await billing.can_use_ai_scan(user)
    assert await billing.can_use_skogsinkomster(user)
    assert await billing.can_use_arsrapport(user)


@pytest.mark.asyncio
async def test_pilot_user_gets_premium_features_without_subscription(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(billing, "user_has_active_subscription", _return_false)
    user = User(username="pilot-user", is_pilot=True)

    assert await billing.get_user_plan(user) == billing.PLAN_PILOT
    assert await billing.is_pilot_user(user)
    assert await billing.is_premium_user(user)
    assert await billing.can_export_excel(user)
    assert await billing.can_use_korjournal(user)
    assert await billing.can_use_ai_scan(user)
    assert await billing.can_use_skogsinkomster(user)
    assert await billing.can_use_arsrapport(user)


@pytest.mark.asyncio
async def test_anonymous_user_gets_no_access(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "user_has_reached_free_limit", _return_false)
    user = AnonymousUser()

    assert await billing.get_user_plan(user) == billing.PLAN_FREE
    assert not await billing.is_pilot_user(user)
    assert not await billing.is_premium_user(user)
    assert not await billing.can_export_excel(user)
    assert not await billing.can_use_korjournal(user)
    assert not await billing.can_use_ai_scan(user)
    assert not await billing.can_use_skogsinkomster(user)
    assert not await billing.can_use_arsrapport(user)


@pytest.mark.asyncio
async def test_get_feature_gates_free_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "user_has_active_subscription", _return_false)
    monkeypatch.setattr(billing, "user_has_reached_free_limit", _return_true)
    user = User(username="free-gates")

    gates = await billing.get_feature_gates(user)

    assert gates["user_plan"] == billing.PLAN_FREE
    assert gates["is_free"] is True
    assert gates["is_premium"] is False
    assert gates["is_pilot"] is False
    assert gates["can_excel_export"] is False
    assert gates["can_korjournal"] is False
    assert gates["can_skogsinkomster"] is False
    assert gates["can_arsrapport"] is False
    assert gates["can_ai_scan"] is False


@pytest.mark.asyncio
async def test_get_feature_gates_premium_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "user_has_active_subscription", _return_true)
    user = User(username="premium-gates")

    gates = await billing.get_feature_gates(user)

    assert gates["user_plan"] == billing.PLAN_PREMIUM
    assert gates["is_free"] is False
    assert gates["is_premium"] is True
    assert gates["is_pilot"] is False
    assert gates["can_excel_export"] is True
    assert gates["can_korjournal"] is True
    assert gates["can_skogsinkomster"] is True
    assert gates["can_arsrapport"] is True
    assert gates["can_ai_scan"] is True


@pytest.mark.asyncio
async def test_get_feature_gates_pilot_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "user_has_active_subscription", _return_false)
    user = User(username="pilot-gates", is_pilot=True)

    gates = await billing.get_feature_gates(user)

    assert gates["user_plan"] == billing.PLAN_PILOT
    assert gates["is_free"] is False
    assert gates["is_premium"] is False
    assert gates["is_pilot"] is True
    assert gates["can_excel_export"] is True
    assert gates["can_korjournal"] is True
    assert gates["can_skogsinkomster"] is True
    assert gates["can_arsrapport"] is True
    assert gates["can_ai_scan"] is True

