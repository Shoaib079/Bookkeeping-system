"""POSTING-SERVICE-01 PS-P2a — sales posting + get_account_by_name extraction proof."""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from registry.coa_seed import seed_chart_of_accounts_for_company
from registry.service import set_setting
from services import posting

ROOT = Path(__file__).resolve().parents[1]
POST_DATE = datetime.date(2026, 3, 15)

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

import app

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(app._DEV_USER)
    sys.modules["streamlit"].session_state["auth_expires"] = (
        datetime.datetime.now() + datetime.timedelta(hours=24)
    )


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    _seed_dev_auth_user()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        co = models.Company(
            name="PS-P2a Co",
            slug="ps_p2a_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        seed_chart_of_accounts_for_company(s, co.id)
        yield s, co.id


def _entries_for(session, ref_type, ref_id):
    return (
        session.query(models.JournalEntry)
        .filter_by(reference_type=ref_type, reference_id=ref_id)
        .order_by(models.JournalEntry.id)
        .all()
    )


def _line_tuples(session, journal_entry_id):
    lines = (
        session.query(models.JournalEntryLine)
        .filter_by(journal_entry_id=journal_entry_id)
        .order_by(models.JournalEntryLine.id)
        .all()
    )
    return [(ln.account_id, ln.debit or 0.0, ln.credit or 0.0) for ln in lines]


def _make_sale(session, sale_type, amount, sale_id=1):
    sale = models.Sale(
        date=POST_DATE,
        invoice_number=f"INV-{sale_type}",
        customer_name="Customer",
        amount=amount,
        sale_type=sale_type,
        paid_amount=amount if sale_type != "Credit" else 0.0,
        balance=0.0 if sale_type != "Credit" else amount,
        due_date=POST_DATE,
        status="Paid" if sale_type != "Credit" else "Outstanding",
    )
    session.add(sale)
    session.flush()
    return sale


APP_SRC = (ROOT / "app.py").read_text(encoding="utf-8")


def _fn_block(name: str) -> str:
    i = APP_SRC.index(f"def {name}(")
    j = APP_SRC.index("\ndef ", i + 10)
    return APP_SRC[i:j]


# ── 1. Shim contracts ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "fn_name,service_call",
    [
        ("get_account_by_name", "posting_service.get_account_by_name("),
        ("post_cash_sale", "posting_service.post_cash_sale("),
        ("post_card_sale", "posting_service.post_card_sale("),
        ("post_credit_sale", "posting_service.post_credit_sale("),
        ("_card_settlement_on", "posting_service.card_settlement_on("),
    ],
)
def test_app_sales_family_shims_delegate(fn_name, service_call):
    block = _fn_block(fn_name)
    assert service_call in block
    if fn_name == "_card_settlement_on":
        assert "_current_company_id()" in block
    else:
        assert "company_id=_current_company_id()" in block


def test_app_sales_shims_have_no_kernel_leftovers():
    for fn_name, leftover in (
        ("get_account_by_name", "ChartOfAccounts.company_id"),
        ("post_cash_sale", "create_journal_entry("),
        ("post_card_sale", "Card Sales Clearing"),
        ("post_credit_sale", '"Accounts Receivable"'),
    ):
        block = _fn_block(fn_name)
        assert leftover not in block, f"{fn_name} still contains kernel logic: {leftover}"


# ── 2. get_account_by_name service behaviour ─────────────────────────────────


def test_service_get_account_by_name_currency_suffix_wins(session):
    db, cid = session
    base = posting.get_account_by_name(db, "Cash", company_id=cid)
    suffixed = posting.get_account_by_name(db, "Cash", currency="USD", company_id=cid)
    assert suffixed is not None
    assert suffixed.account_name == "Cash USD"
    assert suffixed.id != base.id


def test_service_get_account_by_name_currency_column_fallback(session):
    db, cid = session
    acct = models.ChartOfAccounts(
        account_code="1999",
        account_name="Petty Cash",
        account_type="Asset",
        currency="EUR",
        is_active=True,
        company_id=cid,
    )
    db.add(acct)
    db.commit()
    found = posting.get_account_by_name(db, "Petty Cash", currency="EUR", company_id=cid)
    assert found is not None
    assert found.id == acct.id


def test_service_get_account_by_name_name_fallback_without_currency(session):
    db, cid = session
    found = posting.get_account_by_name(db, "Sales Revenue", company_id=cid)
    assert found is not None
    assert found.account_name == "Sales Revenue"


def test_service_get_account_by_name_company_scoped(session):
    db, cid = session
    other = models.Company(
        name="Other Co",
        slug="other_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(other)
    db.flush()
    seed_chart_of_accounts_for_company(db, other.id)
    mine = posting.get_account_by_name(db, "Cash", company_id=cid)
    theirs = posting.get_account_by_name(db, "Cash", company_id=other.id)
    assert mine is not None and theirs is not None
    assert mine.company_id == cid
    assert theirs.company_id == other.id
    assert mine.id != theirs.id


# ── 3. Sales trio — service direct ───────────────────────────────────────────


def test_service_post_cash_sale(session):
    db, cid = session
    sale = _make_sale(db, "Cash", 250.0)
    db.commit()
    posting.post_cash_sale(db, sale.id, 250.0, POST_DATE, company_id=cid)
    entries = _entries_for(db, "CashSale", sale.id)
    assert len(entries) == 1
    je = entries[0]
    assert je.description == f"Cash Sale (ID: {sale.id})"
    cash = posting.get_account_by_name(db, "Cash", company_id=cid)
    revenue = posting.get_account_by_name(db, "Sales Revenue", company_id=cid)
    assert _line_tuples(db, je.id) == [
        (cash.id, 250.0, 0.0),
        (revenue.id, 0.0, 250.0),
    ]


def test_service_post_card_sale_settlement_off_posts_bank(session):
    db, cid = session
    sale = _make_sale(db, "Card", 180.0)
    db.commit()
    assert posting.card_settlement_on(db, cid) is False
    posting.post_card_sale(db, sale.id, 180.0, POST_DATE, company_id=cid)
    entries = _entries_for(db, "CardSale", sale.id)
    assert len(entries) == 1
    bank = posting.get_account_by_name(db, "Bank", company_id=cid)
    revenue = posting.get_account_by_name(db, "Sales Revenue", company_id=cid)
    assert _line_tuples(db, entries[0].id) == [
        (bank.id, 180.0, 0.0),
        (revenue.id, 0.0, 180.0),
    ]


def test_service_post_card_sale_settlement_on_posts_clearing(session):
    db, cid = session
    set_setting(db, "banking.card_settlement_enabled", True, company_id=cid)
    db.commit()
    sale = _make_sale(db, "Card", 180.0)
    db.commit()
    assert posting.card_settlement_on(db, cid) is True
    posting.post_card_sale(db, sale.id, 180.0, POST_DATE, company_id=cid)
    entries = _entries_for(db, "CardSale", sale.id)
    clearing = posting.get_account_by_name(db, "Card Sales Clearing", company_id=cid)
    revenue = posting.get_account_by_name(db, "Sales Revenue", company_id=cid)
    assert _line_tuples(db, entries[0].id) == [
        (clearing.id, 180.0, 0.0),
        (revenue.id, 0.0, 180.0),
    ]


def test_service_post_credit_sale(session):
    db, cid = session
    sale = _make_sale(db, "Credit", 320.0)
    db.commit()
    posting.post_credit_sale(db, sale.id, 320.0, POST_DATE, company_id=cid)
    entries = _entries_for(db, "CreditSale", sale.id)
    assert len(entries) == 1
    ar = posting.get_account_by_name(db, "Accounts Receivable", company_id=cid)
    revenue = posting.get_account_by_name(db, "Sales Revenue", company_id=cid)
    assert _line_tuples(db, entries[0].id) == [
        (ar.id, 320.0, 0.0),
        (revenue.id, 0.0, 320.0),
    ]


# ── 4. Shim vs service equivalence ───────────────────────────────────────────


def test_shim_post_cash_sale_matches_service(session):
    db, cid = session
    sale = _make_sale(db, "Cash", 99.0)
    db.commit()
    app.post_cash_sale(db, sale.id, 99.0, POST_DATE)
    shim_lines = _line_tuples(db, _entries_for(db, "CashSale", sale.id)[0].id)

    sale2 = _make_sale(db, "Cash", 99.0)
    sale2.invoice_number = "INV-Cash-2"
    db.commit()
    posting.post_cash_sale(db, sale2.id, 99.0, POST_DATE, company_id=cid)
    svc_lines = _line_tuples(db, _entries_for(db, "CashSale", sale2.id)[0].id)
    assert shim_lines == svc_lines


def test_shim_get_account_by_name_matches_service(session):
    db, cid = session
    assert app.get_account_by_name(db, "Bank").id == posting.get_account_by_name(
        db, "Bank", company_id=cid
    ).id


def test_card_settlement_shim_matches_service(session):
    db, cid = session
    set_setting(db, "banking.card_settlement_enabled", True, company_id=cid)
    db.commit()
    assert app._card_settlement_on(db) == posting.card_settlement_on(db, cid)


# ── 5. Import purity (PS-P2a additions) ──────────────────────────────────────


def test_posting_service_still_has_no_streamlit_or_app():
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
        assert re.search(pattern, src, re.M) is None
    assert "def get_account_by_name(" in src
    assert "def card_settlement_on(" in src
    assert "def post_cash_sale(" in src
