"""Regression — Sale Cash/Card must record from Add Transaction (QUICK-ENTRY subcat gap)."""

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
from registry.coa_seed import ensure_accounts_for_company


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
        name="Test Co",
        slug="test_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()
    erp.st.session_state["active_company_id"] = co.id
    for code, name, atype, ccy in (
        ("1000", "Cash", "Asset", "TRY"),
        ("4000", "Sales Revenue", "Income", None),
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
    seed_default_categories_for_company(db, co.id)
    sale_cat = (
        db.query(models.TransactionCategory)
        .filter_by(company_id=co.id, transaction_type="Sale", is_active=True)
        .one()
    )
    return co, sale_cat


def _sale_session_state(sale_cat_id: int, *, pm: str = "Cash") -> None:
    """Mimic mobile AT after QUICK-ENTRY seed: sole Sale category, no subcategory yet."""
    erp.st.session_state.update(
        {
            "at_type_idx": 0,
            "mob_at_tab": 0,
            "at_pm": pm,
            "at_amount_display": "100",
            "at_currency": "TRY",
            "at_date": datetime.date.today(),
            "at_cust": "Walk-in Customer",
            "mob_at_cat_id": sale_cat_id,
            "at_notes_field": "",
        }
    )


def _journal_balanced(db) -> bool:
    lines = db.query(models.JournalEntryLine).all()
    deb = round(sum(l.debit or 0 for l in lines), 2)
    cred = round(sum(l.credit or 0 for l in lines), 2)
    return deb == cred and deb > 0


def test_sale_cash_records_from_add_transaction(db):
    _setup_company(db)
    _minimal_sale_state(pm="Cash")
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=db.query(models.BankAccount).all(),
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )
    assert db.query(models.Sale).filter_by(sale_type="Cash", is_void=False).count() == 1
    sale = db.query(models.Sale).one()
    assert sale.amount == 100.0
    assert sale.tx_category_id is None
    assert sale.tx_subcategory_id is None
    assert _journal_balanced(db)


def test_sale_card_records_from_add_transaction(db):
    _setup_company(db)
    _minimal_sale_state(pm="Card")
    erp.st.session_state["at_card_bank_acct"] = "Main Bank"
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=db.query(models.BankAccount).all(),
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )
    assert db.query(models.Sale).filter_by(sale_type="Card", is_void=False).count() == 1
    assert _journal_balanced(db)


def test_expense_cash_still_records(db):
    co, _sale_cat = _setup_company(db)
    db.add(
        models.ChartOfAccounts(
            account_code="5100",
            account_name="Office Expense",
            account_type="Expense",
            company_id=co.id,
            is_active=True,
        )
    )
    db.commit()
    exp_cat = (
        db.query(models.TransactionCategory)
        .filter_by(company_id=co.id, transaction_type="Expense", is_active=True)
        .order_by(models.TransactionCategory.name)
        .first()
    )
    exp_sub = (
        db.query(models.TransactionSubcategory)
        .filter_by(category_id=exp_cat.id, is_active=True)
        .order_by(models.TransactionSubcategory.name)
        .first()
    )
    erp.st.session_state.update(
        {
            "at_type_idx": 1,
            "mob_at_tab": 1,
            "at_pm": "Cash",
            "at_amount_display": "50",
            "at_currency": "TRY",
            "at_date": datetime.date.today(),
            "at_expense_mode": "general",
            "mob_at_cat_id": exp_cat.id,
            "mob_at_subcat_id": exp_sub.id,
            "at_notes_field": "",
        }
    )
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=[],
        open_sales=[],
        txn_type="Expense",
        _TYPE_DISPLAY_MAP={},
    )
    assert db.query(models.ExpenseRecord).count() == 1
    assert _journal_balanced(db)


def test_seed_visible_category_is_noop(db):
    _setup_company(db)
    erp._mob_at_seed_visible_category(db, "Sale")
    assert "mob_at_cat_id" not in erp.st.session_state
    assert "mob_at_subcat_id" not in erp.st.session_state


def test_gather_submit_sale_ignores_category_state(db):
    _co, sale_cat = _setup_company(db)
    exp_cat = (
        db.query(models.TransactionCategory)
        .filter_by(company_id=_co.id, transaction_type="Expense")
        .first()
    )
    _minimal_sale_state()
    erp.st.session_state["mob_at_cat_id"] = exp_cat.id
    erp.st.session_state["at_cat"] = exp_cat.name
    ctx = erp._at_gather_submit_fields(db, "Sale", "TRY", [], [], [])
    assert ctx["at_cat_id"] is None
    assert ctx["at_subcat_name"] is None


def test_stale_expense_subcat_ignored_for_sale(db):
    _co, _sale_cat = _setup_company(db)
    exp_cat = (
        db.query(models.TransactionCategory)
        .filter_by(company_id=_co.id, transaction_type="Expense")
        .first()
    )
    exp_sub = (
        db.query(models.TransactionSubcategory)
        .filter_by(category_id=exp_cat.id)
        .first()
    )
    _minimal_sale_state()
    erp.st.session_state["mob_at_subcat_id"] = exp_sub.id
    ctx = erp._at_gather_submit_fields(db, "Sale", "TRY", [], [], [])
    assert ctx["at_subcat_name"] is None


def test_desktop_sale_records_without_category(db):
    _setup_company(db)
    erp.st.session_state.update(
        {
            "at_type_idx": 0,
            "at_pm": "Cash",
            "at_amount_display": "75",
            "at_currency": "TRY",
            "at_date": datetime.date.today(),
        }
    )
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=db.query(models.BankAccount).all(),
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )
    sale = db.query(models.Sale).filter_by(sale_type="Cash", is_void=False).one()
    assert sale.tx_category_id is None


def test_mobile_sale_cash_full_submit_path(db):
    """Integration: mobile save intent → effective type → process_submit (real wiring)."""
    _setup_company(db)
    erp.st.session_state["_erp_mobile_ui"] = True
    erp.st.session_state.update(
        {
            "at_type_idx": 0,
            "mob_at_tab": 0,
            "at_pm": "Cash",
            "at_amount_display": "120",
            "at_currency": "TRY",
            "at_date": datetime.date.today(),
            "at_cust": "Walk-in Customer",
        }
    )
    erp.st.session_state["_mob_at_submit_pending"] = True
    assert erp._at_consume_mobile_save_pending()
    submit_type = erp._at_effective_txn_type(
        ["Sale", "Expense", "Purchase", "Supplier Payment", "Customer Payment", "Bank Transaction"]
    )
    assert submit_type == "Sale"
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=db.query(models.BankAccount).all(),
        open_sales=[],
        txn_type=submit_type,
        _TYPE_DISPLAY_MAP={},
    )
    sale = db.query(models.Sale).filter_by(sale_type="Cash", is_void=False).one()
    assert sale.amount == 120.0
    assert sale.tx_category_id is None
    assert sale.tx_subcategory_id is None


def test_mobile_sale_card_full_submit_path(db):
    _setup_company(db)
    erp.st.session_state["_erp_mobile_ui"] = True
    erp.st.session_state.update(
        {
            "at_type_idx": 0,
            "mob_at_tab": 0,
            "at_pm": "Card",
            "at_amount_display": "80",
            "at_currency": "TRY",
            "at_date": datetime.date.today(),
            "at_card_bank_acct": "Main Bank",
        }
    )
    erp.st.session_state["mob_at_save_clicked"] = True
    assert erp._at_consume_mobile_save_pending()
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=db.query(models.BankAccount).all(),
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )
    assert db.query(models.Sale).filter_by(sale_type="Card", is_void=False).count() == 1


def test_mobile_submit_pending_survives_panel_rerun(db):
    """Save flag must remain until submit handler (panel may st.rerun() first)."""
    erp.st.session_state["_mob_at_submit_pending"] = True
    assert erp.st.session_state.get("_mob_at_submit_pending")
    assert erp._at_consume_mobile_save_pending()
    assert not erp.st.session_state.get("_mob_at_submit_pending")


def _minimal_sale_state(*, pm: str = "Cash", amount: str = "100") -> None:
    """Sale submit without category/subcategory (ADD-TXN-BR-01)."""
    erp.st.session_state.update(
        {
            "at_type_idx": 0,
            "mob_at_tab": 0,
            "at_pm": pm,
            "at_amount_display": amount,
            "at_currency": "TRY",
            "at_date": datetime.date.today(),
            "at_notes_field": "",
        }
    )


def test_sale_cash_without_category_records(db):
    _setup_company(db)
    _minimal_sale_state(pm="Cash")
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=db.query(models.BankAccount).all(),
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )
    sale = db.query(models.Sale).filter_by(sale_type="Cash", is_void=False).one()
    assert sale.amount == 100.0
    assert sale.tx_category_id is None
    assert sale.tx_subcategory_id is None
    assert _journal_balanced(db)


def test_sale_card_without_category_records(db):
    _setup_company(db)
    _minimal_sale_state(pm="Card")
    erp.st.session_state["at_card_bank_acct"] = "Main Bank"
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=db.query(models.BankAccount).all(),
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )
    assert db.query(models.Sale).filter_by(sale_type="Card", is_void=False).count() == 1
    sale = db.query(models.Sale).one()
    assert sale.tx_category_id is None
    assert _journal_balanced(db)


def test_sale_credit_requires_customer(db):
    co, _sale_cat = _setup_company(db)
    db.add(
        models.ChartOfAccounts(
            account_code="1200",
            account_name="Accounts Receivable",
            account_type="Asset",
            company_id=co.id,
            is_active=True,
        )
    )
    db.commit()
    _minimal_sale_state(pm="Credit")

    erp.st.session_state["at_cust"] = ""
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=[],
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )
    assert db.query(models.Sale).count() == 0

    erp.st.session_state["at_cust"] = "Walk-in Customer"
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=[],
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )
    assert db.query(models.Sale).count() == 0

    erp.st.session_state["at_cust"] = "Acme Corp"
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=[],
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )
    sale = db.query(models.Sale).filter_by(sale_type="Credit", is_void=False).one()
    assert sale.customer_name == "Acme Corp"
    assert sale.balance == 100.0
