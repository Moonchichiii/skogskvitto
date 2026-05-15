from __future__ import annotations

import io
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import RequestFactory

from apps.core.models import User
from apps.receipts import api, billing, views
from apps.receipts.models import Receipt, ReceiptScanJob
from apps.receipts.services import ReceiptScanResult


class _FakeImage:
    def __init__(self, data: bytes = b"img-bytes", name: str = "scan.jpg") -> None:
        self._data = data
        self.name = name

    def open(self, _: str) -> None:
        return None

    def read(self) -> bytes:
        return self._data

    def close(self) -> None:
        return None


class _FakeScanJob:
    def __init__(self) -> None:
        self.pk = 1
        self.image = _FakeImage()
        self.status = ReceiptScanJob.STATUS_PREVIEW_READY
        self.preview_data: dict[str, object] = {}
        self.error_message = ""
        self.confirmed_receipt: object | None = None

    async def asave(self, update_fields: list[str] | None = None) -> None:
        return None


def _render_stub(_: str, __: dict[str, object], status: int = 200) -> HttpResponse:
    return HttpResponse("ok", status=status)


def _allowed_decision(plan: str = billing.PLAN_PREMIUM) -> billing.AccessDecision:
    return billing.AccessDecision(True, "ok", plan, plan == billing.PLAN_PILOT)


@pytest.mark.asyncio
async def test_free_direct_url_to_excel_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _deny(_: Any, __: str) -> billing.AccessDecision:
        return billing.AccessDecision(False, "blocked", billing.PLAN_FREE, False)

    monkeypatch.setattr(views, "can_use_feature", _deny)
    request = RequestFactory().get("/receipts/export/excel/")
    request.user = User(username="free")
    response = await views.export_excel(request)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_trial_direct_url_to_excel_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _deny(_: Any, __: str) -> billing.AccessDecision:
        return billing.AccessDecision(False, "blocked", billing.PLAN_TRIAL, False)

    monkeypatch.setattr(views, "can_use_feature", _deny)
    request = RequestFactory().get("/receipts/export/excel/")
    request.user = User(username="trial")
    response = await views.export_excel(request)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_premium_can_download_excel(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeQuerySet:
        def order_by(self, *_: str) -> "_FakeQuerySet":
            return self

        def __aiter__(self) -> Any:
            class _EmptyAsyncIterator:
                def __aiter__(self) -> "_EmptyAsyncIterator":
                    return self

                async def __anext__(self) -> object:
                    raise StopAsyncIteration

            return _EmptyAsyncIterator()

    class _FakeManager:
        def filter(self, **_: object) -> _FakeQuerySet:
            return _FakeQuerySet()

    async def _allow(_: Any, __: str) -> billing.AccessDecision:
        return _allowed_decision(billing.PLAN_PREMIUM)

    monkeypatch.setattr(views, "can_use_feature", _allow)
    monkeypatch.setattr(Receipt, "objects", _FakeManager())
    monkeypatch.setattr(views, "build_excel", lambda _: io.BytesIO(b"xlsx"))
    request = RequestFactory().get("/receipts/export/excel/")
    request.user = User(username="premium")
    response = await views.export_excel(request)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_pilot_can_download_excel(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeQuerySet:
        def order_by(self, *_: str) -> "_FakeQuerySet":
            return self

        def __aiter__(self) -> Any:
            class _EmptyAsyncIterator:
                def __aiter__(self) -> "_EmptyAsyncIterator":
                    return self

                async def __anext__(self) -> object:
                    raise StopAsyncIteration

            return _EmptyAsyncIterator()

    class _FakeManager:
        def filter(self, **_: object) -> _FakeQuerySet:
            return _FakeQuerySet()

    async def _allow(_: Any, __: str) -> billing.AccessDecision:
        return _allowed_decision(billing.PLAN_PILOT)

    monkeypatch.setattr(views, "can_use_feature", _allow)
    monkeypatch.setattr(Receipt, "objects", _FakeManager())
    monkeypatch.setattr(views, "build_excel", lambda _: io.BytesIO(b"xlsx"))
    request = RequestFactory().get("/receipts/export/excel/")
    request.user = User(username="pilot", is_pilot=True)
    response = await views.export_excel(request)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_free_can_create_preview_job(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _allow(_: Any, __: str) -> billing.AccessDecision:
        return _allowed_decision(billing.PLAN_FREE)

    class _FakeManager:
        async def acreate(self, **_: object) -> _FakeScanJob:
            return _FakeScanJob()

    async def _fake_process(_: Any) -> ReceiptScanResult:
        return ReceiptScanResult(
            vendor="ICA",
            total_amount=Decimal("10.00"),
            vat_amount=Decimal("2.00"),
        )

    monkeypatch.setattr(api, "can_use_feature", _allow)
    monkeypatch.setattr(api, "_render_fragment", _render_stub)
    monkeypatch.setattr(api, "_detect_image_mime", lambda _: "image/jpeg")
    monkeypatch.setattr(
        api,
        "strip_exif_and_prepare_image",
        lambda *_: ContentFile(b"img", name="u.jpg"),
    )
    monkeypatch.setattr(ReceiptScanJob, "objects", _FakeManager())
    monkeypatch.setattr(
        api,
        "process_receipt_image",
        _fake_process,
    )

    upload = SimpleUploadedFile("receipt.jpg", b"image-data", content_type="image/jpeg")
    request = RequestFactory().post("/api/receipts/scan")
    request.user = User(username="free")
    response = await api.scan_receipt(request, cast(Any, upload))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_free_cannot_confirm_save_if_not_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _deny(_: Any, __: str) -> billing.AccessDecision:
        return billing.AccessDecision(False, "blocked", billing.PLAN_FREE, False)

    class _FakeManager:
        async def aget(self, **_: object) -> _FakeScanJob:
            return _FakeScanJob()

    monkeypatch.setattr(api, "can_use_feature", _deny)
    monkeypatch.setattr(api, "_render_fragment", _render_stub)
    monkeypatch.setattr(ReceiptScanJob, "objects", _FakeManager())

    request = RequestFactory().post("/api/receipts/save")
    request.user = User(username="free")
    signed = api.SCAN_JOB_SIGNER.sign("1")
    response = await api.save_receipt(request, signed_scan_job=signed)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_paid_can_confirm_save(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _allow(_: Any, __: str) -> billing.AccessDecision:
        return _allowed_decision(billing.PLAN_PREMIUM)

    class _FakeManager:
        async def aget(self, **_: object) -> _FakeScanJob:
            return _FakeScanJob()

    class _FakeImageField:
        def save(self, name: str, content: ContentFile[bytes], save: bool = False) -> None:
            assert name
            assert content.read()
            assert save is False

    class _FakeReceipt:
        def __init__(self, **_: object) -> None:
            self.image = _FakeImageField()
            self.pk = 2
            self.vendor = "ICA"

        async def asave(self) -> None:
            return None

    monkeypatch.setattr(api, "can_use_feature", _allow)
    monkeypatch.setattr(api, "_render_fragment", _render_stub)
    monkeypatch.setattr(ReceiptScanJob, "objects", _FakeManager())
    monkeypatch.setattr(api, "Receipt", _FakeReceipt)

    request = RequestFactory().post("/api/receipts/save")
    request.user = User(username="premium")
    signed = api.SCAN_JOB_SIGNER.sign("1")
    response = await api.save_receipt(request, signed_scan_job=signed)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_pilot_can_confirm_save(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _allow(_: Any, __: str) -> billing.AccessDecision:
        return _allowed_decision(billing.PLAN_PILOT)

    class _FakeManager:
        async def aget(self, **_: object) -> _FakeScanJob:
            return _FakeScanJob()

    class _FakeImageField:
        def save(self, *args: object, **kwargs: object) -> None:
            assert kwargs.get("save") is False

    class _FakeReceipt:
        def __init__(self, **_: object) -> None:
            self.image = _FakeImageField()
            self.pk = 3
            self.vendor = "Pilot"

        async def asave(self) -> None:
            return None

    monkeypatch.setattr(api, "can_use_feature", _allow)
    monkeypatch.setattr(api, "_render_fragment", _render_stub)
    monkeypatch.setattr(ReceiptScanJob, "objects", _FakeManager())
    monkeypatch.setattr(api, "Receipt", _FakeReceipt)

    request = RequestFactory().post("/api/receipts/save")
    request.user = User(username="pilot", is_pilot=True)
    signed = api.SCAN_JOB_SIGNER.sign("1")
    response = await api.save_receipt(request, signed_scan_job=signed)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cross_user_access_to_scan_job_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeManager:
        async def aget(self, **_: object) -> Any:
            raise ReceiptScanJob.DoesNotExist

    monkeypatch.setattr(api, "_render_fragment", _render_stub)
    monkeypatch.setattr(ReceiptScanJob, "objects", _FakeManager())
    request = RequestFactory().post("/api/receipts/save")
    request.user = User(username="user-a")
    signed = api.SCAN_JOB_SIGNER.sign("1")
    response = await api.save_receipt(request, signed_scan_job=signed)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_wrong_file_type_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _allow(_: Any, __: str) -> billing.AccessDecision:
        return _allowed_decision(billing.PLAN_FREE)

    monkeypatch.setattr(api, "can_use_feature", _allow)
    monkeypatch.setattr(api, "_render_fragment", _render_stub)
    monkeypatch.setattr(api, "_detect_image_mime", lambda _: "text/plain")
    upload = SimpleUploadedFile("receipt.txt", b"not-image", content_type="text/plain")
    request = RequestFactory().post("/api/receipts/scan")
    request.user = User(username="free")
    response = await api.scan_receipt(request, cast(Any, upload))
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_oversized_file_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _allow(_: Any, __: str) -> billing.AccessDecision:
        return _allowed_decision(billing.PLAN_FREE)

    monkeypatch.setattr(api, "can_use_feature", _allow)
    monkeypatch.setattr(api, "_render_fragment", _render_stub)
    upload = SimpleUploadedFile(
        "large.jpg",
        b"a" * (api.MAX_UPLOAD_SIZE_BYTES + 1),
        content_type="image/jpeg",
    )
    request = RequestFactory().post("/api/receipts/scan")
    request.user = User(username="free")
    response = await api.scan_receipt(request, cast(Any, upload))
    assert response.status_code == 400


def test_ui_locked_cta_for_free_trial_copy_present() -> None:
    template_path = (
        Path(__file__).resolve().parents[1]
        / "templates"
        / "receipts"
        / "dashboard.html"
    )
    content = template_path.read_text(encoding="utf-8")
    assert "Du kan testa scanningen gratis." in content
    assert "Export och nedladdning ingår i betalplanen." in content
    assert "Uppgradera för att ladda ner Excel/PDF." in content
