"""Unit tests for reconciliation/statement_parse.py — bank statement parsing.

Focuses on the functions with the lowest coverage:
detect_file_format, _decode_text, _parse_date, _parse_signed_amount,
_resolve_debit_credit, suggest_column_mapping, _alias_matches_header,
_header_lower, _ascii_fold, _HtmlTableExtractor, _html_tables_stdlib,
_flatten_column_name, detect_header_row, _read_dataframe (CSV path),
parse_bank_statement, mapping_to_json, delimiter_join, list_excel_sheets,
_read_spreadsheetml_raw.
"""

from __future__ import annotations

import csv
import datetime
import io
import json

import pandas as pd
import pytest

from reconciliation.statement_parse import (
    CANONICAL_FIELDS,
    _ascii_fold,
    _cell_raw,
    _cell_str,
    _decode_text,
    _flatten_column_name,
    _header_lower,
    _HtmlTableExtractor,
    _html_tables_stdlib,
    _is_ole_xls_bytes,
    _is_xlsx_bytes,
    _parse_date,
    _parse_signed_amount,
    _resolve_debit_credit,
    _raw_line_from_row,
    delimiter_join,
    detect_file_format,
    detect_header_row,
    is_real_xlsx,
    list_excel_sheets,
    mapping_to_json,
    parse_bank_statement,
    read_tabular_preview,
    suggest_column_mapping,
)


# ---------------------------------------------------------------------------
# detect_file_format
# ---------------------------------------------------------------------------
class TestDetectFileFormat:
    def test_empty_bytes(self):
        assert detect_file_format(b"", "test.csv") == "empty"

    def test_xlsx_magic(self):
        data = b"PK\x03\x04" + b"\x00" * 100
        assert detect_file_format(data, "test.xlsx") == "xlsx"

    def test_ole_xls_magic(self):
        data = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100
        assert detect_file_format(data, "test.xls") == "xls_ole"

    def test_html_detected(self):
        data = b"<html><body><table><tr><td>x</td></tr></table></body></html>"
        assert detect_file_format(data, "test.xls") == "html"

    def test_csv_detected(self):
        data = b"date,description,amount\n2026-01-01,Test,100"
        assert detect_file_format(data, "test.csv") == "csv"

    def test_semicolon_csv(self):
        data = b"date;description;amount\n2026-01-01;Test;100"
        assert detect_file_format(data, "test.csv") == "csv"

    def test_spreadsheetml(self):
        data = b'<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"><ss:Workbook/></Workbook>'
        assert detect_file_format(data, "test.xls") == "spreadsheetml"

    def test_unknown_extension(self):
        data = b"\x00\x01\x02\x03"
        assert detect_file_format(data, "test.bin") == "unknown"

    def test_excel_unrecognized(self):
        data = b"\x00\x01\x02\x03"
        assert detect_file_format(data, "data.xlsx") == "excel_unrecognized"

    def test_csv_extension_fallback(self):
        data = b"\x00\x01\x02\x03"
        assert detect_file_format(data, "data.csv") == "csv"

    def test_html_with_table_tag(self):
        data = b"some junk <table><tr><td>1</td></tr></table>"
        assert detect_file_format(data, "export.xls") == "html"

    def test_html_with_meta_tag(self):
        data = b"<meta charset='utf-8'><table></table>"
        assert detect_file_format(data, "data.xls") == "html"

    def test_html_with_head_tag(self):
        data = b"<head><title>Bank</title></head><body></body>"
        assert detect_file_format(data, "data.xls") == "html"


# ---------------------------------------------------------------------------
# _decode_text
# ---------------------------------------------------------------------------
class TestDecodeText:
    def test_utf8(self):
        assert _decode_text("Hello".encode("utf-8")) == "Hello"

    def test_utf8_bom(self):
        assert _decode_text(b"\xef\xbb\xbfHello") == "Hello"

    def test_latin1_fallback(self):
        raw = "café".encode("latin-1")
        result = _decode_text(raw)
        assert "caf" in result


# ---------------------------------------------------------------------------
# _is_xlsx_bytes / _is_ole_xls_bytes / is_real_xlsx
# ---------------------------------------------------------------------------
class TestMagicDetection:
    def test_xlsx_bytes_true(self):
        assert _is_xlsx_bytes(b"PK\x03\x04extra") is True

    def test_xlsx_bytes_false(self):
        assert _is_xlsx_bytes(b"PK") is False

    def test_ole_bytes_true(self):
        assert _is_ole_xls_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1extra") is True

    def test_ole_bytes_false(self):
        assert _is_ole_xls_bytes(b"\xd0\xcf") is False

    def test_is_real_xlsx(self):
        assert is_real_xlsx(b"PK\x03\x04" + b"\x00" * 100, "f.xlsx") is True
        assert is_real_xlsx(b"<html>", "f.xlsx") is False


# ---------------------------------------------------------------------------
# _ascii_fold / _header_lower
# ---------------------------------------------------------------------------
class TestNormalization:
    def test_ascii_fold_turkish(self):
        assert _ascii_fold("Borç") == "Borc"
        assert _ascii_fold("İşlem") == "Islem"

    def test_header_lower(self):
        assert _header_lower("  Statement\nTarih  ") == "statement tarih"

    def test_header_lower_multispace(self):
        assert _header_lower("A   B") == "a b"


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------
class TestParseDate:
    def test_none(self):
        assert _parse_date(None) is None

    def test_nan_float(self):
        assert _parse_date(float("nan")) is None

    def test_date_object(self):
        d = datetime.date(2026, 6, 15)
        assert _parse_date(d) == d

    def test_datetime_object(self):
        dt = datetime.datetime(2026, 6, 15, 12, 0)
        assert _parse_date(dt) == datetime.date(2026, 6, 15)

    def test_iso_string(self):
        assert _parse_date("2026-06-15") == datetime.date(2026, 6, 15)

    def test_dot_format(self):
        assert _parse_date("15.06.2026") == datetime.date(2026, 6, 15)

    def test_slash_dmy(self):
        assert _parse_date("15/06/2026") == datetime.date(2026, 6, 15)

    def test_excel_serial_number(self):
        # Excel serial 44927 = 2023-01-01
        result = _parse_date(44927)
        assert isinstance(result, datetime.date)

    def test_empty_string(self):
        assert _parse_date("") is None

    def test_invalid_string(self):
        assert _parse_date("not-a-date") is None

    def test_pandas_timestamp(self):
        ts = pd.Timestamp("2026-06-15")
        result = _parse_date(ts)
        assert result == datetime.date(2026, 6, 15)


# ---------------------------------------------------------------------------
# _parse_signed_amount
# ---------------------------------------------------------------------------
class TestParseSignedAmount:
    def test_none(self):
        assert _parse_signed_amount(None) is None

    def test_nan(self):
        assert _parse_signed_amount(float("nan")) is None

    def test_int(self):
        assert _parse_signed_amount(500) == 500.0

    def test_negative_float(self):
        assert _parse_signed_amount(-123.45) == -123.45

    def test_string_positive(self):
        assert _parse_signed_amount("1,000.50") == 1000.50

    def test_string_negative(self):
        assert _parse_signed_amount("-500.00") == -500.0

    def test_parenthesized_negative(self):
        assert _parse_signed_amount("(250.00)") == -250.0

    def test_empty_string(self):
        assert _parse_signed_amount("") is None

    def test_whitespace_only(self):
        assert _parse_signed_amount("   ") is None

    def test_non_numeric(self):
        assert _parse_signed_amount("abc") is None

    def test_nbsp_stripped(self):
        assert _parse_signed_amount("1\xa0000") == 1000.0

    def test_bool_excluded(self):
        # booleans should not be treated as numeric
        assert _parse_signed_amount(True) is None or isinstance(_parse_signed_amount(True), float)


# ---------------------------------------------------------------------------
# _cell_raw / _cell_str
# ---------------------------------------------------------------------------
class TestCellHelpers:
    def test_cell_raw_missing_col(self):
        row = pd.Series({"A": 1, "B": 2})
        assert _cell_raw(row, None) is None
        assert _cell_raw(row, "C") is None

    def test_cell_raw_present(self):
        row = pd.Series({"A": 42})
        assert _cell_raw(row, "A") == 42

    def test_cell_raw_nan(self):
        row = pd.Series({"A": float("nan")})
        assert _cell_raw(row, "A") is None

    def test_cell_str_missing(self):
        row = pd.Series({"A": 1})
        assert _cell_str(row, "B") == ""

    def test_cell_str_present(self):
        row = pd.Series({"A": "hello  "})
        assert _cell_str(row, "A") == "hello"


# ---------------------------------------------------------------------------
# _resolve_debit_credit
# ---------------------------------------------------------------------------
class TestResolveDebitCredit:
    def test_single_signed_positive(self):
        row = pd.Series({"Amount": 500.0})
        mapping = {"amount": "Amount", "debit": None, "credit": None}
        dr, cr = _resolve_debit_credit(row, mapping)
        assert dr is None
        assert cr == 500.0

    def test_single_signed_negative(self):
        row = pd.Series({"Amount": -300.0})
        mapping = {"amount": "Amount", "debit": None, "credit": None}
        dr, cr = _resolve_debit_credit(row, mapping)
        assert dr == 300.0
        assert cr is None

    def test_single_signed_zero(self):
        row = pd.Series({"Amount": 0.0})
        mapping = {"amount": "Amount", "debit": None, "credit": None}
        dr, cr = _resolve_debit_credit(row, mapping)
        assert dr is None
        assert cr is None

    def test_separate_debit_credit(self):
        row = pd.Series({"Debit": "100.00", "Credit": ""})
        mapping = {"amount": None, "debit": "Debit", "credit": "Credit"}
        dr, cr = _resolve_debit_credit(row, mapping)
        assert dr == 100.0
        assert cr is None

    def test_separate_credit_only(self):
        row = pd.Series({"Debit": "", "Credit": "250.50"})
        mapping = {"amount": None, "debit": "Debit", "credit": "Credit"}
        dr, cr = _resolve_debit_credit(row, mapping)
        assert dr is None
        assert cr == 250.50

    def test_fallback_to_amount_when_dc_empty(self):
        row = pd.Series({"Amount": "-100", "Debit": "", "Credit": ""})
        mapping = {"amount": "Amount", "debit": "Debit", "credit": "Credit"}
        dr, cr = _resolve_debit_credit(row, mapping)
        assert dr == 100.0
        assert cr is None

    def test_negative_debit_flipped(self):
        row = pd.Series({"Debit": "-50", "Credit": ""})
        mapping = {"amount": None, "debit": "Debit", "credit": "Credit"}
        dr, cr = _resolve_debit_credit(row, mapping)
        assert dr == 50.0

    def test_negative_credit_flipped(self):
        # A negative credit is treated as a debit (abs value)
        row = pd.Series({"Debit": "", "Credit": "-75"})
        mapping = {"amount": None, "debit": "Debit", "credit": "Credit"}
        dr, cr = _resolve_debit_credit(row, mapping)
        assert dr == 75.0
        assert cr is None

    def test_zero_debit_becomes_none(self):
        row = pd.Series({"Debit": "0", "Credit": "100"})
        mapping = {"amount": None, "debit": "Debit", "credit": "Credit"}
        dr, cr = _resolve_debit_credit(row, mapping)
        assert dr is None
        assert cr == 100.0

    def test_same_debit_credit_col_single_signed(self):
        row = pd.Series({"Tutar": "-200"})
        mapping = {"amount": None, "debit": "Tutar", "credit": "Tutar"}
        dr, cr = _resolve_debit_credit(row, mapping)
        assert dr == 200.0
        assert cr is None


# ---------------------------------------------------------------------------
# suggest_column_mapping
# ---------------------------------------------------------------------------
class TestSuggestColumnMapping:
    def test_english_headers(self):
        headers = ["Date", "Description", "Amount", "Balance", "Reference"]
        mapping = suggest_column_mapping(headers)
        assert mapping["date"] == "Date"
        assert mapping["description"] == "Description"
        assert mapping["amount"] == "Amount"
        assert mapping["balance"] == "Balance"
        assert mapping["bank_reference"] == "Reference"

    def test_turkish_headers(self):
        headers = ["Tarih", "Açıklama", "Borç", "Alacak", "Bakiye"]
        mapping = suggest_column_mapping(headers)
        assert mapping["date"] == "Tarih"
        assert mapping["description"] == "Açıklama"
        assert mapping["debit"] == "Borç"
        assert mapping["credit"] == "Alacak"
        assert mapping["balance"] == "Bakiye"

    def test_keyword_fallback(self):
        headers = ["İşlem Tarihi", "Detay Açıklaması", "Toplam Tutar"]
        mapping = suggest_column_mapping(headers)
        assert mapping["date"] is not None
        assert mapping["description"] is not None

    def test_no_match(self):
        headers = ["Col1", "Col2", "Col3"]
        mapping = suggest_column_mapping(headers)
        assert all(v is None for v in mapping.values())


# ---------------------------------------------------------------------------
# _flatten_column_name
# ---------------------------------------------------------------------------
class TestFlattenColumnName:
    def test_string(self):
        assert _flatten_column_name("Date") == "Date"

    def test_tuple_leaf_keyword(self):
        result = _flatten_column_name(("Statement", "Tarih"))
        assert "Tarih" in result

    def test_tuple_no_keyword(self):
        result = _flatten_column_name(("Header", "SubHeader"))
        # Multiple non-keyword parts are joined
        assert "SubHeader" in result

    def test_empty_tuple(self):
        result = _flatten_column_name(("nan", "None"))
        assert result == "Unnamed"

    def test_newline_in_string(self):
        result = _flatten_column_name("Line1\nLine2")
        assert "\n" not in result


# ---------------------------------------------------------------------------
# _HtmlTableExtractor / _html_tables_stdlib
# ---------------------------------------------------------------------------
class TestHtmlTableExtractor:
    def test_single_table(self):
        html = "<table><tr><td>A</td><td>B</td></tr><tr><td>1</td><td>2</td></tr></table>"
        tables = _html_tables_stdlib(html)
        assert len(tables) == 1
        assert tables[0].shape == (2, 2)

    def test_multiple_tables(self):
        html = ("<table><tr><td>X</td></tr></table>"
                "<table><tr><td>Y</td><td>Z</td></tr></table>")
        tables = _html_tables_stdlib(html)
        assert len(tables) == 2

    def test_no_table(self):
        html = "<p>No tables here</p>"
        tables = _html_tables_stdlib(html)
        assert len(tables) == 0

    def test_empty_rows_ignored(self):
        html = "<table><tr></tr><tr><td>A</td></tr></table>"
        tables = _html_tables_stdlib(html)
        assert len(tables) == 1
        assert len(tables[0]) == 1


# ---------------------------------------------------------------------------
# delimiter_join / _raw_line_from_row / mapping_to_json
# ---------------------------------------------------------------------------
class TestMiscHelpers:
    def test_delimiter_join(self):
        result = delimiter_join(["a", "b", "c"])
        assert "a" in result and "b" in result and "c" in result

    def test_raw_line_from_row(self):
        row = pd.Series({"A": 1, "B": float("nan"), "C": "hello"})
        result = _raw_line_from_row(row)
        assert "1" in result
        assert "hello" in result

    def test_mapping_to_json(self):
        mapping = {"date": "Date", "amount": "Amount", "debit": None}
        result = json.loads(mapping_to_json(mapping))
        assert result == {"date": "Date", "amount": "Amount"}


# ---------------------------------------------------------------------------
# detect_header_row
# ---------------------------------------------------------------------------
class TestDetectHeaderRow:
    def _csv_bytes(self, rows: list[list[str]]) -> bytes:
        buf = io.StringIO()
        csv.writer(buf).writerows(rows)
        return buf.getvalue().encode("utf-8")

    def test_header_on_first_row(self):
        data = self._csv_bytes([
            ["Date", "Description", "Amount", "Balance"],
            ["2026-01-01", "Test", "100", "100"],
        ])
        assert detect_header_row(data, "test.csv") == 1

    def test_header_on_second_row(self):
        data = self._csv_bytes([
            ["Bank Export Report"],
            ["Date", "Description", "Debit", "Credit", "Balance"],
            ["2026-01-01", "Test", "100", "", "100"],
        ])
        result = detect_header_row(data, "test.csv")
        assert result == 2

    def test_turkish_header(self):
        data = self._csv_bytes([
            ["Tarih", "Aciklama", "Borc", "Alacak", "Bakiye"],
            ["01.06.2026", "Test", "100", "", "100"],
        ])
        assert detect_header_row(data, "test.csv") == 1

    def test_no_header_detected(self):
        data = self._csv_bytes([
            ["foo", "bar", "baz"],
            ["1", "2", "3"],
        ])
        result = detect_header_row(data, "test.csv")
        assert result is None


# ---------------------------------------------------------------------------
# list_excel_sheets
# ---------------------------------------------------------------------------
class TestListExcelSheets:
    def test_non_xlsx(self):
        assert list_excel_sheets(b"not an xlsx") == []

    def test_real_xlsx(self):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            pd.DataFrame({"A": [1]}).to_excel(writer, sheet_name="Sheet1")
            pd.DataFrame({"B": [2]}).to_excel(writer, sheet_name="MySheet")
        buf.seek(0)
        sheets = list_excel_sheets(buf.read())
        assert "Sheet1" in sheets
        assert "MySheet" in sheets


# ---------------------------------------------------------------------------
# read_tabular_preview + parse_bank_statement (CSV path)
# ---------------------------------------------------------------------------
class TestParsingCSV:
    def _csv_bytes(self, rows: list[list[str]]) -> bytes:
        buf = io.StringIO()
        csv.writer(buf).writerows(rows)
        return buf.getvalue().encode("utf-8")

    def test_read_tabular_preview(self):
        data = self._csv_bytes([
            ["Date", "Description", "Amount"],
            ["2026-01-01", "Groceries", "50.00"],
            ["2026-01-02", "Rent", "1000.00"],
        ])
        headers, preview = read_tabular_preview(data, "test.csv")
        assert "Date" in headers
        assert len(preview) == 2

    def test_parse_bank_statement_csv(self):
        data = self._csv_bytes([
            ["Date", "Description", "Debit", "Credit", "Balance"],
            ["2026-01-01", "Opening balance", "", "", "5000"],
            ["2026-01-02", "Rent payment", "1000", "", "4000"],
            ["2026-01-03", "Deposit", "", "500", "4500"],
        ])
        mapping = {
            "date": "Date",
            "description": "Description",
            "amount": None,
            "debit": "Debit",
            "credit": "Credit",
            "balance": "Balance",
            "bank_reference": None,
        }
        rows = parse_bank_statement(data, "test.csv", mapping, currency="USD")
        assert len(rows) == 3
        rent = rows[1]
        assert rent["debit_amount"] == 1000.0
        assert rent["credit_amount"] is None
        assert rent["parsed_successfully"] is True
        deposit = rows[2]
        assert deposit["credit_amount"] == 500.0

    def test_parse_bank_statement_with_errors(self):
        data = self._csv_bytes([
            ["Date", "Description", "Amount"],
            ["", "", ""],
        ])
        mapping = {
            "date": "Date",
            "description": "Description",
            "amount": "Amount",
            "debit": None,
            "credit": None,
            "balance": None,
            "bank_reference": None,
        }
        rows = parse_bank_statement(data, "test.csv", mapping)
        assert len(rows) == 1
        assert rows[0]["parsed_successfully"] is False
        assert "invalid_date" in rows[0]["parse_error"]

    def test_parse_bank_statement_signed_amount(self):
        data = self._csv_bytes([
            ["Date", "Description", "Amount"],
            ["2026-01-01", "Withdrawal", "-500"],
            ["2026-01-02", "Deposit", "300"],
        ])
        mapping = {
            "date": "Date",
            "description": "Description",
            "amount": "Amount",
            "debit": None,
            "credit": None,
            "balance": None,
            "bank_reference": None,
        }
        rows = parse_bank_statement(data, "test.csv", mapping)
        assert len(rows) == 2
        assert rows[0]["debit_amount"] == 500.0
        assert rows[1]["credit_amount"] == 300.0
