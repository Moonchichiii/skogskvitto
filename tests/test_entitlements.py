from __future__ import annotations

from typing import Any

import pytest

from apps.core.models import User
from apps.receipts import billing


def _plan_fn(plan: str) -> Any:
    async def _inner(_: Any) -> str:
        return plan

    return _inner


@pytest.mark.asyncio
async def test_free_gets_receipt_scan_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "get_user_plan", _plan_fn(billing.PLAN_FREE))
    user = User(username="free-user")
    decision = await billing.can_use_feature(user, billing.FEATURE_RECEIPT_SCAN_PREVIEW)
    assert decision.allowed is True
    assert decision.plan == billing.PLAN_FREE


@pytest.mark.asyncio
async def test_free_does_not_get_excel_download(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "get_user_plan", _plan_fn(billing.PLAN_FREE))
    user = User(username="free-user")
    decision = await billing.can_use_feature(user, billing.FEATURE_EXCEL_DOWNLOAD)
    assert decision.allowed is False
    assert decision.is_pilot_bypass is False


@pytest.mark.asyncio
async def test_trial_gets_receipt_scan_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "get_user_plan", _plan_fn(billing.PLAN_TRIAL))
    user = User(username="trial-user")
    decision = await billing.can_use_feature(user, billing.FEATURE_RECEIPT_SCAN_PREVIEW)
    assert decision.allowed is True
    assert decision.plan == billing.PLAN_TRIAL


@pytest.mark.asyncio
async def test_trial_does_not_get_excel_download(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "get_user_plan", _plan_fn(billing.PLAN_TRIAL))
    user = User(username="trial-user")
    decision = await billing.can_use_feature(user, billing.FEATURE_EXCEL_DOWNLOAD)
    assert decision.allowed is False
    assert decision.plan == billing.PLAN_TRIAL


@pytest.mark.asyncio
async def test_premium_gets_excel_download(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "get_user_plan", _plan_fn(billing.PLAN_PREMIUM))
    user = User(username="premium-user")
    decision = await billing.can_use_feature(user, billing.FEATURE_EXCEL_DOWNLOAD)
    assert decision.allowed is True
    assert decision.is_pilot_bypass is False


@pytest.mark.asyncio
async def test_pilot_gets_excel_download_via_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "get_user_plan", _plan_fn(billing.PLAN_PILOT))
    user = User(username="pilot-user", is_pilot=True)
    decision = await billing.can_use_feature(user, billing.FEATURE_EXCEL_DOWNLOAD)
    assert decision.allowed is True
    assert decision.is_pilot_bypass is True


@pytest.mark.asyncio
async def test_normal_user_does_not_get_pilot_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "get_user_plan", _plan_fn(billing.PLAN_PREMIUM))
    user = User(username="premium-user")
    decision = await billing.can_use_feature(user, billing.FEATURE_EXCEL_DOWNLOAD)
    assert decision.is_pilot_bypass is False


@pytest.mark.asyncio
async def test_access_decision_reason_and_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing, "get_user_plan", _plan_fn(billing.PLAN_FREE))
    user = User(username="free-user")
    decision = await billing.can_use_feature(user, billing.FEATURE_EXCEL_DOWNLOAD)
    assert decision.reason == "Export och nedladdning ingår i betalplanen."
    assert decision.plan == billing.PLAN_FREE
