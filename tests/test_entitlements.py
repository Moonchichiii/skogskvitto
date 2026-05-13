from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from apps.receipts import billing


@dataclass
class DummyUser:
    is_authenticated: bool
    is_pilot: bool = False
    pk: int | None = 1


async def _return_false(_: Any) -> bool:
    return False


async def _return_true(_: Any) -> bool:
    return True


@pytest.mark.asyncio
async def test_free_user_lacks_premium_features(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "user_has_active_subscription", _return_false)
    monkeypatch.setattr(billing, "user_has_reached_free_limit", _return_true)
    user = DummyUser(is_authenticated=True)

    assert await billing.get_user_plan(user) == billing.PLAN_FREE
    assert not await billing.is_premium_user(user)
    assert not await billing.can_export_excel(user)
    assert not await billing.can_use_korjournal(user)
    assert not await billing.can_use_ai_scan(user)


@pytest.mark.asyncio
async def test_premium_user_gets_premium_features(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "user_has_active_subscription", _return_true)
    user = DummyUser(is_authenticated=True)

    assert await billing.get_user_plan(user) == billing.PLAN_PREMIUM
    assert await billing.is_premium_user(user)
    assert await billing.can_export_excel(user)
    assert await billing.can_use_korjournal(user)
    assert await billing.can_use_ai_scan(user)


@pytest.mark.asyncio
async def test_pilot_user_gets_premium_features_without_subscription(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(billing, "user_has_active_subscription", _return_false)
    user = DummyUser(is_authenticated=True, is_pilot=True)

    assert await billing.get_user_plan(user) == billing.PLAN_PILOT
    assert await billing.is_pilot_user(user)
    assert await billing.is_premium_user(user)
    assert await billing.can_export_excel(user)
    assert await billing.can_use_korjournal(user)
    assert await billing.can_use_ai_scan(user)


@pytest.mark.asyncio
async def test_anonymous_user_gets_no_access(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "user_has_reached_free_limit", _return_false)
    user = DummyUser(is_authenticated=False, pk=None)

    assert await billing.get_user_plan(user) == billing.PLAN_FREE
    assert not await billing.is_pilot_user(user)
    assert not await billing.is_premium_user(user)
    assert not await billing.can_export_excel(user)
    assert not await billing.can_use_korjournal(user)
    assert not await billing.can_use_ai_scan(user)
