"""BANKING-SERVICE-01 BS-04 — manual banking path parity regression guard.

Pins ``render_banking`` manual deposit/withdrawal/transfer behavior against
``services.write_banking.create_manual_bank_transaction`` after BS-04 wired
Streamlit to the write service (BS-04-CHAR baseline).
"""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import Session, sessionmaker

import app as erp_app
import models
from db import Base
from registry.coa_seed import seed_chart_of_accounts_for_company
from services import audit as audit_svc
from services.write_banking import (
    BANK_NOT_FOUND_MSG,
    CC_MANUAL_DEPOSIT_MSG,
    CC_TRANSFER_MSG,
    DEST_ACCOUNT_MSG,
    INVALID_AMOUNT_MSG,
    create_manual_bank_transaction,
)

if "streamlit" not in sys.modules:
    from unittest.mock import MagicMock

    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

import streamlit as st

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True

CHAR_MARKER = "BS-04"
CHAR_MODULE = Path(__file__).resolve()
APP_SRC = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
WRITE_BANKING_SRC = (
    Path(__file__).resolve().parents[1] / "services" / "write_banking.py"
).read_text(encoding="utf-8")

POST_DATE = datetime.date(2026, 6, 15)
AMOUNT = 250.0
CURRENCY = "TRY"
NOTES = "BS-04 char manual txn"
PERFORMED_BY = "admin"


def _make_session() -> tuple[Session, sessionmaker]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp_company(sess, ctx, instances):
        erp_app._stamp_company_id_on_new_objects(sess, ctx, instances)

    return Session(), Session


def _seed_manual_bank_env(session: Session) -> dict[str, Any]:
    co_a = models.Company(
        name="Co A BS04",
        slug="co_a_bs04",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_b = models.Company(
        name="Co B BS04",
        slug="co_b_bs04",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    session.add_all([co_a, co_b])
    session.flush()
    seed_chart_of_accounts_for_company(session, co_a.id)
    seed_chart_of_accounts_for_company(session, co_b.id)

    bank_a = models.BankAccount(
        name="Main Bank",
        currency=CURRENCY,
        company_id=co_a.id,
        is_active=True,
        balance=5000.0,
        kind="bank",
    )
    cash_a = models.BankAccount(
        name="Office Cash",
        currency=CURRENCY,
        company_id=co_a.id,
        is_active=True,
        balance=1000.0,
        kind="bank",
    )
    bank_b = models.BankAccount(
        name="Other Co Bank",
        currency=CURRENCY,
        company_id=co_b.id,
        is_active=True,
        balance=5000.0,
        kind="bank",
    )
    cc_a = models.BankAccount(
        name="Company Card",
        currency=CURRENCY,
        company_id=co_a.id,
        is_active=True,
        balance=0.0,
        kind="credit_card",
    )
    session.add_all([bank_a, cash_a, bank_b, cc_a])
    session.commit()
    return {
        "company_id": co_a.id,
        "other_company_id": co_b.id,
        "bank_account_id": bank_a.id,
        "cash_account_id": cash_a.id,
        "other_bank_account_id": bank_b.id,
        "cc_account_id": cc_a.id,
        "initial_balances": {
            "Main Bank": 5000.0,
            "Office Cash": 1000.0,
            "Other Co Bank": 5000.0,
            "Company Card": 0.0,
        },
    }


def streamlit_render_banking_manual_submit(
    session: Session,
    *,
    company_id: int,
    bank_account_id: int,
    entry_date: datetime.date,
    transaction_type: str,
    amount: float | None,
    destination_bank_account_id: int | None = None,
    notes: str = "",
) -> None:
    """Mirror ``render_banking`` manual form submit after BS-04 (write_banking)."""
    st.session_state["active_company_id"] = company_id

    if amount is None or amount <= 0:
        raise ValueError(INVALID_AMOUNT_MSG)

    acct = session.get(models.BankAccount, bank_account_id)
    if acct is None:
        raise RuntimeError("Streamlit manual path assumes account from cq() dropdown")

    dest_id = None
    if transaction_type == "transfer":
        if destination_bank_account_id is None:
            raise ValueError(DEST_ACCOUNT_MSG)
        dest = session.get(models.BankAccount, destination_bank_account_id)
        if dest is None or dest.id == acct.id:
            raise ValueError(DEST_ACCOUNT_MSG)
        dest_id = dest.id

    create_manual_bank_transaction(
        session,
        company_id=company_id,
        performed_by=PERFORMED_BY,
        entry_date=entry_date,
        amount=amount,
        transaction_type=transaction_type,
        bank_account_id=bank_account_id,
        destination_bank_account_id=dest_id,
        currency=acct.currency,
        notes=notes,
    )


def _bank_balances_by_name(session: Session) -> dict[str, float]:
    return {
        acct.name: round(acct.balance or 0.0, 2)
        for acct in session.query(models.BankAccount).order_by(models.BankAccount.id).all()
    }


def _bank_txn_fingerprint(session: Session) -> list[tuple[Any, ...]]:
    acct_names = {
        a.id: a.name for a in session.query(models.BankAccount).all()
    }
    rows = (
        session.query(models.BankTransaction)
        .order_by(
            models.BankTransaction.date,
            models.BankTransaction.type,
            models.BankTransaction.amount,
            models.BankTransaction.description,
        )
        .all()
    )
    return [
        (
            acct_names[r.account_id],
            str(r.date),
            r.type,
            round(r.amount, 2),
            r.description,
            r.company_id,
            r.is_void,
        )
        for r in rows
    ]


def _gl_fingerprint(session: Session, company_id: int) -> list[tuple[Any, ...]]:
    coa_names = {
        a.id: a.account_name
        for a in session.query(models.ChartOfAccounts).filter_by(company_id=company_id).all()
    }
    out: list[tuple[Any, ...]] = []
    entries = (
        session.query(models.JournalEntry)
        .filter_by(company_id=company_id)
        .order_by(models.JournalEntry.id)
        .all()
    )
    for je in entries:
        lines = (
            session.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=je.id)
            .order_by(models.JournalEntryLine.id)
            .all()
        )
        for ln in lines:
            out.append(
                (
                    je.reference_type,
                    coa_names.get(ln.account_id, ln.account_id),
                    round(ln.debit or 0.0, 2),
                    round(ln.credit or 0.0, 2),
                )
            )
    return out


def _manual_parity_fingerprint(session: Session, company_id: int) -> dict[str, Any]:
    return {
        "balances": _bank_balances_by_name(session),
        "bank_txns": _bank_txn_fingerprint(session),
        "gl_lines": _gl_fingerprint(session, company_id),
    }


def _fresh_env() -> tuple[Session, dict[str, Any]]:
    _, Session = _make_session()
    session = Session()
    env = _seed_manual_bank_env(session)
    return session, env


def _run_streamlit(
    session: Session,
    env: dict[str, Any],
    *,
    transaction_type: str,
    bank_account_id: int | None = None,
    destination_bank_account_id: int | None = None,
    amount: float | None = AMOUNT,
    notes: str = NOTES,
) -> None:
    streamlit_render_banking_manual_submit(
        session,
        company_id=env["company_id"],
        bank_account_id=bank_account_id or env["bank_account_id"],
        entry_date=POST_DATE,
        transaction_type=transaction_type,
        amount=amount,
        destination_bank_account_id=destination_bank_account_id,
        notes=notes,
    )


def _run_service(
    session: Session,
    env: dict[str, Any],
    *,
    transaction_type: str,
    bank_account_id: int | None = None,
    destination_bank_account_id: int | None = None,
    amount: float = AMOUNT,
    notes: str = NOTES,
) -> None:
    create_manual_bank_transaction(
        session,
        company_id=env["company_id"],
        performed_by=PERFORMED_BY,
        entry_date=POST_DATE,
        amount=amount,
        transaction_type=transaction_type,
        bank_account_id=bank_account_id or env["bank_account_id"],
        destination_bank_account_id=destination_bank_account_id,
        currency=CURRENCY,
        notes=notes,
    )


def _assert_manual_parity(
    streamlit_fp: dict[str, Any],
    service_fp: dict[str, Any],
) -> None:
    assert streamlit_fp["balances"] == service_fp["balances"]
    assert streamlit_fp["bank_txns"] == service_fp["bank_txns"]
    assert streamlit_fp["gl_lines"] == service_fp["gl_lines"]


class TestBS04CharContract:
    def test_module_marker_present(self):
        text = CHAR_MODULE.read_text(encoding="utf-8")
        assert CHAR_MARKER in text
        assert "parity" in text.lower()

    def test_render_banking_manual_submit_delegates_to_write_banking(self):
        start = APP_SRC.index('key="bank_txn_form"')
        end = APP_SRC.index('st.subheader(_t("bank.txn_history")')
        block = APP_SRC[start:end]
        assert "create_manual_bank_transaction" in block
        assert "apply_account_balance_delta" not in block
        assert "post_bank_transaction(session" not in block
        assert "post_bank_transfer(session" not in block

    def test_write_banking_service_exists(self):
        assert "def create_manual_bank_transaction" in WRITE_BANKING_SRC


class TestManualDepositParity:
    def test_deposit_gl_subledger_and_balance_delta_match_service(self):
        sl_sess, sl_env = _fresh_env()
        svc_sess, svc_env = _fresh_env()
        try:
            _run_streamlit(sl_sess, sl_env, transaction_type="deposit")
            _run_service(svc_sess, svc_env, transaction_type="deposit")
            sl_fp = _manual_parity_fingerprint(sl_sess, sl_env["company_id"])
            svc_fp = _manual_parity_fingerprint(svc_sess, svc_env["company_id"])
            _assert_manual_parity(sl_fp, svc_fp)
            assert sl_fp["balances"]["Main Bank"] == pytest.approx(5250.0)
            assert len(sl_fp["bank_txns"]) == 1
            assert sl_fp["bank_txns"][0][2] == "deposit"
            assert len(sl_fp["gl_lines"]) == 2
            assert sl_fp["gl_lines"][0][0] == "BankDeposit"
        finally:
            sl_sess.close()
            svc_sess.close()


class TestManualWithdrawalParity:
    def test_withdrawal_gl_subledger_and_balance_delta_match_service(self):
        sl_sess, sl_env = _fresh_env()
        svc_sess, svc_env = _fresh_env()
        try:
            _run_streamlit(sl_sess, sl_env, transaction_type="withdrawal")
            _run_service(svc_sess, svc_env, transaction_type="withdrawal")
            sl_fp = _manual_parity_fingerprint(sl_sess, sl_env["company_id"])
            svc_fp = _manual_parity_fingerprint(svc_sess, svc_env["company_id"])
            _assert_manual_parity(sl_fp, svc_fp)
            assert sl_fp["balances"]["Main Bank"] == pytest.approx(4750.0)
            assert sl_fp["bank_txns"][0][2] == "withdrawal"
            assert sl_fp["gl_lines"][0][0] == "BankWithdrawal"
        finally:
            sl_sess.close()
            svc_sess.close()

    def test_cc_withdrawal_subledger_only_no_je_parity(self):
        sl_sess, sl_env = _fresh_env()
        svc_sess, svc_env = _fresh_env()
        try:
            _run_streamlit(
                sl_sess,
                sl_env,
                transaction_type="withdrawal",
                bank_account_id=sl_env["cc_account_id"],
            )
            _run_service(
                svc_sess,
                svc_env,
                transaction_type="withdrawal",
                bank_account_id=svc_env["cc_account_id"],
            )
            sl_fp = _manual_parity_fingerprint(sl_sess, sl_env["company_id"])
            svc_fp = _manual_parity_fingerprint(svc_sess, svc_env["company_id"])
            _assert_manual_parity(sl_fp, svc_fp)
            assert sl_fp["balances"]["Company Card"] == pytest.approx(AMOUNT)
            assert sl_fp["gl_lines"] == []
        finally:
            sl_sess.close()
            svc_sess.close()


class TestManualTransferParity:
    def test_transfer_paired_txns_balances_and_je_match_service(self):
        sl_sess, sl_env = _fresh_env()
        svc_sess, svc_env = _fresh_env()
        try:
            _run_streamlit(
                sl_sess,
                sl_env,
                transaction_type="transfer",
                destination_bank_account_id=sl_env["cash_account_id"],
            )
            _run_service(
                svc_sess,
                svc_env,
                transaction_type="transfer",
                destination_bank_account_id=svc_env["cash_account_id"],
            )
            sl_fp = _manual_parity_fingerprint(sl_sess, sl_env["company_id"])
            svc_fp = _manual_parity_fingerprint(svc_sess, svc_env["company_id"])
            _assert_manual_parity(sl_fp, svc_fp)
            assert sl_fp["balances"]["Main Bank"] == pytest.approx(4750.0)
            assert sl_fp["balances"]["Office Cash"] == pytest.approx(1250.0)
            assert len(sl_fp["bank_txns"]) == 2
            dest_desc = next(t for t in sl_fp["bank_txns"] if t[0] == "Office Cash")
            assert dest_desc[4].startswith("Transfer from Main Bank:")
            assert len(sl_fp["gl_lines"]) == 2
            assert sl_fp["gl_lines"][0][0] == "BankTransfer"
        finally:
            sl_sess.close()
            svc_sess.close()


class TestValidationErrorParity:
    @pytest.mark.parametrize(
        "runner,kwargs",
        [
            ("streamlit", {"amount": 0}),
            ("service", {"amount": 0}),
        ],
    )
    def test_invalid_amount(self, runner, kwargs):
        session, env = _fresh_env()
        try:
            with pytest.raises(ValueError, match=INVALID_AMOUNT_MSG):
                if runner == "streamlit":
                    _run_streamlit(session, env, transaction_type="deposit", **kwargs)
                else:
                    _run_service(session, env, transaction_type="deposit", **kwargs)
        finally:
            session.close()

    @pytest.mark.parametrize("runner", ["streamlit", "service"])
    def test_missing_destination_for_transfer(self, runner):
        session, env = _fresh_env()
        try:
            with pytest.raises(ValueError, match=DEST_ACCOUNT_MSG):
                if runner == "streamlit":
                    _run_streamlit(
                        session,
                        env,
                        transaction_type="transfer",
                        destination_bank_account_id=None,
                    )
                else:
                    _run_service(
                        session,
                        env,
                        transaction_type="transfer",
                        destination_bank_account_id=None,
                    )
        finally:
            session.close()

    @pytest.mark.parametrize("runner", ["streamlit", "service"])
    def test_same_source_and_dest_transfer(self, runner):
        session, env = _fresh_env()
        try:
            with pytest.raises(ValueError, match=DEST_ACCOUNT_MSG):
                if runner == "streamlit":
                    _run_streamlit(
                        session,
                        env,
                        transaction_type="transfer",
                        destination_bank_account_id=env["bank_account_id"],
                    )
                else:
                    _run_service(
                        session,
                        env,
                        transaction_type="transfer",
                        destination_bank_account_id=env["bank_account_id"],
                    )
        finally:
            session.close()

    @pytest.mark.parametrize("runner", ["streamlit", "service"])
    def test_cc_manual_deposit_rejected(self, runner):
        session, env = _fresh_env()
        try:
            with pytest.raises(ValueError, match=re.escape(CC_MANUAL_DEPOSIT_MSG)):
                if runner == "streamlit":
                    _run_streamlit(
                        session,
                        env,
                        transaction_type="deposit",
                        bank_account_id=env["cc_account_id"],
                    )
                else:
                    _run_service(
                        session,
                        env,
                        transaction_type="deposit",
                        bank_account_id=env["cc_account_id"],
                    )
        finally:
            session.close()

    @pytest.mark.parametrize("runner", ["streamlit", "service"])
    def test_cc_transfer_source_rejected(self, runner):
        session, env = _fresh_env()
        try:
            with pytest.raises(ValueError, match=CC_TRANSFER_MSG):
                if runner == "streamlit":
                    _run_streamlit(
                        session,
                        env,
                        transaction_type="transfer",
                        bank_account_id=env["cc_account_id"],
                        destination_bank_account_id=env["cash_account_id"],
                    )
                else:
                    _run_service(
                        session,
                        env,
                        transaction_type="transfer",
                        bank_account_id=env["cc_account_id"],
                        destination_bank_account_id=env["cash_account_id"],
                    )
        finally:
            session.close()

    def test_service_missing_bank_account(self):
        session, env = _fresh_env()
        try:
            with pytest.raises(ValueError, match=BANK_NOT_FOUND_MSG):
                create_manual_bank_transaction(
                    session,
                    company_id=env["company_id"],
                    performed_by=PERFORMED_BY,
                    entry_date=POST_DATE,
                    amount=AMOUNT,
                    transaction_type="deposit",
                    bank_account_id=99999,
                )
            assert session.query(models.BankTransaction).count() == 0
        finally:
            session.close()

    def test_service_rejects_other_company_bank_account(self):
        session, env = _fresh_env()
        try:
            with pytest.raises(ValueError, match=BANK_NOT_FOUND_MSG):
                create_manual_bank_transaction(
                    session,
                    company_id=env["company_id"],
                    performed_by=PERFORMED_BY,
                    entry_date=POST_DATE,
                    amount=AMOUNT,
                    transaction_type="deposit",
                    bank_account_id=env["other_bank_account_id"],
                )
            assert session.query(models.BankTransaction).count() == 0
        finally:
            session.close()


class TestCompanyScoping:
    def test_active_company_deposit_does_not_touch_other_company_balances(self):
        session, env = _fresh_env()
        try:
            _run_service(session, env, transaction_type="deposit")
            balances = _bank_balances_by_name(session)
            assert balances["Other Co Bank"] == pytest.approx(5000.0)
            assert balances["Main Bank"] == pytest.approx(5250.0)
        finally:
            session.close()

    def test_streamlit_active_company_stamp_on_manual_txn(self):
        session, env = _fresh_env()
        try:
            _run_streamlit(session, env, transaction_type="deposit")
            txn = session.query(models.BankTransaction).one()
            assert txn.company_id == env["company_id"]
        finally:
            session.close()


class TestAuditBehavior:
    def test_manual_submit_records_create_audit_via_write_banking(self):
        session, env = _fresh_env()
        try:
            _run_streamlit(session, env, transaction_type="deposit")
            audit_rows = session.query(models.AuditLog).all()
            assert len(audit_rows) == 1
            row = audit_rows[0]
            assert row.action == audit_svc.ACTION_CREATE
            assert row.entity_type == audit_svc.ENTITY_BANK_TRANSACTION
            assert row.company_id == env["company_id"]
            assert row.performed_by == PERFORMED_BY
            assert "Bank Deposit" in row.description
            assert "Main Bank" in row.description
        finally:
            session.close()

    def test_service_transfer_audit_entity_is_source_txn(self):
        session, env = _fresh_env()
        try:
            result = create_manual_bank_transaction(
                session,
                company_id=env["company_id"],
                performed_by=PERFORMED_BY,
                entry_date=POST_DATE,
                amount=AMOUNT,
                transaction_type="transfer",
                bank_account_id=env["bank_account_id"],
                destination_bank_account_id=env["cash_account_id"],
                currency=CURRENCY,
                notes=NOTES,
            )
            audit_row = session.query(models.AuditLog).one()
            assert audit_row.entity_id == result.bank_transaction_id
            assert "Transfer" in audit_row.description
            assert "Main Bank" in audit_row.description
            assert "Office Cash" in audit_row.description
        finally:
            session.close()
