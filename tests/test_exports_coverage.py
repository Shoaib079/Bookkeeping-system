"""Unit tests for exports.py — PDF and Excel generation functions.

Covers: df_to_excel_bytes, df_to_pdf_bytes, generate_invoice_pdf,
generate_receipt_pdf, _fmt_date, _fmt_amt, _stmt_common_styles,
generate_customer_statement_pdf, generate_vendor_statement_pdf.
"""

from __future__ import annotations

import datetime

import pandas as pd
import pytest

from exports import (
    _fmt_amt,
    _fmt_date,
    df_to_excel_bytes,
    df_to_pdf_bytes,
    generate_customer_statement_pdf,
    generate_invoice_pdf,
    generate_receipt_pdf,
    generate_vendor_statement_pdf,
)


# ---------------------------------------------------------------------------
# df_to_excel_bytes
# ---------------------------------------------------------------------------
class TestDfToExcelBytes:
    def test_basic_round_trip(self):
        df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
        result = df_to_excel_bytes(df, sheet_name="Test")
        assert isinstance(result, bytes)
        assert len(result) > 0
        # The output should be a valid xlsx (starts with PK zip header)
        assert result[:2] == b"PK"

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = df_to_excel_bytes(df)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_custom_sheet_name(self):
        df = pd.DataFrame({"col": [1]})
        result = df_to_excel_bytes(df, sheet_name="MySheet")
        assert isinstance(result, bytes)
        roundtrip = pd.read_excel(pd.io.common.BytesIO(result), sheet_name="MySheet")
        assert list(roundtrip.columns) == ["col"]


# ---------------------------------------------------------------------------
# df_to_pdf_bytes
# ---------------------------------------------------------------------------
class TestDfToPdfBytes:
    def test_non_empty_df(self):
        df = pd.DataFrame({"Name": ["Alice", "Bob"], "Amount": [100.0, 200.0]})
        result = df_to_pdf_bytes(df, title="Sales Report")
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_empty_df(self):
        df = pd.DataFrame()
        result = df_to_pdf_bytes(df, title="Empty")
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_default_title(self):
        df = pd.DataFrame({"x": [1]})
        result = df_to_pdf_bytes(df)
        assert isinstance(result, bytes)
        assert len(result) > 100


# ---------------------------------------------------------------------------
# generate_invoice_pdf
# ---------------------------------------------------------------------------
class TestGenerateInvoicePdf:
    def test_basic_invoice(self):
        result = generate_invoice_pdf(
            invoice_number="INV-001",
            invoice_date=datetime.date(2026, 1, 15),
            due_date=datetime.date(2026, 2, 15),
            customer_name="Acme Corp",
            description="Consulting services",
            amount=1000.00,
            paid_amount=250.00,
            status="Partial",
            currency="USD",
            company_name="Test LLC",
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_paid_status(self):
        result = generate_invoice_pdf(
            invoice_number="INV-002",
            invoice_date=datetime.date(2026, 3, 1),
            due_date=datetime.date(2026, 3, 31),
            customer_name="Customer X",
            description="Widgets",
            amount=500.00,
            paid_amount=500.00,
            status="Paid",
        )
        assert isinstance(result, bytes)

    def test_overdue_status(self):
        result = generate_invoice_pdf(
            invoice_number="INV-003",
            invoice_date="2026-01-01",
            due_date=None,
            customer_name="Late Payer",
            description="",
            amount=200.00,
            paid_amount=0.0,
            status="Overdue",
        )
        assert isinstance(result, bytes)

    def test_unknown_status_defaults(self):
        result = generate_invoice_pdf(
            invoice_number="INV-004",
            invoice_date=datetime.datetime(2026, 6, 1, 12, 0),
            due_date=datetime.datetime(2026, 7, 1, 12, 0),
            customer_name="Someone",
            description="Misc",
            amount=100.00,
            paid_amount=50.00,
            status="Draft",
        )
        assert isinstance(result, bytes)

    def test_balance_never_negative(self):
        result = generate_invoice_pdf(
            invoice_number="INV-005",
            invoice_date=datetime.date(2026, 1, 1),
            due_date=datetime.date(2026, 1, 31),
            customer_name="Overpay",
            description="Test",
            amount=100.00,
            paid_amount=150.00,
            status="Paid",
        )
        assert isinstance(result, bytes)


# ---------------------------------------------------------------------------
# generate_receipt_pdf
# ---------------------------------------------------------------------------
class TestGenerateReceiptPdf:
    def test_basic_receipt(self):
        result = generate_receipt_pdf(
            receipt_number="REC-001",
            receipt_date=datetime.date(2026, 6, 10),
            customer_name="Walk-in Customer",
            description="Coffee beans",
            amount=45.00,
            payment_method="Cash",
            currency="TRY",
            company_name="My Cafe",
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_card_payment_receipt(self):
        result = generate_receipt_pdf(
            receipt_number="REC-002",
            receipt_date=datetime.datetime(2026, 6, 10, 14, 30),
            customer_name="",
            description="",
            amount=120.50,
            payment_method="Card",
        )
        assert isinstance(result, bytes)

    def test_string_date_receipt(self):
        result = generate_receipt_pdf(
            receipt_number="REC-003",
            receipt_date="2026-06-10",
            customer_name="Someone",
            description="Items",
            amount=99.99,
            payment_method="Bank Transfer",
        )
        assert isinstance(result, bytes)


# ---------------------------------------------------------------------------
# _fmt_date
# ---------------------------------------------------------------------------
class TestFmtDate:
    def test_date_object(self):
        assert _fmt_date(datetime.date(2026, 6, 15)) == "15 Jun 2026"

    def test_datetime_object(self):
        assert _fmt_date(datetime.datetime(2026, 12, 25, 10, 0)) == "25 Dec 2026"

    def test_iso_string(self):
        assert _fmt_date("2026-03-01") == "01 Mar 2026"

    def test_invalid_string(self):
        assert _fmt_date("not-a-date") == "not-a-date"

    def test_empty_string(self):
        assert _fmt_date("") == ""

    def test_none(self):
        assert _fmt_date(None) == ""


# ---------------------------------------------------------------------------
# _fmt_amt
# ---------------------------------------------------------------------------
class TestFmtAmt:
    def test_numeric(self):
        assert _fmt_amt(1234.5) == "1,234.50"

    def test_zero(self):
        assert _fmt_amt(0) == "0.00"

    def test_string_number(self):
        assert _fmt_amt("99.1") == "99.10"

    def test_empty_string(self):
        assert _fmt_amt("") == ""

    def test_none(self):
        assert _fmt_amt(None) == ""

    def test_non_numeric_string(self):
        assert _fmt_amt("abc") == "abc"


# ---------------------------------------------------------------------------
# generate_customer_statement_pdf
# ---------------------------------------------------------------------------
class TestGenerateCustomerStatementPdf:
    def test_basic_statement(self):
        lines = [
            {"Date": datetime.date(2026, 1, 5), "Type": "Invoice", "Reference": "INV-100",
             "Invoice": 500.00, "Payment": "", "Balance": 500.00},
            {"Date": datetime.date(2026, 1, 20), "Type": "Payment", "Reference": "PAY-50",
             "Invoice": "", "Payment": 200.00, "Balance": 300.00},
        ]
        result = generate_customer_statement_pdf(
            customer_name="Big Customer",
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 1, 31),
            opening_balance=0.0,
            closing_balance=300.0,
            lines=lines,
            currency="USD",
            company_name="Test Corp",
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_empty_lines(self):
        result = generate_customer_statement_pdf(
            customer_name="No Activity",
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 1, 31),
            opening_balance=100.0,
            closing_balance=100.0,
            lines=[],
        )
        assert isinstance(result, bytes)


# ---------------------------------------------------------------------------
# generate_vendor_statement_pdf
# ---------------------------------------------------------------------------
class TestGenerateVendorStatementPdf:
    def test_basic_vendor_statement(self):
        lines = [
            {"Date": datetime.date(2026, 2, 1), "Type": "Purchase", "Reference": "PO-10",
             "Purchases": 1000.00, "Payments": "", "Balance": 1000.00},
            {"Date": datetime.date(2026, 2, 15), "Type": "Payment", "Reference": "PAY-20",
             "Purchases": "", "Payments": 600.00, "Balance": 400.00},
        ]
        result = generate_vendor_statement_pdf(
            vendor_name="Supplier Co",
            start_date=datetime.date(2026, 2, 1),
            end_date=datetime.date(2026, 2, 28),
            opening_balance=0.0,
            closing_balance=400.0,
            lines=lines,
            currency="TRY",
            company_name="My Business",
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_empty_vendor_statement(self):
        result = generate_vendor_statement_pdf(
            vendor_name="Idle Vendor",
            start_date="2026-03-01",
            end_date="2026-03-31",
            opening_balance=0.0,
            closing_balance=0.0,
            lines=[],
        )
        assert isinstance(result, bytes)
