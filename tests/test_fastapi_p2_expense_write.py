"""FASTAPI-P2.2 — POST /api/v1/expenses write endpoint."""

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
from services.commit_modes import CommitMode, POST_EXPENSE_FAMILY
from services.money import money_to_float
from tests.fastapi_p1_jwt import TEST_JWT_SECRET, api_headers, password_hash_for_tests
from tests.helpers.commit_parity import journal_line_tuples

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock

EXPENSE_DATE = datetime.date(2026, 6, 10)
AMOUNT = 50.0
CURRENCY = "TRY"
WRITE_EXPENSES_ENV = "ERP_API_WRITE_EXPENSES"
INVALID_AMOUNT_MSG = "❌ Please enter a valid amount greater than zero."
CATEGORY_REQUIRED_MSG = "Select a category before saving"
SUBCATEGORY_REQUIRED_MSG = "Select a subcategory for this category"
BANK_NOT_SELECTED_MSG = "No bank account selected."


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setenv(token_service.JWT_SECRET_ENV, TEST_JWT_SECRET)
    monkeypatch.delenv(DEV_HEADERS_ENV, raising=False)


@pytest.fixture(autouse=True)
def _write_expenses_enabled(monkeypatch):
    monkeypatch.setenv(WRITE_EXPENSES_ENV, "1")


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
        username="owner_p22",
        display_name="Owner P22",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    outsider = models.User(
        username="outsider_p22",
        display_name="Outsider P22",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_a = models.Company(
        name="Co A P22",
        slug="co_a_p22",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_b = models.Company(
        name="Co B P22",
        slug="co_b_p22",
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
    bank = models.BankAccount(
        name="Main Bank",
        currency=CURRENCY,
        company_id=co_a.id,
        is_active=True,
        balance=5000.0,
        kind="bank",
    )
    db.add(bank)
    db.commit()

    office_cat = (
        db.query(models.TransactionCategory)
        .filter_by(company_id=co_a.id, transaction_type="Expense", name="Office")
        .one()
    )
    other_sub = (
        db.query(models.TransactionSubcategory)
        .filter_by(category_id=office_cat.id, name="Other")
        .one()
    )
    return {
        "owner": owner,
        "outsider": outsider,
        "company_id": co_a.id,
        "other_company_id": co_b.id,
        "bank_account_id": bank.id,
        "office_category_id": office_cat.id,
        "other_subcategory_id": other_sub.id,
    }


def _expense_payload(**overrides) -> dict:
    base = {
        "date": EXPENSE_DATE.isoformat(),
        "amount": AMOUNT,
        "currency": CURRENCY,
        "payment_method": "Cash",
        "category_id": None,
        "notes": "API expense",
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}


def _post_expense(client, user, company_id, payload=None):
    return client.post(
        "/api/v1/expenses",
        json=payload or _expense_payload(category_id=1),
        headers=api_headers(user, company_id=company_id),
    )


def _journal_balanced(db) -> bool:
    lines = db.query(models.JournalEntryLine).all()
    deb = round(sum(l.debit or 0 for l in lines), 2)
    cred = round(sum(l.credit or 0 for l in lines), 2)
    return deb == cred and deb > 0


def _streamlit_cash_expense(db, company_id, category_id):
    sys.modules["streamlit"].session_state.clear()
    sys.modules["streamlit"].session_state["auth_user"] = dict(erp_app._DEV_USER)
    sys.modules["streamlit"].session_state["active_company_id"] = company_id
    sys.modules["streamlit"].session_state.update(
        {
            "at_type_idx": 1,
            "mob_at_tab": 1,
            "at_pm": "Cash",
            "at_amount_display": str(int(AMOUNT)),
            "at_currency": CURRENCY,
            "at_date": EXPENSE_DATE,
            "at_expense_mode": "general",
            "mob_at_cat_id": category_id,
            "at_notes_field": "Streamlit expense",
        }
    )
    erp_app._at_process_submit(
        db,
        currency_default=CURRENCY,
        vendors=[],
        bank_accounts=db.query(models.BankAccount).all(),
        open_sales=[],
        txn_type="Expense",
        _TYPE_DISPLAY_MAP={},
    )


class TestExpenseWriteFeatureFlag:
    def test_disabled_returns_404(self, api_client, tenant, monkeypatch):
        monkeypatch.delenv(WRITE_EXPENSES_ENV, raising=False)
        resp = _post_expense(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _expense_payload(category_id=tenant["office_category_id"]),
        )
        assert resp.status_code == 404


class TestExpenseWriteAuth:
    def test_missing_bearer_rejected(self, api_client, tenant):
        resp = api_client.post(
            "/api/v1/expenses",
            json=_expense_payload(category_id=tenant["office_category_id"]),
            headers={"X-Company-Id": str(tenant["company_id"])},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_MISSING_DETAIL

    def test_invalid_bearer_rejected(self, api_client, tenant):
        resp = api_client.post(
            "/api/v1/expenses",
            json=_expense_payload(category_id=tenant["office_category_id"]),
            headers=api_headers("bad-token", company_id=tenant["company_id"]),
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_INVALID_DETAIL

    def test_missing_company_rejected(self, api_client, tenant):
        resp = api_client.post(
            "/api/v1/expenses",
            json=_expense_payload(category_id=tenant["office_category_id"]),
            headers=api_headers(tenant["owner"]),
        )
        assert resp.status_code == 400
        assert COMPANY_MISSING_MARKER in resp.json()["detail"]

    def test_user_without_membership_rejected(self, api_client, tenant):
        resp = _post_expense(
            api_client,
            tenant["outsider"],
            tenant["company_id"],
            _expense_payload(category_id=tenant["office_category_id"]),
        )
        assert resp.status_code == 403
        assert MEMBERSHIP_DENIED_MARKER in resp.json()["detail"]


class TestExpenseWriteValidation:
    def test_invalid_amount_rejected(self, api_client, tenant, db):
        resp = _post_expense(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _expense_payload(
                category_id=tenant["office_category_id"],
                amount=0,
            ),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == INVALID_AMOUNT_MSG
        assert db.query(models.ExpenseRecord).count() == 0

    def test_invalid_payment_method_rejected(self, api_client, tenant, db):
        resp = _post_expense(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _expense_payload(
                category_id=tenant["office_category_id"],
                payment_method="Card",
            ),
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "Card" in detail
        assert "Expense" in detail

    def test_company_id_in_body_rejected(self, api_client, tenant):
        payload = _expense_payload(category_id=tenant["office_category_id"])
        payload["company_id"] = tenant["other_company_id"]
        resp = _post_expense(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 422

    def test_category_required(self, api_client, tenant, db):
        resp = _post_expense(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _expense_payload(),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == CATEGORY_REQUIRED_MSG
        assert db.query(models.ExpenseRecord).count() == 0

    def test_bank_payment_requires_account(self, api_client, tenant, db):
        resp = _post_expense(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _expense_payload(
                category_id=tenant["office_category_id"],
                payment_method="Bank",
            ),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == BANK_NOT_SELECTED_MSG
        assert db.query(models.ExpenseRecord).count() == 0


class TestExpenseWriteCash:
    def test_cash_expense_posts_balanced_journal(self, api_client, tenant, db):
        resp = _post_expense(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _expense_payload(
                category_id=tenant["office_category_id"],
                subcategory_id=tenant["other_subcategory_id"],
            ),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["expense_id"] > 0
        assert body["journal_entry_id"] > 0
        assert body["status"] == "ok"
        assert "expense recorded" in body["message"].lower()

        exp = db.get(models.ExpenseRecord, body["expense_id"])
        assert exp is not None
        assert exp.company_id == tenant["company_id"]
        assert exp.payment_method == "Cash"
        assert exp.amount == AMOUNT
        assert exp.expense_type == "Office"
        assert exp.category == "Other"
        assert _journal_balanced(db)

        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "Expense"
        assert je.reference_id == exp.id
        assert je.company_id == tenant["company_id"]

    def test_cash_expense_matches_streamlit_accounting(self, api_client, tenant, db):
        _streamlit_cash_expense(db, tenant["company_id"], tenant["office_category_id"])
        st_exp = db.query(models.ExpenseRecord).one()
        st_lines = journal_line_tuples(db)

        db.query(models.ExpenseRecord).delete()
        db.query(models.JournalEntryLine).delete()
        db.query(models.JournalEntry).delete()
        db.query(models.AuditLog).delete()
        db.commit()

        resp = _post_expense(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _expense_payload(category_id=tenant["office_category_id"]),
        )
        assert resp.status_code == 201
        api_exp = db.get(models.ExpenseRecord, resp.json()["expense_id"])
        api_lines = journal_line_tuples(db)

        assert api_exp.amount == st_exp.amount
        assert api_exp.payment_method == st_exp.payment_method
        assert api_exp.expense_type == st_exp.expense_type
        assert api_exp.category == st_exp.category
        assert len(api_lines) == len(st_lines)
        assert {(a, d, c) for _, a, d, c in api_lines} == {
            (a, d, c) for _, a, d, c in st_lines
        }


class TestExpenseWriteBank:
    def test_bank_expense_posts_and_records_withdrawal(self, api_client, tenant, db):
        bank_before = db.get(models.BankAccount, tenant["bank_account_id"]).balance
        resp = _post_expense(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _expense_payload(
                category_id=tenant["office_category_id"],
                subcategory_id=tenant["other_subcategory_id"],
                payment_method="Bank",
                bank_account_id=tenant["bank_account_id"],
            ),
        )
        assert resp.status_code == 201
        body = resp.json()
        exp = db.get(models.ExpenseRecord, body["expense_id"])
        assert exp.payment_method == "Bank"
        assert _journal_balanced(db)

        bank = db.get(models.BankAccount, tenant["bank_account_id"])
        assert money_to_float(bank.balance) == round(money_to_float(bank_before) - AMOUNT, 2)
        bt = db.query(models.BankTransaction).one()
        assert bt.type == "withdrawal"
        assert bt.amount == AMOUNT


class TestExpenseWriteCategoryBehavior:
    def test_auto_picks_first_subcategory_when_omitted(self, api_client, tenant, db):
        resp = _post_expense(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _expense_payload(category_id=tenant["office_category_id"]),
        )
        assert resp.status_code == 201
        exp = db.get(models.ExpenseRecord, resp.json()["expense_id"])
        # Streamlit auto-picks first subcategory by name: "Office Supplies"
        assert exp.category == "Office Supplies"

    def test_category_name_resolution(self, api_client, tenant, db):
        resp = _post_expense(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _expense_payload(
                category_name="Office",
                subcategory_name="Other",
            ),
        )
        assert resp.status_code == 201
        exp = db.get(models.ExpenseRecord, resp.json()["expense_id"])
        assert exp.expense_type == "Office"
        assert exp.category == "Other"


class TestExpenseWriteAudit:
    def test_audit_row_created(self, api_client, tenant, db):
        resp = _post_expense(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _expense_payload(
                category_id=tenant["office_category_id"],
                subcategory_id=tenant["other_subcategory_id"],
            ),
        )
        assert resp.status_code == 201
        expense_id = resp.json()["expense_id"]
        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action=audit_svc.ACTION_CREATE,
                entity_type=audit_svc.ENTITY_EXPENSE_RECORD,
                entity_id=expense_id,
                company_id=tenant["company_id"],
            )
            .one()
        )
        assert audit.performed_by == tenant["owner"].username
        assert "Office" in audit.description


class TestExpenseWriteCompanyIsolation:
    def test_expense_belongs_to_selected_company(self, api_client, tenant, db):
        resp = _post_expense(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _expense_payload(
                category_id=tenant["office_category_id"],
                subcategory_id=tenant["other_subcategory_id"],
            ),
        )
        assert resp.status_code == 201
        exp = db.get(models.ExpenseRecord, resp.json()["expense_id"])
        assert exp.company_id == tenant["company_id"]
        assert (
            db.query(models.ExpenseRecord)
            .filter(models.ExpenseRecord.company_id == tenant["other_company_id"])
            .count()
            == 0
        )


class TestExpenseWriteBoundaryCommit:
    def test_cash_expense_boundary_mode_single_boundary_commit(
        self, api_client, tenant, db
    ):
        commit_modes.set_commit_mode_for_tests(POST_EXPENSE_FAMILY, CommitMode.BOUNDARY)
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = _post_expense(
                api_client,
                tenant["owner"],
                tenant["company_id"],
                _expense_payload(
                    category_id=tenant["office_category_id"],
                    subcategory_id=tenant["other_subcategory_id"],
                ),
            )
            assert resp.status_code == 201
            # expense post + audit in one boundary commit (cash, no extra bank commit)
            assert mock_commit.call_count == 1


class TestExpenseWriteNoGetCommits:
    def test_read_get_still_performs_no_commit(self, api_client, tenant, db):
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get(
                "/api/v1/receivables",
                headers=api_headers(tenant["owner"], company_id=tenant["company_id"]),
            )
            assert resp.status_code == 200
            mock_commit.assert_not_called()
