"""FASTAPI-P0.5c — reconciliation JE company stamp fix tests."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

import app as erp_app
from db import Base
import models
from reconciliation.match_post import post_bank_charge_outflow, post_generic_deposit
from registry.coa_seed import seed_chart_of_accounts_for_company
from registry.service import set_setting

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(erp_app._DEV_USER)
    sys.modules["streamlit"].session_state["auth_expires"] = (
        datetime.datetime.now() + datetime.timedelta(hours=24)
    )


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    _seed_dev_auth_user()
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
        erp_app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        yield s


def _set_active(company_id: int | None):
    if company_id is None:
        sys.modules["streamlit"].session_state.pop("active_company_id", None)
    else:
        sys.modules["streamlit"].session_state["active_company_id"] = company_id


def _company(session, *, name: str, slug: str):
    co = models.Company(
        name=name,
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    session.add(co)
    session.flush()
    seed_chart_of_accounts_for_company(session, co.id)
    set_setting(session, "banking.bank_charges_enabled", True, company_id=co.id)
    return co


def _bank(session, company_id, *, name="Main TRY"):
    ba = models.BankAccount(
        name=name,
        currency="TRY",
        company_id=company_id,
        is_active=True,
        balance=0.0,
    )
    session.add(ba)
    session.flush()
    return ba


def _stmt_row(session, company_id, bank_account_id, *, credit=True, amount=250.0):
    imp = models.BankStatementImport(
        company_id=company_id,
        bank_account_id=bank_account_id,
        file_name="stmt.csv",
        file_hash="stamp-hash",
        file_size=10,
        file_path="/tmp/stmt.csv",
        status="staging",
        import_date=datetime.date.today(),
        row_count=1,
        valid_count=1,
        flagged_count=0,
        error_count=0,
        currency="TRY",
        created_at=datetime.datetime.now(),
    )
    session.add(imp)
    session.flush()
    row = models.BankStatementRow(
        bank_statement_import_id=imp.id,
        status="staging",
        import_row_index=1,
        date=datetime.date.today(),
        description="Deposit test",
        debit_amount=None if credit else amount,
        credit_amount=amount if credit else None,
        amount=amount,
        currency="TRY",
        original_amount=amount,
        parsed_successfully=True,
        created_at=datetime.datetime.now(),
    )
    session.add(row)
    session.flush()
    return row, imp


class TestReconciliationCompanyStamp:
    def test_generic_deposit_je_uses_explicit_company_not_ambient(self, db):
        """PS-P6-5: JE must match explicit company_id even when ambient differs."""
        co_a = _company(db, name="Stamp Co A", slug="stamp_a")
        co_b = _company(db, name="Stamp Co B", slug="stamp_b")
        db.commit()

        _set_active(co_b.id)
        ba_b = _bank(db, co_b.id)
        row, imp = _stmt_row(db, co_b.id, ba_b.id, credit=True, amount=300.0)
        imp_id = imp.id
        db.commit()

        _set_active(co_a.id)
        result = post_generic_deposit(
            db,
            row_id=row.id,
            company_id=co_b.id,
            credit_account_name="Sales Revenue",
            user_id=1,
        )
        db.refresh(row)
        db.refresh(imp)

        je = db.get(models.JournalEntry, result["journal_entry_id"])
        btxn = db.get(models.BankTransaction, result["bank_transaction_id"])

        assert je is not None
        assert je.company_id == co_b.id
        assert je.company_id != co_a.id
        assert btxn.company_id == co_b.id
        assert imp.company_id == co_b.id
        assert imp.id == imp_id
        assert row.posted_journal_entry_id == je.id
        assert row.bank_transaction_id == btxn.id

    def test_bank_charge_je_and_btxn_share_explicit_company(self, db):
        co_a = _company(db, name="Fee Co A", slug="fee_a")
        co_b = _company(db, name="Fee Co B", slug="fee_b")
        db.commit()

        _set_active(co_b.id)
        ba_b = _bank(db, co_b.id)
        row, imp = _stmt_row(
            db, co_b.id, ba_b.id, credit=False, amount=15.0
        )
        row.description = "Bank commission fee"
        db.commit()

        _set_active(co_a.id)
        result = post_bank_charge_outflow(
            db,
            row_id=row.id,
            company_id=co_b.id,
            user_id=1,
        )

        je = db.get(models.JournalEntry, result["journal_entry_id"])
        btxn = db.get(models.BankTransaction, result["bank_transaction_id"])

        assert je.company_id == co_b.id
        assert btxn.company_id == co_b.id
        assert imp.company_id == co_b.id

    def test_single_company_behavior_unchanged_when_ambient_matches_explicit(self, db):
        co = _company(db, name="Single Stamp Co", slug="single_stamp")
        db.commit()
        _set_active(co.id)
        ba = _bank(db, co.id)
        row, _imp = _stmt_row(db, co.id, ba.id, credit=True, amount=120.0)
        db.commit()

        result = post_generic_deposit(
            db,
            row_id=row.id,
            company_id=co.id,
            credit_account_name="Sales Revenue",
            user_id=1,
        )
        je = db.get(models.JournalEntry, result["journal_entry_id"])
        btxn = db.get(models.BankTransaction, result["bank_transaction_id"])

        assert je.company_id == co.id
        assert btxn.company_id == co.id
        assert row.status == "posted"

    def test_create_journal_entry_shim_accepts_explicit_company_id(self, db):
        co_a = _company(db, name="Shim A", slug="shim_a")
        co_b = _company(db, name="Shim B", slug="shim_b")
        db.commit()
        _set_active(co_a.id)

        from services import posting

        cash_b = posting.get_account_by_name(db, "Cash", company_id=co_b.id)
        revenue_b = posting.get_account_by_name(db, "Sales Revenue", company_id=co_b.id)

        je = erp_app.create_journal_entry(
            db,
            datetime.date.today(),
            "Explicit company shim test",
            "Characterization",
            None,
            [(cash_b.id, 10.0, 0), (revenue_b.id, 0, 10.0)],
            company_id=co_b.id,
        )
        assert je.company_id == co_b.id
        assert je.company_id != co_a.id
