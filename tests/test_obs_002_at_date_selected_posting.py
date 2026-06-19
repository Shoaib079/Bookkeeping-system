"""OBS-002 — selected Add Transaction date must post to records and JEs."""

from __future__ import annotations

import datetime
import inspect
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

SELECTED = datetime.date(2026, 6, 10)


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
        name="OBS-002 Co",
        slug="obs_002_co",
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
            balance=5000.0,
            kind="bank",
        )
    )
    db.commit()
    return co


def _expense_cat(db, co):
    return (
        db.query(models.TransactionCategory)
        .filter_by(company_id=co.id, transaction_type="Expense", is_active=True)
        .order_by(models.TransactionCategory.id)
        .first()
    )


def _purchase_cat(db, co):
    return (
        db.query(models.TransactionCategory)
        .filter_by(company_id=co.id, transaction_type="Purchase", is_active=True)
        .order_by(models.TransactionCategory.id)
        .first()
    )


def _vendor(db, co, name="Acme Vendor"):
    v = models.Vendor(name=name, company_id=co.id, is_active=True)
    db.add(v)
    db.commit()
    return v


def _simulate_desktop_submit_pipeline():
    """Render-order guard: rollover runs before capture on the submit rerun."""
    erp._mob_at_apply_date_follow_today()
    erp._at_capture_submit_resolved_date()


def _assert_record_and_je_dates(
    db,
    *,
    reference_type: str,
    reference_id: int,
    expected: datetime.date,
):
    if reference_type == "CashSale":
        record = db.get(models.Sale, reference_id)
        assert record is not None
        assert record.date == expected
    elif reference_type == "Expense":
        record = db.get(models.ExpenseRecord, reference_id)
        assert record is not None
        assert record.date == expected
    elif reference_type in ("Purchase", "CashPurchase", "BankPurchase"):
        record = db.get(models.Purchase, reference_id)
        assert record is not None
        assert record.date == expected
    else:
        raise AssertionError(reference_type)

    je = (
        db.query(models.JournalEntry)
        .filter_by(reference_type=reference_type, reference_id=reference_id)
        .one()
    )
    assert je.entry_date == expected


def test_desktop_date_change_clears_stale_follow_flag():
    erp.st.session_state["at_date"] = SELECTED
    erp.st.session_state["at_date_follows_today"] = True

    erp._at_on_desktop_date_change()

    assert erp.st.session_state["at_date_follows_today"] is False


def test_desktop_date_change_keeps_follow_flag_for_today():
    today = datetime.date.today()
    erp.st.session_state["at_date"] = today
    erp.st.session_state["at_date_follows_today"] = False

    erp._at_on_desktop_date_change()

    assert erp.st.session_state["at_date_follows_today"] is True


def test_desktop_date_input_wires_on_change_callback():
    src = inspect.getsource(erp._at_render_desktop_date_field)
    assert "on_change=_at_on_desktop_date_change" in src


def test_submit_pipeline_preserves_selected_date_with_stale_follow_flag(db):
    co = _setup_company(db)
    erp.st.session_state.update(
        {
            "at_date": SELECTED,
            "at_date_follows_today": True,
            "at_pm": "Cash",
            "at_amount_display": "100",
            "at_currency": "TRY",
            "at_notes_field": "",
            "at_cust": "Walk-in Customer",
        }
    )

    _simulate_desktop_submit_pipeline()

    assert erp.st.session_state["at_date"] == SELECTED
    assert erp.st.session_state["at_submit_resolved_date"] == SELECTED

    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=[],
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )

    sale = (
        db.query(models.Sale)
        .filter_by(company_id=co.id, is_void=False)
        .order_by(models.Sale.id.desc())
        .first()
    )
    assert sale is not None
    _assert_record_and_je_dates(
        db,
        reference_type="CashSale",
        reference_id=sale.id,
        expected=SELECTED,
    )
    assert erp.st.session_state["at_date"] == SELECTED


@pytest.mark.parametrize(
    "txn_type,reference_type,pm,extra",
    [
        (
            "Expense",
            "Expense",
            "Cash",
            {"at_expense_mode": "general"},
        ),
        (
            "Purchase",
            "CashPurchase",
            "Cash",
            {},
        ),
    ],
)
def test_submit_pipeline_posts_selected_date_for_expense_and_purchase(
    db, txn_type, reference_type, pm, extra
):
    co = _setup_company(db)
    vendor = _vendor(db, co)
    bank_accounts = db.query(models.BankAccount).all()
    if txn_type == "Expense":
        cat = _expense_cat(db, co)
    else:
        cat = _purchase_cat(db, co)
    sub = (
        db.query(models.TransactionSubcategory)
        .filter_by(category_id=cat.id, is_active=True)
        .first()
    )

    erp.st.session_state.update(
        {
            "at_date": SELECTED,
            "at_date_follows_today": True,
            "at_amount_display": "100",
            "at_currency": "TRY",
            "at_notes_field": "",
            "at_pm": pm,
            "at_vendor": vendor.name,
            "mob_at_cat_id": cat.id,
            "at_cat": cat.name,
            "mob_at_subcat_id": sub.id,
            **extra,
        }
    )

    _simulate_desktop_submit_pipeline()

    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[vendor],
        bank_accounts=bank_accounts,
        open_sales=[],
        txn_type=txn_type,
        _TYPE_DISPLAY_MAP={},
    )

    if reference_type == "Expense":
        record = (
            db.query(models.ExpenseRecord)
            .filter_by(company_id=co.id, is_void=False)
            .order_by(models.ExpenseRecord.id.desc())
            .first()
        )
    else:
        record = (
            db.query(models.Purchase)
            .filter_by(company_id=co.id, is_void=False)
            .order_by(models.Purchase.id.desc())
            .first()
        )

    assert record is not None
    _assert_record_and_je_dates(
        db,
        reference_type=reference_type,
        reference_id=record.id,
        expected=SELECTED,
    )
