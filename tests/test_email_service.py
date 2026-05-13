from __future__ import annotations

import pytest
from django.core import mail

from apps.core.email_service import send_transactional_email


def test_send_kvitto_mottaget() -> None:
    ok = send_transactional_email(
        to="anvandare@test.invalid",
        template="email/kvitto_mottaget.txt",
        context={
            "subject": "Kvitto mottaget",
            "user_name": "Anna",
            "vendor": "ICA",
            "receipt_date": "2026-01-15",
            "total_amount": "249.00",
        },
    )
    assert ok
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "Kvitto mottaget"
    assert "ICA" in mail.outbox[0].body


def test_send_tack_for_betalningen() -> None:
    ok = send_transactional_email(
        to="anvandare@test.invalid",
        template="email/tack_for_betalningen.txt",
        context={
            "subject": "Tack för betalningen",
            "user_name": "Erik",
            "plan_name": "Månadsplan",
            "period_end": "2026-06-01",
        },
    )
    assert ok
    assert len(mail.outbox) == 2
    assert "prenumeration" in mail.outbox[1].body


def test_send_valkommen() -> None:
    ok = send_transactional_email(
        to="ny@test.invalid",
        template="email/valkommen.txt",
        context={
            "subject": "Välkommen till SkogsKvitto",
            "user_name": "Maja",
            "login_url": "https://skogskvitto.se/accounts/login/",
        },
    )
    assert ok
    assert len(mail.outbox) == 3
    assert "testpilot" in mail.outbox[2].body


def test_failure_is_logged_and_returns_false(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("ERROR", logger="apps.core.email_service"):
        ok = send_transactional_email(
            to="fel@test.invalid",
            template="email/finns_inte.txt",
            context={"subject": "test"},
        )
    assert not ok
    assert "Transaktionsmail misslyckades" in caplog.text
