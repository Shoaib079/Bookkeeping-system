"""Add Transaction date ownership — all txn types + subcategory widget safety."""

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


def _setup_company(db):
    co = models.Company(
        name="Date Ownership Co",
        slug="date_ownership_co",
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


def _past_date_state(**extra):
    state = {
        "at_date": PAST,
        "at_date_follows_today": False,
        "_user_date_format": "DD.MM.YYYY",
        "at_amount_display": "100",
        "at_currency": "TRY",
        "at_notes_field": "",
    }
    state.update(extra)
    return state


def _submit(db, *, txn_type: str, extra_state: dict | None = None, **kwargs):
    erp.st.session_state.update(_past_date_state(**(extra_state or {})))
    erp._at_capture_submit_resolved_date()
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=kwargs.get("vendors", []),
        bank_accounts=kwargs.get("bank_accounts", db.query(models.BankAccount).all()),
        open_sales=kwargs.get("open_sales", []),
        txn_type=txn_type,
        _TYPE_DISPLAY_MAP={},
    )


def _je(db, ref_type: str, ref_id: int):
    return (
        db.query(models.JournalEntry)
        .filter_by(reference_type=ref_type, reference_id=ref_id)
        .one()
    )


# ── Sales ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "pm,ref_type,extra",
    [
        ("Cash", "CashSale", {}),
        (
            "Card",
            "CardSale",
            {"at_card_bank_acct": "Main Bank"},
        ),
        (
            "Credit",
            "CreditSale",
            {"at_cust": "Acme Corp"},
        ),
    ],
)
def test_past_date_sale_types(db, pm, ref_type, extra):
    co = _setup_company(db)
    if pm == "Credit":
        db.add(
            models.Customer(
                name="Acme Corp",
                company_id=co.id,
                is_active=True,
            )
        )
        db.commit()
    _submit(
        db,
        txn_type="Sale",
        extra_state={
            "at_type_idx": 0,
            "at_pm": pm,
            "at_cust": "Walk-in Customer",
            **extra,
        },
    )
    sale = (
        db.query(models.Sale)
        .filter_by(sale_type=pm, is_void=False)
        .order_by(models.Sale.id.desc())
        .first()
    )
    assert sale.date == PAST
    assert _je(db, ref_type, sale.id).entry_date == PAST
    if pm == "Card":
        btxn = (
            db.query(models.BankTransaction)
            .filter_by(type="deposit", is_void=False)
            .order_by(models.BankTransaction.id.desc())
            .first()
        )
        assert btxn is not None
        assert btxn.date == PAST


# ── Expense ──────────────────────────────────────────────────────────────────


def test_past_date_expense_cash(db):
    co = _setup_company(db)
    cat = _expense_cat(db, co)
    _submit(
        db,
        txn_type="Expense",
        extra_state={
            "at_type_idx": 1,
            "at_pm": "Cash",
            "mob_at_cat_id": cat.id,
            "at_cat": cat.name,
            "mob_at_subcat_id": (
                db.query(models.TransactionSubcategory)
                .filter_by(category_id=cat.id, is_active=True)
                .first()
                .id
            ),
        },
    )
    exp = (
        db.query(models.ExpenseRecord)
        .filter_by(is_void=False)
        .order_by(models.ExpenseRecord.id.desc())
        .first()
    )
    assert exp.date == PAST
    assert _je(db, "Expense", exp.id).entry_date == PAST


def test_past_date_expense_bank(db):
    co = _setup_company(db)
    cat = _expense_cat(db, co)
    _submit(
        db,
        txn_type="Expense",
        extra_state={
            "at_type_idx": 1,
            "at_pm": "Bank",
            "at_bank_pay_acct": "Main Bank",
            "mob_at_cat_id": cat.id,
            "at_cat": cat.name,
            "mob_at_subcat_id": (
                db.query(models.TransactionSubcategory)
                .filter_by(category_id=cat.id, is_active=True)
                .first()
                .id
            ),
        },
    )
    exp = db.query(models.ExpenseRecord).order_by(models.ExpenseRecord.id.desc()).first()
    btxn = (
        db.query(models.BankTransaction)
        .filter_by(type="withdrawal", is_void=False)
        .order_by(models.BankTransaction.id.desc())
        .first()
    )
    assert exp.date == PAST
    assert _je(db, "Expense", exp.id).entry_date == PAST
    assert btxn.date == PAST


# ── Purchase ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("pm,ref_type", [
    ("Cash", "CashPurchase"),
    ("Bank", "BankPurchase"),
    ("Credit", "Purchase"),
])
def test_past_date_purchase_types(db, pm, ref_type):
    co = _setup_company(db)
    cat = _purchase_cat(db, co)
    vendor = _vendor(db, co)
    extra = {
        "at_type_idx": 2,
        "at_pm": pm,
        "at_vendor": vendor.name,
        "mob_at_cat_id": cat.id,
        "at_cat": cat.name,
        "mob_at_subcat_id": (
            db.query(models.TransactionSubcategory)
            .filter_by(category_id=cat.id, is_active=True)
            .first()
            .id
        ),
    }
    if pm == "Bank":
        extra["at_bank_pay_acct"] = "Main Bank"
    _submit(db, txn_type="Purchase", extra_state=extra, vendors=[vendor])
    pur = (
        db.query(models.Purchase)
        .filter_by(is_void=False)
        .order_by(models.Purchase.id.desc())
        .first()
    )
    assert pur.date == PAST
    assert _je(db, ref_type, pur.id).entry_date == PAST
    if pm == "Bank":
        btxn = (
            db.query(models.BankTransaction)
            .filter_by(type="withdrawal", is_void=False)
            .order_by(models.BankTransaction.id.desc())
            .first()
        )
        assert btxn.date == PAST
    if pm == "Credit":
        payable = (
            db.query(models.Payable)
            .filter_by(purchase_id=pur.id, is_void=False)
            .one()
        )
        assert payable.date == PAST
        assert payable.due_date == PAST + datetime.timedelta(days=30)


# ── Supplier / customer payments ─────────────────────────────────────────────


def test_past_date_supplier_payment(db):
    co = _setup_company(db)
    vendor = _vendor(db, co)
    cat = _purchase_cat(db, co)
    _submit(
        db,
        txn_type="Purchase",
        extra_state={
            "at_type_idx": 2,
            "at_pm": "Credit",
            "at_vendor": vendor.name,
            "mob_at_cat_id": cat.id,
            "at_cat": cat.name,
            "mob_at_subcat_id": (
                db.query(models.TransactionSubcategory)
                .filter_by(category_id=cat.id, is_active=True)
                .first()
                .id
            ),
        },
        vendors=[vendor],
    )
    payable = (
        db.query(models.Payable)
        .filter_by(vendor_id=vendor.id, is_void=False)
        .one()
    )
    assert payable.date == PAST
    _submit(
        db,
        txn_type="Supplier Payment",
        extra_state={
            "at_type_idx": 3,
            "at_pm": "Cash",
            "at_vendor": vendor.name,
            "at_payable_id": payable.id,
            "at_amount_display": "100",
        },
        vendors=[vendor],
    )
    assert _je(db, "PayablePayment", payable.id).entry_date == PAST


def test_past_date_customer_payment(db):
    co = _setup_company(db)
    sale = models.Sale(
        date=PAST,
        invoice_number="INV-OPEN-1",
        customer_name="Buyer",
        amount=150.0,
        sale_type="Credit",
        paid_amount=0.0,
        balance=150.0,
        due_date=PAST + datetime.timedelta(days=30),
        status="Open",
        company_id=co.id,
    )
    db.add(sale)
    db.commit()
    erp.post_credit_sale(db, sale.id, sale.amount, PAST)
    db.commit()
    label = erp._at_invoice_choice_label(sale)
    _submit(
        db,
        txn_type="Customer Payment",
        extra_state={
            "at_type_idx": 4,
            "at_pm": "Bank",
            "at_bank_pay_acct": "Main Bank",
            "at_inv": label,
            "at_amount_display": "150",
        },
        open_sales=[sale],
    )
    assert _je(db, "ReceivablePayment", sale.id).entry_date == PAST
    btxn = (
        db.query(models.BankTransaction)
        .filter_by(type="deposit", is_void=False)
        .order_by(models.BankTransaction.id.desc())
        .first()
    )
    assert btxn.date == PAST


# ── Bank transaction ───────────────────────────────────────────────────────────


def test_past_date_bank_deposit(db):
    _setup_company(db)
    bank = db.query(models.BankAccount).filter_by(name="Main Bank").one()
    _submit(
        db,
        txn_type="Bank Transaction",
        extra_state={
            "at_type_idx": 5,
            "at_bank_sub": "Deposit",
            "at_bank_acct": bank.name,
        },
    )
    btxn = (
        db.query(models.BankTransaction)
        .filter_by(type="deposit", is_void=False)
        .order_by(models.BankTransaction.id.desc())
        .first()
    )
    assert btxn.date == PAST
    assert _je(db, "BankDeposit", btxn.id).entry_date == PAST


# ── Subcategory widget safety ─────────────────────────────────────────────────


def test_gather_submit_subcat_none_when_unpicked(db, monkeypatch):
    co = _setup_company(db)
    cat = _expense_cat(db, co)
    writes: list[tuple[str, object]] = []

    class TrackingState(dict):
        def __setitem__(self, key, value):
            writes.append((key, value))
            super().__setitem__(key, value)

    state = TrackingState(
        {
            "active_company_id": co.id,
            "at_date": PAST,
            "at_date_follows_today": False,
            "mob_at_cat_id": cat.id,
            "at_cat": cat.name,
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    ctx = erp._at_gather_submit_fields(db, "Expense", "TRY", [], [], [])
    assert ctx["at_subcat_name"] is None
    assert not any(k == "at_subcat" for k, _ in writes)


def test_gather_submit_preserves_existing_subcat(db):
    co = _setup_company(db)
    cat = _expense_cat(db, co)
    sub = (
        db.query(models.TransactionSubcategory)
        .filter_by(category_id=cat.id, is_active=True)
        .order_by(models.TransactionSubcategory.name)
        .offset(1)
        .first()
    )
    erp.st.session_state.update(
        {
            "at_date": PAST,
            "mob_at_cat_id": cat.id,
            "at_cat": cat.name,
            "mob_at_subcat_id": sub.id,
            "at_subcat": sub.name,
        }
    )
    ctx = erp._at_gather_submit_fields(db, "Expense", "TRY", [], [], [])
    assert ctx["at_subcat_name"] == sub.name


def test_deferred_subcat_sync_before_widget(monkeypatch):
    state = {}
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_defer_subcat_default("Electricity")
    erp._at_apply_deferred_subcat_sync()
    assert state["at_subcat"] == "Electricity"
    erp._at_defer_subcat_clear()
    state["at_subcat"] = "stale"
    erp._at_apply_deferred_subcat_sync()
    assert "at_subcat" not in state
