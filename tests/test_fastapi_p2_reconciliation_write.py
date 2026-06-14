"""FASTAPI-P2.8 — POST /api/v1/reconciliation match/unmatch endpoints."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app as erp_app
import models
from api.bearer_auth import BEARER_MISSING_DETAIL
from api.dependencies import DEV_HEADERS_ENV, get_db
from api.errors import COMPANY_MISSING_MARKER, MEMBERSHIP_DENIED_MARKER
from api.main import create_app
from db import Base
from registry.coa_seed import ensure_accounts_for_company, seed_chart_of_accounts_for_company
from registry.service import set_setting
from reconciliation.company_card import post_credit_card_bill_payment
from services import audit as audit_svc
from services import commit_modes
from services.commit_modes import RECONCILIATION_FAMILY, CommitMode
from services import tokens as token_service
from tests.fastapi_p1_jwt import TEST_JWT_SECRET, api_headers, password_hash_for_tests

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock

WRITE_RECON_ENV = "ERP_API_WRITE_RECONCILIATION"
DEPOSIT_AMT = 300.0
FEE_AMT = 15.0
CREDIT_ACCT = "Sales Revenue"
VOID_REASON_REQUIRED_MSG = "Void reason is required."
UNMATCH_NOT_SUPPORTED_MSG = (
    "Only credit card bill payment rows can be unposted with this action."
)
POSTED_OK_MSG = "Posted row #1 to the general ledger."
UNPOSTED_OK_MSG = "Bill payment unposted."


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setenv(token_service.JWT_SECRET_ENV, TEST_JWT_SECRET)
    monkeypatch.delenv(DEV_HEADERS_ENV, raising=False)


@pytest.fixture(autouse=True)
def _write_recon_enabled(monkeypatch):
    monkeypatch.setenv(WRITE_RECON_ENV, "1")


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

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        erp_app._stamp_company_id_on_new_objects(sess, ctx, instances)

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
        username="owner_p28",
        display_name="Owner P28",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    outsider = models.User(
        username="outsider_p28",
        display_name="Outsider P28",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_a = models.Company(
        name="Co A P28",
        slug="co_a_p28",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_b = models.Company(
        name="Co B P28",
        slug="co_b_p28",
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
    ensure_accounts_for_company(db, co_a.id)
    ensure_accounts_for_company(db, co_b.id)
    set_setting(db, "banking.bank_charges_enabled", True, company_id=co_a.id)
    set_setting(db, "banking.company_card_enabled", True, company_id=co_a.id)
    bank_a = models.BankAccount(
        name="Main TRY",
        currency="TRY",
        company_id=co_a.id,
        is_active=True,
        balance=0.0,
        kind="bank",
    )
    bank_b = models.BankAccount(
        name="Other Bank",
        currency="TRY",
        company_id=co_b.id,
        is_active=True,
        balance=0.0,
        kind="bank",
    )
    cc_a = models.BankAccount(
        name="Company Card",
        currency="TRY",
        company_id=co_a.id,
        is_active=True,
        balance=500.0,
        kind="credit_card",
    )
    db.add_all([bank_a, bank_b, cc_a])
    db.commit()
    return {
        "owner": owner,
        "outsider": outsider,
        "company_id": co_a.id,
        "other_company_id": co_b.id,
        "bank_account_id": bank_a.id,
        "other_bank_account_id": bank_b.id,
        "cc_account_id": cc_a.id,
    }


def _stmt_row(
    db,
    *,
    company_id: int,
    bank_account_id: int,
    credit: bool = True,
    amount: float = DEPOSIT_AMT,
    description: str = "Deposit test",
) -> models.BankStatementRow:
    imp = models.BankStatementImport(
        company_id=company_id,
        bank_account_id=bank_account_id,
        file_name="stmt.csv",
        file_hash="p28-recon-hash",
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
    db.add(imp)
    db.flush()
    row = models.BankStatementRow(
        bank_statement_import_id=imp.id,
        status="staging",
        import_row_index=1,
        date=datetime.date.today(),
        description=description,
        debit_amount=None if credit else amount,
        credit_amount=amount if credit else None,
        amount=amount,
        currency="TRY",
        original_amount=amount,
        parsed_successfully=True,
        created_at=datetime.datetime.now(),
    )
    db.add(row)
    db.commit()
    return row


def _match_payload(row_id: int, **overrides) -> dict:
    base = {
        "statement_row_id": row_id,
        "match_type": "generic_deposit",
        "credit_account_name": CREDIT_ACCT,
    }
    base.update(overrides)
    return base


def _post_match(client, user, company_id, payload):
    return client.post(
        "/api/v1/reconciliation/match",
        json=payload,
        headers=api_headers(user, company_id=company_id),
    )


def _post_unmatch(client, user, company_id, row_id, reason="Correction"):
    return client.post(
        "/api/v1/reconciliation/unmatch",
        json={"statement_row_id": row_id, "reason": reason},
        headers=api_headers(user, company_id=company_id),
    )


def _journal_balanced(db) -> bool:
    lines = db.query(models.JournalEntryLine).all()
    deb = round(sum(l.debit or 0 for l in lines), 2)
    cred = round(sum(l.credit or 0 for l in lines), 2)
    return abs(deb - cred) < 0.02 and deb > 0


class TestReconciliationWriteFeatureFlag:
    def test_match_disabled_returns_404(self, api_client, tenant, db, monkeypatch):
        monkeypatch.delenv(WRITE_RECON_ENV, raising=False)
        row = _stmt_row(
            db,
            company_id=tenant["company_id"],
            bank_account_id=tenant["bank_account_id"],
        )
        resp = _post_match(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _match_payload(row.id),
        )
        assert resp.status_code == 404


class TestReconciliationWriteAuth:
    def test_jwt_required(self, api_client, tenant, db):
        row = _stmt_row(
            db,
            company_id=tenant["company_id"],
            bank_account_id=tenant["bank_account_id"],
        )
        resp = api_client.post(
            "/api/v1/reconciliation/match",
            json=_match_payload(row.id),
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_MISSING_DETAIL

    def test_company_header_required(self, api_client, tenant, db):
        row = _stmt_row(
            db,
            company_id=tenant["company_id"],
            bank_account_id=tenant["bank_account_id"],
        )
        resp = api_client.post(
            "/api/v1/reconciliation/match",
            json=_match_payload(row.id),
            headers=api_headers(tenant["owner"]),
        )
        assert resp.status_code == 400
        assert COMPANY_MISSING_MARKER in resp.json()["detail"]

    def test_user_without_membership_rejected(self, api_client, tenant, db):
        row = _stmt_row(
            db,
            company_id=tenant["company_id"],
            bank_account_id=tenant["bank_account_id"],
        )
        resp = _post_match(
            api_client,
            tenant["outsider"],
            tenant["company_id"],
            _match_payload(row.id),
        )
        assert resp.status_code == 403
        assert MEMBERSHIP_DENIED_MARKER in resp.json()["detail"]


class TestReconciliationWriteValidation:
    def test_invalid_match_type_rejected(self, api_client, tenant, db):
        row = _stmt_row(
            db,
            company_id=tenant["company_id"],
            bank_account_id=tenant["bank_account_id"],
        )
        resp = _post_match(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _match_payload(row.id, match_type="unknown_kind"),
        )
        assert resp.status_code == 400
        assert "Unknown reconciliation match type" in resp.json()["detail"]

    def test_company_id_in_body_rejected(self, api_client, tenant, db):
        row = _stmt_row(
            db,
            company_id=tenant["company_id"],
            bank_account_id=tenant["bank_account_id"],
        )
        payload = _match_payload(row.id)
        payload["company_id"] = tenant["other_company_id"]
        resp = _post_match(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 422

    def test_unmatch_reason_required(self, api_client, tenant, db):
        row = _stmt_row(
            db,
            company_id=tenant["company_id"],
            bank_account_id=tenant["bank_account_id"],
        )
        resp = _post_unmatch(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            row.id,
            reason="   ",
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == VOID_REASON_REQUIRED_MSG


class TestReconciliationWriteMatch:
    def test_generic_deposit_matches_streamlit_accounting(
        self, api_client, tenant, db
    ):
        row = _stmt_row(
            db,
            company_id=tenant["company_id"],
            bank_account_id=tenant["bank_account_id"],
        )
        history = {
            "description": row.description,
            "amount": row.amount,
            "original_amount": row.original_amount,
            "raw_line_text": row.raw_line_text,
        }
        resp = _post_match(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _match_payload(row.id),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["statement_row_id"] == row.id
        assert body["match_id"] == row.id
        assert body["journal_entry_id"] is not None
        assert body["message"] == POSTED_OK_MSG
        assert body["status"] == "ok"

        db.refresh(row)
        assert row.status == "posted"
        assert row.match_type == "other_deposit"
        assert row.posted_journal_entry_id == body["journal_entry_id"]
        assert row.bank_transaction_id is not None
        assert row.description == history["description"]
        assert row.amount == history["amount"]
        assert row.original_amount == history["original_amount"]

        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "BankStmtDeposit"
        assert je.reference_id == row.id
        assert _journal_balanced(db)

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action=audit_svc.ACTION_POST,
                entity_type=audit_svc.ENTITY_BANK_STATEMENT_ROW,
                entity_id=row.id,
            )
            .one()
        )
        assert f"Deposit · {DEPOSIT_AMT:,.2f} · CR {CREDIT_ACCT}" in audit.description

    def test_bank_charge_match_posts_fee_je(self, api_client, tenant, db):
        row = _stmt_row(
            db,
            company_id=tenant["company_id"],
            bank_account_id=tenant["bank_account_id"],
            credit=False,
            amount=FEE_AMT,
            description="Bank commission fee",
        )
        resp = _post_match(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _match_payload(row.id, match_type="bank_charge"),
        )
        assert resp.status_code == 201
        db.refresh(row)
        assert row.status == "posted"
        assert row.match_type == "bank_charge"
        je = db.get(models.JournalEntry, resp.json()["journal_entry_id"])
        assert je.reference_type == "BankStmtBankCharge"
        assert _journal_balanced(db)

    def test_already_posted_rejected(self, api_client, tenant, db):
        row = _stmt_row(
            db,
            company_id=tenant["company_id"],
            bank_account_id=tenant["bank_account_id"],
        )
        first = _post_match(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _match_payload(row.id),
        )
        assert first.status_code == 201
        second = _post_match(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _match_payload(row.id),
        )
        assert second.status_code == 400
        assert "already posted" in second.json()["detail"].lower()


class TestReconciliationWriteUnmatch:
    def test_cc_bill_unmatch_restores_row_to_voided(self, api_client, tenant, db):
        row = _stmt_row(
            db,
            company_id=tenant["company_id"],
            bank_account_id=tenant["bank_account_id"],
            credit=False,
            amount=250.0,
            description="KK ODEME",
        )
        post_credit_card_bill_payment(
            db,
            row_id=row.id,
            company_id=tenant["company_id"],
            credit_card_account_id=tenant["cc_account_id"],
            user_id=None,
        )
        db.refresh(row)
        assert row.status == "posted"
        assert row.match_type == "cc_bill_payment"

        resp = _post_unmatch(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            row.id,
            reason="API unpost",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["statement_row_id"] == row.id
        assert body["message"] == UNPOSTED_OK_MSG
        assert body["status"] == "ok"

        db.refresh(row)
        assert row.status == "voided"
        assert row.description == "KK ODEME"

    def test_unmatch_non_cc_row_rejected(self, api_client, tenant, db):
        row = _stmt_row(
            db,
            company_id=tenant["company_id"],
            bank_account_id=tenant["bank_account_id"],
        )
        _post_match(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _match_payload(row.id),
        )
        resp = _post_unmatch(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            row.id,
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == UNMATCH_NOT_SUPPORTED_MSG


class TestReconciliationWriteCompanyIsolation:
    def test_cannot_match_row_from_another_company(
        self, api_client, tenant, db
    ):
        other_row = _stmt_row(
            db,
            company_id=tenant["other_company_id"],
            bank_account_id=tenant["other_bank_account_id"],
        )
        resp = _post_match(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _match_payload(other_row.id),
        )
        assert resp.status_code == 400
        assert "Import not found for this company" in resp.json()["detail"]
        db.refresh(other_row)
        assert other_row.status == "staging"


class TestReconciliationWriteBoundaryCommit:
    def test_generic_deposit_boundary_mode_single_commit(
        self, api_client, tenant, db
    ):
        commit_modes.set_commit_mode_for_tests(
            RECONCILIATION_FAMILY, CommitMode.BOUNDARY
        )
        row = _stmt_row(
            db,
            company_id=tenant["company_id"],
            bank_account_id=tenant["bank_account_id"],
        )
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = _post_match(
                api_client,
                tenant["owner"],
                tenant["company_id"],
                _match_payload(row.id),
            )
            assert resp.status_code == 201
            assert mock_commit.call_count == 1


class TestReconciliationWriteNoGetCommits:
    def test_read_get_still_performs_no_commit(self, api_client, tenant, db):
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get(
                "/api/v1/receivables",
                headers=api_headers(tenant["owner"], company_id=tenant["company_id"]),
            )
            assert resp.status_code == 200
            mock_commit.assert_not_called()
