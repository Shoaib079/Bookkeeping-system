"""FASTAPI-P0.2-C — ledger read service contract tests."""

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
from services import read_ledger as rl
from services.money import line_money

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


def _company(db, name="Acme", slug="co1"):
    c = models.Company(
        name=name,
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(c)
    db.flush()
    return c


def _account(db, company_id, code, name, acct_type):
    a = models.ChartOfAccounts(
        account_code=code,
        account_name=name,
        account_type=acct_type,
        is_active=True,
        balance=0.0,
        company_id=company_id,
    )
    db.add(a)
    db.flush()
    return a


def _journal_entry(
    db,
    company_id,
    lines,
    *,
    date=datetime.date(2026, 1, 15),
    description="Test JE",
    reference_type="Sale",
    reference_id=1,
):
    je = models.JournalEntry(
        entry_date=date,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        company_id=company_id,
    )
    db.add(je)
    db.flush()
    for account_id, debit, credit in lines:
        db.add(
            models.JournalEntryLine(
                journal_entry_id=je.id,
                account_id=account_id,
                debit=debit,
                credit=credit,
                company_id=company_id,
            )
        )
    db.flush()
    return je


def _set_company(company_id: int):
    sys.modules["streamlit"].session_state["active_company_id"] = company_id


def _counts(db):
    return (
        db.query(models.JournalEntry).count(),
        db.query(models.BankTransaction).count(),
    )


def _legacy_compute_ledger(
    db,
    company_id,
    account,
    *,
    start_date=None,
    end_date=None,
    search_keyword=None,
):
    """Inline characterization of render_general_ledger compute."""
    lines = (
        db.query(models.JournalEntryLine)
        .join(
            models.JournalEntry,
            models.JournalEntry.id == models.JournalEntryLine.journal_entry_id,
        )
        .filter(
            models.JournalEntryLine.account_id == account.id,
            models.JournalEntry.company_id == company_id,
        )
        .order_by(models.JournalEntry.entry_date, models.JournalEntry.id)
        .all()
    )

    def _delta(line):
        if account.account_type in ["Asset", "Expense"]:
            return line_money(line.debit) - line_money(line.credit)
        return line_money(line.credit) - line_money(line.debit)

    opening = 0.0
    if start_date is not None:
        for line in lines:
            entry = db.get(models.JournalEntry, line.journal_entry_id)
            if entry and entry.entry_date < start_date:
                opening += _delta(line)

    data = []
    running = opening
    for line in lines:
        entry = db.get(models.JournalEntry, line.journal_entry_id)
        if entry is None:
            continue
        if start_date is not None and entry.entry_date < start_date:
            continue
        if end_date is not None and entry.entry_date > end_date:
            continue
        if search_keyword:
            needle = search_keyword.casefold()
            hay = f"{entry.description or ''} {entry.reference_type or ''}".casefold()
            if needle not in hay:
                continue
        running += _delta(line)
        data.append({
            "date": entry.entry_date,
            "reference": entry.reference_type,
            "description": entry.description,
            "debit": line_money(line.debit),
            "credit": line_money(line.credit),
            "running_balance": running,
            "journal_entry_id": entry.id,
            "journal_entry_line_id": line.id,
        })

    return opening, data


@pytest.fixture()
def seeded_ledger(db):
    co_a = _company(db, "Alpha", "alpha")
    co_b = _company(db, "Beta", "beta")
    cash_a = _account(db, co_a.id, "1000", "Cash", "Asset")
    income_a = _account(db, co_a.id, "4000", "Sales", "Income")
    cash_b = _account(db, co_b.id, "1000", "Cash", "Asset")
    income_b = _account(db, co_b.id, "4000", "Sales B", "Income")

    _journal_entry(
        db, co_a.id,
        [(cash_a.id, 100.0, 0.0), (income_a.id, 0.0, 100.0)],
        date=datetime.date(2026, 1, 10),
        description="January cash sale",
        reference_type="Sale",
        reference_id=1,
    )
    _journal_entry(
        db, co_a.id,
        [(cash_a.id, 50.0, 0.0), (income_a.id, 0.0, 50.0)],
        date=datetime.date(2026, 1, 10),
        description="Second sale same day",
        reference_type="Sale",
        reference_id=2,
    )
    _journal_entry(
        db, co_a.id,
        [(cash_a.id, 0.0, 30.0), (income_a.id, 30.0, 0.0)],
        date=datetime.date(2026, 2, 1),
        description="February refund",
        reference_type="Expense",
        reference_id=3,
    )
    _journal_entry(
        db, co_b.id,
        [(cash_b.id, 999.0, 0.0), (income_b.id, 0.0, 999.0)],
        date=datetime.date(2026, 1, 15),
        description="Other company",
        reference_type="Sale",
        reference_id=4,
    )
    db.commit()
    return co_a, co_b, cash_a, income_a


def _row_dict(row: rl.LedgerRow) -> dict:
    return {
        "date": row.date,
        "reference": row.reference,
        "description": row.description,
        "debit": row.debit,
        "credit": row.credit,
        "running_balance": row.running_balance,
        "journal_entry_id": row.journal_entry_id,
        "journal_entry_line_id": row.journal_entry_line_id,
    }


class TestLedgerMatchesLegacy:
    def test_matches_legacy_full_ledger(self, db, seeded_ledger):
        co_a, _co_b, cash_a, _income_a = seeded_ledger
        opening, legacy = _legacy_compute_ledger(db, co_a.id, cash_a)
        page = rl.compute_ledger_page(
            db, company_id=co_a.id, account_id=cash_a.id,
        )

        assert page.opening_balance == pytest.approx(opening)
        assert page.row_count == len(legacy)
        assert [_row_dict(r) for r in page.rows] == legacy
        assert page.closing_balance == pytest.approx(legacy[-1]["running_balance"])
        assert page.current_balance == pytest.approx(120.0)

    def test_matches_app_shim(self, db, seeded_ledger):
        co_a, _co_b, cash_a, _income_a = seeded_ledger
        _set_company(co_a.id)

        app_page = erp_app.compute_general_ledger_page(db, cash_a.id)
        svc_page = rl.compute_ledger_page(
            db, company_id=co_a.id, account_id=cash_a.id,
        )
        assert app_page == svc_page


class TestRunningBalance:
    def test_asset_debit_increases_running_balance(self, db, seeded_ledger):
        co_a, _co_b, cash_a, _income_a = seeded_ledger
        page = rl.compute_ledger_page(
            db, company_id=co_a.id, account_id=cash_a.id,
        )
        assert [r.running_balance for r in page.rows] == pytest.approx([100.0, 150.0, 120.0])


class TestOrdering:
    def test_same_date_ordered_by_journal_entry_id(self, db, seeded_ledger):
        co_a, _co_b, cash_a, _income_a = seeded_ledger
        page = rl.compute_ledger_page(
            db, company_id=co_a.id, account_id=cash_a.id,
        )
        jan_rows = [r for r in page.rows if r.date == datetime.date(2026, 1, 10)]
        assert len(jan_rows) == 2
        assert jan_rows[0].journal_entry_id < jan_rows[1].journal_entry_id
        assert jan_rows[0].running_balance == pytest.approx(100.0)
        assert jan_rows[1].running_balance == pytest.approx(150.0)


class TestSearch:
    def test_keyword_filters_description(self, db, seeded_ledger):
        co_a, _co_b, cash_a, _income_a = seeded_ledger
        page = rl.compute_ledger_page(
            db,
            company_id=co_a.id,
            account_id=cash_a.id,
            search_keyword="refund",
        )
        assert page.row_count == 1
        assert page.rows[0].description == "February refund"


class TestDateFilters:
    def test_period_opening_and_closing(self, db, seeded_ledger):
        co_a, _co_b, cash_a, _income_a = seeded_ledger
        opening, legacy = _legacy_compute_ledger(
            db,
            co_a.id,
            cash_a,
            start_date=datetime.date(2026, 2, 1),
            end_date=datetime.date(2026, 2, 28),
        )
        page = rl.compute_ledger_page(
            db,
            company_id=co_a.id,
            account_id=cash_a.id,
            start_date=datetime.date(2026, 2, 1),
            end_date=datetime.date(2026, 2, 28),
        )
        assert page.opening_balance == pytest.approx(opening)
        assert page.opening_balance == pytest.approx(150.0)
        assert [_row_dict(r) for r in page.rows] == legacy
        assert page.closing_balance == pytest.approx(120.0)


class TestCompanyIsolation:
    def test_other_company_jes_excluded(self, db, seeded_ledger):
        co_a, co_b, cash_a, _income_a = seeded_ledger
        page_a = rl.compute_ledger_page(
            db, company_id=co_a.id, account_id=cash_a.id,
        )
        cash_b = (
            db.query(models.ChartOfAccounts)
            .filter_by(company_id=co_b.id, account_name="Cash")
            .one()
        )
        page_b = rl.compute_ledger_page(
            db, company_id=co_b.id, account_id=cash_b.id,
        )
        assert page_a.closing_balance == pytest.approx(120.0)
        assert page_b.closing_balance == pytest.approx(999.0)


class TestReadOnly:
    def test_ledger_reads_create_no_rows(self, db, seeded_ledger):
        co_a, _co_b, cash_a, _income_a = seeded_ledger
        je_before, bt_before = _counts(db)

        rl.compute_ledger_page(
            db, company_id=co_a.id, account_id=cash_a.id,
        )

        je_after, bt_after = _counts(db)
        assert je_after == je_before
        assert bt_after == bt_before
