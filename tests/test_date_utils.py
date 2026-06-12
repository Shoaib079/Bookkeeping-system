"""Shared date engine — registry.date_utils contract tests."""

from __future__ import annotations

import datetime

import pytest

from registry import date_utils as du


@pytest.mark.parametrize(
    "pref,raw,expected",
    [
        ("DD.MM.YYYY", "03062026", "03.06.2026"),
        ("DD/MM/YYYY", "03062026", "03/06/2026"),
        ("YYYY-MM-DD", "20260603", "2026-06-03"),
        ("DD.MM.YYYY", "03", "03"),
        ("DD.MM.YYYY", "0306", "03.06"),
        ("DD/MM/YYYY", "0306", "03/06"),
        ("YYYY-MM-DD", "2026", "2026"),
        ("YYYY-MM-DD", "202606", "2026-06"),
    ],
)
def test_format_date_input_for_preference(pref, raw, expected):
    assert du.format_date_input_for_preference(raw, pref) == expected


@pytest.mark.parametrize(
    "pref,raw,expected",
    [
        ("DD.MM.YYYY", "03.06.2026", datetime.date(2026, 6, 3)),
        ("DD/MM/YYYY", "03/06/2026", datetime.date(2026, 6, 3)),
        ("YYYY-MM-DD", "2026-06-03", datetime.date(2026, 6, 3)),
        ("DD.MM.YYYY", "03062026", datetime.date(2026, 6, 3)),
        ("YYYY-MM-DD", "20260603", datetime.date(2026, 6, 3)),
    ],
)
def test_parse_date_text(pref, raw, expected):
    assert du.parse_date_text(raw, pref) == expected


@pytest.mark.parametrize("raw", ["31022026", "31.02.2026", "31/02/2026"])
def test_parse_date_text_rejects_invalid(raw):
    assert du.parse_date_text(raw, "DD.MM.YYYY") is None


def test_format_date_for_preference_display():
    d = datetime.date(2026, 6, 12)
    assert du.format_date_for_preference(d, "DD.MM.YYYY") == "12.06.2026"
    assert du.format_date_for_preference(d, "DD/MM/YYYY") == "12/06/2026"
    assert du.format_date_for_preference(d, "YYYY-MM-DD") == "2026-06-12"


def test_normalize_date_digits():
    assert du.normalize_date_digits("03.06.2026") == "03062026"
    assert du.normalize_date_digits("ab03cd06ef") == "0306"
