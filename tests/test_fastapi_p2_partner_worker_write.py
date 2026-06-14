"""FASTAPI-P2.6 — POST partner-movements and worker-payments write endpoints."""

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
from api.bearer_auth import BEARER_INVALID_DETAIL, BEARER_MISSING_DETAIL
from api.dependencies import DEV_HEADERS_ENV, get_db
from api.errors import COMPANY_MISSING_MARKER, MEMBERSHIP_DENIED_MARKER
from api.main import create_app
from db import Base
from registry.coa_seed import seed_chart_of_accounts_for_company
from services import audit as audit_svc
from services import commit_modes
from services.commit_modes import (
    CommitMode,
    POST_PARTNER_MOVEMENT_FAMILY,
    POST_WORKER_MOVEMENT_FAMILY,
)
from services import tokens as token_service
from tests.fastapi_p1_jwt import TEST_JWT_SECRET, api_headers, password_hash_for_tests

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock

POST_DATE = datetime.date(2026, 6, 12)
AMOUNT = 500.0
CURRENCY = "TRY"
WRITE_PARTNER_WORKER_ENV = "ERP_API_WRITE_PARTNER_WORKER"
INVALID_AMOUNT_MSG = "Amount must be greater than zero."
PARTNER_NOT_FOUND_MSG = "Partner not found or inactive."
WORKER_NOT_FOUND_MSG = "Worker not found or inactive."
UNKNOWN_MOVEMENT_MSG = "Unknown movement type"


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setenv(token_service.JWT_SECRET_ENV, TEST_JWT_SECRET)
    monkeypatch.delenv(DEV_HEADERS_ENV, raising=False)


@pytest.fixture(autouse=True)
def _write_partner_worker_enabled(monkeypatch):
    monkeypatch.setenv(WRITE_PARTNER_WORKER_ENV, "1")


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
        username="owner_p26",
        display_name="Owner P26",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    outsider = models.User(
        username="outsider_p26",
        display_name="Outsider P26",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_a = models.Company(
        name="Co A P26",
        slug="co_a_p26",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_b = models.Company(
        name="Co B P26",
        slug="co_b_p26",
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
        balance=10000.0,
        kind="bank",
    )
    bank_b = models.BankAccount(
        name="Other Bank",
        currency=CURRENCY,
        company_id=co_b.id,
        is_active=True,
        balance=10000.0,
        kind="bank",
    )
    db.add_all([bank_a, bank_b])
    db.commit()
    return {
        "owner": owner,
        "outsider": outsider,
        "company_id": co_a.id,
        "other_company_id": co_b.id,
        "bank_account_id": bank_a.id,
        "other_bank_account_id": bank_b.id,
    }


def _set_company(company_id: int) -> None:
    sys.modules["streamlit"].session_state.clear()
    sys.modules["streamlit"].session_state["auth_user"] = dict(erp_app._DEV_USER)
    sys.modules["streamlit"].session_state["active_company_id"] = company_id


def _seed_partner(db, company_id: int) -> int:
    _set_company(company_id)
    pid, err = erp_app.create_partner(db, "Alice", 100.0)
    assert err == ""
    return pid


def _seed_worker(db, company_id: int) -> int:
    _set_company(company_id)
    wid, err = erp_app.create_worker(db, "Bob", role="Sales")
    assert err == ""
    return wid


def _partner_payload(partner_id: int, **overrides) -> dict:
    base = {
        "partner_id": partner_id,
        "movement_type": "CapitalContribution",
        "amount": AMOUNT,
        "date": POST_DATE.isoformat(),
        "bank_account_id": None,
        "notes": "API partner movement",
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None or k == "bank_account_id"}


def _worker_payload(worker_id: int, **overrides) -> dict:
    base = {
        "worker_id": worker_id,
        "movement_type": "Advance",
        "date": POST_DATE.isoformat(),
        "bank_account_id": None,
        "amount": AMOUNT,
        "notes": "API worker payment",
    }
    base.update(overrides)
    return base


def _post_partner(client, user, company_id, payload):
    return client.post(
        "/api/v1/partner-movements",
        json=payload,
        headers=api_headers(user, company_id=company_id),
    )


def _post_worker(client, user, company_id, payload):
    return client.post(
        "/api/v1/worker-payments",
        json=payload,
        headers=api_headers(user, company_id=company_id),
    )


def _journal_balanced(db) -> bool:
    lines = db.query(models.JournalEntryLine).all()
    deb = round(sum(l.debit or 0 for l in lines), 2)
    cred = round(sum(l.credit or 0 for l in lines), 2)
    return abs(deb - cred) < 0.02 and deb > 0


class TestPartnerWorkerWriteFeatureFlag:
    def test_partner_movement_disabled_returns_404(self, api_client, tenant, db, monkeypatch):
        monkeypatch.delenv(WRITE_PARTNER_WORKER_ENV, raising=False)
        pid = _seed_partner(db, tenant["company_id"])
        payload = _partner_payload(
            pid,
            bank_account_id=tenant["bank_account_id"],
        )
        resp = _post_partner(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 404

    def test_worker_payment_disabled_returns_404(self, api_client, tenant, db, monkeypatch):
        monkeypatch.delenv(WRITE_PARTNER_WORKER_ENV, raising=False)
        wid = _seed_worker(db, tenant["company_id"])
        payload = _worker_payload(wid, bank_account_id=tenant["bank_account_id"])
        resp = _post_worker(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 404


class TestPartnerWorkerWriteAuth:
    def test_jwt_required_partner(self, api_client, tenant, db):
        pid = _seed_partner(db, tenant["company_id"])
        payload = _partner_payload(pid, bank_account_id=tenant["bank_account_id"])
        resp = api_client.post("/api/v1/partner-movements", json=payload)
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_MISSING_DETAIL

    def test_jwt_required_worker(self, api_client, tenant, db):
        wid = _seed_worker(db, tenant["company_id"])
        payload = _worker_payload(wid, bank_account_id=tenant["bank_account_id"])
        resp = api_client.post("/api/v1/worker-payments", json=payload)
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_MISSING_DETAIL

    def test_invalid_jwt_rejected(self, api_client, tenant, db):
        pid = _seed_partner(db, tenant["company_id"])
        payload = _partner_payload(pid, bank_account_id=tenant["bank_account_id"])
        resp = api_client.post(
            "/api/v1/partner-movements",
            json=payload,
            headers={"Authorization": "Bearer bad.token.here", "X-Company-Id": "1"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_INVALID_DETAIL

    def test_company_header_required(self, api_client, tenant, db):
        pid = _seed_partner(db, tenant["company_id"])
        payload = _partner_payload(pid, bank_account_id=tenant["bank_account_id"])
        resp = api_client.post(
            "/api/v1/partner-movements",
            json=payload,
            headers=api_headers(tenant["owner"]),
        )
        assert resp.status_code == 400
        assert COMPANY_MISSING_MARKER in resp.json()["detail"]

    def test_user_without_membership_rejected(self, api_client, tenant, db):
        pid = _seed_partner(db, tenant["company_id"])
        payload = _partner_payload(pid, bank_account_id=tenant["bank_account_id"])
        resp = _post_partner(api_client, tenant["outsider"], tenant["company_id"], payload)
        assert resp.status_code == 403
        assert MEMBERSHIP_DENIED_MARKER in resp.json()["detail"]


class TestPartnerMovementWriteValidation:
    def test_invalid_amount_rejected(self, api_client, tenant, db):
        pid = _seed_partner(db, tenant["company_id"])
        payload = _partner_payload(
            pid,
            amount=0,
            bank_account_id=tenant["bank_account_id"],
        )
        resp = _post_partner(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 400
        assert resp.json()["detail"] == INVALID_AMOUNT_MSG
        assert db.query(models.PartnerMovement).count() == 0

    def test_invalid_movement_type_rejected(self, api_client, tenant, db):
        pid = _seed_partner(db, tenant["company_id"])
        payload = _partner_payload(
            pid,
            movement_type="ProfitAllocation",
            bank_account_id=tenant["bank_account_id"],
        )
        resp = _post_partner(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 400
        assert UNKNOWN_MOVEMENT_MSG in resp.json()["detail"]

    def test_company_id_in_body_rejected(self, api_client, tenant, db):
        pid = _seed_partner(db, tenant["company_id"])
        payload = _partner_payload(pid, bank_account_id=tenant["bank_account_id"])
        payload["company_id"] = tenant["other_company_id"]
        resp = _post_partner(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 422


class TestWorkerPaymentWriteValidation:
    def test_invalid_amount_rejected(self, api_client, tenant, db):
        wid = _seed_worker(db, tenant["company_id"])
        payload = _worker_payload(
            wid,
            amount=0,
            bank_account_id=tenant["bank_account_id"],
        )
        resp = _post_worker(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 400
        assert resp.json()["detail"] == INVALID_AMOUNT_MSG
        assert db.query(models.WorkerMovement).count() == 0

    def test_invalid_movement_type_rejected(self, api_client, tenant, db):
        wid = _seed_worker(db, tenant["company_id"])
        payload = _worker_payload(
            wid,
            movement_type="Bonus",
            bank_account_id=tenant["bank_account_id"],
        )
        resp = _post_worker(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 400
        assert UNKNOWN_MOVEMENT_MSG in resp.json()["detail"]

    def test_company_id_in_body_rejected(self, api_client, tenant, db):
        wid = _seed_worker(db, tenant["company_id"])
        payload = _worker_payload(wid, bank_account_id=tenant["bank_account_id"])
        payload["company_id"] = tenant["other_company_id"]
        resp = _post_worker(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 422


class TestPartnerMovementWriteAccounting:
    def test_capital_contribution_posts_balanced_journal_and_audit(
        self, api_client, tenant, db
    ):
        pid = _seed_partner(db, tenant["company_id"])
        partner = db.get(models.Partner, pid)
        payload = _partner_payload(
            pid,
            movement_type="CapitalContribution",
            bank_account_id=tenant["bank_account_id"],
        )
        resp = _post_partner(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["movement_id"] > 0
        assert body["journal_entry_id"] > 0
        assert body["status"] == "ok"
        assert "CapitalContribution" in body["message"]
        assert partner.name in body["message"]

        movement = db.get(models.PartnerMovement, body["movement_id"])
        assert movement is not None
        assert movement.movement_type == "CapitalContribution"
        assert movement.amount == AMOUNT
        assert movement.journal_entry_id == body["journal_entry_id"]

        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "PartnerCapital"
        assert je.reference_id == movement.id
        assert je.company_id == tenant["company_id"]
        assert _journal_balanced(db)

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action=audit_svc.ACTION_CREATE,
                entity_type=audit_svc.ENTITY_PARTNER_MOVEMENT,
                entity_id=movement.id,
            )
            .one()
        )
        assert f"CapitalContribution: {partner.name}" in audit.description

    def test_drawing_posts_withdrawal(self, api_client, tenant, db):
        pid = _seed_partner(db, tenant["company_id"])
        payload = _partner_payload(
            pid,
            movement_type="Drawing",
            bank_account_id=tenant["bank_account_id"],
        )
        resp = _post_partner(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 201
        body = resp.json()
        movement = db.get(models.PartnerMovement, body["movement_id"])
        assert movement.movement_type == "Drawing"
        assert movement.bank_transaction_id is not None
        btxn = db.get(models.BankTransaction, movement.bank_transaction_id)
        assert btxn.type == "withdrawal"
        assert btxn.amount == AMOUNT
        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "PartnerDrawing"


class TestWorkerPaymentWriteAccounting:
    def test_advance_posts_balanced_journal_and_audit(self, api_client, tenant, db):
        wid = _seed_worker(db, tenant["company_id"])
        worker = db.get(models.Worker, wid)
        payload = _worker_payload(wid, bank_account_id=tenant["bank_account_id"])
        resp = _post_worker(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["payment_id"] > 0
        assert body["journal_entry_id"] > 0
        assert body["status"] == "ok"
        assert "Advance" in body["message"]
        assert worker.name in body["message"]

        movement = db.get(models.WorkerMovement, body["payment_id"])
        assert movement.movement_type == "Advance"
        assert movement.amount == AMOUNT
        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "WorkerAdvance"
        assert _journal_balanced(db)

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action=audit_svc.ACTION_CREATE,
                entity_type=audit_svc.ENTITY_WORKER_MOVEMENT,
                entity_id=movement.id,
            )
            .one()
        )
        assert f"Advance: {worker.name}" in audit.description

    def test_salary_payment_matches_streamlit_behavior(self, api_client, tenant, db):
        wid = _seed_worker(db, tenant["company_id"])
        payload = {
            "worker_id": wid,
            "movement_type": "Salary",
            "date": POST_DATE.isoformat(),
            "bank_account_id": tenant["bank_account_id"],
            "gross_salary": 10000.0,
            "deductions": 1000.0,
            "advance_recovery": 0.0,
            "pay_period": "Jun 2026",
            "notes": "Monthly salary",
        }
        resp = _post_worker(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 201
        body = resp.json()
        movement = db.get(models.WorkerMovement, body["payment_id"])
        assert movement.movement_type == "Salary"
        assert movement.gross_salary == 10000.0
        assert movement.deductions == 1000.0
        assert movement.amount == 9000.0
        assert movement.net_paid == 9000.0
        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "WorkerSalary"
        assert _journal_balanced(db)


class TestPartnerWorkerWriteCompanyIsolation:
    def test_cannot_use_partner_from_another_company(self, api_client, tenant, db):
        other_pid = _seed_partner(db, tenant["other_company_id"])
        payload = _partner_payload(
            other_pid,
            bank_account_id=tenant["bank_account_id"],
        )
        resp = _post_partner(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 400
        assert resp.json()["detail"] == PARTNER_NOT_FOUND_MSG
        assert db.query(models.PartnerMovement).count() == 0

    def test_cannot_use_worker_from_another_company(self, api_client, tenant, db):
        other_wid = _seed_worker(db, tenant["other_company_id"])
        payload = _worker_payload(other_wid, bank_account_id=tenant["bank_account_id"])
        resp = _post_worker(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 400
        assert resp.json()["detail"] == WORKER_NOT_FOUND_MSG
        assert db.query(models.WorkerMovement).count() == 0

    def test_cannot_use_bank_account_from_another_company(
        self, api_client, tenant, db
    ):
        pid = _seed_partner(db, tenant["company_id"])
        payload = _partner_payload(
            pid,
            bank_account_id=tenant["other_bank_account_id"],
        )
        resp = _post_partner(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 400
        assert "Bank account not found" in resp.json()["detail"]


class TestPartnerWorkerWriteBoundaryCommit:
    def test_partner_movement_boundary_mode_single_commit(
        self, api_client, tenant, db
    ):
        commit_modes.set_commit_mode_for_tests(
            POST_PARTNER_MOVEMENT_FAMILY, CommitMode.BOUNDARY
        )
        pid = _seed_partner(db, tenant["company_id"])
        payload = _partner_payload(
            pid,
            bank_account_id=tenant["bank_account_id"],
        )
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = _post_partner(
                api_client, tenant["owner"], tenant["company_id"], payload
            )
            assert resp.status_code == 201
            assert mock_commit.call_count == 1

    def test_worker_payment_boundary_mode_single_commit(
        self, api_client, tenant, db
    ):
        commit_modes.set_commit_mode_for_tests(
            POST_WORKER_MOVEMENT_FAMILY, CommitMode.BOUNDARY
        )
        wid = _seed_worker(db, tenant["company_id"])
        payload = _worker_payload(wid, bank_account_id=tenant["bank_account_id"])
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = _post_worker(
                api_client, tenant["owner"], tenant["company_id"], payload
            )
            assert resp.status_code == 201
            assert mock_commit.call_count == 1


class TestPartnerWorkerWriteNoGetCommits:
    def test_read_get_still_performs_no_commit(self, api_client, tenant, db):
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get(
                "/api/v1/receivables",
                headers=api_headers(tenant["owner"], company_id=tenant["company_id"]),
            )
            assert resp.status_code == 200
            mock_commit.assert_not_called()
