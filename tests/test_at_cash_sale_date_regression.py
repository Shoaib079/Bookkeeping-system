"""Cash sale date regression — submit-pinned date must reach Sale + JE."""

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
        name="Cash Date Co",
        slug="cash_date_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()
    erp.st.session_state["active_company_id"] = co.id
    for code, name, atype, ccy in (
        ("1000", "Cash", "Asset", "TRY"),
        ("4000", "Sales Revenue", "Income", None),
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
    db.commit()
    return co


def _cash_sale_state(**extra):
    state = {
        "at_type_idx": 0,
        "at_pm": "Cash",
        "at_amount_display": "100",
        "at_currency": "TRY",
        "at_notes_field": "",
        "at_cust": "Walk-in Customer",
    }
    state.update(extra)
    return state


def _submit_cash_sale(db, *, extra_state: dict | None = None):
    erp.st.session_state.update(_cash_sale_state(**(extra_state or {})))
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=[],
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )


def _latest_cash_sale(db):
    return (
        db.query(models.Sale)
        .filter_by(sale_type="Cash", is_void=False)
        .order_by(models.Sale.id.desc())
        .first()
    )


def _assert_cash_dates(db, expected: datetime.date):
    sale = _latest_cash_sale(db)
    assert sale is not None
    je = (
        db.query(models.JournalEntry)
        .filter_by(reference_type="CashSale", reference_id=sale.id)
        .one()
    )
    assert sale.date == expected
    assert je.entry_date == expected
    return sale


def test_submit_capture_pins_desktop_at_date(db):
    """Simulate desktop form submit: capture before rerender clobber."""
    _setup_company(db)
    erp.st.session_state.update(
        {
            **_cash_sale_state(),
            "at_date": PAST,
            "at_date_follows_today": False,
            "_user_date_format": "DD.MM.YYYY",
        }
    )
    erp._at_capture_submit_resolved_date()
    assert erp.st.session_state["at_submit_resolved_date"] == PAST

    erp.st.session_state["at_date"] = datetime.date.today()
    _submit_cash_sale(db)
    _assert_cash_dates(db, PAST)


def test_submit_capture_pins_mobile_backdated_date(db):
    """Mobile save captures date before follow-today rollover on next rerun."""
    _setup_company(db)
    erp.st.session_state.update(
        {
            **_cash_sale_state(),
            "_erp_mobile_ui": True,
            "at_date": PAST,
            "at_date_follows_today": False,
        }
    )
    erp._at_capture_submit_resolved_date()

    erp._mob_at_apply_date_follow_today()
    assert erp.st.session_state["at_date"] == PAST

    erp.st.session_state["_mob_at_submit_pending"] = True
    _submit_cash_sale(db)
    _assert_cash_dates(db, PAST)


def test_resolve_submit_date_uses_cache_then_falls_back(db):
    _setup_company(db)
    erp.st.session_state["at_submit_resolved_date"] = PAST
    assert erp._at_resolve_submit_date() == PAST

    erp.st.session_state.update(
        at_date=PAST,
        at_date_follows_today=False,
    )
    assert erp._at_resolve_submit_date() == PAST


def test_recent_display_uses_sale_date_not_today(db):
    _setup_company(db)
    _submit_cash_sale(
        db,
        extra_state={
            "at_date": PAST,
            "at_date_follows_today": False,
            "_user_date_format": "DD.MM.YYYY",
        },
    )
    sale = _assert_cash_dates(db, PAST)
    rows = []
    for s in (
        db.query(models.Sale)
        .filter_by(is_void=False)
        .order_by(models.Sale.date.desc())
        .limit(5)
        .all()
    ):
        rows.append({"Date": s.date, "Reference": s.invoice_number})
    assert any(r["Date"] == PAST and r["Reference"] == sale.invoice_number for r in rows)
