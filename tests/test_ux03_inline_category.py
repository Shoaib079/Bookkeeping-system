"""UX-03 — inline Expense category creation in mobile picker sheet."""

from __future__ import annotations

import datetime
import inspect
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app as erp

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock
else:
    _st_mock = sys.modules["streamlit"]
    if not isinstance(getattr(_st_mock, "session_state", None), dict):
        _st_mock.session_state = {}


class _FakeSessionState(dict):
    def get(self, key, default=None):
        return super().get(key, default)


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

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        erp._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        yield s


def _company(db, name="Alpha", slug="alpha"):
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
    sys.modules["streamlit"].session_state["active_company_id"] = company_id


def test_cat_create_or_reactivate_creates_expense_category(db):
    co = _company(db)
    _set_active(co.id)
    cat, err = erp._cat_create_or_reactivate(db, "Expense", "Travel")
    assert err is None
    assert cat is not None
    assert cat.name == "Travel"
    assert cat.transaction_type == "Expense"
    assert cat.is_active is True
    assert cat.company_id == co.id


def test_cat_create_or_reactivate_dedup_case_insensitive(db):
    co = _company(db)
    _set_active(co.id)
    first, err1 = erp._cat_create_or_reactivate(db, "Expense", "Office")
    assert err1 is None
    dup, err2 = erp._cat_create_or_reactivate(db, "Expense", "office")
    assert dup is None
    assert err2 == "exists_active"
    assert (
        db.query(models.TransactionCategory)
        .filter_by(company_id=co.id, transaction_type="Expense")
        .count()
        == 1
    )
    assert first.id is not None


def test_cat_create_or_reactivate_reactivates_inactive_duplicate(db):
    co = _company(db)
    _set_active(co.id)
    inactive = models.TransactionCategory(
        transaction_type="Expense",
        name="Old Supplies",
        is_active=False,
        company_id=co.id,
    )
    db.add(inactive)
    db.commit()

    cat, err = erp._cat_create_or_reactivate(db, "Expense", "old supplies")
    assert err is None
    assert cat.id == inactive.id
    assert cat.is_active is True
    assert cat.name == "Old Supplies"


def test_cat_create_or_reactivate_whitespace_only_blocked(db):
    co = _company(db)
    _set_active(co.id)
    cat, err = erp._cat_create_or_reactivate(db, "Expense", "   ")
    assert cat is None
    assert err == "empty"
    assert db.query(models.TransactionCategory).count() == 0


def test_expense_empty_search_add_applies_pick_and_memory(db, monkeypatch):
    co = _company(db)
    state = _FakeSessionState({"active_company_id": co.id})
    monkeypatch.setattr(erp.st, "session_state", state)
    closed: list[str] = []
    monkeypatch.setattr(erp, "_mob_at_close_picker", lambda: closed.append("closed"))

    assert erp._mob_at_expense_category_empty_search_add(db, "New Expense Cat") is True
    assert closed == ["closed"]
    assert "mob_at_cat_id" in state
    assert state["mob_at_last_cat_expense"] == state["mob_at_cat_id"]
    assert "mob_at_subcat_id" not in state


def test_expense_category_picker_enables_empty_search_add_only():
    src = inspect.getsource(erp._mob_at_render_category_picker_sheet)
    assert 'picker_kind == "expense_cat"' in src
    assert "allow_empty_search_add=expense_add" in src
    assert "_mob_at_expense_category_empty_search_add" in src


def test_list_picker_cta_gated_by_permission_and_locale():
    src = inspect.getsource(erp._mob_at_render_list_picker_sheet)
    assert '_can("manage_categories")' in src
    assert "txn.mob.add_category_cta" in src
    assert "allow_empty_search_add" in src


def test_sale_purchase_category_pickers_do_not_enable_cta():
    src = inspect.getsource(erp._mob_at_render_category_picker_sheet)
    assert 'expense_add = picker_kind == "expense_cat"' in src
    mobile = inspect.getsource(erp._render_add_transaction_mobile)
    assert 'picker_kind="sale_cat"' in mobile
    assert 'picker_kind="purchase_cat"' in mobile
    assert 'picker_kind="expense_cat"' in mobile
    assert src.count("allow_empty_search_add=expense_add") == 1


def test_cat_add_dialog_uses_shared_helper():
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    start = app_src.index("def _cat_add_dialog")
    end = app_src.index('@st.dialog("Manage Category")', start)
    dlg = app_src[start:end]
    assert "_cat_create_or_reactivate" in dlg
    assert "TransactionCategory(" not in dlg


def test_no_always_visible_add_category_on_at_panel():
    src = inspect.getsource(erp._render_add_transaction_mobile)
    assert "txn.mob.add_category_cta" not in src
    assert "mob_at_pick_expense_cat_add_cta" not in src
    assert "_cat_create_or_reactivate" not in src


def test_locale_add_category_cta_en_tr():
    from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR

    assert TRANSACTIONAL_EN["txn.mob.add_category_cta"] == '+ Add "{name}"'
    assert TRANSACTIONAL_TR["txn.mob.add_category_cta"] == '+ "{name}" ekle'
