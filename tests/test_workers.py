"""Workers — staff payroll ledger."""

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit"].session_state = {}

from db import Base
import models
import app as erp_app


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    erp_app.st.session_state = {}
    with Session() as session:
        yield session


def _seed_coa(db, co):
    for code, name, atype in (
        ("1010", "Bank", "Asset"),
        ("1250", "Employee Advances", "Asset"),
        ("5100", "Salary Expense", "Expense"),
        ("3900", "Opening Balance Equity", "Equity"),
    ):
        db.add(
            models.ChartOfAccounts(
                account_code=code,
                account_name=name,
                account_type=atype,
                currency="TRY" if name == "Bank" else None,
                company_id=co.id,
            )
        )
    db.commit()


def _company(db):
    co = models.Company(
        name="Acme",
        slug="acme",
        is_active=True,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(co)
    db.commit()
    erp_app.st.session_state["active_company_id"] = co.id
    _seed_coa(db, co)
    return co


def _bank(db, co):
    ba = models.BankAccount(
        name="Main TRY",
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=50000.0,
    )
    db.add(ba)
    db.commit()
    return ba


def test_create_worker_and_advance_salary_recovery(db):
    co = _company(db)
    ba = _bank(db, co)
    wid, err = erp_app.create_worker(db, "Ahmet", role="Sales")
    assert err == ""
    assert wid

    mv_id, err = erp_app.post_worker_movement(
        db, wid, "Advance", datetime.date.today(),
        bank_account_id=ba.id, amount=5000.0,
    )
    assert err == ""
    assert mv_id
    assert erp_app.get_worker_advance_balance(db, wid) == 5000.0

    mv_id, err = erp_app.post_worker_movement(
        db, wid, "Salary", datetime.date.today(),
        bank_account_id=ba.id,
        gross_salary=10000.0,
        deductions=1000.0,
        advance_recovery=2000.0,
        pay_period="May 2026",
    )
    assert err == ""
    assert erp_app.get_worker_advance_balance(db, wid) == 3000.0
    assert erp_app.get_worker_salary_ytd(db, wid) == 9000.0

    adv = erp_app.get_account_by_name(db, "Employee Advances")
    assert erp_app.calculate_account_balance(db, adv) == 3000.0


def test_advance_repayment(db):
    co = _company(db)
    ba = _bank(db, co)
    wid, _ = erp_app.create_worker(db, "Ayşe")
    erp_app.post_worker_movement(
        db, wid, "Advance", datetime.date.today(),
        bank_account_id=ba.id, amount=1000.0,
    )
    mv_id, err = erp_app.post_worker_movement(
        db, wid, "Repayment", datetime.date.today(),
        bank_account_id=ba.id, amount=400.0,
    )
    assert err == ""
    assert erp_app.get_worker_advance_balance(db, wid) == 600.0

    _, err = erp_app.post_worker_movement(
        db, wid, "Repayment", datetime.date.today(),
        bank_account_id=ba.id, amount=700.0,
    )
    assert "exceeds outstanding" in err


def test_void_worker_movement(db):
    co = _company(db)
    ba = _bank(db, co)
    wid, _ = erp_app.create_worker(db, "Mehmet")
    mv_id, _ = erp_app.post_worker_movement(
        db, wid, "Advance", datetime.date.today(),
        bank_account_id=ba.id, amount=800.0,
    )
    err = erp_app.void_worker_movement(db, mv_id, 1, "mistake")
    assert err == ""
    assert erp_app.get_worker_advance_balance(db, wid) == 0.0
