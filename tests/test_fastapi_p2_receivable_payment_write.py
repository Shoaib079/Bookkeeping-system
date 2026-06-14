"""FASTAPI-P2.4 — POST /api/v1/receivable-payments write endpoint."""

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
from services.commit_modes import CommitMode, POST_RECEIVABLE_PAYMENT_FAMILY
from tests.fastapi_p1_jwt import TEST_JWT_SECRET, api_headers, password_hash_for_tests
from tests.helpers.commit_parity import journal_line_tuples

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock

PAYMENT_DATE = datetime.date(2026, 6, 15)
SALE_AMOUNT = 200.0
PARTIAL = 80.0
FULL = 200.0
CURRENCY = "TRY"
INV_NUM = "INV-P24-001"
WRITE_RECEIVABLE_PAYMENTS_ENV = "ERP_API_WRITE_RECEIVABLE_PAYMENTS"

ZERO_PAYMENT_MSG = "Payment amount must be greater than zero."
OVERPAY_MSG = "Payment amount exceeds the remaining balance."
NOT_CREDIT_SALE_MSG = "Sale not found or is not a credit sale."
BANK_NOT_SELECTED_MSG = "No bank account selected."
CUSTOMER_PAYMENT_MSG = "Payment of {amount:,.2f} recorded against {invoice}."


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setenv(token_service.JWT_SECRET_ENV, TEST_JWT_SECRET)
    monkeypatch.delenv(DEV_HEADERS_ENV, raising=False)


@pytest.fixture(autouse=True)
def _write_receivable_payments_enabled(monkeypatch):
    monkeypatch.setenv(WRITE_RECEIVABLE_PAYMENTS_ENV, "1")


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
        username="owner_p24",
        display_name="Owner P24",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    outsider = models.User(
        username="outsider_p24",
        display_name="Outsider P24",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_a = models.Company(
        name="Co A P24",
        slug="co_a_p24",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_b = models.Company(
        name="Co B P24",
        slug="co_b_p24",
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
    customer = models.Customer(
        name="Credit Customer",
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
    db.add_all([customer, bank])
    db.flush()
    return {
        "owner": owner,
        "outsider": outsider,
        "company_id": co_a.id,
        "other_company_id": co_b.id,
        "customer_id": customer.id,
        "bank_account_id": bank.id,
    }


def _seed_credit_sale(
    db,
    company_id,
    *,
    amount: float = SALE_AMOUNT,
    customer_id: int | None = None,
    customer_name: str = "Credit Customer",
    invoice_number: str = INV_NUM,
) -> models.Sale:
    sale = models.Sale(
        date=PAYMENT_DATE,
        invoice_number=invoice_number,
        customer_name=customer_name,
        description="P24 credit sale",
        amount=amount,
        sale_type="Credit",
        paid_amount=0.0,
        balance=amount,
        due_date=PAYMENT_DATE + datetime.timedelta(days=30),
        status="Open",
        currency=CURRENCY,
        fx_rate=1.0,
        company_id=company_id,
        customer_id=customer_id,
    )
    db.add(sale)
    db.commit()
    posting.post_credit_sale(
        db, sale.id, amount, PAYMENT_DATE, currency=CURRENCY, company_id=company_id
    )
    return sale


@pytest.fixture()
def credit_sale(db, tenant):
    return _seed_credit_sale(
        db,
        tenant["company_id"],
        customer_id=tenant["customer_id"],
    )


def _payment_payload(sale_id: int, **overrides) -> dict:
    base = {
        "date": PAYMENT_DATE.isoformat(),
        "amount": PARTIAL,
        "currency": CURRENCY,
        "payment_method": "Cash",
        "sale_id": sale_id,
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}


def _post_payment(client, user, company_id, payload):
    return client.post(
        "/api/v1/receivable-payments",
        json=payload,
        headers=api_headers(user, company_id=company_id),
    )


def _journal_balanced(db) -> bool:
    lines = db.query(models.JournalEntryLine).all()
    deb = round(sum(l.debit or 0 for l in lines), 2)
    cred = round(sum(l.credit or 0 for l in lines), 2)
    return deb == cred and deb > 0


def _streamlit_customer_payment(db, company_id, sale, amount, payment_method="Cash"):
    sys.modules["streamlit"].session_state.clear()
    sys.modules["streamlit"].session_state["auth_user"] = dict(erp_app._DEV_USER)
    sys.modules["streamlit"].session_state["active_company_id"] = company_id
    label = erp_app._at_invoice_choice_label(sale)
    state = {
        "at_type_idx": 4,
        "at_pm": payment_method,
        "at_amount_display": str(int(amount)),
        "at_currency": CURRENCY,
        "at_date": PAYMENT_DATE,
        "at_inv": label,
    }
    if payment_method == "Bank":
        state["at_bank_pay_acct"] = "Main Bank"
    sys.modules["streamlit"].session_state.update(state)
    erp_app._at_process_submit(
        db,
        currency_default=CURRENCY,
        vendors=[],
        bank_accounts=db.query(models.BankAccount).all(),
        open_sales=[sale],
        txn_type="Customer Payment",
        _TYPE_DISPLAY_MAP={},
    )


class TestReceivablePaymentWriteFeatureFlag:
    def test_disabled_returns_404(self, api_client, tenant, credit_sale, monkeypatch):
        monkeypatch.delenv(WRITE_RECEIVABLE_PAYMENTS_ENV, raising=False)
        resp = _post_payment(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _payment_payload(credit_sale.id),
        )
        assert resp.status_code == 404


class TestReceivablePaymentWriteAuth:
    def test_missing_bearer_rejected(self, api_client, tenant, credit_sale):
        resp = api_client.post(
            "/api/v1/receivable-payments",
            json=_payment_payload(credit_sale.id),
            headers={"X-Company-Id": str(tenant["company_id"])},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_MISSING_DETAIL

    def test_user_without_membership_rejected(self, api_client, tenant, credit_sale):
        resp = _post_payment(
            api_client,
            tenant["outsider"],
            tenant["company_id"],
            _payment_payload(credit_sale.id),
        )
        assert resp.status_code == 403
        assert MEMBERSHIP_DENIED_MARKER in resp.json()["detail"]


class TestReceivablePaymentWriteValidation:
    def test_invalid_amount_rejected(self, api_client, tenant, credit_sale, db):
        resp = _post_payment(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _payment_payload(credit_sale.id, amount=0),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == ZERO_PAYMENT_MSG
        db.refresh(credit_sale)
        assert credit_sale.paid_amount == 0.0

    def test_overpayment_rejected(self, api_client, tenant, credit_sale, db):
        resp = _post_payment(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _payment_payload(credit_sale.id, amount=SALE_AMOUNT + 50),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == OVERPAY_MSG
        db.refresh(credit_sale)
        assert credit_sale.balance == SALE_AMOUNT

    def test_invalid_payment_method_rejected(self, api_client, tenant, credit_sale):
        resp = _post_payment(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _payment_payload(credit_sale.id, payment_method="Card"),
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "Card" in detail
        assert "Customer Payment" in detail

    def test_company_id_in_body_rejected(self, api_client, tenant, credit_sale):
        payload = _payment_payload(credit_sale.id)
        payload["company_id"] = tenant["other_company_id"]
        resp = _post_payment(api_client, tenant["owner"], tenant["company_id"], payload)
        assert resp.status_code == 422

    def test_bank_payment_requires_account(self, api_client, tenant, credit_sale):
        resp = _post_payment(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _payment_payload(credit_sale.id, payment_method="Bank"),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == BANK_NOT_SELECTED_MSG


class TestReceivablePaymentWriteCash:
    def test_partial_payment_updates_balance(self, api_client, tenant, credit_sale, db):
        resp = _post_payment(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _payment_payload(credit_sale.id, amount=PARTIAL),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["sale_id"] == credit_sale.id
        assert body["payment_id"] == body["journal_entry_id"]
        assert body["status"] == "ok"
        assert CUSTOMER_PAYMENT_MSG.format(
            amount=PARTIAL, invoice=INV_NUM
        ) == body["message"]

        db.refresh(credit_sale)
        assert credit_sale.paid_amount == PARTIAL
        assert credit_sale.balance == SALE_AMOUNT - PARTIAL
        assert credit_sale.status == "Partial"
        assert _journal_balanced(db)

        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "ReceivablePayment"
        assert je.reference_id == credit_sale.id
        assert je.company_id == tenant["company_id"]

    def test_full_payment_sets_paid(self, api_client, tenant, credit_sale, db):
        resp = _post_payment(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _payment_payload(credit_sale.id, amount=FULL),
        )
        assert resp.status_code == 201
        db.refresh(credit_sale)
        assert credit_sale.balance == 0.0
        assert credit_sale.status == "Paid"

    def test_cash_payment_matches_streamlit_accounting(
        self, api_client, tenant, credit_sale, db
    ):
        _streamlit_customer_payment(
            db, tenant["company_id"], credit_sale, PARTIAL, "Cash"
        )
        st_lines = [
            row
            for row in journal_line_tuples(db)
            if db.get(models.JournalEntry, row[0])
            and db.get(models.JournalEntry, row[0]).reference_type == "ReceivablePayment"
        ]

        db.query(models.JournalEntryLine).delete()
        db.query(models.JournalEntry).delete()
        db.query(models.AuditLog).delete()
        db.query(models.BankTransaction).delete()
        st_sale = db.get(models.Sale, credit_sale.id)
        st_sale.paid_amount = 0.0
        st_sale.balance = SALE_AMOUNT
        st_sale.status = "Open"
        db.commit()
        posting.post_credit_sale(
            db,
            credit_sale.id,
            SALE_AMOUNT,
            PAYMENT_DATE,
            currency=CURRENCY,
            company_id=tenant["company_id"],
        )

        resp = _post_payment(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _payment_payload(credit_sale.id, amount=PARTIAL),
        )
        assert resp.status_code == 201
        api_lines = [
            row
            for row in journal_line_tuples(db)
            if db.get(models.JournalEntry, row[0])
            and db.get(models.JournalEntry, row[0]).reference_type == "ReceivablePayment"
        ]
        assert len(api_lines) == len(st_lines)
        assert {(a, d, c) for _, a, d, c in api_lines} == {
            (a, d, c) for _, a, d, c in st_lines
        }


class TestReceivablePaymentWriteBank:
    def test_bank_payment_records_deposit(self, api_client, tenant, credit_sale, db):
        bank_before = db.get(models.BankAccount, tenant["bank_account_id"]).balance
        resp = _post_payment(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _payment_payload(
                credit_sale.id,
                payment_method="Bank",
                bank_account_id=tenant["bank_account_id"],
            ),
        )
        assert resp.status_code == 201
        bank = db.get(models.BankAccount, tenant["bank_account_id"])
        assert bank.balance == round(bank_before + PARTIAL, 2)
        bt = db.query(models.BankTransaction).one()
        assert bt.type == "deposit"
        assert INV_NUM in bt.description


class TestReceivablePaymentWriteCompanyIsolation:
    def test_cannot_pay_sale_from_another_company(
        self, api_client, tenant, db, credit_sale
    ):
        other_sale = _seed_credit_sale(
            db,
            tenant["other_company_id"],
            invoice_number="INV-OTHER",
            customer_name="Other Co Customer",
        )
        resp = _post_payment(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _payment_payload(other_sale.id),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == NOT_CREDIT_SALE_MSG
        db.refresh(other_sale)
        assert other_sale.paid_amount == 0.0

    def test_payment_je_belongs_to_selected_company(
        self, api_client, tenant, credit_sale, db
    ):
        resp = _post_payment(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _payment_payload(credit_sale.id),
        )
        assert resp.status_code == 201
        je = db.get(models.JournalEntry, resp.json()["journal_entry_id"])
        assert je.company_id == tenant["company_id"]


class TestReceivablePaymentWriteAudit:
    def test_audit_row_created(self, api_client, tenant, credit_sale, db):
        resp = _post_payment(
            api_client,
            tenant["owner"],
            tenant["company_id"],
            _payment_payload(credit_sale.id),
        )
        assert resp.status_code == 201
        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action=audit_svc.ACTION_PAYMENT,
                entity_type=audit_svc.ENTITY_SALE,
                entity_id=credit_sale.id,
                company_id=tenant["company_id"],
            )
            .one()
        )
        assert audit.performed_by == tenant["owner"].username
        assert INV_NUM in audit.description


class TestReceivablePaymentWriteBoundaryCommit:
    def test_boundary_mode_single_boundary_commit(
        self, api_client, tenant, credit_sale, db
    ):
        commit_modes.set_commit_mode_for_tests(
            POST_RECEIVABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = _post_payment(
                api_client,
                tenant["owner"],
                tenant["company_id"],
                _payment_payload(credit_sale.id),
            )
            assert resp.status_code == 201
            assert mock_commit.call_count == 1


class TestReceivablePaymentWriteNoGetCommits:
    def test_read_get_still_performs_no_commit(self, api_client, tenant, db):
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get(
                "/api/v1/receivables",
                headers=api_headers(tenant["owner"], company_id=tenant["company_id"]),
            )
            assert resp.status_code == 200
            mock_commit.assert_not_called()
