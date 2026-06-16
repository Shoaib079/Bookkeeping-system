"""Unit tests for reconciliation/settlement_parse.py — merchant settlement parsing.

Covers: suggest_settlement_mapping, _alias_matches_header, _parse_amount_cell,
parse_settlement_statement.
"""

from __future__ import annotations

import csv
import io

import pandas as pd
import pytest

from reconciliation.settlement_parse import (
    SETTLEMENT_FIELDS,
    _alias_matches_header,
    _parse_amount_cell,
    parse_settlement_statement,
    suggest_settlement_mapping,
)


# ---------------------------------------------------------------------------
# _alias_matches_header
# ---------------------------------------------------------------------------
class TestAliasMatchesHeader:
    def test_exact_match(self):
        assert _alias_matches_header("date", "date") is True

    def test_word_match(self):
        assert _alias_matches_header("settlement date", "date") is True

    def test_no_match(self):
        assert _alias_matches_header("amount", "date") is False

    def test_case_insensitive(self):
        assert _alias_matches_header("date", "Date") is True


# ---------------------------------------------------------------------------
# suggest_settlement_mapping
# ---------------------------------------------------------------------------
class TestSuggestSettlementMapping:
    def test_english_headers(self):
        headers = ["Date", "Description", "Gross Amount", "Fee", "Net Amount", "Batch No"]
        mapping = suggest_settlement_mapping(headers)
        assert mapping["date"] == "Date"
        assert mapping["description"] == "Description"
        assert mapping["gross"] == "Gross Amount"
        assert mapping["fee"] == "Fee"
        assert mapping["net"] == "Net Amount"
        assert mapping["batch_reference"] == "Batch No"

    def test_turkish_headers(self):
        headers = ["Tarih", "Açıklama", "Brüt Tutar", "Komisyon", "Net Tutar", "Referans"]
        mapping = suggest_settlement_mapping(headers)
        assert mapping["date"] == "Tarih"
        assert mapping["description"] == "Açıklama"
        assert mapping["gross"] == "Brüt Tutar"
        assert mapping["fee"] == "Komisyon"
        assert mapping["net"] == "Net Tutar"
        assert mapping["batch_reference"] == "Referans"

    def test_keyword_fallback(self):
        headers = ["İşlem Tarihi", "Detay Aciklama", "Toplam Satış", "Banka Masrafı", "Yatırılan Tutar"]
        mapping = suggest_settlement_mapping(headers)
        assert mapping["date"] is not None
        assert mapping["description"] is not None

    def test_no_match(self):
        headers = ["Col1", "Col2"]
        mapping = suggest_settlement_mapping(headers)
        for field in SETTLEMENT_FIELDS:
            assert mapping[field] is None

    def test_all_fields_present(self):
        """Each canonical settlement field should appear in the returned dict."""
        mapping = suggest_settlement_mapping(["X"])
        for field in SETTLEMENT_FIELDS:
            assert field in mapping


# ---------------------------------------------------------------------------
# _parse_amount_cell
# ---------------------------------------------------------------------------
class TestParseAmountCell:
    def test_none_col(self):
        row = pd.Series({"A": 100})
        assert _parse_amount_cell(row, None) is None

    def test_numeric_value(self):
        row = pd.Series({"Amount": 123.456})
        result = _parse_amount_cell(row, "Amount")
        assert result == 123.46

    def test_negative_numeric_abs(self):
        row = pd.Series({"Amount": -50.0})
        result = _parse_amount_cell(row, "Amount")
        assert result == 50.0

    def test_string_amount(self):
        row = pd.Series({"Amount": "1,234.56"})
        result = _parse_amount_cell(row, "Amount")
        assert result == 1234.56

    def test_nan_returns_none(self):
        row = pd.Series({"Amount": float("nan")})
        result = _parse_amount_cell(row, "Amount")
        assert result is None

    def test_non_parseable_string(self):
        row = pd.Series({"Amount": "N/A"})
        result = _parse_amount_cell(row, "Amount")
        assert result is None

    def test_missing_column(self):
        row = pd.Series({"Other": 100})
        result = _parse_amount_cell(row, "Amount")
        assert result is None


# ---------------------------------------------------------------------------
# parse_settlement_statement
# ---------------------------------------------------------------------------
class TestParseSettlementStatement:
    def _csv_bytes(self, rows: list[list[str]]) -> bytes:
        buf = io.StringIO()
        csv.writer(buf).writerows(rows)
        return buf.getvalue().encode("utf-8")

    def test_valid_rows(self):
        data = self._csv_bytes([
            ["Date", "Description", "Gross", "Fee", "Net", "Ref"],
            ["2026-01-01", "Batch A", "1000.00", "25.00", "975.00", "B001"],
            ["2026-01-02", "Batch B", "500.00", "10.00", "490.00", "B002"],
        ])
        mapping = {
            "date": "Date",
            "description": "Description",
            "gross": "Gross",
            "fee": "Fee",
            "net": "Net",
            "batch_reference": "Ref",
        }
        rows = parse_settlement_statement(data, "test.csv", mapping, currency="USD")
        assert len(rows) == 2
        assert rows[0]["parsed_successfully"] is True
        assert rows[0]["gross_amount"] == 1000.0
        assert rows[0]["fee_amount"] == 25.0
        assert rows[0]["net_amount"] == 975.0
        assert rows[0]["batch_reference"] == "B001"
        assert rows[0]["currency"] == "USD"
        assert rows[0]["status"] == "staging"

    def test_net_computed_from_gross_minus_fee(self):
        data = self._csv_bytes([
            ["Date", "Description", "Gross", "Fee"],
            ["2026-01-01", "Auto net", "200.00", "5.00"],
        ])
        mapping = {
            "date": "Date",
            "description": "Description",
            "gross": "Gross",
            "fee": "Fee",
            "net": None,
            "batch_reference": None,
        }
        rows = parse_settlement_statement(data, "test.csv", mapping)
        assert rows[0]["net_amount"] == 195.0
        assert rows[0]["parsed_successfully"] is True

    def test_parse_error_invalid_date(self):
        data = self._csv_bytes([
            ["Date", "Description", "Gross", "Fee", "Net"],
            ["", "Bad row", "100", "5", "95"],
        ])
        mapping = {
            "date": "Date",
            "description": "Description",
            "gross": "Gross",
            "fee": "Fee",
            "net": "Net",
            "batch_reference": None,
        }
        rows = parse_settlement_statement(data, "test.csv", mapping)
        assert rows[0]["parsed_successfully"] is False
        assert "invalid_date" in rows[0]["parse_error"]
        assert rows[0]["status"] == "parse_error"

    def test_parse_error_invalid_gross(self):
        data = self._csv_bytes([
            ["Date", "Description", "Gross", "Fee", "Net"],
            ["2026-01-01", "Zero gross", "0", "0", "0"],
        ])
        mapping = {
            "date": "Date",
            "description": "Description",
            "gross": "Gross",
            "fee": "Fee",
            "net": "Net",
            "batch_reference": None,
        }
        rows = parse_settlement_statement(data, "test.csv", mapping)
        assert rows[0]["parsed_successfully"] is False
        assert "invalid_gross" in rows[0]["parse_error"]

    def test_parse_error_gross_fee_net_mismatch(self):
        data = self._csv_bytes([
            ["Date", "Description", "Gross", "Fee", "Net"],
            ["2026-01-01", "Mismatch", "1000", "50", "900"],
        ])
        mapping = {
            "date": "Date",
            "description": "Description",
            "gross": "Gross",
            "fee": "Fee",
            "net": "Net",
            "batch_reference": None,
        }
        rows = parse_settlement_statement(data, "test.csv", mapping)
        assert rows[0]["parsed_successfully"] is False
        assert "gross_fee_net_mismatch" in rows[0]["parse_error"]

    def test_description_falls_back_to_batch_ref(self):
        data = self._csv_bytes([
            ["Date", "Description", "Gross", "Fee", "Net", "Ref"],
            ["2026-01-01", "", "100", "5", "95", "BATCH-1"],
        ])
        mapping = {
            "date": "Date",
            "description": "Description",
            "gross": "Gross",
            "fee": "Fee",
            "net": "Net",
            "batch_reference": "Ref",
        }
        rows = parse_settlement_statement(data, "test.csv", mapping)
        assert rows[0]["description"] == "BATCH-1"
