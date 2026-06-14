"""FASTAPI-P2.1 — POST /api/v1/sales write endpoint."""

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
from services import commit_modes
from services.commit_modes import CommitMode, POST_CASH_SALE_FAMILY
from services import tokens as token_service
from tests.fastapi_p1_jwt import TEST_JWT_SECRET, api_headers, password_hash_for_tests
from tests.helpers.commit_parity import journal_line_tuples

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock

SALE_DATE = datetime.date(2026, 6, 5)
AMOUNT = 100.0
CURRENCY = "TRY"
WRITE_SALES_ENV = "ERP_API_WRITE_SALES"
INVALID_AMOUNT_MSG = "❌ Please enter a valid amount greater than zero."
CREDIT_CUSTOMER_MSG = "Enter a customer name for on-account (credit) sales."


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setenv(token_service.JWT_SECRET_ENV, TEST_JWT_SECRET)
    monkeypatch.delenv(DEV_HEADERS_ENV, raising=False)


@pytest.fixture(autouse=True)
def _write_sales_enabled(monkeypatch):
    monkeypatch.setenv(WRITE_SALES_ENV, "1")


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
        username="owner_p21",
        display_name="Owner P21",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    outsider = models.User(
        username="outsider_p21",
        display_name="Outsider P21",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_a = models.Company(
        name="Co A P21",
        slug="co_a_p21",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_b = models.Company(
        name="Co B P21",
        slug="co_b_p21",
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
    bank = models.BankAccount(
        name="Main Bank",
        balance=0.0,
        company_id=co_a.id,
        is_active=True,
    )
    db.add(bank)
    db.add(
        models.Customer(
            name="Acme Corp",
            company_id=co_a.id,
            is_active=True,
        )
    )
    db.commit()
    return {
        "owner": owner,
        "outsider": outsider,
        "company_id": co_a.id,
        "other_company_id": co_b.id,
        "bank_account_id": bank.id,
    }


def _sale_payload(**overrides) -> dict:
    base = {
        "date": SALE_DATE.isoformat(),
        "amount": AMOUNT,
        "currency": CURRENCY,
        "payment_method": "Cash",
        "notes": "API sale",
    }
    base.update(overrides)
    return base


def _post_sale(client, user, company_id, payload=None):
    return client.post(
        "/api/v1/sales",
        json=payload or _sale_payload(),
        headers=api_headers(user, company_id=company_id),
    )


def _journal_balanced(db) -> bool:
    lines = db.query(models.JournalEntryLine).all()
    deb = round(sum(l.debit or 0 for l in lines), 2)
    cred = round(sum(l.credit or 0 for l in lines), 2)
    return deb == cred and deb > 0


def _streamlit_cash_sale(db, company_id):
    sys.modules["streamlit"].session_state.clear()
    sys.modules["streamlit"].session_state["auth_user"] = dict(erp_app._DEV_USER)
    sys.modules["streamlit"].session_state["active_company_id"] = company_id
    sys.modules["streamlit"].session_state.update(
        {
            "at_type_idx": 0,
            "at_pm": "Cash",
            "at_amount_display": str(int(AMOUNT)),
            "at_currency": CURRENCY,
            "at_date": SALE_DATE,
            "at_cust": "Walk-in Customer",
            "at_notes_field": "Streamlit sale",
        }
    )
    erp_app._at_process_submit(
        db,
        currency_default=CURRENCY,
        vendors=[],
        bank_accounts=db.query(models.BankAccount).all(),
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )


class TestSalesWriteFeatureFlag:
    def test_disabled_returns_404(self, api_client, tenant, monkeypatch):
        monkeypatch.delenv(WRITE_SALES_ENV, raising=False)
        resp = _post_sale(api_client, tenant["owner"], tenant["company_id"])
        assert resp.status_code == 404


class TestSalesWriteAuth:
    def test_missing_bearer_rejected(self, api_client, tenant):
        resp = api_client.post(
            "/api/v1/sales",
            json=_sale_payload(),
            headers={"X-Company-Id": str(tenant["company_id"])},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_MISSING_DETAIL

    def test_invalid_bearer_rejected(self, api_client, tenant):
        resp = api_client.post(
            "/api/v1/sales",
            json=_sale_payload(),
            headers=api_headers("bad-token", company_id=tenant["company_id"]),
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_INVALID_DETAIL

    def test_missing_company_rejected(self, api_client, tenant):
        resp = api_client.post(
            "/api/v1/sales",
            json=_sale_payload(),
            headers=api_headers(tenant["owner"]),
        )
        assert resp.status_code == 400
        assert COMPANY_MISSING_MARKER in resp.json()["detail"]

    def test_user_without_membership_rejected(self, api_client, tenant):
        resp = _post_sale(api_client, tenant["outsider"], tenant["company_id"])
        assert resp.status_code == 403
        assert MEMBERSHIP_DENIED_MARKER in resp.json()["detail"]


class TestSalesWriteValidation:
    def test_invalid_amount_rejected(self, api_client, tenant, db):
        resp = _post_sale(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _sale_payload(amount=0),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == INVALID_AMOUNT_MSG
        assert db.query(models.Sale).count() == 0

    def test_invalid_payment_method_rejected(self, api_client, tenant, db):
        resp = _post_sale(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _sale_payload(payment_method="Crypto"),
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "Crypto" in detail
        assert "Sale" in detail

    def test_company_id_in_body_rejected(self, api_client, tenant):
        payload = _sale_payload()
        payload["company_id"] = tenant["other_company_id"]
        resp = _post_sale(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 422

    def test_credit_sale_requires_customer(self, api_client, tenant, db):
        for customer in ("", "Walk-in Customer"):
            resp = _post_sale(
                api_client,
                tenant["owner"],
                tenant["company_id"],
                _sale_payload(payment_method="Credit", customer_name=customer),
            )
            assert resp.status_code == 400
            assert resp.json()["detail"] == CREDIT_CUSTOMER_MSG
        assert db.query(models.Sale).count() == 0


class TestSalesWriteCash:
    def test_cash_sale_posts_balanced_journal(self, api_client, tenant, db):
        resp = _post_sale(api_client, tenant["owner"], tenant["company_id"])
        assert resp.status_code == 201
        body = resp.json()
        assert body["sale_id"] > 0
        assert body["journal_entry_id"] > 0
        assert "Sale recorded" in body["message"]
        assert "Invoice" in body["message"]

        sale = db.get(models.Sale, body["sale_id"])
        assert sale is not None
        assert sale.company_id == tenant["company_id"]
        assert sale.sale_type == "Cash"
        assert sale.amount == AMOUNT
        assert sale.status == "Paid"
        assert _journal_balanced(db)

        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "CashSale"
        assert je.reference_id == sale.id
        assert je.company_id == tenant["company_id"]

    def test_cash_sale_matches_streamlit_accounting(self, api_client, tenant, db):
        _streamlit_cash_sale(db, tenant["company_id"])
        st_sale = db.query(models.Sale).filter_by(sale_type="Cash").one()
        st_lines = journal_line_tuples(db)

        db.query(models.Sale).delete()
        db.query(models.JournalEntryLine).delete()
        db.query(models.JournalEntry).delete()
        db.query(models.AuditLog).delete()
        db.commit()

        resp = _post_sale(api_client, tenant["owner"], tenant["company_id"])
        assert resp.status_code == 201
        api_sale = db.get(models.Sale, resp.json()["sale_id"])
        api_lines = journal_line_tuples(db)

        assert api_sale.amount == st_sale.amount
        assert api_sale.sale_type == st_sale.sale_type
        assert api_sale.status == st_sale.status
        assert api_sale.balance == st_sale.balance
        assert api_sale.paid_amount == st_sale.paid_amount
        assert len(api_lines) == len(st_lines)
        assert {(a, d, c) for _, a, d, c in api_lines} == {
            (a, d, c) for _, a, d, c in st_lines
        }


class TestSalesWriteCard:
    def test_card_sale_posts_balanced_journal(self, api_client, tenant, db):
        resp = _post_sale(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _sale_payload(
                payment_method="Card",
                card_bank_account_id=tenant["bank_account_id"],
            ),
        )
        assert resp.status_code == 201
        body = resp.json()
        sale = db.get(models.Sale, body["sale_id"])
        assert sale.sale_type == "Card"
        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "CardSale"
        assert _journal_balanced(db)

        bank = db.get(models.BankAccount, tenant["bank_account_id"])
        assert bank.balance == AMOUNT
        assert db.query(models.BankTransaction).count() == 1


class TestSalesWriteCredit:
    def test_credit_sale_with_customer(self, api_client, tenant, db):
        resp = _post_sale(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _sale_payload(payment_method="Credit", customer_name="Acme Corp"),
        )
        assert resp.status_code == 201
        body = resp.json()
        sale = db.get(models.Sale, body["sale_id"])
        assert sale.sale_type == "Credit"
        assert sale.customer_name == "Acme Corp"
        assert sale.status == "Open"
        assert sale.balance == AMOUNT
        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "CreditSale"
        assert _journal_balanced(db)


class TestSalesWriteAudit:
    def test_audit_row_created(self, api_client, tenant, db):
        resp = _post_sale(api_client, tenant["owner"], tenant["company_id"])
        assert resp.status_code == 201
        sale_id = resp.json()["sale_id"]
        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action=audit_svc.ACTION_CREATE,
                entity_type=audit_svc.ENTITY_SALE,
                entity_id=sale_id,
                company_id=tenant["company_id"],
            )
            .one()
        )
        assert audit.performed_by == tenant["owner"].username
        assert str(AMOUNT) in audit.description or f"{AMOUNT:,.2f}" in audit.description


class TestSalesWriteCompanyIsolation:
    def test_sale_belongs_to_selected_company(self, api_client, tenant, db):
        resp = _post_sale(api_client, tenant["owner"], tenant["company_id"])
        assert resp.status_code == 201
        sale = db.get(models.Sale, resp.json()["sale_id"])
        assert sale.company_id == tenant["company_id"]
        other_sales = (
            db.query(models.Sale)
            .filter(models.Sale.company_id == tenant["other_company_id"])
            .count()
        )
        assert other_sales == 0


class TestSalesWriteBoundaryCommit:
    def test_cash_sale_boundary_mode_single_boundary_commit(self, api_client, tenant, db):
        commit_modes.set_commit_mode_for_tests(POST_CASH_SALE_FAMILY, CommitMode.BOUNDARY)
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = _post_sale(api_client, tenant["owner"], tenant["company_id"])
            assert resp.status_code == 201
            # sale row commit + one boundary commit (JE + audit)
            assert mock_commit.call_count == 2


class TestSalesWriteNoGetCommits:
    def test_read_get_still_performs_no_commit(self, api_client, tenant, db):
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get(
                "/api/v1/receivables",
                headers=api_headers(tenant["owner"], company_id=tenant["company_id"]),
            )
            assert resp.status_code == 200
            mock_commit.assert_not_called()
