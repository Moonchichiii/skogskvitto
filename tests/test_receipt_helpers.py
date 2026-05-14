from __future__ import annotations

from apps.receipts.api import _suggest_correction
from apps.receipts.services import _sanitize_text


def test_suggest_correction_extracts_amount_and_category() -> None:
    suggestion = _suggest_correction("Beloppet ska vara 1 249,50 kr och det här är drivmedel")
    assert suggestion["total_amount"] == "1249.50"
    assert suggestion["category"] == "Drivmedel"


def test_suggest_correction_handles_empty_or_unmatched_text() -> None:
    suggestion = _suggest_correction("Det här är fel")
    assert suggestion == {}


def test_sanitize_text_redacts_sensitive_patterns() -> None:
    text = "Personnummer 19900101-1234, tel 0701234567, e-post namn@example.com"
    sanitized = _sanitize_text(text)
    assert "19900101-1234" not in sanitized
    assert "0701234567" not in sanitized
    assert "namn@example.com" not in sanitized
    assert sanitized.count("[redacted]") >= 3
