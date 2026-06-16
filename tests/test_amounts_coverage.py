"""Unit tests for reconciliation/amounts.py — parse_amount_str."""

from __future__ import annotations

import pytest

from reconciliation.amounts import parse_amount_str


class TestParseAmountStr:
    # --- None / empty / dash ---
    def test_none_returns_none(self):
        assert parse_amount_str(None) is None

    def test_empty_string(self):
        assert parse_amount_str("") is None

    def test_dash(self):
        assert parse_amount_str("-") is None

    def test_em_dash(self):
        assert parse_amount_str("\u2014") is None

    # --- Plain integers ---
    def test_plain_integer(self):
        assert parse_amount_str("1234") == 1234.0

    def test_plain_negative(self):
        assert parse_amount_str("-50") == -50.0

    # --- US format: comma thousands, period decimal ---
    def test_us_format(self):
        assert parse_amount_str("1,234.56") == 1234.56

    def test_us_large(self):
        assert parse_amount_str("1,000,000.00") == 1000000.0

    # --- EU format: period thousands, comma decimal ---
    def test_eu_format(self):
        assert parse_amount_str("1.234,56") == 1234.56

    def test_eu_large(self):
        assert parse_amount_str("1.000.000,00") == 1000000.0

    # --- Comma-only: thousands vs decimal disambiguation ---
    def test_comma_only_thousands(self):
        # "1,000" — groups of 3 after comma → thousands separator
        assert parse_amount_str("1,000") == 1000.0

    def test_comma_only_decimal(self):
        # "1,50" — not a group of 3 → treated as decimal
        assert parse_amount_str("1,50") == 1.50

    def test_comma_multiple_thousands(self):
        assert parse_amount_str("1,000,000") == 1000000.0

    # --- Period-only: thousands vs decimal disambiguation ---
    def test_period_only_thousands(self):
        # "1.000" — group of 3 after period → thousands separator
        assert parse_amount_str("1.000") == 1000.0

    def test_period_only_decimal(self):
        # "1.50" — not a group of 3 → decimal
        assert parse_amount_str("1.50") == 1.50

    def test_period_multiple_thousands(self):
        assert parse_amount_str("1.000.000") == 1000000.0

    # --- Whitespace / non-breaking space ---
    def test_strips_whitespace(self):
        assert parse_amount_str("  1234  ") == 1234.0

    def test_strips_nbsp(self):
        assert parse_amount_str("1\xa0234") == 1234.0

    def test_strips_space_in_number(self):
        assert parse_amount_str("1 234") == 1234.0

    # --- Non-numeric garbage ---
    def test_garbage_returns_none(self):
        assert parse_amount_str("abc") is None

    def test_mixed_garbage(self):
        assert parse_amount_str("12abc34") is None

    # --- Edge: numeric-ish ---
    def test_zero(self):
        assert parse_amount_str("0") == 0.0

    def test_float_passthrough(self):
        # str(float) should round-trip
        assert parse_amount_str("3.14") == 3.14
