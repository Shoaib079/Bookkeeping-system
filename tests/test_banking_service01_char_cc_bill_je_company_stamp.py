"""BANKING-SERVICE-01 BS-03 — CC bill payment JE company stamp regression guard.

Pins ``reconciliation.company_card.post_credit_card_bill_payment`` JE structure,
GL lines, sub-ledger pairing, balance deltas, and explicit
``services.posting.create_journal_entry(..., company_id=...)`` after BS-03.
"""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import Session, sessionmaker

import app as erp_app
import models
from services.money import money_to_float
from db import Base
from reconciliation.company_card import post_credit_card_bill_payment
from reconciliation.match_post import MatchPostError
from registry.coa_seed import seed_chart_of_accounts_for_company
from registry.service import set_setting
from utc_datetime import utc_now_naive

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

import streamlit as st

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True

CHAR_MARKER = "BS-03"
CHAR_MODULE = Path(__file__).resolve()
COMPANY_CARD_SRC = (
    Path(__file__).resolve().parents[1] / "reconciliation" / "company_card.py"
).read_text(encoding="utf-8")

AMOUNT = 275.0
CC_CARD_START = 820.0
BANK_START = 10000.0


def _make_session() -> sessionmaker:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp_company(sess, ctx, instances):
        erp_app._stamp_company_id_on_new_objects(sess, ctx, instances)

    return Session


def _set_active(company_id: int | None) -> None:
    if company_id is None:
        st.session_state.pop("active_company_id", None)
    else:
        st.session_state["active_company_id"] = company_id


def _company(session: Session, *, name: str, slug: str) -> models.Company:
    co = models.Company(
        name=name,
        slug=slug,
        is_active=True,
        created_at=utc_now_naive(),
    )
    session.add(co)
    session.flush()
    seed_chart_of_accounts_for_company(session, co.id)
    set_setting(session, "banking.company_card_enabled", True, company_id=co.id)
    set_setting(session, "banking.reconciliation_enabled", True, company_id=co.id)
    return co


def _bank_account(
    session: Session,
    company_id: int,
    *,
    kind: str = "bank",
    name: str = "Main TRY",
    balance: float | None = None,
) -> models.BankAccount:
    if balance is None:
        balance = BANK_START if kind == "bank" else CC_CARD_START
    ba = models.BankAccount(
        name=name,
        currency="TRY",
        company_id=company_id,
        is_active=True,
        balance=balance,
        kind=kind,
    )
    session.add(ba)
    session.flush()
    return ba


def _stmt_row(
    session: Session,
    company_id: int,
    bank_account_id: int,
    *,
    amount: float = AMOUNT,
    desc: str = "KK ODEME BS03",
    credit: bool = False,
) -> models.BankStatementRow:
    imp = models.BankStatementImport(
        company_id=company_id,
        bank_account_id=bank_account_id,
        file_name="bs03.csv",
        file_hash=f"hash-{company_id}-{bank_account_id}-{amount}",
        file_size=10,
        file_path="/tmp/bs03.csv",
        status="staging",
        import_date=datetime.date(2026, 6, 15),
        row_count=1,
        valid_count=1,
        flagged_count=0,
        error_count=0,
        currency="TRY",
        created_at=utc_now_naive(),
    )
    session.add(imp)
    session.flush()
    row = models.BankStatementRow(
        bank_statement_import_id=imp.id,
        status="staging",
        import_row_index=1,
        date=datetime.date(2026, 6, 15),
        description=desc,
        debit_amount=None if credit else amount,
        credit_amount=amount if credit else None,
        amount=amount,
        currency="TRY",
        original_amount=amount,
        parsed_successfully=True,
        created_at=utc_now_naive(),
    )
    session.add(row)
    session.flush()
    return row


def _post_bill(
    session: Session,
    *,
    company_id: int,
    row_id: int,
    credit_card_account_id: int,
) -> dict[str, Any]:
    return post_credit_card_bill_payment(
        session,
        row_id=row_id,
        company_id=company_id,
        credit_card_account_id=credit_card_account_id,
        user_id=None,
    )


def _gl_account(session: Session, company_id: int, name: str) -> models.ChartOfAccounts:
    return (
        session.query(models.ChartOfAccounts)
        .filter_by(account_name=name, company_id=company_id)
        .one()
    )


def _je_fingerprint(session: Session, je_id: int) -> dict[str, Any]:
    je = session.get(models.JournalEntry, je_id)
    assert je is not None
    lines = (
        session.query(models.JournalEntryLine)
        .filter_by(journal_entry_id=je.id)
        .order_by(models.JournalEntryLine.id)
        .all()
    )
    coa_names = {
        a.id: a.account_name
        for a in session.query(models.ChartOfAccounts)
        .filter_by(company_id=je.company_id)
        .all()
    }
    return {
        "reference_type": je.reference_type,
        "reference_id": je.reference_id,
        "company_id": je.company_id,
        "entry_date": str(je.entry_date),
        "description": je.description,
        "lines": [
            (
                coa_names.get(ln.account_id, ln.account_id),
                round(ln.debit or 0.0, 2),
                round(ln.credit or 0.0, 2),
            )
            for ln in lines
        ],
    }


def _bank_txn_fingerprint(session: Session, txn_id: int) -> dict[str, Any]:
    txn = session.get(models.BankTransaction, txn_id)
    assert txn is not None
    acct = session.get(models.BankAccount, txn.account_id)
    return {
        "account_name": acct.name if acct else None,
        "account_kind": acct.kind if acct else None,
        "date": str(txn.date),
        "amount": round(txn.amount, 2),
        "type": txn.type,
        "description": txn.description,
        "company_id": txn.company_id,
        "statement_ref": txn.statement_ref,
        "is_reconciled": txn.is_reconciled,
        "is_void": txn.is_void,
    }


@pytest.fixture()
def db():
    Session = _make_session()
    st.session_state.clear()
    with Session() as session:
        yield session


@pytest.fixture()
def seeded(db: Session):
    co = _company(db, name="Co BS03", slug="co_bs03")
    db.commit()
    _set_active(co.id)
    bank = _bank_account(db, co.id, kind="bank", name="Main TRY")
    card = _bank_account(db, co.id, kind="credit_card", name="Company Visa")
    row = _stmt_row(db, co.id, bank.id)
    db.commit()
    return {
        "company_id": co.id,
        "bank": bank,
        "card": card,
        "row": row,
    }


class TestBS03CharContract:
    def test_bs03_doc_exists(self):
        doc = Path(__file__).resolve().parents[1] / "docs" / "BANKING_SERVICE_01_BS03.md"
        assert doc.exists()
        text = doc.read_text(encoding="utf-8").lower()
        assert "create_journal_entry" in text
        assert "company_id" in text

    def test_module_marker_present(self):
        text = CHAR_MODULE.read_text(encoding="utf-8")
        assert CHAR_MARKER in text
        assert "parity" in text.lower() or "regression" in text.lower()

    def test_post_uses_posting_service_create_journal_entry_with_company_id(self):
        fn_block = COMPANY_CARD_SRC.split("def post_credit_card_bill_payment", 1)[1].split(
            "def void_credit_card_bill_payment", 1
        )[0]
        assert "posting_svc.create_journal_entry(" in fn_block
        assert "company_id=company_id" in fn_block
        assert "app.create_journal_entry(" not in fn_block
        assert "app = _app()" not in fn_block

    def test_post_uses_posting_service_get_account_by_name(self):
        fn_block = COMPANY_CARD_SRC.split("def post_credit_card_bill_payment", 1)[1].split(
            "def void_credit_card_bill_payment", 1
        )[0]
        assert fn_block.count("posting_svc.get_account_by_name(") >= 2
        assert "company_id=company_id" in fn_block
        assert "app.get_account_by_name" not in fn_block


class TestCCBillPaymentJEStructure:
    def test_je_reference_type_lines_and_description(self, db: Session, seeded: dict):
        result = _post_bill(
            db,
            company_id=seeded["company_id"],
            row_id=seeded["row"].id,
            credit_card_account_id=seeded["card"].id,
        )
        fp = _je_fingerprint(db, result["journal_entry_id"])
        cc_gl = _gl_account(db, seeded["company_id"], "Credit Card Payable")
        bank_gl = _gl_account(db, seeded["company_id"], "Bank")

        assert fp["reference_type"] == "BankStmtCCBillPay"
        assert fp["reference_id"] == seeded["row"].id
        assert fp["entry_date"] == str(seeded["row"].date)
        assert fp["description"] == (
            f"Credit card bill payment — {seeded['card'].name} "
            f"(stmt row {seeded['row'].import_row_index})"
        )
        assert fp["lines"] == [
            ("Credit Card Payable", AMOUNT, 0.0),
            ("Bank", 0.0, AMOUNT),
        ]
        assert fp["lines"][0][0] == cc_gl.account_name
        assert fp["lines"][1][0] == bank_gl.account_name


class TestCCBillPaymentCompanyStamp:
    def test_je_company_id_matches_active_company_when_aligned(self, db: Session, seeded: dict):
        _set_active(seeded["company_id"])
        result = _post_bill(
            db,
            company_id=seeded["company_id"],
            row_id=seeded["row"].id,
            credit_card_account_id=seeded["card"].id,
        )
        je = db.get(models.JournalEntry, result["journal_entry_id"])
        btxn = db.get(models.BankTransaction, result["bank_transaction_id"])
        cc_txn = db.get(models.BankTransaction, result["credit_card_transaction_id"])

        assert je is not None
        assert je.company_id == seeded["company_id"]
        assert btxn.company_id == seeded["company_id"]
        assert cc_txn.company_id == seeded["company_id"]

    def test_je_company_id_uses_explicit_param_not_ambient(self, db: Session):
        """BS-03: JE must match explicit company_id even when ambient differs."""
        co_a = _company(db, name="Ambient Co", slug="ambient_co")
        co_b = _company(db, name="Target Co", slug="target_co")
        db.commit()

        _set_active(co_a.id)
        bank_b = _bank_account(db, co_b.id, kind="bank", name="Target Bank")
        card_b = _bank_account(db, co_b.id, kind="credit_card", name="Target Card")
        row_b = _stmt_row(db, co_b.id, bank_b.id)
        db.commit()

        result = _post_bill(
            db,
            company_id=co_b.id,
            row_id=row_b.id,
            credit_card_account_id=card_b.id,
        )

        je = db.get(models.JournalEntry, result["journal_entry_id"])
        btxn = db.get(models.BankTransaction, result["bank_transaction_id"])
        cc_txn = db.get(models.BankTransaction, result["credit_card_transaction_id"])

        assert je is not None
        assert je.company_id == co_b.id
        assert je.company_id != co_a.id
        assert btxn.company_id == co_b.id
        assert cc_txn.company_id == co_b.id
        cc_gl = _gl_account(db, co_b.id, "Credit Card Payable")
        bank_gl = _gl_account(db, co_b.id, "Bank")
        lines = (
            db.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=je.id)
            .all()
        )
        line_accounts = {ln.account_id for ln in lines}
        assert cc_gl.id in line_accounts
        assert bank_gl.id in line_accounts


class TestCCBillPaymentSubledgerPairing:
    def test_bank_and_card_transactions_paired_to_statement_row(self, db: Session, seeded: dict):
        row = seeded["row"]
        result = _post_bill(
            db,
            company_id=seeded["company_id"],
            row_id=row.id,
            credit_card_account_id=seeded["card"].id,
        )
        db.refresh(row)

        bank_fp = _bank_txn_fingerprint(db, result["bank_transaction_id"])
        cc_fp = _bank_txn_fingerprint(db, result["credit_card_transaction_id"])

        assert bank_fp == {
            "account_name": seeded["bank"].name,
            "account_kind": "bank",
            "date": str(row.date),
            "amount": AMOUNT,
            "type": "withdrawal",
            "description": row.description,
            "company_id": seeded["company_id"],
            "statement_ref": f"bsr:{row.id}",
            "is_reconciled": True,
            "is_void": False,
        }
        assert cc_fp["account_name"] == seeded["card"].name
        assert cc_fp["account_kind"] == "credit_card"
        assert cc_fp["type"] == "deposit"
        assert cc_fp["statement_ref"] == f"bsr:{row.id}:cc"
        assert cc_fp["description"].startswith("Bill payment — stmt row 1")
        assert cc_fp["amount"] == AMOUNT
        assert cc_fp["company_id"] == seeded["company_id"]

        assert row.status == "posted"
        assert row.match_type == "cc_bill_payment"
        assert row.credit_card_account_id == seeded["card"].id
        assert row.posted_journal_entry_id == result["journal_entry_id"]
        assert row.bank_transaction_id == result["bank_transaction_id"]
        assert result["match_type"] == "cc_bill_payment"


class TestCCBillPaymentBalanceDeltas:
    def test_bank_and_card_balances_after_post(self, db: Session, seeded: dict):
        bank_before = money_to_float(seeded["bank"].balance)
        card_before = money_to_float(seeded["card"].balance)

        _post_bill(
            db,
            company_id=seeded["company_id"],
            row_id=seeded["row"].id,
            credit_card_account_id=seeded["card"].id,
        )

        db.refresh(seeded["bank"])
        db.refresh(seeded["card"])
        assert money_to_float(seeded["bank"].balance) == pytest.approx(bank_before - AMOUNT)
        assert money_to_float(seeded["card"].balance) == pytest.approx(card_before - AMOUNT)


class TestCCBillPaymentAuditBehavior:
    def test_post_does_not_write_audit_log(self, db: Session, seeded: dict):
        _post_bill(
            db,
            company_id=seeded["company_id"],
            row_id=seeded["row"].id,
            credit_card_account_id=seeded["card"].id,
        )
        assert db.query(models.AuditLog).count() == 0


class TestCCBillPaymentValidationErrors:
    def test_company_card_disabled(self, db: Session, seeded: dict):
        set_setting(
            db,
            "banking.company_card_enabled",
            False,
            company_id=seeded["company_id"],
        )
        db.commit()
        with pytest.raises(MatchPostError, match=re.escape("Company credit card")):
            _post_bill(
                db,
                company_id=seeded["company_id"],
                row_id=seeded["row"].id,
                credit_card_account_id=seeded["card"].id,
            )

    def test_deposit_row_rejected(self, db: Session, seeded: dict):
        row = _stmt_row(db, seeded["company_id"], seeded["bank"].id, credit=True)
        db.commit()
        with pytest.raises(MatchPostError, match="deposit, not a card bill payment"):
            _post_bill(
                db,
                company_id=seeded["company_id"],
                row_id=row.id,
                credit_card_account_id=seeded["card"].id,
            )

    def test_credit_card_account_not_found(self, db: Session, seeded: dict):
        with pytest.raises(MatchPostError, match="Credit card account not found"):
            _post_bill(
                db,
                company_id=seeded["company_id"],
                row_id=seeded["row"].id,
                credit_card_account_id=99999,
            )

    def test_selected_account_not_credit_card(self, db: Session, seeded: dict):
        with pytest.raises(MatchPostError, match="not a company credit card"):
            _post_bill(
                db,
                company_id=seeded["company_id"],
                row_id=seeded["row"].id,
                credit_card_account_id=seeded["bank"].id,
            )

    def test_statement_import_must_be_bank_account(self, db: Session, seeded: dict):
        cc_bank = _bank_account(
            db,
            seeded["company_id"],
            kind="credit_card",
            name="Card Stmt Acct",
        )
        row = _stmt_row(db, seeded["company_id"], cc_bank.id)
        db.commit()
        with pytest.raises(MatchPostError, match="linked to a bank account"):
            _post_bill(
                db,
                company_id=seeded["company_id"],
                row_id=row.id,
                credit_card_account_id=seeded["card"].id,
            )

    def test_non_positive_amount_rejected(self, db: Session, seeded: dict):
        row = _stmt_row(db, seeded["company_id"], seeded["bank"].id, amount=0.0)
        db.commit()
        with pytest.raises(MatchPostError, match="Payment amount must be positive"):
            _post_bill(
                db,
                company_id=seeded["company_id"],
                row_id=row.id,
                credit_card_account_id=seeded["card"].id,
            )

    def test_missing_gl_accounts(self, db: Session, seeded: dict):
        db.query(models.ChartOfAccounts).filter_by(
            account_name="Credit Card Payable",
            company_id=seeded["company_id"],
        ).delete()
        db.commit()
        with pytest.raises(MatchPostError, match="Credit Card Payable or Bank GL account missing"):
            _post_bill(
                db,
                company_id=seeded["company_id"],
                row_id=seeded["row"].id,
                credit_card_account_id=seeded["card"].id,
            )

    def test_cross_company_credit_card_rejected(self, db: Session, seeded: dict):
        other = _company(db, name="Other Co", slug="other_bs03")
        other_card = _bank_account(db, other.id, kind="credit_card", name="Other Card")
        db.commit()
        with pytest.raises(MatchPostError, match="Credit card account not found"):
            _post_bill(
                db,
                company_id=seeded["company_id"],
                row_id=seeded["row"].id,
                credit_card_account_id=other_card.id,
            )
