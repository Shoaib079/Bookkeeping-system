"""OBS-01 / ADD-TRANSACTION-FIX-01 — Add Transaction friction regression tests."""

from __future__ import annotations

import datetime
import inspect
import sys
from pathlib import Path
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

ROOT = Path(__file__).resolve().parents[1]


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


def _company(db, *, cash_gl=True, bank_gl=True):
    co = models.Company(
        name="Fix Co",
        slug="fix_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()
    erp.st.session_state["active_company_id"] = co.id
    if cash_gl:
        db.add(
            models.ChartOfAccounts(
                account_code="1000",
                account_name="Cash",
                account_type="Asset",
                currency="TRY",
                company_id=co.id,
                is_active=True,
            )
        )
    if bank_gl:
        db.add(
            models.ChartOfAccounts(
                account_code="1010",
                account_name="Bank",
                account_type="Asset",
                currency="TRY",
                company_id=co.id,
                is_active=True,
            )
        )
    db.add(
        models.ChartOfAccounts(
            account_code="5100",
            account_name="Salary Expense",
            account_type="Expense",
            company_id=co.id,
            is_active=True,
        )
    )
    db.add(
        models.ChartOfAccounts(
            account_code="1250",
            account_name="Employee Advances",
            account_type="Asset",
            company_id=co.id,
            is_active=True,
        )
    )
    db.commit()
    ensure_accounts_for_company(db, co.id)
    return co


# ── Date parsing ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2026-06-05", datetime.date(2026, 6, 5)),
        ("05.06.2026", datetime.date(2026, 6, 5)),
        ("05/06/2026", datetime.date(2026, 6, 5)),
        ("", None),
        ("not-a-date", None),
        ("32.13.2026", None),
    ],
)
def test_at_parse_date_text_formats(raw, expected):
    assert erp._at_parse_date_text(raw) == expected


def test_at_entry_date_error_invalid_only_in_manual_mode(monkeypatch):
    monkeypatch.setattr(erp.st, "session_state", {"at_date_text": "bad"})
    assert erp._at_entry_date_error() is None
    monkeypatch.setattr(
        erp.st,
        "session_state",
        {"at_date_text": "bad", "at_date_manual_entry": True},
    )
    assert erp._at_entry_date_error() is not None


def test_at_resolve_entry_date_prefers_manual_text_when_enabled(monkeypatch):
    state = {
        "at_date_manual_entry": True,
        "at_date_text": "05.06.2026",
        "at_date": datetime.date(2020, 1, 1),
        "at_date_picker": datetime.date(2020, 1, 2),
    }
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._at_resolve_entry_date() == datetime.date(2026, 6, 5)
    assert state["at_date"] == datetime.date(2026, 6, 5)


def test_at_resolve_entry_date_uses_picker_when_not_manual(monkeypatch):
    state = {
        "at_date_manual_entry": False,
        "at_date_text": "05.06.2026",
        "at_date_picker": datetime.date(2026, 3, 10),
    }
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._at_resolve_entry_date() == datetime.date(2026, 3, 10)
    assert state["at_date"] == datetime.date(2026, 3, 10)


def test_at_manual_date_toggle_syncs_picker_to_text(monkeypatch):
    state = {
        "at_date_manual_entry": True,
        "at_date_picker": datetime.date(2026, 4, 1),
        "at_date": datetime.date(2026, 4, 1),
    }
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_on_manual_date_toggle()
    assert state["at_date_text"] == "2026-04-01"
    assert state["at_date"] == datetime.date(2026, 4, 1)


def test_at_manual_date_toggle_syncs_text_to_picker(monkeypatch):
    state = {
        "at_date_manual_entry": False,
        "at_date_text": "15.05.2026",
    }
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_on_manual_date_toggle()
    assert state["at_date_picker"] == datetime.date(2026, 5, 15)
    assert state["at_date"] == datetime.date(2026, 5, 15)


def test_desktop_date_field_single_visible_control():
    src = inspect.getsource(erp._at_render_desktop_date_field)
    assert 'key="at_date_manual_entry"' in src
    assert "if st.session_state.get(\"at_date_manual_entry\"):" in src
    text_block = src.split('if st.session_state.get("at_date_manual_entry"):', 1)[1]
    calendar_block = src.split("else:", 1)[1]
    assert 'st.text_input' in text_block
    assert 'st.date_input' not in text_block.split("else:")[0]
    assert 'st.date_input' in calendar_block
    assert 'st.text_input' not in calendar_block


# ── No remembered transaction ─────────────────────────────────────────────────


def test_remember_last_pm_is_noop(monkeypatch):
    state = {}
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mob_at_remember_last_pm("Expense", "Bank")
    assert "mob_at_last_pm_expense" not in state
    assert erp._mob_at_recall_last_pm("Expense") is None


def test_remember_last_category_is_noop(monkeypatch):
    state = {}
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mob_at_remember_last_category("Expense", 5)
    assert "mob_at_last_cat_expense" not in state


def test_seed_visible_category_is_noop(monkeypatch):
    state = {}
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mob_at_seed_visible_category(None, "Expense")
    assert "mob_at_cat_id" not in state


def test_post_save_clears_category_state(monkeypatch):
    state = {
        "at_cat": "Rent",
        "at_subcat": "Office",
        "at_last_cat_id": 3,
        "mob_at_cat_id": 3,
        "mob_at_subcat_id": 7,
        "mob_at_last_cat_expense": 3,
    }
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_clear_post_save_transient_fields()
    for key in (
        "at_cat",
        "at_subcat",
        "at_last_cat_id",
        "mob_at_cat_id",
        "mob_at_subcat_id",
        "mob_at_last_cat_expense",
    ):
        assert key not in state


# ── Sale has no category ──────────────────────────────────────────────────────


def test_gather_submit_sale_ignores_expense_category(db):
    co = _company(db)
    exp_cat = models.TransactionCategory(
        transaction_type="Expense",
        name="Utilities",
        company_id=co.id,
        is_active=True,
    )
    db.add(exp_cat)
    db.commit()
    erp.st.session_state.update(
        {
            "mob_at_cat_id": exp_cat.id,
            "at_cat": "Utilities",
            "at_subcat": "Electric",
            "at_last_cat_id": exp_cat.id,
        }
    )
    ctx = erp._at_gather_submit_fields(db, "Sale", "TRY", [], [], [])
    assert ctx["at_cat_id"] is None
    assert ctx["at_subcat_name"] is None


def test_clear_category_on_type_switch():
    src = inspect.getsource(erp.render_add_transaction)
    assert "_at_clear_category_session_state()" in src


def test_desktop_sale_branch_has_no_inline_category():
    src = inspect.getsource(erp.render_add_transaction)
    sale_block = src.split('if txn_type == "Sale":', 1)[1].split('elif txn_type == "Expense":', 1)[0]
    assert "_inline_cat_row" not in sale_block
    assert "_inline_subcat_row" not in sale_block


def test_mobile_sale_has_no_category_chips():
    src = inspect.getsource(erp._render_add_transaction_mobile)
    sale_block = src.split("elif at_idx == 0:", 1)[1].split("elif at_idx == 1:", 1)[0]
    assert "_mob_at_render_quick_cat_chips" not in sale_block
    assert "sale_cat" not in sale_block


# ── Enter-to-submit form ──────────────────────────────────────────────────────


def test_desktop_at_uses_entry_form():
    src = inspect.getsource(erp.render_add_transaction)
    assert 'st.form("at_entry_form"' in src
    assert "st.form_submit_button" in src
    assert "st.form_submit_button" in src.split('st.form("at_entry_form"')[1]


def test_desktop_date_field_outside_form_for_calendar_callback():
    src = inspect.getsource(erp.render_add_transaction)
    form_pos = src.index('st.form("at_entry_form"')
    date_pos = src.index("_at_render_desktop_date_field()")
    assert date_pos < form_pos
    date_helper = inspect.getsource(erp._at_render_desktop_date_field)
    assert "on_change=_at_sync_date_from_picker" in date_helper


def test_at_resolve_entry_date_falls_back_to_picker(monkeypatch):
    picked = datetime.date(2026, 3, 15)
    monkeypatch.setattr(
        erp.st,
        "session_state",
        {"at_date_text": "", "at_date_picker": picked},
    )
    assert erp._at_resolve_entry_date() == picked


# ── Dialog / dark theme contracts ─────────────────────────────────────────────


def test_category_dialogs_use_small_st_dialog():
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    for label in ("Add Category", "Manage Category", "Add Subcategory", "Manage Subcategory"):
        assert f'@st.dialog("{label}", width="small")' in app_src


def test_portal_theme_css_covers_dialog_and_calendar():
    css = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    assert "PORTAL-THEME-01" in css
    assert '[data-testid="stDialog"]' in css
    assert "Calendar / date popup" in css


# ── Worker salary account resolution ────────────────────────────────────────────


def test_worker_payment_cash_subledger(db):
    co = _company(db)
    cash_ba = models.BankAccount(
        name="Petty Cash",
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=1000.0,
    )
    db.add(cash_ba)
    db.commit()
    ba, err = erp._bank_account_for_worker_payment(db, "Cash", currency="TRY")
    assert err is None
    assert ba is not None
    assert "cash" in ba.name.lower()


def test_worker_payment_bank_subledger(db):
    co = _company(db)
    bank_ba = models.BankAccount(
        name="Main TRY",
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=5000.0,
    )
    db.add(bank_ba)
    db.commit()
    ba, err = erp._bank_account_for_worker_payment(db, "Bank", currency="TRY")
    assert err is None
    assert ba.name == "Main TRY"


def test_worker_payment_cash_gl_only_friendly_error(db):
    co = _company(db, bank_gl=False)
    ba, err = erp._bank_account_for_worker_payment(db, "Cash", currency="TRY")
    assert ba is None
    assert err is not None
    assert "cash" in err.lower() or "Kasa" in err or "bank" in err.lower()


def test_worker_payment_missing_bank_friendly_error(db):
    co = _company(db, cash_gl=False)
    ba, err = erp._bank_account_for_worker_payment(db, "Bank", currency="TRY")
    assert ba is None
    assert err is not None


def test_worker_salary_cash_posting_succeeds(db):
    co = _company(db)
    cash_ba = models.BankAccount(
        name="Cash Drawer",
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=10000.0,
    )
    db.add(cash_ba)
    wid, err = erp.create_worker(db, "Ali")
    assert err == ""
    erp.st.session_state.update(
        {
            "at_expense_mode": "worker",
            "at_worker_id": wid,
            "at_worker_mv_type": "Salary",
            "at_worker_gross": "3000",
            "at_worker_ded": "0",
            "at_worker_adv_rec": "0",
            "at_pm": "Cash",
            "at_amount_display": "3000",
            "at_currency": "TRY",
            "at_date": datetime.date.today(),
        }
    )
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=[cash_ba],
        open_sales=[],
        txn_type="Expense",
        _TYPE_DISPLAY_MAP={},
    )
    assert db.query(models.WorkerMovement).filter_by(movement_type="Salary").count() == 1
