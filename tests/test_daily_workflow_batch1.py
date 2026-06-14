"""Daily Workflow Bug Fix Batch 1 — regression tests."""

from __future__ import annotations

import datetime
import inspect
import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

if "streamlit" not in sys.modules:
    import streamlit as st
else:
    st = sys.modules["streamlit"]
    if not isinstance(getattr(st, "session_state", None), dict):
        st.session_state = {}

import app as erp
import models
from db import Base

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def clear_session():
    st.session_state.clear()
    yield
    st.session_state.clear()


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


# ── Fix 1: Login Enter ────────────────────────────────────────────────────────


def test_login_form_allows_enter_submit():
    src = inspect.getsource(erp.render_login)
    assert 'with st.form("login_form"):' in src
    assert "enter_to_submit=False" not in src


# ── Fix 2: Category placeholder / validation ────────────────────────────────


def test_inline_cat_row_uses_placeholder_not_first_category():
    src = inspect.getsource(erp._inline_cat_row)
    assert "cats[0]" not in src
    assert "index=None" in src
    assert "txn.select_category_ph" in src
    assert "placeholder=" in src


def test_gather_submit_fields_no_silent_category_fallback():
    src = inspect.getsource(erp._at_gather_submit_fields)
    assert "_AT_EXPENSE_CATS[0]" not in src


def test_process_submit_requires_category_before_save():
    src = inspect.getsource(erp._at_process_submit)
    assert "txn.category_required" in src
    idx_cat = src.index("txn.category_required")
    idx_save = src.index("_at_save(")
    assert idx_cat < idx_save


# ── Fix 3: Profile suppresses AT panel CSS ────────────────────────────────────


def test_css_profile_open_suppresses_mobile_at_panel():
    widgets = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    marker = "/* Profile open — suppress mobile AT panel and picker behind profile sheet */"
    assert marker in widgets
    block = widgets.split(marker, 1)[1].split("/* Header popover open", 1)[0]
    assert "erp-mobile-profile-host" in block
    assert "erp_mob_at_panel" in block
    assert "erp_mob_at_picker_sheet" in block
    assert "display: none !important" in block


# ── Fix 4: Company-scoped AT keys ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "key",
    [
        "at_date",
        "at_type_idx",
        "at_expense_mode",
        "at_currency",
        "at_pm",
        "at_notes_field",
    ],
)
def test_company_scoped_at_keys_include_draft_fields(key):
    assert key in erp._COMPANY_SCOPED_AT_KEYS


def test_clear_company_scoped_session_state_clears_new_keys():
    st.session_state.update(
        {
            "at_date": datetime.date(2026, 1, 15),
            "at_type_idx": 2,
            "at_expense_mode": "worker",
            "at_currency": "USD",
            "at_pm": "Bank",
            "at_notes_field": "note",
        }
    )
    erp._clear_company_scoped_session_state()
    for key in (
        "at_date",
        "at_type_idx",
        "at_expense_mode",
        "at_currency",
        "at_pm",
        "at_notes_field",
    ):
        assert key not in st.session_state


# ── Fix 5: Mobile AT date control ───────────────────────────────────────────


def test_mobile_at_renders_date_picker():
    """Mobile date picker uses quick rows (Today/Yesterday/Custom), not st.date_input."""
    panel_src = inspect.getsource(erp._render_add_transaction_mobile)
    picker_src = inspect.getsource(erp._mob_at_render_date_picker_sheet)

    assert "_mob_at_open_picker" in panel_src or "mob_at_picker" in panel_src
    assert "mob_at_pick_date_today" in picker_src
    assert "mob_at_pick_date_yesterday" in picker_src
    assert "mob_at_pick_date_custom" in picker_src
    assert "st.date_input" not in picker_src
    assert '"at_date"' in picker_src


def test_gather_submit_fields_reads_entry_date():
    src = inspect.getsource(erp._at_gather_submit_fields)
    assert "_at_resolve_submit_date()" in src


# ── Fix 6: Card-bank picker gated by POS settlement ───────────────────────────


def test_mobile_sale_card_bank_gated_by_card_settlement():
    src = inspect.getsource(erp._render_add_transaction_mobile)
    sale_block = src.split("elif at_idx == 0:")[1].split("elif at_idx == 1")[0]
    assert "_card_settlement_on(session)" in sale_block
    assert "not _card_settlement_on(session)" in sale_block


def test_desktop_sale_card_bank_gated_by_card_settlement():
    src = inspect.getsource(erp.render_add_transaction)
    sale_block = src.split('if txn_type == "Sale":', 1)[1].split(
        'elif txn_type == "Expense":', 1
    )[0]
    assert "_card_settlement_on(session)" in sale_block
    assert "not _card_settlement_on(session)" in sale_block


def test_card_settlement_on_uses_active_company_setting(db, monkeypatch):
    from registry.company_provision import create_company
    from registry.service import set_setting

    user = models.User(
        username="owner",
        display_name="Owner",
        password_hash=erp._hash_password("pw"),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(user)
    db.flush()
    co = create_company(db, name="Test Co", created_by_user_id=user.id)
    db.commit()

    monkeypatch.setattr(erp, "_current_company_id", lambda: co.id)
    set_setting(db, "banking.card_settlement_enabled", True, company_id=co.id)
    db.commit()
    assert erp._card_settlement_on(db) is True

    set_setting(db, "banking.card_settlement_enabled", False, company_id=co.id)
    db.commit()
    assert erp._card_settlement_on(db) is False


def test_bank_accounts_query_uses_company_scope():
    src = inspect.getsource(erp.render_add_transaction)
    assert "cq(session, BankAccount)" in src


def _company(db, name: str, slug: str) -> models.Company:
    c = models.Company(
        name=name,
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(c)
    db.flush()
    return c


def _set_active(company_id: int) -> None:
    st.session_state["active_company_id"] = company_id


def test_render_add_transaction_bank_list_company_scoped(db):
    """Bank names in AT come from cq — active company only."""
    co_a = _company(db, "Co A", "co_a")
    co_b = _company(db, "Co B", "co_b")

    _set_active(co_a.id)
    db.add(
        models.BankAccount(
            name="YapiKredi A",
            bank_name="YKB",
            account_number="1",
            balance=0.0,
            currency="TRY",
            is_active=True,
        )
    )
    db.flush()

    _set_active(co_b.id)
    db.add(
        models.BankAccount(
            name="Is Bank B",
            bank_name="ISB",
            account_number="2",
            balance=0.0,
            currency="TRY",
            is_active=True,
        )
    )
    db.commit()

    _set_active(co_a.id)
    scoped = erp.cq(db, models.BankAccount).filter_by(is_active=True).all()
    names = {a.name for a in scoped}
    assert names == {"YapiKredi A"}
    assert "Is Bank B" not in names
