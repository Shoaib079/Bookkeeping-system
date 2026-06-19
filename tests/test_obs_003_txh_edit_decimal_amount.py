"""OBS-003 — Transaction History edit amount compare (Decimal vs float)."""

from __future__ import annotations

import datetime
import inspect
import sys
from decimal import Decimal
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

PAST = datetime.date(2026, 6, 10)
WRONG = datetime.date(2026, 6, 5)
AMOUNT = Decimal("150.00")


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


def _provision_company(db, *, name: str, slug: str):
    """SETUP-01-style fresh company (seeded COA + categories)."""
    co = models.Company(
        name=name,
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()
    seed_chart_of_accounts_for_company(db, co.id)
    seed_default_categories_for_company(db, co.id)
    db.commit()
    return co


def _legacy_style_company(db):
    """Existing-company proxy: extra COA row + activity before edit."""
    co = _provision_company(db, name="spice corner", slug="company_1_proxy")
    db.add(
        models.ChartOfAccounts(
            account_code="9999",
            account_name="Legacy Custom",
            account_type="Expense",
            company_id=co.id,
            is_active=True,
        )
    )
    db.commit()
    return co


def _cash_sale(db, co, *, sale_date: datetime.date, amount=AMOUNT):
    erp.st.session_state["active_company_id"] = co.id
    sale = models.Sale(
        date=sale_date,
        invoice_number=f"INV-{sale_date.isoformat()}",
        customer_name="Walk-in Customer",
        description="OBS-003",
        amount=amount,
        sale_type="Cash",
        paid_amount=amount,
        balance=Decimal("0.00"),
        due_date=sale_date,
        status="Paid",
        company_id=co.id,
        currency="TRY",
        native_amount=amount,
    )
    db.add(sale)
    db.commit()
    erp.post_cash_sale(db, sale.id, float(amount), sale_date)
    db.refresh(sale)
    return sale


def _sale_edit_fields(eobj, *, new_date, new_amt):
    """Mirror Transaction History Sale edit dirty detection."""
    fields = {}
    if new_date != eobj.date:
        fields["date"] = new_date
    if erp._txh_edit_amount_changed(new_amt, eobj.amount):
        fields["amount"] = new_amt
    return fields


def test_row_panels_uses_decimal_safe_amount_compare():
    src = inspect.getsource(erp._txh_render_row_panels)
    assert "_txh_edit_amount_changed" in src
    assert "abs(_new_amt - eobj.amount)" not in src


def test_edit_amount_changed_decimal_stored_float_input_no_crash():
    assert erp._txh_edit_amount_changed(150.0, Decimal("150.00")) is False


def test_edit_amount_changed_marks_dirty_on_real_change():
    assert erp._txh_edit_amount_changed(150.01, Decimal("150.00")) is True


def test_edit_amount_changed_unchanged_after_quantization():
    assert erp._txh_edit_amount_changed(100.01, Decimal("100.01")) is False


@pytest.mark.parametrize(
    "company_factory",
    [
        pytest.param(lambda db: _provision_company(db, name="Fresh Co", slug="fresh_co"), id="setup01_new"),
        pytest.param(_legacy_style_company, id="existing_legacy"),
    ],
)
def test_date_only_edit_does_not_mark_amount_dirty(db, company_factory):
    co = company_factory(db)
    sale = _cash_sale(db, co, sale_date=WRONG)
    fields = _sale_edit_fields(sale, new_date=PAST, new_amt=150.0)
    assert fields == {"date": PAST}
    assert "amount" not in fields


@pytest.mark.parametrize(
    "company_factory",
    [
        pytest.param(lambda db: _provision_company(db, name="Fresh Co 2", slug="fresh_co_2"), id="setup01_new"),
        pytest.param(_legacy_style_company, id="existing_legacy"),
    ],
)
def test_amount_change_marks_dirty_with_decimal_stored(db, company_factory):
    co = company_factory(db)
    sale = _cash_sale(db, co, sale_date=PAST)
    fields = _sale_edit_fields(sale, new_date=PAST, new_amt=200.0)
    assert fields["amount"] == 200.0
    assert "date" not in fields


@pytest.mark.parametrize(
    "company_factory",
    [
        pytest.param(lambda db: _provision_company(db, name="Prod Co", slug="prod_co"), id="setup01_new"),
        pytest.param(_legacy_style_company, id="existing_legacy"),
    ],
)
def test_edit_sale_date_correction_works_with_decimal_amount(db, company_factory):
    co = company_factory(db)
    sale = _cash_sale(db, co, sale_date=WRONG)
    ok, err = erp.edit_sale(db, sale.id, {"date": PAST})
    assert ok is True, err
    db.refresh(sale)
    assert sale.date == PAST
    assert sale.amount == AMOUNT
    je = (
        db.query(models.JournalEntry)
        .filter_by(reference_type="CashSale", reference_id=sale.id)
        .order_by(models.JournalEntry.id.desc())
        .first()
    )
    assert je is not None
    assert je.entry_date == PAST


def test_add_transaction_backdated_post_still_works_on_setup01_company(db):
    """OBS-002 regression on SETUP-01-style company (global, not seed-specific)."""
    co = _provision_company(db, name="AT Date Co", slug="at_date_co")
    erp.st.session_state.update(
        {
            "active_company_id": co.id,
            "at_date": PAST,
            "at_date_follows_today": True,
            "at_submit_resolved_date": PAST,
            "at_pm": "Cash",
            "at_amount_display": "75",
            "at_currency": "TRY",
            "at_notes_field": "",
            "at_cust": "Walk-in Customer",
        }
    )
    erp._mob_at_apply_date_follow_today()
    erp._at_capture_submit_resolved_date()
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=[],
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )
    sale = db.query(models.Sale).filter_by(company_id=co.id).one()
    assert sale.date == PAST
    je = (
        db.query(models.JournalEntry)
        .filter_by(reference_type="CashSale", reference_id=sale.id)
        .one()
    )
    assert je.entry_date == PAST
