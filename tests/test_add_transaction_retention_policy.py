"""RETENTION-01 — Add Transaction post-save keeps only section + date."""

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
from registry.categories_seed import seed_default_categories_for_company
from registry.coa_seed import seed_chart_of_accounts_for_company

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


def _setup(db, *, cc_card: bool = False):
    co = models.Company(
        name="Retention Co",
        slug="retention_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()
    erp.st.session_state["active_company_id"] = co.id
    seed_chart_of_accounts_for_company(db, co.id)
    seed_default_categories_for_company(db, co.id)
    db.add(
        models.BankAccount(
            name="Main Bank",
            currency="TRY",
            company_id=co.id,
            is_active=True,
            balance=1000.0,
            kind="bank",
        )
    )
    if cc_card:
        db.add(
            models.BankAccount(
                name="Company Visa",
                currency="TRY",
                company_id=co.id,
                is_active=True,
                balance=0.0,
                kind="credit_card",
            )
        )
    db.commit()
    return co


def _filled_state(**extra) -> dict:
    base = {
        "at_type_idx": 1,
        "mob_at_tab": 1,
        "at_date": PAST,
        "at_date_follows_today": False,
        "at_amount_display": "250",
        "at_notes_field": "keep clearing me",
        "at_currency": "USD",
        "at_pm": erp._COMPANY_CC_METHOD,
        "at_cc_card_id": 99,
        "mob_at_cc_card_id": 99,
        "at_bank_pay_acct": "Main Bank",
        "mob_at_bank_pay_sel": "Main Bank",
        "at_card_bank_acct": "Main Bank",
        "mob_at_card_bank_sel": "Main Bank",
        "at_vendor": "Old Vendor",
        "at_last_vendor": "Old Vendor",
        "mob_at_vendor_sel": "Old Vendor",
        "at_cust": "Old Customer",
        "at_cust_sel": "Old Customer",
        "at_payable_id": 5,
        "mob_at_payable_sel": "PAY#5",
        "at_inv": "INV-OLD",
        "mob_at_inv_sel": "INV-OLD",
        "mob_at_cat_id": 1,
        "mob_at_subcat_id": 2,
        "at_cat": "Utilities",
        "at_subcat": "Electricity",
        "at_last_cat_id": 1,
    }
    base.update(extra)
    return base


def _apply_retention(db, txn_type: str, *, currency_default: str = "TRY"):
    erp._at_clear_post_save_transient_fields(
        db, txn_type=txn_type, currency_default=currency_default
    )
    erp._at_refresh_date_text_display()
    erp._mob_at_ensure_defaults(db, txn_type, currency_default, [])


def test_post_save_clear_does_not_write_pm_or_currency(monkeypatch):
    writes: list[str] = []

    class _TrackingState(dict):
        def __setitem__(self, key, value):
            if key in ("at_pm", "at_currency"):
                writes.append(key)
            super().__setitem__(key, value)

    state = _TrackingState(_filled_state())
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_clear_post_save_transient_fields(
        MagicMock(), txn_type="Expense", currency_default="TRY"
    )
    assert writes == []
    assert "at_pm" not in state
    assert "at_currency" not in state


def test_cc_expense_save_resets_payment_and_card_state(db, monkeypatch):
    _setup(db, cc_card=True)
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: True)
    erp.st.session_state.update(_filled_state(at_type_idx=1, mob_at_tab=1))
    _apply_retention(db, "Expense")

    assert erp.st.session_state["at_type_idx"] == 1
    assert erp.st.session_state["at_date"] == PAST
    assert "at_pm" not in erp.st.session_state
    assert "at_cc_card_id" not in erp.st.session_state
    assert "mob_at_cc_card_id" not in erp.st.session_state
    assert "at_amount_display" not in erp.st.session_state
    assert erp.st.session_state.get("at_notes_field") == ""
    assert "mob_at_cat_id" not in erp.st.session_state

    erp.st.session_state["at_pm"] = "Cash"
    ctx = erp._at_gather_submit_fields(db, "Expense", "TRY", [], [], [])
    assert ctx["at_payment_method"] == "Cash"
    assert ctx["at_subcat_name"] is None


def test_next_cash_expense_ignores_hidden_cc_card_id(db, monkeypatch):
    _setup(db, cc_card=True)
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: True)
    erp.st.session_state.update(
        _filled_state(
            at_pm="Cash",
            at_cc_card_id=42,
            mob_at_cc_card_id=42,
        )
    )
    _apply_retention(db, "Expense")
    erp.st.session_state["at_amount_display"] = "50"
    cat = (
        db.query(models.TransactionCategory)
        .filter_by(transaction_type="Expense", is_active=True)
        .first()
    )
    erp.st.session_state["mob_at_cat_id"] = cat.id
    erp.st.session_state["mob_at_subcat_id"] = (
        db.query(models.TransactionSubcategory)
        .filter_by(category_id=cat.id, is_active=True)
        .first()
        .id
    )
    cc_id = erp._resolve_submit_company_cc_card_id(
        db, "Cash", erp.st.session_state.get("at_cc_card_id")
    )
    assert cc_id is None


def test_purchase_credit_save_resets_vendor_and_payable_state(db, monkeypatch):
    _setup(db)
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: False)
    erp.st.session_state.update(
        _filled_state(
            at_type_idx=2,
            mob_at_tab=2,
            at_pm="Credit",
            at_vendor="Supplier A",
        )
    )
    _apply_retention(db, "Purchase")

    assert erp.st.session_state["at_type_idx"] == 2
    assert erp.st.session_state["at_date"] == PAST
    assert "at_pm" not in erp.st.session_state
    assert "at_vendor" not in erp.st.session_state
    assert "at_payable_id" not in erp.st.session_state
    assert "mob_at_vendor_sel" not in erp.st.session_state

    ctx = erp._at_gather_submit_fields(db, "Purchase", "TRY", [], [], [])
    assert not ctx["vendor_name_val"]


def test_credit_sale_save_resets_customer_and_payment_state(db, monkeypatch):
    _setup(db)
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: False)
    erp.st.session_state.update(
        _filled_state(
            at_type_idx=0,
            mob_at_tab=0,
            at_pm="Credit",
            at_cust="Acme Corp",
            at_cust_sel="Acme Corp",
        )
    )
    _apply_retention(db, "Sale")

    assert erp.st.session_state["at_type_idx"] == 0
    assert erp.st.session_state["at_date"] == PAST
    assert "at_pm" not in erp.st.session_state
    assert erp.st.session_state.get("at_cust") == "Walk-in Customer"
    assert "at_cust_sel" not in erp.st.session_state

    ctx = erp._at_gather_submit_fields(db, "Sale", "TRY", [], [], [])
    assert ctx["customer_name_val"] == "Walk-in Customer"


def test_retention_resets_currency_to_company_default(db, monkeypatch):
    _setup(db)
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: False)
    erp.st.session_state.update(_filled_state(at_currency="USD"))
    _apply_retention(db, "Expense", currency_default="TRY")
    assert erp.st.session_state["at_currency"] == "TRY"


def test_retention_syncs_mobile_tab_with_type(db, monkeypatch):
    _setup(db)
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: False)
    erp.st.session_state.update(
        _filled_state(at_type_idx=4, mob_at_tab=3, mob_at_more_idx=4)
    )
    _apply_retention(db, "Customer Payment")
    assert erp.st.session_state["mob_at_tab"] == 3
    assert erp.st.session_state["mob_at_more_idx"] == 4
