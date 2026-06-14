"""POSTING-SERVICE-01 PS-P1 — kernel extraction proof.

Proves behaviour is unchanged after moving create_journal_entry + the
period/year-end guard into services/posting.py behind app.py shims:

1. Service functional tests (no app import) — the kernel through the service
   with explicit company_id, asserting the exact PS-P0-pinned behaviour.
2. Shim contracts — app.py delegates, signatures unchanged, ambient company
   resolution preserved.
3. Import purity — the service touches neither streamlit nor app.

The PS-P0 characterization suite re-running unchanged through the shims is
the primary equivalence proof; these tests add the service-direct angle.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from db import Base
from services import posting

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        yield s


def _accounts(session):
    a = models.ChartOfAccounts(account_code="1000", account_name="Cash",
                               account_type="Asset", balance=0.0, is_active=True,
                               company_id=1)
    b = models.ChartOfAccounts(account_code="4000", account_name="Sales Revenue",
                               account_type="Income", balance=0.0, is_active=True,
                               company_id=1)
    session.add_all([a, b])
    session.commit()
    return a, b


# ── 1. Service functional behaviour (explicit company_id) ────────────────────


def test_service_balanced_entry_persists_and_returns_orm(session):
    a, b = _accounts(session)
    entry = posting.create_journal_entry(
        session, datetime.date(2026, 6, 1), "Cash Sale (ID: 1)", "CashSale", 1,
        [(a.id, 100.0, 0), (b.id, 0, 100.0)], company_id=1,
    )
    assert isinstance(entry, models.JournalEntry)
    assert entry.id is not None
    assert entry.company_id == 1
    lines = (
        session.query(models.JournalEntryLine)
        .filter_by(journal_entry_id=entry.id)
        .order_by(models.JournalEntryLine.id)
        .all()
    )
    assert [(l.account_id, l.debit, l.credit, l.company_id) for l in lines] == [
        (a.id, 100.0, 0.0, 1),
        (b.id, 0.0, 100.0, 1),
    ]
    # commit happened inside the kernel (PS-P1 verbatim behaviour)
    session.rollback()
    assert session.get(models.JournalEntry, entry.id) is not None


def test_service_unbalanced_raises_exact_message_and_persists_nothing(session):
    a, b = _accounts(session)
    with pytest.raises(ValueError) as exc:
        posting.create_journal_entry(
            session, datetime.date(2026, 6, 1), "bad", "Expense", 1,
            [(a.id, 100.0, 0), (b.id, 0, 90.0)], company_id=1,
        )
    assert str(exc.value) == (
        "Journal entry is not balanced: Debit $100.00 vs Credit $90.00"
    )
    assert session.query(models.JournalEntry).count() == 0
    assert session.query(models.JournalEntryLine).count() == 0


def test_service_closed_period_blocks_with_exact_message(session):
    a, b = _accounts(session)
    session.add(models.FiscalPeriod(
        name="May 2026", start_date=datetime.date(2026, 5, 1),
        end_date=datetime.date(2026, 5, 31), is_closed=True, company_id=1,
    ))
    session.commit()
    with pytest.raises(ValueError) as exc:
        posting.create_journal_entry(
            session, datetime.date(2026, 5, 15), "late", "Expense", 1,
            [(a.id, 10.0, 0), (b.id, 0, 10.0)], company_id=1,
        )
    assert str(exc.value) == (
        "Period 'May 2026' (2026-05-01 – 2026-05-31) is closed. "
        "Cannot post entries to 2026-05-15."
    )


def test_service_period_close_reference_type_exempt(session):
    a, b = _accounts(session)
    session.add(models.FiscalPeriod(
        name="May 2026", start_date=datetime.date(2026, 5, 1),
        end_date=datetime.date(2026, 5, 31), is_closed=True, company_id=1,
    ))
    session.commit()
    entry = posting.create_journal_entry(
        session, datetime.date(2026, 5, 31), "close", "PeriodClose", 1,
        [(a.id, 10.0, 0), (b.id, 0, 10.0)], company_id=1,
    )
    assert entry.id is not None


def test_service_guard_is_company_scoped(session):
    """Company 1's closed period must not block company 2 — and None scopes off."""
    session.add(models.FiscalPeriod(
        name="May 2026", start_date=datetime.date(2026, 5, 1),
        end_date=datetime.date(2026, 5, 31), is_closed=True, company_id=1,
    ))
    session.commit()
    d = datetime.date(2026, 5, 15)
    assert posting.entry_date_posting_blocked(session, d, company_id=1) is not None
    assert posting.entry_date_posting_blocked(session, d, company_id=2) is None
    # company_id=None — unscoped legacy behaviour: any closed period blocks
    assert posting.entry_date_posting_blocked(session, d, company_id=None) is not None


def test_service_fx_amount_native_rounding(session):
    a, b = _accounts(session)
    entry = posting.create_journal_entry(
        session, datetime.date(2026, 6, 1), "fx", "Expense", 1,
        [(a.id, 33.33, 0), (b.id, 0, 33.33)],
        currency="USD", fx_rate=1.23456, company_id=1,
    )
    lines = session.query(models.JournalEntryLine).filter_by(
        journal_entry_id=entry.id).order_by(models.JournalEntryLine.id).all()
    assert lines[0].amount_native == round(33.33 * 1.23456, 4)
    assert lines[1].amount_native == round(-33.33 * 1.23456, 4)


def test_service_no_currency_means_no_amount_native(session):
    a, b = _accounts(session)
    entry = posting.create_journal_entry(
        session, datetime.date(2026, 6, 1), "plain", "Expense", 1,
        [(a.id, 10.0, 0), (b.id, 0, 10.0)], company_id=1,
    )
    for line in session.query(models.JournalEntryLine).filter_by(
            journal_entry_id=entry.id):
        assert line.amount_native is None
        assert line.currency is None


def test_service_does_not_touch_balance_cache(session):
    a, b = _accounts(session)
    posting.create_journal_entry(
        session, datetime.date(2026, 6, 1), "x", "CashSale", 1,
        [(a.id, 50.0, 0), (b.id, 0, 50.0)], company_id=1,
    )
    session.refresh(a); session.refresh(b)
    assert a.balance == 0.0 and b.balance == 0.0


# ── 2. Shim contracts (source-level — app.py stays un-imported) ──────────────

APP_SRC = (ROOT / "app.py").read_text(encoding="utf-8")


def _fn_block(name: str) -> str:
    i = APP_SRC.index(f"def {name}(")
    j = APP_SRC.index("\ndef ", i + 10)
    return APP_SRC[i:j]


def test_app_create_journal_entry_is_a_pure_shim():
    block = _fn_block("create_journal_entry")
    assert "posting_service.create_journal_entry(" in block
    assert "_current_company_id()" in block, "ambient company resolution must stay in the shim"
    # no kernel logic left behind
    for leftover in ("JournalEntry(", "total_debit", "session.flush()", "session.commit()"):
        assert leftover not in block, f"kernel logic remained in shim: {leftover}"
    # signature: legacy positional args + optional explicit company_id (P0.5c)
    assert re.search(
        r"def create_journal_entry\(session, entry_date, description, reference_type, "
        r"reference_id, lines,\n\s+currency: str = None, fx_rate: float = 1\.0, "
        r"\*, company_id: int \| None = None\):",
        APP_SRC,
    )


def test_app_period_guard_is_a_pure_shim():
    block = _fn_block("_entry_date_posting_blocked")
    assert "posting_service.entry_date_posting_blocked(" in block
    assert "_current_company_id()" in block
    assert "FiscalPeriod" not in block and "YearEndClose" not in block


def test_shim_import_present_once():
    assert APP_SRC.count("from services import posting as posting_service") == 1


# ── 3. Import purity ──────────────────────────────────────────────────────────


def test_posting_service_import_purity():
    src = (ROOT / "services" / "posting.py").read_text(encoding="utf-8")
    forbidden = [
        r"^\s*import streamlit\b",
        r"^\s*from streamlit\b",
        r"\bst\.session_state\b",
        r"\b_current_company_id\b",
        r"^\s*from app import\b",
        r"^\s*import app\b",
    ]
    for pattern in forbidden:
        assert re.search(pattern, src, re.M) is None, (
            f"forbidden in services/posting.py: {pattern}"
        )


def test_kernel_message_strings_match_ps_p0_pins():
    """The characterization suite pins these strings; keep the service identical."""
    src = (ROOT / "services" / "posting.py").read_text(encoding="utf-8")
    assert "is closed. \"\n" in src or "is closed. " in src
    assert "Journal entry is not balanced: Debit ${total_debit:.2f} vs Credit ${total_credit:.2f}" in src
    assert "Cannot post entries to {entry_date}." in src
