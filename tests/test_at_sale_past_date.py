"""Regression — Add Transaction sales must persist the selected date on Sale + JE."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
    sys.modules["streamlit"].session_state = {}

import app as erp
import models
from db import Base
from registry.coa_seed import ensure_accounts_for_company

PAST = datetime.date(2026, 3, 15)


@pytest.fixture(autouse=True)
def clear_session():
    erp.st.session_state.clear()
    yield
    erp.st.session_state.clear()


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        erp._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as session:
        yield session


def _setup_company(db):
    co = models.Company(
        name="Past Date Co",
        slug="past_date_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()
    erp.st.session_state["active_company_id"] = co.id
    for code, name, atype, ccy in (
        ("1000", "Cash", "Asset", "TRY"),
        ("4000", "Sales Revenue", "Income", None),
        ("1100", "Accounts Receivable", "Asset", None),
        ("1010", "Bank", "Asset", None),
    ):
        db.add(
            models.ChartOfAccounts(
                account_code=code,
                account_name=name,
                account_type=atype,
                currency=ccy,
                company_id=co.id,
                is_active=True,
            )
        )
    ensure_accounts_for_company(db, co.id)
    db.add(
        models.BankAccount(
            name="Main Bank",
            currency="TRY",
            company_id=co.id,
            is_active=True,
            balance=0.0,
            kind="bank",
        )
    )
    db.commit()
    return co


def _submit_sale(db, *, pm: str, extra_state: dict | None = None):
    state = {
        "at_type_idx": 0,
        "at_pm": pm,
        "at_amount_display": "100",
        "at_currency": "TRY",
        "at_notes_field": "",
        "at_cust": "Walk-in Customer",
    }
    if extra_state:
        state.update(extra_state)
    erp.st.session_state.update(state)
    if state.get("at_pm") == "Credit" and state.get("at_cust") not in (None, "", "Walk-in Customer"):
        cust = (
            db.query(models.Customer)
            .filter_by(name=state["at_cust"], is_active=True)
            .first()
        )
        if cust is None:
            db.add(
                models.Customer(
                    name=state["at_cust"],
                    is_active=True,
                    company_id=erp.st.session_state.get("active_company_id"),
                )
            )
            db.commit()
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=db.query(models.BankAccount).all(),
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )


def _assert_sale_and_je_dates(
    db,
    *,
    sale_type: str,
    ref_type: str,
    expected: datetime.date,
):
    sale = (
        db.query(models.Sale)
        .filter_by(sale_type=sale_type, is_void=False)
        .order_by(models.Sale.id.desc())
        .first()
    )
    je = (
        db.query(models.JournalEntry)
        .filter_by(reference_type=ref_type, reference_id=sale.id)
        .one()
    )
    assert sale.date == expected
    assert je.entry_date == expected


@pytest.mark.parametrize(
    "pm,ref_type,extra",
    [
        (
            "Cash",
            "CashSale",
            {
                "at_date_text": "15.03.2026",
                "_user_date_format": "DD.MM.YYYY",
                "at_date": datetime.date.today(),
                "at_date_follows_today": True,
            },
        ),
        (
            "Card",
            "CardSale",
            {
                "at_date_text": "15.03.2026",
                "_user_date_format": "DD.MM.YYYY",
                "at_date": datetime.date.today(),
                "at_date_follows_today": True,
                "at_card_bank_acct": "Main Bank",
            },
        ),
        (
            "Credit",
            "CreditSale",
            {
                "at_date_text": "15.03.2026",
                "_user_date_format": "DD.MM.YYYY",
                "at_date": datetime.date.today(),
                "at_date_follows_today": True,
                "at_cust": "Acme Corp",
            },
        ),
    ],
)
def test_desktop_typed_past_date_persists_on_sale_and_je(db, pm, ref_type, extra):
    _setup_company(db)
    _submit_sale(db, pm=pm, extra_state=extra)
    _assert_sale_and_je_dates(db, sale_type=pm, ref_type=ref_type, expected=PAST)
    assert erp.st.session_state.get("at_date_follows_today") is False


def test_explicit_backdated_at_date_wins_over_stale_today_text(db):
    """Mobile/custom pick stored in at_date must not lose to stale today text."""
    _setup_company(db)
    today_text = erp._format_at_display_date(datetime.date.today())
    _submit_sale(
        db,
        pm="Cash",
        extra_state={
            "at_date": PAST,
            "at_date_follows_today": False,
            "at_date_text": today_text,
            "_user_date_format": "DD.MM.YYYY",
        },
    )
    _assert_sale_and_je_dates(db, sale_type="Cash", ref_type="CashSale", expected=PAST)


def test_mobile_backdated_at_date_persists_on_sale_and_je(db):
    _setup_company(db)
    _submit_sale(
        db,
        pm="Cash",
        extra_state={
            "_erp_mobile_ui": True,
            "at_date": PAST,
            "at_date_follows_today": False,
            "at_date_text": "stale-desktop-text",
        },
    )
    _assert_sale_and_je_dates(db, sale_type="Cash", ref_type="CashSale", expected=PAST)


def test_default_today_when_no_date_selected(db):
    _setup_company(db)
    today = datetime.date.today()
    _submit_sale(
        db,
        pm="Cash",
        extra_state={
            "at_date": today,
            "at_date_follows_today": True,
            "at_date_text": "",
        },
    )
    _assert_sale_and_je_dates(db, sale_type="Cash", ref_type="CashSale", expected=today)


def test_resolve_entry_date_does_not_mutate_widget_key(monkeypatch):
    state = {
        "_user_date_format": "DD.MM.YYYY",
        "at_date_text": "15032026",
        "at_date": datetime.date(2020, 1, 1),
        "at_date_follows_today": True,
    }
    monkeypatch.setattr(erp.st, "session_state", state)
    resolved = erp._at_resolve_entry_date()
    assert resolved == PAST
    assert state["at_date_text"] == "15032026"
    assert state["at_date"] == PAST
    erp._at_apply_deferred_date_text_sync()
    assert state["at_date_text"] == "15.03.2026"
