"""FASTAPI-P0.2-E — AR/AP read service contract tests."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app as erp_app
from db import Base
import models
from services import read_ar_ap as arap

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        yield s


def _company(db, slug: str):
    co = models.Company(
        name=slug.title(),
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()
    return co


def _vendor(db, co, name="Acme Supplies"):
    v = models.Vendor(name=name, company_id=co.id, is_active=True)
    db.add(v)
    db.commit()
    return v


def _legacy_receivables(
    db,
    company_id,
    *,
    search_keyword=None,
    customer_filter="all",
    status_filter="all",
):
    credit_sales = (
        db.query(models.Sale)
        .filter(
            models.Sale.company_id == company_id,
            models.Sale.sale_type == "Credit",
            models.Sale.is_void == False,  # noqa: E712
        )
        .order_by(models.Sale.date.desc())
        .all()
    )
    filtered = [
        s
        for s in credit_sales
        if (
            not search_keyword
            or search_keyword.lower() in s.customer_name.lower()
            or search_keyword.lower() in s.invoice_number.lower()
            or search_keyword.lower() in (s.description or "").lower()
        )
        and (customer_filter == "all" or s.customer_name == customer_filter)
        and (status_filter == "all" or s.status == status_filter)
    ]
    open_filtered = [s for s in filtered if s.status != "Paid"]
    return {
        "rows": filtered,
        "outstanding": sum(s.balance for s in open_filtered),
        "overdue": sum(s.balance for s in filtered if s.status == "Overdue"),
        "open_count": len(open_filtered),
    }


def _legacy_payables(
    db,
    company_id,
    *,
    search_keyword=None,
    vendor_filter="all",
    paid_filter="all",
    show_voided=False,
):
    all_payables = (
        db.query(models.Payable)
        .filter(models.Payable.company_id == company_id)
        .order_by(models.Payable.date.desc())
        .all()
    )

    def _status(record):
        return arap.payable_status(record)

    filtered = []
    for record in all_payables:
        if record.is_void and not show_voided:
            continue
        vendor = db.get(models.Vendor, record.vendor_id)
        vname = vendor.name if vendor else "Unknown"
        if search_keyword and search_keyword.lower() not in vname.lower() and search_keyword.lower() not in (record.description or "").lower():
            continue
        if vendor_filter != "all" and vname != vendor_filter:
            continue
        if paid_filter != "all" and _status(record) != paid_filter:
            continue
        filtered.append((record, vname))

    today = datetime.date.today()
    total_outstanding = sum(
        arap.payable_balance(r) for r, _ in filtered if not r.is_void and not r.paid
    )
    overdue = sum(
        arap.payable_balance(r) for r, _ in filtered
        if not r.is_void and not r.paid and r.due_date < today
    )
    return {
        "rows": filtered,
        "total_outstanding": total_outstanding,
        "overdue": overdue,
        "showing_count": len(filtered),
    }


@pytest.fixture()
def seeded_ar_ap(db):
    co_a = _company(db, "alpha")
    co_b = _company(db, "beta")
    vendor_a = _vendor(db, co_a, "Vendor A")
    _vendor(db, co_b, "Vendor B")

    sales = [
        models.Sale(
            date=datetime.date(2026, 1, 10),
            invoice_number="INV-001",
            customer_name="Alice",
            description="Widgets",
            amount=1000.0,
            sale_type="Credit",
            paid_amount=200.0,
            balance=800.0,
            due_date=datetime.date(2026, 2, 1),
            status="Partial",
            is_void=False,
            company_id=co_a.id,
        ),
        models.Sale(
            date=datetime.date(2026, 1, 5),
            invoice_number="INV-002",
            customer_name="Bob",
            description="",
            amount=500.0,
            sale_type="Credit",
            paid_amount=500.0,
            balance=0.0,
            due_date=datetime.date(2026, 1, 20),
            status="Paid",
            is_void=False,
            company_id=co_a.id,
        ),
        models.Sale(
            date=datetime.date(2026, 1, 1),
            invoice_number="INV-VOID",
            customer_name="Alice",
            description="",
            amount=99.0,
            sale_type="Credit",
            paid_amount=0.0,
            balance=99.0,
            due_date=datetime.date(2026, 1, 1),
            status="Open",
            is_void=True,
            company_id=co_a.id,
        ),
        models.Sale(
            date=datetime.date(2026, 1, 8),
            invoice_number="INV-B",
            customer_name="Other Co",
            description="",
            amount=300.0,
            sale_type="Credit",
            paid_amount=0.0,
            balance=300.0,
            due_date=datetime.date(2025, 12, 1),
            status="Overdue",
            is_void=False,
            company_id=co_b.id,
        ),
    ]
    payables = [
        models.Payable(
            date=datetime.date(2026, 1, 12),
            vendor_id=vendor_a.id,
            amount=400.0,
            paid_amount=100.0,
            balance=300.0,
            due_date=datetime.date(2026, 2, 15),
            paid=False,
            description="Rent",
            company_id=co_a.id,
        ),
        models.Payable(
            date=datetime.date(2026, 1, 3),
            vendor_id=vendor_a.id,
            amount=200.0,
            paid_amount=200.0,
            balance=0.0,
            due_date=datetime.date(2026, 1, 10),
            paid=True,
            description="Paid bill",
            company_id=co_a.id,
        ),
        models.Payable(
            date=datetime.date(2026, 1, 2),
            vendor_id=vendor_a.id,
            amount=150.0,
            paid_amount=0.0,
            balance=150.0,
            due_date=datetime.date(2025, 12, 20),
            paid=False,
            is_void=True,
            void_reason="Duplicate",
            description="Voided",
            company_id=co_a.id,
        ),
    ]
    db.add_all(sales + payables)
    db.commit()
    return co_a, co_b


class TestReceivables:
    def test_matches_legacy_output(self, db, seeded_ar_ap):
        co_a, _co_b = seeded_ar_ap
        legacy = _legacy_receivables(db, co_a.id)
        page = arap.compute_receivables_page(db, company_id=co_a.id)
        assert page.showing_count == len(legacy["rows"])
        assert page.outstanding == pytest.approx(legacy["outstanding"])
        assert page.overdue == pytest.approx(legacy["overdue"])
        assert page.open_count == legacy["open_count"]
        assert {r.invoice_number for r in page.rows} == {s.invoice_number for s in legacy["rows"]}

    def test_void_sales_excluded(self, db, seeded_ar_ap):
        co_a, _co_b = seeded_ar_ap
        page = arap.compute_receivables_page(db, company_id=co_a.id)
        assert "INV-VOID" not in {r.invoice_number for r in page.rows}

    def test_status_filter(self, db, seeded_ar_ap):
        co_a, _co_b = seeded_ar_ap
        page = arap.compute_receivables_page(
            db, company_id=co_a.id, status_filter="Paid",
        )
        assert len(page.rows) == 1
        assert page.rows[0].status == "Paid"

    def test_search_filter(self, db, seeded_ar_ap):
        co_a, _co_b = seeded_ar_ap
        page = arap.compute_receivables_page(
            db, company_id=co_a.id, search_keyword="widgets",
        )
        assert len(page.rows) == 1
        assert page.rows[0].invoice_number == "INV-001"

    def test_app_shim_matches_service(self, db, seeded_ar_ap):
        co_a, _co_b = seeded_ar_ap
        sys.modules["streamlit"].session_state["active_company_id"] = co_a.id
        app_page = erp_app.compute_receivables_page(db)
        svc_page = arap.compute_receivables_page(db, company_id=co_a.id)
        assert app_page.rows == svc_page.rows
        assert app_page.outstanding == svc_page.outstanding


class TestPayables:
    def test_matches_legacy_output(self, db, seeded_ar_ap):
        co_a, _co_b = seeded_ar_ap
        legacy = _legacy_payables(db, co_a.id)
        page = arap.compute_payables_page(db, company_id=co_a.id)
        assert page.showing_count == legacy["showing_count"]
        assert page.total_outstanding == pytest.approx(legacy["total_outstanding"])
        assert page.overdue == pytest.approx(legacy["overdue"])
        assert {r.id for r in page.rows} == {r.id for r, _ in legacy["rows"]}

    def test_paid_partial_open_status(self, db, seeded_ar_ap):
        co_a, _co_b = seeded_ar_ap
        page = arap.compute_payables_page(db, company_id=co_a.id)
        by_id = {r.id: r.status for r in page.rows}
        assert by_id  # at least open + paid visible
        assert "Paid" in by_id.values()
        assert "Partial" in by_id.values()

    def test_void_excluded_by_default(self, db, seeded_ar_ap):
        co_a, _co_b = seeded_ar_ap
        page = arap.compute_payables_page(db, company_id=co_a.id)
        assert all(not r.is_void for r in page.rows)

    def test_void_included_when_requested(self, db, seeded_ar_ap):
        co_a, _co_b = seeded_ar_ap
        page = arap.compute_payables_page(
            db, company_id=co_a.id, show_voided=True,
        )
        assert any(r.status == "VOID" for r in page.rows)

    def test_paid_filter(self, db, seeded_ar_ap):
        co_a, _co_b = seeded_ar_ap
        page = arap.compute_payables_page(
            db, company_id=co_a.id, paid_filter="Open",
        )
        assert all(r.status == "Open" for r in page.rows)

    def test_app_shim_matches_service(self, db, seeded_ar_ap):
        co_a, _co_b = seeded_ar_ap
        sys.modules["streamlit"].session_state["active_company_id"] = co_a.id
        app_page = erp_app.compute_payables_page(
            db, search_keyword=None, vendor_filter="all", paid_filter="all", show_voided=False,
        )
        svc_page = arap.compute_payables_page(
            db, company_id=co_a.id,
        )
        assert app_page.rows == svc_page.rows


class TestCompanyIsolation:
    def test_receivables_scoped(self, db, seeded_ar_ap):
        co_a, co_b = seeded_ar_ap
        page_a = arap.compute_receivables_page(db, company_id=co_a.id)
        page_b = arap.compute_receivables_page(db, company_id=co_b.id)
        assert len(page_a.rows) == 2
        assert len(page_b.rows) == 1
        assert page_b.rows[0].customer_name == "Other Co"


class TestReadOnly:
    def test_no_jes_or_bank_txns_created(self, db, seeded_ar_ap):
        co_a, _co_b = seeded_ar_ap
        je_before = db.query(models.JournalEntry).count()
        bt_before = db.query(models.BankTransaction).count()
        arap.compute_receivables_page(db, company_id=co_a.id)
        arap.compute_payables_page(db, company_id=co_a.id)
        assert db.query(models.JournalEntry).count() == je_before
        assert db.query(models.BankTransaction).count() == bt_before


class TestPayableBalanceShim:
    def test_app_payable_balance_matches_service(self, db, seeded_ar_ap):
        co_a, _co_b = seeded_ar_ap
        payable = (
            db.query(models.Payable)
            .filter_by(company_id=co_a.id, paid=False, is_void=False)
            .first()
        )
        assert erp_app._payable_balance(payable) == arap.payable_balance(payable)
