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
        ("05062026", datetime.date(2026, 6, 5)),
        ("", None),
        ("not-a-date", None),
        ("32.13.2026", None),
        ("31022026", None),
    ],
)
def test_at_parse_date_text_formats(raw, expected, monkeypatch):
    monkeypatch.setattr(
        erp.st,
        "session_state",
        {"_user_date_format": "DD.MM.YYYY"},
    )
    assert erp._at_parse_date_text(raw) == expected


def test_at_entry_date_error_always_none(monkeypatch):
    """Native st.date_input — desktop AT has no invalid free-text date path."""
    assert erp._at_entry_date_error() is None


def test_at_resolve_entry_date_reads_at_date(monkeypatch):
    state = {
        "at_date": datetime.date(2026, 6, 5),
        "at_date_follows_today": False,
    }
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._at_resolve_entry_date() == datetime.date(2026, 6, 5)


def test_at_capture_submit_clears_follow_flag_for_backdated_pick(monkeypatch):
    state = {
        "at_date": datetime.date(2026, 3, 15),
        "at_date_follows_today": True,
    }
    monkeypatch.setattr(erp.st, "session_state", state)
    from services import at_date_ownership as at_date

    at_date.capture_submit_resolved_date(state)
    assert state["at_date_follows_today"] is False


def test_at_resolve_entry_date_defaults_missing_at_date(monkeypatch):
    state = {}
    monkeypatch.setattr(erp.st, "session_state", state)
    resolved = erp._at_resolve_entry_date()
    assert resolved == datetime.date.today()
    assert state["at_date"] == datetime.date.today()


def test_at_resolve_entry_date_mobile_uses_at_date(monkeypatch):
    state = {
        "_erp_mobile_ui": True,
        "at_date": datetime.date(2026, 9, 9),
    }
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._at_resolve_entry_date() == datetime.date(2026, 9, 9)


def test_inline_rows_use_form_submit_buttons_inside_at_form():
    """st.button is forbidden inside st.form — inline rows use form_submit_button."""
    for fn_name in (
        "_inline_cat_row",
        "_inline_subcat_row",
        "_inline_vendor_row",
    ):
        src = inspect.getsource(getattr(erp, fn_name))
        assert "inside_form" in src
        assert "st.form_submit_button" in src
    at_src = inspect.getsource(erp.render_add_transaction)
    assert "_at_consume_inline_form_dialog_actions" in at_src
    assert "inside_form=True" in at_src


def test_desktop_date_field_single_native_date_input():
    """UX-STABILIZE-03: desktop AT has exactly one native date picker (key=at_date)."""
    src = inspect.getsource(erp._at_render_desktop_date_field)
    assert "st.date_input" in src
    assert 'key="at_date"' in src
    assert "streamlit_date_input_format" in src
    for banned in (
        "st.checkbox",
        "st.expander",
        "st.popover",
        "render_preferred_date_input",
        "show_calendar",
        "reconcile_text_and_calendar",
        "at_date_text",
        "at_date_manual_entry",
        "date_enter_manually",
    ):
        assert banned not in src, f"banned widget/pattern in date field: {banned}"
    assert "isoformat()" not in src


def test_no_manual_entry_checkbox_anywhere():
    """The txn.date_enter_manually control is fully removed (app + locales)."""
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "date_enter_manually" not in app_src
    assert "at_date_manual_entry" not in app_src
    for loc in ("transactional.py", "messages.py"):
        loc_src = (ROOT / "registry" / "locales" / loc).read_text(encoding="utf-8")
        assert "date_enter_manually" not in loc_src


def test_date_field_renders_inside_entry_form():
    """Enter-to-submit: the date field call sits inside the at_entry_form block."""
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    form_idx = app_src.index('with st.form("at_entry_form"')
    call_idx = app_src.index("_at_render_desktop_date_field()", form_idx)
    # called within 400 chars of the form opening — first element of the form
    assert 0 < call_idx - form_idx < 400


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


def test_desktop_date_field_inside_form_for_enter_submit():
    """Date field inside the form: native picker + Enter submits the transaction."""
    src = inspect.getsource(erp.render_add_transaction)
    form_pos = src.index('st.form("at_entry_form"')
    date_pos = src.index("_at_render_desktop_date_field()")
    assert date_pos > form_pos
    date_helper = inspect.getsource(erp._at_render_desktop_date_field)
    assert "st.date_input" in date_helper
    assert 'key="at_date"' in date_helper


def test_at_date_is_company_scoped():
    assert "at_date" in erp._COMPANY_SCOPED_AT_KEYS
    assert "mob_at_date_custom_pick" in erp._COMPANY_SCOPED_AT_KEYS


def test_no_dual_date_widgets_in_add_transaction_path():
    """AT path uses one st.date_input in the desktop helper only."""
    desktop = inspect.getsource(erp._at_render_desktop_date_field)
    assert desktop.count("st.date_input") == 1
    at_src = inspect.getsource(erp.render_add_transaction)
    assert at_src.count("st.date_input") == 0


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
