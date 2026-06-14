"""FASTAPI-P2.5 — POST /api/v1/voids write endpoint."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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
from services import commit_modes, posting
from services import tokens as token_service
from services.commit_modes import CommitMode, VOID_CASCADE_FAMILY
from services.posting import purchase_ref_type
from tests.fastapi_p1_jwt import TEST_JWT_SECRET, api_headers, password_hash_for_tests

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock

POST_DATE = datetime.date(2026, 6, 20)
AMOUNT = 100.0
CURRENCY = "TRY"
VOID_REASON = "API void test"
WRITE_VOIDS_ENV = "ERP_API_WRITE_VOIDS"
VOID_REASON_REQUIRED_MSG = "Void reason is required."
INVALID_TARGET_TYPE_MSG = "Unsupported void target type"
NOT_FOUND_OR_VOIDED_MSG = "Record not found or is already voided."


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setenv(token_service.JWT_SECRET_ENV, TEST_JWT_SECRET)
    monkeypatch.delenv(DEV_HEADERS_ENV, raising=False)


@pytest.fixture(autouse=True)
def _write_voids_enabled(monkeypatch):
    monkeypatch.setenv(WRITE_VOIDS_ENV, "1")


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
        username="owner_p25",
        display_name="Owner P25",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    outsider = models.User(
        username="outsider_p25",
        display_name="Outsider P25",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_a = models.Company(
        name="Co A P25",
        slug="co_a_p25",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_b = models.Company(
        name="Co B P25",
        slug="co_b_p25",
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
    vendor = models.Vendor(name="Supplier A", company_id=co_a.id, is_active=True)
    bank = models.BankAccount(
        name="Main Bank",
        currency=CURRENCY,
        company_id=co_a.id,
        is_active=True,
        balance=10000.0,
        kind="bank",
    )
    db.add_all([vendor, bank])
    db.commit()
    return {
        "owner": owner,
        "outsider": outsider,
        "company_id": co_a.id,
        "other_company_id": co_b.id,
        "vendor_id": vendor.id,
        "bank_account_id": bank.id,
    }


def _void_payload(target_type: str, target_id: int, **overrides) -> dict:
    base = {
        "target_type": target_type,
        "target_id": target_id,
        "reason": VOID_REASON,
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}


def _post_void(client, user, company_id, payload):
    return client.post(
        "/api/v1/voids",
        json=payload,
        headers=api_headers(user, company_id=company_id),
    )


def _journal_balanced(db) -> bool:
    lines = db.query(models.JournalEntryLine).all()
    deb = round(sum(l.debit or 0 for l in lines), 2)
    cred = round(sum(l.credit or 0 for l in lines), 2)
    return abs(deb - cred) < 0.02


def _post_cash_sale(db, company_id) -> models.Sale:
    sale = models.Sale(
        date=POST_DATE,
        invoice_number="INV-VOID-001",
        customer_name="Walk-in",
        amount=AMOUNT,
        sale_type="Cash",
        paid_amount=AMOUNT,
        balance=0.0,
        due_date=POST_DATE,
        status="Paid",
        company_id=company_id,
        currency=CURRENCY,
    )
    db.add(sale)
    db.commit()
    posting.post_cash_sale(
        db, sale.id, AMOUNT, POST_DATE, currency=CURRENCY, company_id=company_id
    )
    return sale


def _post_credit_sale_with_payment(db, company_id) -> models.Sale:
    sale = models.Sale(
        date=POST_DATE,
        invoice_number="INV-CREDIT-VOID",
        customer_name="Credit Customer",
        amount=AMOUNT,
        sale_type="Credit",
        paid_amount=0.0,
        balance=AMOUNT,
        due_date=POST_DATE + datetime.timedelta(days=30),
        status="Open",
        company_id=company_id,
        currency=CURRENCY,
    )
    db.add(sale)
    db.commit()
    posting.post_credit_sale(
        db, sale.id, AMOUNT, POST_DATE, currency=CURRENCY, company_id=company_id
    )
    posting.post_receivable_payment(
        db,
        sale.id,
        AMOUNT,
        POST_DATE,
        "Cash",
        currency=CURRENCY,
        company_id=company_id,
    )
    return sale


def _post_expense(db, company_id) -> models.ExpenseRecord:
    exp = models.ExpenseRecord(
        date=POST_DATE,
        expense_type="Office",
        category="Office",
        amount=AMOUNT,
        payment_method="Cash",
        company_id=company_id,
        currency=CURRENCY,
    )
    db.add(exp)
    db.commit()
    posting.post_expense(
        db, exp.id, AMOUNT, POST_DATE, "Office", payment_method="Cash", company_id=company_id
    )
    return exp


def _post_cash_purchase(db, company_id, vendor_id) -> models.Purchase:
    pur = models.Purchase(
        date=POST_DATE,
        vendor_id=vendor_id,
        amount=AMOUNT,
        purchase_type="Cash",
        gl_debit="Inventory",
        company_id=company_id,
        currency=CURRENCY,
    )
    db.add(pur)
    db.commit()
    posting.post_purchase(
        db,
        pur.id,
        AMOUNT,
        POST_DATE,
        "Cash",
        "Inventory",
        currency=CURRENCY,
        company_id=company_id,
    )
    return pur


def _post_credit_purchase(db, company_id, vendor_id) -> tuple[models.Purchase, models.Payable]:
    pur = models.Purchase(
        date=POST_DATE,
        vendor_id=vendor_id,
        amount=AMOUNT,
        purchase_type="Credit",
        gl_debit="Inventory",
        company_id=company_id,
        currency=CURRENCY,
    )
    db.add(pur)
    db.commit()
    posting.post_purchase(
        db,
        pur.id,
        AMOUNT,
        POST_DATE,
        "Credit",
        "Inventory",
        currency=CURRENCY,
        company_id=company_id,
    )
    payable = models.Payable(
        date=POST_DATE,
        vendor_id=vendor_id,
        amount=AMOUNT,
        due_date=POST_DATE + datetime.timedelta(days=30),
        paid=False,
        description=f"From Purchase #{pur.id}: test",
        expense_category="Inventory",
        purchase_id=pur.id,
        company_id=company_id,
    )
    db.add(payable)
    db.commit()
    return pur, payable


class TestVoidWriteFeatureFlag:
    def test_disabled_returns_404(self, api_client, tenant, db, monkeypatch):
        monkeypatch.delenv(WRITE_VOIDS_ENV, raising=False)
        sale = _post_cash_sale(db, tenant["company_id"])
        resp = _post_void(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _void_payload("Sale", sale.id),
        )
        assert resp.status_code == 404


class TestVoidWriteAuth:
    def test_missing_bearer_rejected(self, api_client, tenant, db):
        sale = _post_cash_sale(db, tenant["company_id"])
        resp = api_client.post(
            "/api/v1/voids",
            json=_void_payload("Sale", sale.id),
            headers={"X-Company-Id": str(tenant["company_id"])},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_MISSING_DETAIL

    def test_user_without_membership_rejected(self, api_client, tenant, db):
        sale = _post_cash_sale(db, tenant["company_id"])
        resp = _post_void(
            api_client,
            tenant["outsider"],
            tenant["company_id"],
            _void_payload("Sale", sale.id),
        )
        assert resp.status_code == 403
        assert MEMBERSHIP_DENIED_MARKER in resp.json()["detail"]


class TestVoidWriteValidation:
    def test_reason_required(self, api_client, tenant, db):
        sale = _post_cash_sale(db, tenant["company_id"])
        resp = _post_void(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _void_payload("Sale", sale.id, reason="   "),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == VOID_REASON_REQUIRED_MSG

    def test_invalid_target_type_rejected(self, api_client, tenant, db):
        sale = _post_cash_sale(db, tenant["company_id"])
        resp = _post_void(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _void_payload("PartnerMovement", sale.id),
        )
        assert resp.status_code == 400
        assert INVALID_TARGET_TYPE_MSG in resp.json()["detail"]

    def test_company_id_in_body_rejected(self, api_client, tenant, db):
        sale = _post_cash_sale(db, tenant["company_id"])
        payload = _void_payload("Sale", sale.id)
        payload["company_id"] = tenant["other_company_id"]
        resp = _post_void(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 422

    def test_already_voided_rejected(self, api_client, tenant, db):
        sale = _post_cash_sale(db, tenant["company_id"])
        sale.is_void = True
        db.commit()
        resp = _post_void(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _void_payload("Sale", sale.id),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == NOT_FOUND_OR_VOIDED_MSG


class TestVoidWriteSale:
    def test_void_sale_creates_reversal_and_audit(self, api_client, tenant, db):
        sale = _post_cash_sale(db, tenant["company_id"])
        orig_je = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="CashSale", reference_id=sale.id)
            .one()
        )
        resp = _post_void(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _void_payload("Sale", sale.id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["target_type"] == "Sale"
        assert body["target_id"] == sale.id
        assert body["reversal_journal_entry_id"] is not None
        assert body["status"] == "ok"
        assert "voided" in body["message"].lower()

        db.refresh(sale)
        assert sale.is_void is True
        assert sale.status == "Void"
        assert db.get(models.Sale, sale.id) is not None

        reversal = db.get(models.JournalEntry, body["reversal_journal_entry_id"])
        assert reversal.reference_type == "Reversal"
        assert reversal.reference_id == orig_je.id
        assert _journal_balanced(db)

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action=audit_svc.ACTION_VOID,
                entity_type=audit_svc.ENTITY_SALE,
                entity_id=sale.id,
            )
            .one()
        )
        assert VOID_REASON in audit.description


class TestVoidWriteExpense:
    def test_void_expense_creates_reversal_and_audit(self, api_client, tenant, db):
        exp = _post_expense(db, tenant["company_id"])
        resp = _post_void(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _void_payload("ExpenseRecord", exp.id),
        )
        assert resp.status_code == 200
        db.refresh(exp)
        assert exp.is_void is True
        assert db.query(models.JournalEntry).filter_by(reference_type="Reversal").count() >= 1
        assert (
            db.query(models.AuditLog)
            .filter_by(entity_type=audit_svc.ENTITY_EXPENSE_RECORD, entity_id=exp.id)
            .count()
            == 1
        )


class TestVoidWritePurchase:
    def test_void_purchase_creates_reversal_and_audit(self, api_client, tenant, db):
        pur = _post_cash_purchase(db, tenant["company_id"], tenant["vendor_id"])
        resp = _post_void(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _void_payload("Purchase", pur.id),
        )
        assert resp.status_code == 200
        db.refresh(pur)
        assert pur.is_void is True
        ref = purchase_ref_type(pur.purchase_type)
        assert (
            db.query(models.JournalEntry)
            .filter_by(reference_type="Reversal")
            .count()
            >= 1
        )


class TestVoidWriteCascade:
    def test_void_credit_sale_reverses_payment_jes(self, api_client, tenant, db):
        sale = _post_credit_sale_with_payment(db, tenant["company_id"])
        resp = _post_void(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _void_payload("Sale", sale.id),
        )
        assert resp.status_code == 200
        assert (
            db.query(models.JournalEntry)
            .filter_by(reference_type="Reversal")
            .count()
            == 2
        )

    def test_void_credit_purchase_voids_linked_payable(
        self, api_client, tenant, db
    ):
        pur, payable = _post_credit_purchase(
            db, tenant["company_id"], tenant["vendor_id"]
        )
        resp = _post_void(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _void_payload("Purchase", pur.id),
        )
        assert resp.status_code == 200
        db.refresh(payable)
        assert payable.is_void is True


class TestVoidWriteCompanyIsolation:
    def test_cannot_void_record_from_another_company(
        self, api_client, tenant, db
    ):
        other_sale = _post_cash_sale(db, tenant["other_company_id"])
        resp = _post_void(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _void_payload("Sale", other_sale.id),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == NOT_FOUND_OR_VOIDED_MSG
        db.refresh(other_sale)
        assert other_sale.is_void is False


class TestVoidWriteBoundaryCommit:
    def test_void_sale_boundary_mode_single_commit(self, api_client, tenant, db):
        commit_modes.set_commit_mode_for_tests(VOID_CASCADE_FAMILY, CommitMode.BOUNDARY)
        sale = _post_cash_sale(db, tenant["company_id"])
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = _post_void(
                api_client,
                tenant["owner"],
                tenant["company_id"],
                _void_payload("Sale", sale.id),
            )
            assert resp.status_code == 200
            assert mock_commit.call_count == 1


class TestVoidWriteNoGetCommits:
    def test_read_get_still_performs_no_commit(self, api_client, tenant, db):
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get(
                "/api/v1/receivables",
                headers=api_headers(tenant["owner"], company_id=tenant["company_id"]),
            )
            assert resp.status_code == 200
            mock_commit.assert_not_called()
