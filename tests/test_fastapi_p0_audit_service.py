"""FASTAPI-P0.3a-b — audit service contract tests."""

from __future__ import annotations

import datetime
import inspect
import json
import sys
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event as sa_event, func
from sqlalchemy.orm import sessionmaker

import app as erp_app
from db import Base
import models
from services import audit as audit_svc

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


def _company(db, slug: str = "audit_co"):
    co = models.Company(
        name=slug.title(),
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.flush()
    return co


def _set_company(company_id: int | None):
    if company_id is None:
        sys.modules["streamlit"].session_state.pop("active_company_id", None)
    else:
        sys.modules["streamlit"].session_state["active_company_id"] = company_id


def _row_snapshot(entry: models.AuditLog) -> dict:
    return {
        "action": entry.action,
        "entity_type": entry.entity_type,
        "entity_id": entry.entity_id,
        "description": entry.description,
        "performed_by": entry.performed_by,
        "company_id": entry.company_id,
    }


def _legacy_equivalent_row(
    db,
    *,
    action: str,
    entity_type: str | None,
    entity_id: int | None,
    description: str | None,
    performed_by: str | None,
    company_id: int | None,
) -> dict:
    """Pre-extraction semantics: hook stamps company_id when not set on the row."""
    entry = models.AuditLog(
        timestamp=datetime.datetime.now(),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        performed_by=performed_by,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    if company_id is not None:
        assert entry.company_id == company_id
    else:
        assert entry.company_id is None
    return _row_snapshot(entry)


class TestServiceWithoutStreamlit:
    def test_module_has_no_streamlit_or_app_imports(self):
        src = inspect.getsource(audit_svc)
        assert "streamlit" not in src
        assert "import app" not in src
        assert "from app" not in src

    def test_record_audit_persists_without_streamlit(self, db):
        co = _company(db)
        entry = audit_svc.record_audit(
            db,
            action=audit_svc.ACTION_CREATE,
            entity_type=audit_svc.ENTITY_PARTNER,
            entity_id=42,
            description="Partner 'Bob' created",
            performed_by="admin",
            company_id=co.id,
        )
        assert entry.id is not None
        persisted = db.get(models.AuditLog, entry.id)
        assert persisted is not None
        assert _row_snapshot(persisted) == {
            "action": "Create",
            "entity_type": "Partner",
            "entity_id": 42,
            "description": "Partner 'Bob' created",
            "performed_by": "admin",
            "company_id": co.id,
        }


class TestShimDelegatesToService:
    def test_log_audit_matches_explicit_service_call(self, db):
        co = _company(db)
        _set_company(co.id)
        params = {
            "action": "Edit",
            "entity_type": "ExpenseRecord",
            "entity_id": 7,
            "description": json.dumps({"before": {"amount": 10}, "after": {"amount": 20}}),
        }
        shim_entry = erp_app.log_audit(db, **params)
        direct = audit_svc.record_audit(
            db,
            performed_by=erp_app._DEV_USER["username"],
            company_id=co.id,
            **params,
        )
        assert _row_snapshot(shim_entry) == _row_snapshot(direct)

    def test_log_audit_matches_legacy_golden_snapshot(self, db):
        co = _company(db)
        _set_company(co.id)
        performed_by = erp_app._DEV_USER["username"]
        params = {
            "action": "Void",
            "entity_type": "PartnerMovement",
            "entity_id": 99,
            "description": "Voided Drawing: 500.00 — test reason",
        }
        legacy = _legacy_equivalent_row(
            db,
            performed_by=performed_by,
            company_id=co.id,
            **params,
        )
        shim = _row_snapshot(erp_app.log_audit(db, **params))
        assert shim == legacy

    def test_performed_by_from_current_user(self, db):
        co = _company(db)
        _set_company(co.id)
        erp_app.log_audit(db, "Create", "Worker", 1, "Worker 'Ann' created")
        row = db.query(models.AuditLog).filter_by(entity_type="Worker", entity_id=1).one()
        assert row.performed_by == erp_app._DEV_USER["username"]

    def test_company_id_from_active_company(self, db):
        co = _company(db)
        _set_company(co.id)
        erp_app.log_audit(db, "Create", "Partner", 5, "Partner created")
        row = db.query(models.AuditLog).filter_by(entity_type="Partner", entity_id=5).one()
        assert row.company_id == co.id


class TestSystemEventPath:
    def test_company_id_none_without_active_company(self, db):
        _set_company(None)
        sys.modules["streamlit"].session_state.pop("auth_user", None)
        sys.modules["streamlit"].session_state.pop("auth_expires", None)
        entry = audit_svc.record_audit(
            db,
            action="Create",
            entity_type="User",
            entity_id=1,
            description="System bootstrap",
            performed_by=None,
            company_id=None,
        )
        assert entry.company_id is None
        assert entry.performed_by is None

    def test_log_audit_shim_system_event_company_id_none(self, db):
        _set_company(None)
        entry = erp_app.log_audit(
            db, "Create", "User", 1, "Login audit without company"
        )
        assert entry.company_id is None


class TestInternalCommit:
    def test_record_audit_commits_internally(self, db):
        co = _company(db)
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            audit_svc.record_audit(
                db,
                action="Create",
                entity_type="Sale",
                entity_id=3,
                description="Sale INV-1",
                performed_by="admin",
                company_id=co.id,
            )
        assert mock_commit.call_count == 1
        assert db.query(models.AuditLog).filter_by(entity_id=3).count() == 1

    def test_log_audit_shim_commits_internally(self, db):
        co = _company(db)
        _set_company(co.id)
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            erp_app.log_audit(db, "Create", "Sale", 4, "Sale INV-2")
        assert mock_commit.call_count == 1


class TestRepresentativePostingAudit:
    def test_partner_movement_post_audit_unchanged(self, db):
        co = _company(db)
        _set_company(co.id)
        _make_coa = lambda code, name, typ: _add_coa(db, code, name, typ)
        _make_coa("1100", "Cash", "Asset")
        partner_id, err = erp_app.create_partner(db, "Alice", 100.0)
        assert err == ""
        bank = models.BankAccount(
            name="Cash",
            currency="TRY",
            balance=10000.0,
            is_active=True,
            kind="bank",
        )
        db.add(bank)
        db.commit()

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            mid, err = erp_app.post_partner_movement(
                db,
                partner_id,
                "Drawing",
                500.0,
                datetime.date(2026, 6, 10),
                bank_account_id=bank.id,
                created_by_id=1,
            )
            assert err == ""
            assert mock_commit.call_count == 3

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action="Create",
                entity_type="PartnerMovement",
                entity_id=mid,
            )
            .one()
        )
        assert audit.description == "Drawing: Alice — 500.00"
        assert audit.performed_by == erp_app._DEV_USER["username"]
        assert audit.company_id == co.id


def _add_coa(db, code, name, acct_type):
    acct = models.ChartOfAccounts(
        account_code=code,
        account_name=name,
        account_type=acct_type,
        balance=0.0,
        is_active=True,
    )
    db.add(acct)
    db.flush()
    return acct
