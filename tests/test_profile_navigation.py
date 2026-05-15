from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory
from django.utils import timezone

from apps.core import views as core_views
from apps.core.models import User


def _gates(plan: str, *, can_export: bool, is_pilot: bool) -> dict[str, object]:
    return {
        "user_plan": plan,
        "is_pilot": is_pilot,
        "can_excel_download": can_export,
    }


async def _fake_receipt_count(_: int | None) -> int:
    return 2


@pytest.mark.asyncio
async def test_profile_requires_login(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        core_views,
        "redirect_to_login",
        lambda path: HttpResponseRedirect(f"/accounts/login/?next={path}"),
    )
    request = RequestFactory().get("/profile/")
    request.user = AnonymousUser()
    response = await core_views.profile(request)
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.asyncio
async def test_logged_in_user_can_view_profile_and_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_context: dict[str, object] = {}

    async def _fake_gates(_: Any) -> dict[str, object]:
        return _gates("free", can_export=False, is_pilot=False)

    def _fake_render(request: Any, _: str, context: dict[str, object]) -> HttpResponse:
        captured_context.update(context)
        return HttpResponse(f"email={request.user.email}")

    monkeypatch.setattr(core_views, "get_feature_gates", _fake_gates)
    monkeypatch.setattr(core_views, "_get_receipt_count", _fake_receipt_count)
    monkeypatch.setattr(core_views, "render", _fake_render)

    request = RequestFactory().get("/profile/")
    request.user = User(
        id=1,
        username="skog",
        email="skog@example.com",
        date_joined=datetime(2026, 1, 1, tzinfo=timezone.get_current_timezone()),
    )
    response = await core_views.profile(request)
    assert response.status_code == 200
    assert "skog@example.com" in response.content.decode()
    assert captured_context["plan_label"] == "Gratis"


@pytest.mark.asyncio
async def test_testpilot_user_sees_badge(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_context: dict[str, object] = {}

    async def _fake_gates(_: Any) -> dict[str, object]:
        return _gates("pilot", can_export=True, is_pilot=True)

    def _fake_render(_: Any, __: str, context: dict[str, object]) -> HttpResponse:
        captured_context.update(context)
        return HttpResponse("ok")

    monkeypatch.setattr(core_views, "get_feature_gates", _fake_gates)
    monkeypatch.setattr(core_views, "_get_receipt_count", _fake_receipt_count)
    monkeypatch.setattr(core_views, "render", _fake_render)
    request = RequestFactory().get("/profile/")
    request.user = User(
        id=1,
        username="pilot",
        email="pilot@example.com",
        is_pilot=True,
        date_joined=timezone.now(),
    )
    await core_views.profile(request)
    assert captured_context["is_testpilot"] is True


@pytest.mark.asyncio
async def test_free_or_trial_copy_does_not_unlock_export(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_context: dict[str, object] = {}

    async def _fake_gates(_: Any) -> dict[str, object]:
        return _gates("trial", can_export=False, is_pilot=False)

    def _fake_render(_: Any, __: str, context: dict[str, object]) -> HttpResponse:
        captured_context.update(context)
        return HttpResponse("ok")

    monkeypatch.setattr(core_views, "get_feature_gates", _fake_gates)
    monkeypatch.setattr(core_views, "_get_receipt_count", _fake_receipt_count)
    monkeypatch.setattr(core_views, "render", _fake_render)
    request = RequestFactory().get("/profile/")
    request.user = User(
        id=2,
        username="trial",
        email="trial@example.com",
        date_joined=timezone.now(),
    )
    await core_views.profile(request)
    assert captured_context["plan_description"] == (
        "Du testar SkogsKvitto. Export och nedladdning kräver betalplan."
    )


@pytest.mark.asyncio
async def test_premium_user_sees_export_enabled_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_context: dict[str, object] = {}

    async def _fake_gates(_: Any) -> dict[str, object]:
        return _gates("premium", can_export=True, is_pilot=False)

    def _fake_render(_: Any, __: str, context: dict[str, object]) -> HttpResponse:
        captured_context.update(context)
        return HttpResponse("ok")

    monkeypatch.setattr(core_views, "get_feature_gates", _fake_gates)
    monkeypatch.setattr(core_views, "_get_receipt_count", _fake_receipt_count)
    monkeypatch.setattr(core_views, "render", _fake_render)
    request = RequestFactory().get("/profile/")
    request.user = User(
        id=3,
        username="premium",
        email="premium@example.com",
        date_joined=timezone.now(),
    )
    await core_views.profile(request)
    assert captured_context["plan_description"] == "Export och nedladdning är aktiverat."


def test_header_and_bottom_nav_templates_include_logged_in_navigation() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    header_template = (base_dir / "templates" / "partials" / "header.html").read_text(
        encoding="utf-8"
    )
    bottom_template = (base_dir / "templates" / "partials" / "mobile_nav.html").read_text(
        encoding="utf-8"
    )

    assert "Huvudnavigering" in header_template
    assert "Scanna" in header_template
    assert "Granska" in header_template
    assert "Exportera" in header_template
    assert "Profil" in header_template
    assert "Bottennavigering" in bottom_template
    assert "Scanna" in bottom_template
    assert "Granska" in bottom_template
    assert "Exportera" in bottom_template


def test_navigation_templates_reference_existing_route_names() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    url_names_in_project = set(
        re.findall(
            r'name="([^"]+)"',
            (base_dir / "config" / "urls.py").read_text(encoding="utf-8"),
        )
    )
    url_names_in_project.update({"account_login", "account_logout"})

    templates = [
        base_dir / "templates" / "partials" / "header.html",
        base_dir / "templates" / "partials" / "mobile_nav.html",
        base_dir / "templates" / "account" / "profile.html",
    ]
    for template in templates:
        content = template.read_text(encoding="utf-8")
        for route_name in re.findall(r"\{% url '([^']+)' %\}", content):
            assert route_name in url_names_in_project
