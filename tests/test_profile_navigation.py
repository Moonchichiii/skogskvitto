from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.core.models import User
from apps.core import views as core_views


class _FakeReceiptQuerySet:
    async def acount(self) -> int:
        return 2


class _FakeReceiptManager:
    def filter(self, **_: object) -> _FakeReceiptQuerySet:
        return _FakeReceiptQuerySet()


def _gates(plan: str, *, can_export: bool, is_pilot: bool) -> dict[str, object]:
    return {
        "user_plan": plan,
        "is_pilot": is_pilot,
        "can_excel_download": can_export,
    }


@pytest.mark.asyncio
async def test_profile_requires_login() -> None:
    request = RequestFactory().get("/profile/")
    request.user = AnonymousUser()
    response = await core_views.profile(request)
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.asyncio
async def test_logged_in_user_can_view_profile_and_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_gates(_: Any) -> dict[str, object]:
        return _gates("free", can_export=False, is_pilot=False)

    monkeypatch.setattr(core_views, "get_feature_gates", _fake_gates)
    monkeypatch.setattr(core_views.Receipt, "objects", _FakeReceiptManager())

    request = RequestFactory().get("/profile/")
    request.user = User(
        id=1,
        username="skog",
        email="skog@example.com",
        date_joined=datetime(2026, 1, 1, tzinfo=timezone.get_current_timezone()),
    )
    response = await core_views.profile(request)
    content = response.content.decode()
    assert response.status_code == 200
    assert "Min profil" in content
    assert "skog@example.com" in content


@pytest.mark.asyncio
async def test_testpilot_user_sees_badge(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_gates(_: Any) -> dict[str, object]:
        return _gates("pilot", can_export=True, is_pilot=True)

    monkeypatch.setattr(core_views, "get_feature_gates", _fake_gates)
    monkeypatch.setattr(core_views.Receipt, "objects", _FakeReceiptManager())
    request = RequestFactory().get("/profile/")
    request.user = User(
        id=1,
        username="pilot",
        email="pilot@example.com",
        is_pilot=True,
        date_joined=timezone.now(),
    )
    response = await core_views.profile(request)
    assert "Testpilot" in response.content.decode()


@pytest.mark.asyncio
async def test_free_or_trial_copy_does_not_unlock_export(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_gates(_: Any) -> dict[str, object]:
        return _gates("trial", can_export=False, is_pilot=False)

    monkeypatch.setattr(core_views, "get_feature_gates", _fake_gates)
    monkeypatch.setattr(core_views.Receipt, "objects", _FakeReceiptManager())
    request = RequestFactory().get("/profile/")
    request.user = User(id=2, username="trial", email="trial@example.com", date_joined=timezone.now())
    response = await core_views.profile(request)
    content = response.content.decode()
    assert "Export och nedladdning kräver betalplan." in content
    assert "Export och nedladdning är aktiverat." not in content


@pytest.mark.asyncio
async def test_premium_user_sees_export_enabled_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_gates(_: Any) -> dict[str, object]:
        return _gates("premium", can_export=True, is_pilot=False)

    monkeypatch.setattr(core_views, "get_feature_gates", _fake_gates)
    monkeypatch.setattr(core_views.Receipt, "objects", _FakeReceiptManager())
    request = RequestFactory().get("/profile/")
    request.user = User(id=3, username="premium", email="premium@example.com", date_joined=timezone.now())
    response = await core_views.profile(request)
    assert "Export och nedladdning är aktiverat." in response.content.decode()


@pytest.mark.asyncio
async def test_header_and_bottom_nav_render_for_logged_in_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_gates(_: Any) -> dict[str, object]:
        return _gates("free", can_export=False, is_pilot=False)

    monkeypatch.setattr(core_views, "get_feature_gates", _fake_gates)
    monkeypatch.setattr(core_views.Receipt, "objects", _FakeReceiptManager())
    request = RequestFactory().get("/profile/")
    request.user = User(id=4, username="nav", email="nav@example.com", date_joined=timezone.now())
    response = await core_views.profile(request)
    content = response.content.decode()
    assert "Huvudnavigering" in content
    assert "Bottennavigering" in content
    assert "Scanna" in content
    assert "Granska" in content
    assert "Exportera" in content
    assert "Profil" in content


def test_core_routes_reverse_without_errors() -> None:
    route_names = [
        "index",
        "dashboard",
        "profile",
        "privacy_policy",
        "terms_of_service",
        "cookies",
        "export_excel",
        "start_checkout",
        "billing_success",
        "billing_cancel",
        "account_login",
        "account_logout",
    ]
    for route_name in route_names:
        assert reverse(route_name).startswith("/")
