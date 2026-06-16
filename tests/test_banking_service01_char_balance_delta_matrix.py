"""BANKING-SERVICE-01 BS-05 — balance delta matrix regression guard.

Pins ``apply_account_balance_delta`` and ``reverse_account_balance_delta`` in
``services.banking_balance`` after BS-05 extraction (BS-05-CHAR baseline).
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, event as sa_event, func
from sqlalchemy.orm import Session, sessionmaker

import app as erp_app
import models
from db import Base
from reconciliation.company_card import (
    apply_account_balance_delta as apply_via_company_card,
    reverse_account_balance_delta as reverse_via_company_card,
)
from services.banking_balance import (
    apply_account_balance_delta,
    reverse_account_balance_delta,
)
from services.money import money_to_float
from registry.coa_seed import seed_chart_of_accounts_for_company
from utc_datetime import utc_now_naive

if "streamlit" not in sys.modules:
    from unittest.mock import MagicMock

    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True

CHAR_MARKER = "BS-05"
CHAR_MODULE = Path(__file__).resolve()
APP_SRC = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
COMPANY_CARD_SRC = (
    Path(__file__).resolve().parents[1] / "reconciliation" / "company_card.py"
).read_text(encoding="utf-8")
BANKING_BALANCE_SRC = (
    Path(__file__).resolve().parents[1] / "services" / "banking_balance.py"
).read_text(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]

AMOUNT = 175.50
START_BANK = 5000.0
START_CC = 820.0


def _acct(
    *,
    kind: str = "bank",
    balance: float = START_BANK,
    company_id: int = 1,
    name: str = "Acct",
) -> models.BankAccount:
    return models.BankAccount(
        name=name,
        currency="TRY",
        company_id=company_id,
        is_active=True,
        balance=balance,
        kind=kind,
    )


def _apply_then_balance(acct: models.BankAccount, txn_type: str, amount: float) -> float:
    apply_account_balance_delta(acct, txn_type, amount)
    return money_to_float(acct.balance)


def _round_trip(acct: models.BankAccount, txn_type: str, amount: float) -> float:
    start = money_to_float(acct.balance)
    apply_account_balance_delta(acct, txn_type, amount)
    reverse_account_balance_delta(acct, txn_type, amount)
    return money_to_float(acct.balance)


@pytest.fixture()
def db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp_company(sess, ctx, instances):
        erp_app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as session:
        yield session


def _seed_company(session: Session) -> int:
    co = models.Company(
        name="Co BS05",
        slug="co_bs05",
        is_active=True,
        created_at=utc_now_naive(),
    )
    session.add(co)
    session.flush()
    seed_chart_of_accounts_for_company(session, co.id)
    session.commit()
    return co.id


class TestBS05CharContract:
    def test_module_marker_present(self):
        text = CHAR_MODULE.read_text(encoding="utf-8")
        assert CHAR_MARKER in text
        assert "regression" in text.lower() or "matrix" in text.lower()

    def test_helpers_defined_in_banking_balance_service(self):
        assert "def apply_account_balance_delta(" in BANKING_BALANCE_SRC
        assert "def reverse_account_balance_delta(" in BANKING_BALANCE_SRC
        assert "def is_credit_card_account(" in BANKING_BALANCE_SRC
        assert "def sync_bank_account_balances(" in BANKING_BALANCE_SRC
        assert (ROOT / "services" / "banking_balance.py").is_file()

    def test_company_card_reexports_banking_balance_helpers(self):
        assert "from services.banking_balance import" in COMPANY_CARD_SRC
        assert "apply_account_balance_delta" in COMPANY_CARD_SRC
        assert "reverse_account_balance_delta" in COMPANY_CARD_SRC
        assert "is_credit_card_account" in COMPANY_CARD_SRC
        assert "def apply_account_balance_delta(" not in COMPANY_CARD_SRC
        assert "def is_credit_card_account(" not in COMPANY_CARD_SRC

    def test_app_imports_apply_via_company_card_compat_path(self):
        assert "from reconciliation.company_card import" in APP_SRC
        assert "apply_account_balance_delta" in APP_SRC

    def test_posting_imports_reverse_via_company_card_compat_path(self):
        posting_src = (ROOT / "services" / "posting.py").read_text(encoding="utf-8")
        assert "reverse_account_balance_delta" in posting_src
        assert "from reconciliation.company_card import" in posting_src

    def test_company_card_reexport_matches_banking_balance(self):
        acct = _acct(kind="bank", balance=START_BANK)
        apply_via_company_card(acct, "withdrawal", AMOUNT)
        expected = round(START_BANK - AMOUNT, 2)
        assert money_to_float(acct.balance) == pytest.approx(expected)
        acct2 = _acct(kind="credit_card", balance=START_CC, name="Visa")
        reverse_via_company_card(acct2, "deposit", AMOUNT)
        assert money_to_float(acct2.balance) == pytest.approx(START_CC + AMOUNT)


class TestApplyAccountBalanceDeltaBank:
    @pytest.mark.parametrize(
        "txn_type,start,expected",
        [
            ("deposit", START_BANK, START_BANK + AMOUNT),
            ("withdrawal", START_BANK, START_BANK - AMOUNT),
            ("transfer", START_BANK, START_BANK - AMOUNT),
        ],
    )
    def test_bank_asset_deltas(self, txn_type: str, start: float, expected: float):
        acct = _acct(kind="bank", balance=start)
        assert _apply_then_balance(acct, txn_type, AMOUNT) == pytest.approx(expected)

    def test_bank_transfer_destination_uses_deposit(self):
        dest = _acct(kind="bank", balance=1000.0, name="Dest")
        assert _apply_then_balance(dest, "deposit", AMOUNT) == pytest.approx(1000.0 + AMOUNT)

    def test_unknown_txn_type_behaves_like_withdrawal_on_bank(self):
        acct = _acct(kind="bank", balance=START_BANK)
        withdrawal = _apply_then_balance(_acct(kind="bank", balance=START_BANK), "withdrawal", AMOUNT)
        unknown = _apply_then_balance(acct, "manual_adjust", AMOUNT)
        assert unknown == pytest.approx(withdrawal)


class TestApplyAccountBalanceDeltaCreditCard:
    @pytest.mark.parametrize(
        "txn_type,start,expected",
        [
            ("withdrawal", START_CC, START_CC + AMOUNT),
            ("transfer", START_CC, START_CC + AMOUNT),
            ("deposit", START_CC, START_CC - AMOUNT),
        ],
    )
    def test_credit_card_liability_deltas(self, txn_type: str, start: float, expected: float):
        acct = _acct(kind="credit_card", balance=start, name="Company Card")
        assert _apply_then_balance(acct, txn_type, AMOUNT) == pytest.approx(expected)

    def test_cc_deposit_models_bill_payment_liability_reduction(self):
        """CC ``deposit`` txn type = payment / liability down (used in bill payment pair)."""
        card = _acct(kind="credit_card", balance=900.0, name="Visa")
        assert _apply_then_balance(card, "deposit", 300.0) == pytest.approx(600.0)

    def test_unknown_txn_type_behaves_like_deposit_on_credit_card(self):
        acct = _acct(kind="credit_card", balance=START_CC, name="Visa")
        deposit = _apply_then_balance(_acct(kind="credit_card", balance=START_CC), "deposit", AMOUNT)
        unknown = _apply_then_balance(acct, "manual_adjust", AMOUNT)
        assert unknown == pytest.approx(deposit)


class TestReverseAccountBalanceDelta:
    @pytest.mark.parametrize("txn_type", ["deposit", "withdrawal", "transfer"])
    def test_bank_round_trip_restores_balance(self, txn_type: str):
        acct = _acct(kind="bank", balance=START_BANK)
        assert _round_trip(acct, txn_type, AMOUNT) == pytest.approx(START_BANK)

    @pytest.mark.parametrize("txn_type", ["deposit", "withdrawal", "transfer"])
    def test_credit_card_round_trip_restores_balance(self, txn_type: str):
        acct = _acct(kind="credit_card", balance=START_CC, name="Visa")
        assert _round_trip(acct, txn_type, AMOUNT) == pytest.approx(START_CC)

    def test_reverse_is_inverse_of_apply_on_bank(self):
        acct = _acct(kind="bank", balance=START_BANK)
        apply_account_balance_delta(acct, "withdrawal", AMOUNT)
        mid = money_to_float(acct.balance)
        reverse_account_balance_delta(acct, "withdrawal", AMOUNT)
        assert mid == pytest.approx(START_BANK - AMOUNT)
        assert money_to_float(acct.balance) == pytest.approx(START_BANK)

    def test_reverse_is_inverse_of_apply_on_credit_card(self):
        acct = _acct(kind="credit_card", balance=START_CC, name="Visa")
        apply_account_balance_delta(acct, "deposit", AMOUNT)
        mid = money_to_float(acct.balance)
        reverse_account_balance_delta(acct, "deposit", AMOUNT)
        assert mid == pytest.approx(START_CC - AMOUNT)
        assert money_to_float(acct.balance) == pytest.approx(START_CC)


class TestBalanceDeltaPairing:
    def test_transfer_pair_nets_to_zero(self):
        src = _acct(kind="bank", balance=5000.0, name="Main")
        dest = _acct(kind="bank", balance=1200.0, name="Cash", company_id=1)
        total_before = (src.balance or 0) + (dest.balance or 0)

        apply_account_balance_delta(src, "withdrawal", AMOUNT)
        apply_account_balance_delta(dest, "deposit", AMOUNT)

        total_after = (src.balance or 0) + (dest.balance or 0)
        assert src.balance == pytest.approx(5000.0 - AMOUNT)
        assert dest.balance == pytest.approx(1200.0 + AMOUNT)
        assert total_after == pytest.approx(total_before)

    def test_transfer_pair_round_trip_restores_both(self):
        src = _acct(kind="bank", balance=5000.0, name="Main")
        dest = _acct(kind="bank", balance=1200.0, name="Cash")
        src_start, dest_start = src.balance, dest.balance

        apply_account_balance_delta(src, "withdrawal", AMOUNT)
        apply_account_balance_delta(dest, "deposit", AMOUNT)
        reverse_account_balance_delta(dest, "deposit", AMOUNT)
        reverse_account_balance_delta(src, "withdrawal", AMOUNT)

        assert src.balance == pytest.approx(src_start)
        assert dest.balance == pytest.approx(dest_start)

    def test_cc_bill_payment_pair_matches_posting_convention(self):
        """Bank withdrawal + CC deposit — same types used by ``post_credit_card_bill_payment``."""
        bank = _acct(kind="bank", balance=10000.0, name="Main TRY")
        card = _acct(kind="credit_card", balance=800.0, name="Visa")
        bank_before = bank.balance
        card_before = card.balance

        apply_account_balance_delta(bank, "withdrawal", AMOUNT)
        apply_account_balance_delta(card, "deposit", AMOUNT)

        assert bank.balance == pytest.approx(bank_before - AMOUNT)
        assert card.balance == pytest.approx(card_before - AMOUNT)

    def test_cc_bill_payment_pair_void_round_trip(self):
        bank = _acct(kind="bank", balance=10000.0, name="Main TRY")
        card = _acct(kind="credit_card", balance=800.0, name="Visa")
        bank_start, card_start = bank.balance, card.balance

        apply_account_balance_delta(bank, "withdrawal", AMOUNT)
        apply_account_balance_delta(card, "deposit", AMOUNT)
        reverse_account_balance_delta(bank, "withdrawal", AMOUNT)
        reverse_account_balance_delta(card, "deposit", AMOUNT)

        assert bank.balance == pytest.approx(bank_start)
        assert card.balance == pytest.approx(card_start)


class TestBalanceDeltaSafety:
    def test_helpers_do_not_create_journal_entries(self, db: Session):
        company_id = _seed_company(db)
        acct = models.BankAccount(
            name="Main",
            currency="TRY",
            company_id=company_id,
            is_active=True,
            balance=START_BANK,
            kind="bank",
        )
        db.add(acct)
        db.commit()

        je_before = db.query(func.count()).select_from(models.JournalEntry).scalar()
        apply_account_balance_delta(acct, "deposit", AMOUNT)
        db.add(acct)
        db.commit()
        je_after = db.query(func.count()).select_from(models.JournalEntry).scalar()

        assert je_before == 0
        assert je_after == 0

    def test_helpers_do_not_create_audit_log(self, db: Session):
        company_id = _seed_company(db)
        acct = models.BankAccount(
            name="Main",
            currency="TRY",
            company_id=company_id,
            is_active=True,
            balance=START_BANK,
            kind="bank",
        )
        db.add(acct)
        db.commit()

        apply_account_balance_delta(acct, "withdrawal", AMOUNT)
        reverse_account_balance_delta(acct, "withdrawal", AMOUNT)
        db.add(acct)
        db.commit()
        assert db.query(func.count()).select_from(models.AuditLog).scalar() == 0

    def test_helpers_do_not_change_bank_transaction_status(self, db: Session):
        company_id = _seed_company(db)
        acct = models.BankAccount(
            name="Main",
            currency="TRY",
            company_id=company_id,
            is_active=True,
            balance=START_BANK,
            kind="bank",
        )
        db.add(acct)
        db.flush()
        txn = models.BankTransaction(
            account_id=acct.id,
            date=datetime.date(2026, 6, 15),
            amount=AMOUNT,
            type="withdrawal",
            description="Pinned txn",
            company_id=company_id,
            is_void=False,
        )
        db.add(txn)
        db.commit()

        apply_account_balance_delta(acct, "deposit", AMOUNT)
        db.add(acct)
        db.commit()
        db.refresh(txn)

        assert txn.is_void is False
        assert txn.type == "withdrawal"
        assert txn.amount == AMOUNT

    def test_company_isolation_across_accounts(self):
        co_a_bank = _acct(kind="bank", balance=3000.0, company_id=1, name="Co A Bank")
        co_b_bank = _acct(kind="bank", balance=7000.0, company_id=2, name="Co B Bank")
        co_a_start = co_a_bank.balance
        co_b_start = co_b_bank.balance

        apply_account_balance_delta(co_a_bank, "withdrawal", AMOUNT)

        assert co_a_bank.balance == pytest.approx(co_a_start - AMOUNT)
        assert co_b_bank.balance == pytest.approx(co_b_start)

    def test_amount_is_rounded_to_two_decimals(self):
        acct = _acct(kind="bank", balance=100.0)
        apply_account_balance_delta(acct, "deposit", 10.005)
        assert money_to_float(acct.balance) == pytest.approx(110.01)

    def test_none_balance_treated_as_zero(self):
        acct = _acct(kind="bank", balance=0.0)
        acct.balance = None
        apply_account_balance_delta(acct, "deposit", 50.0)
        assert money_to_float(acct.balance) == pytest.approx(50.0)
