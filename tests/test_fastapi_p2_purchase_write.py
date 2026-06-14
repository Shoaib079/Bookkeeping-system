"""FASTAPI-P2.3 — POST /api/v1/purchases write endpoint."""

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
from registry.categories_seed import seed_default_categories_for_company
from registry.coa_seed import seed_chart_of_accounts_for_company
from services import audit as audit_svc
from services import commit_modes
from services import tokens as token_service
from services.commit_modes import CommitMode, POST_PURCHASE_FAMILY
from tests.fastapi_p1_jwt import TEST_JWT_SECRET, api_headers, password_hash_for_tests
from tests.helpers.commit_parity import journal_line_tuples

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock

PURCHASE_DATE = datetime.date(2026, 6, 12)
AMOUNT = 200.0
CURRENCY = "TRY"
WRITE_PURCHASES_ENV = "ERP_API_WRITE_PURCHASES"
INVALID_AMOUNT_MSG = "❌ Please enter a valid amount greater than zero."
CATEGORY_REQUIRED_MSG = "Select a category before saving"
VENDOR_REQUIRED_MSG = "Select a vendor before saving a purchase."
VENDOR_NOT_FOUND_MSG = "Vendor not found."
BANK_NOT_SELECTED_MSG = "No bank account selected."


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setenv(token_service.JWT_SECRET_ENV, TEST_JWT_SECRET)
    monkeypatch.delenv(DEV_HEADERS_ENV, raising=False)


@pytest.fixture(autouse=True)
def _write_purchases_enabled(monkeypatch):
    monkeypatch.setenv(WRITE_PURCHASES_ENV, "1")


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
        username="owner_p23",
        display_name="Owner P23",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    outsider = models.User(
        username="outsider_p23",
        display_name="Outsider P23",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_a = models.Company(
        name="Co A P23",
        slug="co_a_p23",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_b = models.Company(
        name="Co B P23",
        slug="co_b_p23",
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
    seed_default_categories_for_company(db, co_a.id)
    vendor = models.Vendor(
        name="Acme Supplies",
        company_id=co_a.id,
        is_active=True,
    )
    bank = models.BankAccount(
        name="Main Bank",
        currency=CURRENCY,
        company_id=co_a.id,
        is_active=True,
        balance=5000.0,
        kind="bank",
    )
    db.add_all([vendor, bank])
    db.commit()

    inv_cat = (
        db.query(models.TransactionCategory)
        .filter_by(company_id=co_a.id, transaction_type="Purchase", name="Inventory")
        .one()
    )
    stock_sub = (
        db.query(models.TransactionSubcategory)
        .filter_by(category_id=inv_cat.id, name="General Stock")
        .one()
    )
    return {
        "owner": owner,
        "outsider": outsider,
        "company_id": co_a.id,
        "other_company_id": co_b.id,
        "vendor_id": vendor.id,
        "bank_account_id": bank.id,
        "inventory_category_id": inv_cat.id,
        "stock_subcategory_id": stock_sub.id,
    }


def _purchase_payload(**overrides) -> dict:
    base = {
        "date": PURCHASE_DATE.isoformat(),
        "amount": AMOUNT,
        "currency": CURRENCY,
        "payment_method": "Cash",
        "vendor_id": None,
        "category_id": None,
        "notes": "API purchase",
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}


def _post_purchase(client, user, company_id, payload=None):
    return client.post(
        "/api/v1/purchases",
        json=payload or _purchase_payload(),
        headers=api_headers(user, company_id=company_id),
    )


def _journal_balanced(db) -> bool:
    lines = db.query(models.JournalEntryLine).all()
    deb = round(sum(l.debit or 0 for l in lines), 2)
    cred = round(sum(l.credit or 0 for l in lines), 2)
    return deb == cred and deb > 0


def _streamlit_cash_purchase(db, company_id, vendor_id, category_id, subcategory_id):
    vendor = db.get(models.Vendor, vendor_id)
    sys.modules["streamlit"].session_state.clear()
    sys.modules["streamlit"].session_state["auth_user"] = dict(erp_app._DEV_USER)
    sys.modules["streamlit"].session_state["active_company_id"] = company_id
    sys.modules["streamlit"].session_state.update(
        {
            "at_type_idx": 2,
            "at_pm": "Cash",
            "at_amount_display": str(int(AMOUNT)),
            "at_currency": CURRENCY,
            "at_date": PURCHASE_DATE,
            "at_vendor": vendor.name,
            "mob_at_cat_id": category_id,
            "mob_at_subcat_id": subcategory_id,
            "at_notes_field": "Streamlit purchase",
        }
    )
    erp_app._at_process_submit(
        db,
        currency_default=CURRENCY,
        vendors=db.query(models.Vendor).filter_by(company_id=company_id).all(),
        bank_accounts=db.query(models.BankAccount).all(),
        open_sales=[],
        txn_type="Purchase",
        _TYPE_DISPLAY_MAP={},
    )


class TestPurchaseWriteFeatureFlag:
    def test_disabled_returns_404(self, api_client, tenant, monkeypatch):
        monkeypatch.delenv(WRITE_PURCHASES_ENV, raising=False)
        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(
                vendor_id=tenant["vendor_id"],
                category_id=tenant["inventory_category_id"],
            ),
        )
        assert resp.status_code == 404


class TestPurchaseWriteAuth:
    def test_missing_bearer_rejected(self, api_client, tenant):
        payload = _purchase_payload(
            vendor_id=tenant["vendor_id"],
            category_id=tenant["inventory_category_id"],
        )
        resp = api_client.post(
            "/api/v1/purchases",
            json=payload,
            headers={"X-Company-Id": str(tenant["company_id"])},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_MISSING_DETAIL

    def test_invalid_bearer_rejected(self, api_client, tenant):
        payload = _purchase_payload(
            vendor_id=tenant["vendor_id"],
            category_id=tenant["inventory_category_id"],
        )
        resp = api_client.post(
            "/api/v1/purchases",
            json=payload,
            headers=api_headers("bad-token", company_id=tenant["company_id"]),
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_INVALID_DETAIL

    def test_missing_company_rejected(self, api_client, tenant):
        payload = _purchase_payload(
            vendor_id=tenant["vendor_id"],
            category_id=tenant["inventory_category_id"],
        )
        resp = api_client.post(
            "/api/v1/purchases",
            json=payload,
            headers=api_headers(tenant["owner"]),
        )
        assert resp.status_code == 400
        assert COMPANY_MISSING_MARKER in resp.json()["detail"]

    def test_user_without_membership_rejected(self, api_client, tenant):
        resp = _post_purchase(
            api_client,
            tenant["outsider"],
            tenant["company_id"],
            _purchase_payload(
                vendor_id=tenant["vendor_id"],
                category_id=tenant["inventory_category_id"],
            ),
        )
        assert resp.status_code == 403
        assert MEMBERSHIP_DENIED_MARKER in resp.json()["detail"]


class TestPurchaseWriteValidation:
    def test_invalid_amount_rejected(self, api_client, tenant, db):
        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(
                vendor_id=tenant["vendor_id"],
                category_id=tenant["inventory_category_id"],
                amount=0,
            ),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == INVALID_AMOUNT_MSG
        assert db.query(models.Purchase).count() == 0

    def test_invalid_payment_method_rejected(self, api_client, tenant, db):
        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(
                vendor_id=tenant["vendor_id"],
                category_id=tenant["inventory_category_id"],
                payment_method="Card",
            ),
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "Card" in detail
        assert "Purchase" in detail

    def test_company_id_in_body_rejected(self, api_client, tenant):
        payload = _purchase_payload(
            vendor_id=tenant["vendor_id"],
            category_id=tenant["inventory_category_id"],
        )
        payload["company_id"] = tenant["other_company_id"]
        resp = _post_purchase(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 422

    def test_vendor_required(self, api_client, tenant, db):
        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(category_id=tenant["inventory_category_id"]),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == VENDOR_REQUIRED_MSG
        assert db.query(models.Purchase).count() == 0

    def test_vendor_not_found(self, api_client, tenant, db):
        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(
                vendor_name="Missing Vendor",
                category_id=tenant["inventory_category_id"],
            ),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == VENDOR_NOT_FOUND_MSG

    def test_category_required(self, api_client, tenant, db):
        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(vendor_id=tenant["vendor_id"]),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == CATEGORY_REQUIRED_MSG

    def test_bank_payment_requires_account(self, api_client, tenant, db):
        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(
                vendor_id=tenant["vendor_id"],
                category_id=tenant["inventory_category_id"],
                payment_method="Bank",
            ),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == BANK_NOT_SELECTED_MSG


class TestPurchaseWriteCash:
    def test_cash_purchase_posts_balanced_journal(self, api_client, tenant, db):
        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(
                vendor_id=tenant["vendor_id"],
                category_id=tenant["inventory_category_id"],
                subcategory_id=tenant["stock_subcategory_id"],
            ),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["purchase_id"] > 0
        assert body["journal_entry_id"] > 0
        assert body["payable_id"] is None
        assert body["status"] == "ok"
        assert f"PUR#{body['purchase_id']}" in body["message"]

        pur = db.get(models.Purchase, body["purchase_id"])
        assert pur.company_id == tenant["company_id"]
        assert pur.purchase_type == "Cash"
        assert pur.gl_debit == "Inventory"
        assert _journal_balanced(db)

        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "CashPurchase"
        assert je.reference_id == pur.id

    def test_cash_purchase_matches_streamlit_accounting(self, api_client, tenant, db):
        _streamlit_cash_purchase(
            db,
            tenant["company_id"],
            tenant["vendor_id"],
            tenant["inventory_category_id"],
            tenant["stock_subcategory_id"],
        )
        st_pur = db.query(models.Purchase).one()
        st_lines = journal_line_tuples(db)

        db.query(models.Payable).delete()
        db.query(models.Purchase).delete()
        db.query(models.JournalEntryLine).delete()
        db.query(models.JournalEntry).delete()
        db.query(models.AuditLog).delete()
        db.commit()

        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(
                vendor_id=tenant["vendor_id"],
                category_id=tenant["inventory_category_id"],
                subcategory_id=tenant["stock_subcategory_id"],
            ),
        )
        assert resp.status_code == 201
        api_pur = db.get(models.Purchase, resp.json()["purchase_id"])
        api_lines = journal_line_tuples(db)

        assert api_pur.amount == st_pur.amount
        assert api_pur.purchase_type == st_pur.purchase_type
        assert api_pur.gl_debit == st_pur.gl_debit
        assert len(api_lines) == len(st_lines)
        assert {(a, d, c) for _, a, d, c in api_lines} == {
            (a, d, c) for _, a, d, c in st_lines
        }


class TestPurchaseWriteBank:
    def test_bank_purchase_posts_and_records_withdrawal(self, api_client, tenant, db):
        bank_before = db.get(models.BankAccount, tenant["bank_account_id"]).balance
        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(
                vendor_id=tenant["vendor_id"],
                category_id=tenant["inventory_category_id"],
                subcategory_id=tenant["stock_subcategory_id"],
                payment_method="Bank",
                bank_account_id=tenant["bank_account_id"],
            ),
        )
        assert resp.status_code == 201
        pur = db.get(models.Purchase, resp.json()["purchase_id"])
        assert pur.purchase_type == "Bank"
        je = db.get(models.JournalEntry, resp.json()["journal_entry_id"])
        assert je.reference_type == "BankPurchase"
        assert _journal_balanced(db)

        bank = db.get(models.BankAccount, tenant["bank_account_id"])
        assert bank.balance == round(bank_before - AMOUNT, 2)
        bt = db.query(models.BankTransaction).one()
        assert bt.type == "withdrawal"
        assert f"Purchase PUR#{pur.id}" in bt.description


class TestPurchaseWriteCredit:
    def test_credit_purchase_creates_payable(self, api_client, tenant, db):
        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(
                vendor_id=tenant["vendor_id"],
                category_id=tenant["inventory_category_id"],
                subcategory_id=tenant["stock_subcategory_id"],
                payment_method="Credit",
            ),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["payable_id"] is not None
        assert "Payable created" in body["message"]

        pur = db.get(models.Purchase, body["purchase_id"])
        payable = db.get(models.Payable, body["payable_id"])
        assert pur.purchase_type == "Credit"
        assert payable.purchase_id == pur.id
        assert payable.vendor_id == tenant["vendor_id"]
        assert payable.company_id == tenant["company_id"]
        assert payable.amount == AMOUNT
        assert payable.paid is False
        assert payable.due_date == PURCHASE_DATE + datetime.timedelta(days=30)
        assert payable.expense_category == "Inventory"
        assert payable.description == f"From Purchase #{pur.id}: API purchase"

        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "Purchase"
        assert _journal_balanced(db)


class TestPurchaseWriteCategoryBehavior:
    def test_auto_picks_first_subcategory_when_omitted(self, api_client, tenant, db):
        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(
                vendor_id=tenant["vendor_id"],
                category_id=tenant["inventory_category_id"],
            ),
        )
        assert resp.status_code == 201
        pur = db.get(models.Purchase, resp.json()["purchase_id"])
        assert pur.tx_subcategory_id == tenant["stock_subcategory_id"]

    def test_category_name_resolution(self, api_client, tenant, db):
        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(
                vendor_name="Acme Supplies",
                category_name="Inventory",
                subcategory_name="General Stock",
            ),
        )
        assert resp.status_code == 201
        pur = db.get(models.Purchase, resp.json()["purchase_id"])
        assert pur.gl_debit == "Inventory"


class TestPurchaseWriteAudit:
    def test_audit_row_created_cash(self, api_client, tenant, db):
        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(
                vendor_id=tenant["vendor_id"],
                category_id=tenant["inventory_category_id"],
                subcategory_id=tenant["stock_subcategory_id"],
            ),
        )
        assert resp.status_code == 201
        purchase_id = resp.json()["purchase_id"]
        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action=audit_svc.ACTION_CREATE,
                entity_type="Purchase",
                entity_id=purchase_id,
                company_id=tenant["company_id"],
            )
            .one()
        )
        assert audit.performed_by == tenant["owner"].username
        assert f"PUR#{purchase_id}" in audit.description
        assert "payable created" not in audit.description

    def test_audit_row_credit_includes_payable_note(self, api_client, tenant, db):
        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(
                vendor_id=tenant["vendor_id"],
                category_id=tenant["inventory_category_id"],
                payment_method="Credit",
            ),
        )
        assert resp.status_code == 201
        audit = (
            db.query(models.AuditLog)
            .filter_by(entity_type="Purchase", entity_id=resp.json()["purchase_id"])
            .one()
        )
        assert "payable created" in audit.description


class TestPurchaseWriteCompanyIsolation:
    def test_purchase_and_payable_belong_to_company(self, api_client, tenant, db):
        resp = _post_purchase(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _purchase_payload(
                vendor_id=tenant["vendor_id"],
                category_id=tenant["inventory_category_id"],
                payment_method="Credit",
            ),
        )
        assert resp.status_code == 201
        pur = db.get(models.Purchase, resp.json()["purchase_id"])
        payable = db.get(models.Payable, resp.json()["payable_id"])
        assert pur.company_id == tenant["company_id"]
        assert payable.company_id == tenant["company_id"]
        assert payable.vendor_id == tenant["vendor_id"]
        assert (
            db.query(models.Purchase)
            .filter(models.Purchase.company_id == tenant["other_company_id"])
            .count()
            == 0
        )


class TestPurchaseWriteBoundaryCommit:
    def test_cash_purchase_boundary_mode_single_boundary_commit(
        self, api_client, tenant, db
    ):
        commit_modes.set_commit_mode_for_tests(POST_PURCHASE_FAMILY, CommitMode.BOUNDARY)
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = _post_purchase(
                api_client,
                tenant["owner"],
                tenant["company_id"],
                _purchase_payload(
                    vendor_id=tenant["vendor_id"],
                    category_id=tenant["inventory_category_id"],
                    subcategory_id=tenant["stock_subcategory_id"],
                ),
            )
            assert resp.status_code == 201
            assert mock_commit.call_count == 1


class TestPurchaseWriteNoGetCommits:
    def test_read_get_still_performs_no_commit(self, api_client, tenant, db):
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get(
                "/api/v1/receivables",
                headers=api_headers(tenant["owner"], company_id=tenant["company_id"]),
            )
            assert resp.status_code == 200
            mock_commit.assert_not_called()
