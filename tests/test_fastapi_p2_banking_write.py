"""FASTAPI-P2.7 — POST /api/v1/bank-transactions write endpoint."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from api.bearer_auth import BEARER_INVALID_DETAIL, BEARER_MISSING_DETAIL
from api.dependencies import DEV_HEADERS_ENV, get_db
from api.errors import COMPANY_MISSING_MARKER, MEMBERSHIP_DENIED_MARKER
from api.main import create_app
from db import Base
from registry.coa_seed import seed_chart_of_accounts_for_company
from services import audit as audit_svc
from services import commit_modes
from services.commit_modes import CommitMode, POST_BANK_TRANSACTION_FAMILY
from services import tokens as token_service
from tests.fastapi_p1_jwt import TEST_JWT_SECRET, api_headers, password_hash_for_tests
from services.money import money_to_float

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock

POST_DATE = datetime.date(2026, 6, 15)
AMOUNT = 250.0
CURRENCY = "TRY"
WRITE_BANKING_ENV = "ERP_API_WRITE_BANKING"
INVALID_AMOUNT_MSG = "Please enter a valid amount."
BANK_NOT_FOUND_MSG = "Bank account not found."
DEST_ACCOUNT_MSG = "Choose a different destination account for transfer."
CC_MANUAL_DEPOSIT_MSG = (
    "Use **Banking → Statement import** to record a card bill payment (bank debit), "
    "not a manual deposit on the card account."
)
CC_TRANSFER_MSG = (
    "Transfers between bank and credit card accounts are not supported here — "
    "use Match & post for bill payments."
)
BSR_GUARD_MSG = (
    "Statement-linked transactions must be unposted from Bank Reconciliation."
)
CARD_SALE_DESC = "Card Sale INV-001"


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setenv(token_service.JWT_SECRET_ENV, TEST_JWT_SECRET)
    monkeypatch.delenv(DEV_HEADERS_ENV, raising=False)


@pytest.fixture(autouse=True)
def _write_banking_enabled(monkeypatch):
    monkeypatch.setenv(WRITE_BANKING_ENV, "1")


@pytest.fixture(autouse=True)
def _reset_commit_modes():
    commit_modes.reset_commit_modes_for_tests()
    yield
    commit_modes.reset_commit_modes_for_tests()


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        yield s


@pytest.fixture()
def api_client(db):
    app = create_app()

    def _override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def tenant(db):
    owner = models.User(
        username="owner_p27",
        display_name="Owner P27",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    outsider = models.User(
        username="outsider_p27",
        display_name="Outsider P27",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_a = models.Company(
        name="Co A P27",
        slug="co_a_p27",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_b = models.Company(
        name="Co B P27",
        slug="co_b_p27",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add_all([owner, outsider, co_a, co_b])
    db.flush()
    db.add_all(
        [
            models.CompanyUser(
                company_id=co_a.id,
                user_id=owner.id,
                role="owner",
                is_active=True,
                created_at=datetime.datetime.now(),
            ),
            models.CompanyUser(
                company_id=co_b.id,
                user_id=outsider.id,
                role="owner",
                is_active=True,
                created_at=datetime.datetime.now(),
            ),
        ]
    )
    seed_chart_of_accounts_for_company(db, co_a.id)
    seed_chart_of_accounts_for_company(db, co_b.id)
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
    db.add_all([bank_a, cash_a, bank_b, cc_a])
    db.commit()
    return {
        "owner": owner,
        "outsider": outsider,
        "company_id": co_a.id,
        "other_company_id": co_b.id,
        "bank_account_id": bank_a.id,
        "cash_account_id": cash_a.id,
        "other_bank_account_id": bank_b.id,
        "cc_account_id": cc_a.id,
    }


def _bank_payload(**overrides) -> dict:
    base = {
        "date": POST_DATE.isoformat(),
        "amount": AMOUNT,
        "transaction_type": "deposit",
        "bank_account_id": None,
        "notes": "API bank txn",
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}


def _post_bank(client, user, company_id, payload):
    return client.post(
        "/api/v1/bank-transactions",
        json=payload,
        headers=api_headers(user, company_id=company_id),
    )


def _journal_balanced(db) -> bool:
    lines = db.query(models.JournalEntryLine).all()
    deb = round(sum(l.debit or 0 for l in lines), 2)
    cred = round(sum(l.credit or 0 for l in lines), 2)
    return abs(deb - cred) < 0.02 and deb > 0


class TestBankingWriteFeatureFlag:
    def test_disabled_returns_404(self, api_client, tenant, monkeypatch):
        monkeypatch.delenv(WRITE_BANKING_ENV, raising=False)
        payload = _bank_payload(bank_account_id=tenant["bank_account_id"])
        resp = _post_bank(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 404


class TestBankingWriteAuth:
    def test_jwt_required(self, api_client, tenant):
        payload = _bank_payload(bank_account_id=tenant["bank_account_id"])
        resp = api_client.post("/api/v1/bank-transactions", json=payload)
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_MISSING_DETAIL

    def test_invalid_jwt_rejected(self, api_client, tenant):
        payload = _bank_payload(bank_account_id=tenant["bank_account_id"])
        resp = api_client.post(
            "/api/v1/bank-transactions",
            json=payload,
            headers={"Authorization": "Bearer bad.token", "X-Company-Id": "1"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_INVALID_DETAIL

    def test_company_header_required(self, api_client, tenant):
        payload = _bank_payload(bank_account_id=tenant["bank_account_id"])
        resp = api_client.post(
            "/api/v1/bank-transactions",
            json=payload,
            headers=api_headers(tenant["owner"]),
        )
        assert resp.status_code == 400
        assert COMPANY_MISSING_MARKER in resp.json()["detail"]

    def test_user_without_membership_rejected(self, api_client, tenant):
        payload = _bank_payload(bank_account_id=tenant["bank_account_id"])
        resp = _post_bank(api_client, tenant["outsider"], tenant["company_id"], payload)
        assert resp.status_code == 403
        assert MEMBERSHIP_DENIED_MARKER in resp.json()["detail"]


class TestBankingWriteValidation:
    def test_invalid_amount_rejected(self, api_client, tenant, db):
        payload = _bank_payload(bank_account_id=tenant["bank_account_id"], amount=0)
        resp = _post_bank(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 400
        assert resp.json()["detail"] == INVALID_AMOUNT_MSG
        assert db.query(models.BankTransaction).count() == 0

    def test_invalid_transaction_type_rejected(self, api_client, tenant, db):
        payload = _bank_payload(
            bank_account_id=tenant["bank_account_id"],
            transaction_type="payment",
        )
        resp = _post_bank(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 400
        assert "Unknown transaction type" in resp.json()["detail"]

    def test_company_id_in_body_rejected(self, api_client, tenant):
        payload = _bank_payload(bank_account_id=tenant["bank_account_id"])
        payload["company_id"] = tenant["other_company_id"]
        resp = _post_bank(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 422

    def test_same_account_transfer_rejected(self, api_client, tenant, db):
        payload = _bank_payload(
            bank_account_id=tenant["bank_account_id"],
            transaction_type="transfer",
            destination_bank_account_id=tenant["bank_account_id"],
        )
        resp = _post_bank(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 400
        assert resp.json()["detail"] == DEST_ACCOUNT_MSG


class TestBankingWriteDeposit:
    def test_deposit_updates_balance_and_posts_je(self, api_client, tenant, db):
        bank = db.get(models.BankAccount, tenant["bank_account_id"])
        start_bal = money_to_float(bank.balance)
        payload = _bank_payload(
            bank_account_id=tenant["bank_account_id"],
            transaction_type="deposit",
        )
        resp = _post_bank(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["bank_transaction_id"] > 0
        assert body["paired_transaction_id"] is None
        assert body["journal_entry_id"] is not None
        assert body["status"] == "ok"
        assert f"{AMOUNT:,.2f}" in body["message"]

        db.refresh(bank)
        assert money_to_float(bank.balance) == pytest.approx(start_bal + AMOUNT)

        txn = db.get(models.BankTransaction, body["bank_transaction_id"])
        assert txn.type == "deposit"
        assert money_to_float(txn.amount) == AMOUNT
        assert txn.company_id == tenant["company_id"]

        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "BankDeposit"
        assert je.reference_id == txn.id
        assert _journal_balanced(db)

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action=audit_svc.ACTION_CREATE,
                entity_type=audit_svc.ENTITY_BANK_TRANSACTION,
                entity_id=txn.id,
            )
            .one()
        )
        assert "Bank Deposit" in audit.description
        assert bank.name in audit.description


class TestBankingWriteWithdrawal:
    def test_withdrawal_updates_balance_and_posts_je(self, api_client, tenant, db):
        bank = db.get(models.BankAccount, tenant["bank_account_id"])
        start_bal = money_to_float(bank.balance)
        payload = _bank_payload(
            bank_account_id=tenant["bank_account_id"],
            transaction_type="withdrawal",
        )
        resp = _post_bank(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["journal_entry_id"] is not None

        db.refresh(bank)
        assert money_to_float(bank.balance) == pytest.approx(start_bal - AMOUNT)

        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "BankWithdrawal"
        assert _journal_balanced(db)


class TestBankingWriteTransfer:
    def test_transfer_creates_paired_transactions(self, api_client, tenant, db):
        src = db.get(models.BankAccount, tenant["bank_account_id"])
        dest = db.get(models.BankAccount, tenant["cash_account_id"])
        src_start = money_to_float(src.balance)
        dest_start = money_to_float(dest.balance)
        payload = _bank_payload(
            bank_account_id=tenant["bank_account_id"],
            transaction_type="transfer",
            destination_bank_account_id=tenant["cash_account_id"],
        )
        resp = _post_bank(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["paired_transaction_id"] is not None
        assert body["paired_transaction_id"] != body["bank_transaction_id"]

        db.refresh(src)
        db.refresh(dest)
        assert money_to_float(src.balance) == pytest.approx(src_start - AMOUNT)
        assert money_to_float(dest.balance) == pytest.approx(dest_start + AMOUNT)

        src_txn = db.get(models.BankTransaction, body["bank_transaction_id"])
        dest_txn = db.get(models.BankTransaction, body["paired_transaction_id"])
        assert src_txn.type == "transfer"
        assert dest_txn.type == "transfer"
        assert dest_txn.description.startswith(f"Transfer from {src.name}:")

        if body["journal_entry_id"] is not None:
            je = db.get(models.JournalEntry, body["journal_entry_id"])
            assert je.reference_type == "BankTransfer"
            assert _journal_balanced(db)

    def test_same_gl_transfer_has_no_je(self, api_client, tenant, db):
        other_bank = models.BankAccount(
            name="Secondary Bank",
            currency=CURRENCY,
            company_id=tenant["company_id"],
            is_active=True,
            balance=1000.0,
            kind="bank",
        )
        db.add(other_bank)
        db.commit()
        payload = _bank_payload(
            bank_account_id=tenant["bank_account_id"],
            transaction_type="transfer",
            destination_bank_account_id=other_bank.id,
        )
        resp = _post_bank(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["journal_entry_id"] is None
        assert (
            db.query(models.JournalEntry)
            .filter_by(reference_type="BankTransfer")
            .count()
            == 0
        )


class TestBankingWriteRestrictions:
    def test_cc_manual_deposit_rejected(self, api_client, tenant, db):
        payload = _bank_payload(
            bank_account_id=tenant["cc_account_id"],
            transaction_type="deposit",
        )
        resp = _post_bank(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 400
        assert resp.json()["detail"] == CC_MANUAL_DEPOSIT_MSG

    def test_cc_transfer_rejected(self, api_client, tenant, db):
        payload = _bank_payload(
            bank_account_id=tenant["bank_account_id"],
            transaction_type="transfer",
            destination_bank_account_id=tenant["cc_account_id"],
        )
        resp = _post_bank(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 400
        assert resp.json()["detail"] == CC_TRANSFER_MSG

    def test_cc_withdrawal_subledger_only_no_je(self, api_client, tenant, db):
        cc = db.get(models.BankAccount, tenant["cc_account_id"])
        start = money_to_float(cc.balance)
        payload = _bank_payload(
            bank_account_id=tenant["cc_account_id"],
            transaction_type="withdrawal",
        )
        resp = _post_bank(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["journal_entry_id"] is None
        db.refresh(cc)
        assert money_to_float(cc.balance) == pytest.approx(start + AMOUNT)

    def test_statement_linked_void_guard_preserved(self, api_client, tenant, db):
        """Write API creates only; void kernel still blocks statement-linked rows."""
        from services import posting as posting_svc

        txn = models.BankTransaction(
            account_id=tenant["bank_account_id"],
            date=POST_DATE,
            amount=AMOUNT,
            type="deposit",
            description="Imported row",
            statement_ref="bsr:99",
            company_id=tenant["company_id"],
        )
        db.add(txn)
        db.commit()
        with pytest.raises(ValueError, match=BSR_GUARD_MSG):
            posting_svc.void_bank_transaction(
                db, txn.id, "test void", company_id=tenant["company_id"]
            )

    def test_card_sale_deposit_void_guard_preserved(self, api_client, tenant, db):
        from services import posting as posting_svc

        txn = models.BankTransaction(
            account_id=tenant["bank_account_id"],
            date=POST_DATE,
            amount=AMOUNT,
            type="deposit",
            description=CARD_SALE_DESC,
            company_id=tenant["company_id"],
        )
        db.add(txn)
        db.commit()
        assert (
            posting_svc.void_bank_transaction(
                db, txn.id, "test void", company_id=tenant["company_id"]
            )
            is False
        )


class TestBankingWriteCompanyIsolation:
    def test_cannot_use_bank_account_from_another_company(
        self, api_client, tenant, db
    ):
        payload = _bank_payload(bank_account_id=tenant["other_bank_account_id"])
        resp = _post_bank(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 400
        assert resp.json()["detail"] == BANK_NOT_FOUND_MSG
        assert db.query(models.BankTransaction).count() == 0


class TestBankingWriteBoundaryCommit:
    def test_deposit_boundary_mode_single_commit(self, api_client, tenant, db):
        commit_modes.set_commit_mode_for_tests(
            POST_BANK_TRANSACTION_FAMILY, CommitMode.BOUNDARY
        )
        payload = _bank_payload(
            bank_account_id=tenant["bank_account_id"],
            transaction_type="deposit",
        )
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = _post_bank(
                api_client, tenant["owner"], tenant["company_id"], payload
            )
            assert resp.status_code == 201
            assert mock_commit.call_count == 1


class TestBankingWriteNoGetCommits:
    def test_read_get_still_performs_no_commit(self, api_client, tenant, db):
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get(
                "/api/v1/receivables",
                headers=api_headers(tenant["owner"], company_id=tenant["company_id"]),
            )
            assert resp.status_code == 200
            mock_commit.assert_not_called()
