"""MD-05-IMPL-3 — cache re-sync smoke tests."""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from models import BankAccount, BankTransaction, ChartOfAccounts, JournalEntry, JournalEntryLine
from services.banking_balance import derive_bank_account_balance, sync_bank_account_balances
from services.money import money_to_float
from services.read_balances import calculate_account_balance


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_gl_with_entry(session, *, debit: float = 100.0):
    acct = ChartOfAccounts(
        account_code="1000",
        account_name="Cash",
        account_type="Asset",
        company_id=1,
        balance=0.0,
    )
    session.add(acct)
    session.flush()
    entry = JournalEntry(
        entry_date=datetime.date.today(),
        description="seed",
        reference_type="Test",
        reference_id=1,
        company_id=1,
    )
    session.add(entry)
    session.flush()
    session.add(
        JournalEntryLine(
            journal_entry_id=entry.id,
            account_id=acct.id,
            debit=debit,
            credit=0.0,
            company_id=1,
        )
    )
    session.commit()
    return acct


class TestGlCacheResync:
    def test_sync_account_balances_matches_derived(self, db, monkeypatch):
        import app as erp_app

        acct = _seed_gl_with_entry(db, debit=250.0)
        acct.balance = 0.0
        db.commit()

        erp_app.sync_account_balances(db)

        db.refresh(acct)
        expected = calculate_account_balance(db, acct, company_id=1)
        assert money_to_float(acct.balance) == pytest.approx(expected)
        assert money_to_float(acct.balance) == 250.0


class TestBankCacheResync:
    def test_derive_and_sync_bank_balance(self, db):
        ba = BankAccount(name="Main", balance=999.0, company_id=1)
        db.add(ba)
        db.flush()
        db.add(
            BankTransaction(
                account_id=ba.id,
                date=datetime.date.today(),
                amount=100.0,
                type="deposit",
                description="Seed",
                company_id=1,
            )
        )
        db.add(
            BankTransaction(
                account_id=ba.id,
                date=datetime.date.today(),
                amount=40.0,
                type="withdrawal",
                description="Pay",
                company_id=1,
            )
        )
        db.commit()

        derived = derive_bank_account_balance(db, ba)
        assert derived == pytest.approx(60.0)

        ba.balance = 999.0
        db.commit()
        sync_bank_account_balances(db)
        db.refresh(ba)
        assert money_to_float(ba.balance) == pytest.approx(60.0)
