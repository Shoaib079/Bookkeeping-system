"""FASTAPI-P1.1 — read-only API endpoint expansion contract tests."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

import app as erp_app
import models
from api.dependencies import get_db
from api.main import create_app
from api.serialization import (
    bank_accounts_list_to_dict,
    bank_statement_rows_list_to_dict,
    budget_vs_actual_to_dict,
    cash_flow_to_dict,
    coa_list_to_dict,
    fiscal_periods_list_to_dict,
    year_end_closes_list_to_dict,
    journal_entries_list_to_dict,
    ledger_page_to_dict,
    opening_balances_status_to_dict,
    audit_log_list_to_dict,
    company_members_page_to_dict,
    company_settings_page_to_dict,
    backup_status_page_to_dict,
    my_account_page_to_dict,
    effective_permissions_page_to_dict,
    partner_statement_to_dict,
    partners_list_to_dict,
    payables_page_to_dict,
    permission_members_page_to_dict,
    profit_allocations_list_to_dict,
    receivable_sales_list_to_dict,
    sales_list_to_dict,
    expenses_list_to_dict,
    receivables_page_to_dict,
    recon_health_to_dict,
    statement_readiness_list_to_dict,
    trial_balance_to_dict,
    transaction_history_page_to_dict,
    vendors_list_to_dict,
    customers_list_to_dict,
    products_list_to_dict,
    purchases_list_to_dict,
    workers_list_to_dict,
)
from db import Base
from registry.coa_seed import seed_chart_of_accounts_for_company
from services import read_ar_ap, read_audit_log, read_backup_status, read_bank_accounts, read_bank_statement_rows, read_budget, read_coa, read_company_members, read_company_settings, read_customers, read_expenses, read_fiscal_periods, read_journal_entries, read_ledger, read_my_account, read_opening_balances, read_partner_statement, read_partners, read_permissions, read_products, read_profit_allocations, read_purchases, read_receivable_sales, read_recon_health, read_reconciliation, read_reports, read_sales, read_transaction_history, read_trial_balance, read_vendors, read_workers, read_year_end_closes
from services import tokens as token_service
from tests.fastapi_p1_jwt import TEST_JWT_SECRET, api_headers, password_hash_for_tests

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

POST_DATE = datetime.date(2026, 6, 1)
FROM_DATE = datetime.date(2026, 6, 1)
TO_DATE = datetime.date(2026, 6, 30)


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch):
    monkeypatch.setenv(token_service.JWT_SECRET_ENV, TEST_JWT_SECRET)


@pytest.fixture()
def db():
    from sqlalchemy.pool import StaticPool

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
def seeded_tenant(db):
    owner = models.User(
        id=erp_app._DEV_USER["id"],
        username=erp_app._DEV_USER["username"],
        display_name=erp_app._DEV_USER["display_name"],
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    cashier = models.User(
        username="cashier_p11",
        display_name="Cashier P11",
        password_hash=password_hash_for_tests(),
        role="cashier",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    viewer = models.User(
        username="viewer_p11",
        display_name="Viewer P11",
        password_hash=password_hash_for_tests(),
        role="viewer",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_a = models.Company(
        name="P11 Co A",
        slug="p11_co_a",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_b = models.Company(
        name="P11 Co B",
        slug="p11_co_b",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add_all([owner, cashier, viewer, co_a, co_b])
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
                user_id=owner.id,
                role="owner",
                is_active=True,
                created_at=datetime.datetime.now(),
            ),
            models.CompanyUser(
                company_id=co_a.id,
                user_id=cashier.id,
                role="cashier",
                is_active=True,
                created_at=datetime.datetime.now(),
            ),
            models.CompanyUser(
                company_id=co_a.id,
                user_id=viewer.id,
                role="viewer",
                is_active=True,
                created_at=datetime.datetime.now(),
            ),
        ]
    )
    seed_chart_of_accounts_for_company(db, co_a.id)
    seed_chart_of_accounts_for_company(db, co_b.id)

    cash_a = (
        db.query(models.ChartOfAccounts)
        .filter_by(company_id=co_a.id, account_name="Cash")
        .one()
    )
    sales_a = (
        db.query(models.ChartOfAccounts)
        .filter_by(company_id=co_a.id, account_name="Sales Revenue")
        .one()
    )
    je = models.JournalEntry(
        entry_date=POST_DATE,
        description="Cash sale",
        reference_type="CashSale",
        reference_id=1,
        company_id=co_a.id,
    )
    db.add(je)
    db.flush()
    db.add_all(
        [
            models.JournalEntryLine(
                journal_entry_id=je.id,
                account_id=cash_a.id,
                debit=250.0,
                credit=0.0,
                company_id=co_a.id,
            ),
            models.JournalEntryLine(
                journal_entry_id=je.id,
                account_id=sales_a.id,
                debit=0.0,
                credit=250.0,
                company_id=co_a.id,
            ),
        ]
    )

    vendor_a = models.Vendor(name="Vendor A", company_id=co_a.id, is_active=True)
    vendor_b = models.Vendor(name="Vendor B", company_id=co_b.id, is_active=True)
    customer_a = models.Customer(
        name="Customer A",
        contact="Alice",
        phone="555-0100",
        email="alice@example.com",
        company_id=co_a.id,
        is_active=True,
    )
    db.add_all([vendor_a, vendor_b, customer_a])
    db.flush()

    db.add_all(
        [
            models.Sale(
                date=POST_DATE,
                invoice_number="INV-A1",
                customer_name="Alice",
                description="Widgets",
                amount=1000.0,
                sale_type="Credit",
                paid_amount=200.0,
                balance=800.0,
                due_date=datetime.date(2026, 7, 1),
                status="Partial",
                is_void=False,
                company_id=co_a.id,
            ),
            models.Sale(
                date=POST_DATE,
                invoice_number="INV-B1",
                customer_name="Bob",
                description="",
                amount=300.0,
                sale_type="Credit",
                paid_amount=0.0,
                balance=300.0,
                due_date=datetime.date(2026, 5, 1),
                status="Open",
                is_void=False,
                company_id=co_b.id,
            ),
            models.Payable(
                date=POST_DATE,
                vendor_id=vendor_a.id,
                amount=400.0,
                paid_amount=100.0,
                balance=300.0,
                due_date=datetime.date(2026, 7, 15),
                paid=False,
                description="Rent",
                company_id=co_a.id,
            ),
            models.Payable(
                date=POST_DATE,
                vendor_id=vendor_b.id,
                amount=150.0,
                paid_amount=0.0,
                balance=150.0,
                due_date=datetime.date(2026, 7, 1),
                paid=False,
                description="Supplies",
                company_id=co_b.id,
            ),
            models.ExpenseRecord(
                date=POST_DATE,
                expense_type="Office",
                category="Office",
                description="Supplies",
                amount=75.0,
                payment_method="Cash",
                company_id=co_a.id,
                is_void=False,
            ),
            models.Purchase(
                date=POST_DATE,
                vendor_id=vendor_a.id,
                purchase_number="PO-100",
                amount=500.0,
                description="Stock",
                purchase_type="Credit",
                gl_debit="Inventory",
                is_void=False,
                company_id=co_a.id,
            ),
        ]
    )

    cap = models.ChartOfAccounts(
        account_code="P11-CAP",
        account_name="Partner Capital P11",
        account_type="Equity",
        is_active=True,
        balance=0.0,
        company_id=co_a.id,
    )
    cur = models.ChartOfAccounts(
        account_code="P11-CUR",
        account_name="Partner Current P11",
        account_type="Equity",
        is_active=True,
        balance=0.0,
        company_id=co_a.id,
    )
    adv = models.ChartOfAccounts(
        account_code="P11-ADV",
        account_name="Partner Advances P11",
        account_type="Asset",
        is_active=True,
        balance=0.0,
        company_id=co_a.id,
    )
    db.add_all([cap, cur, adv])
    db.flush()
    partner = models.Partner(
        name="Alice Partner",
        profit_share_pct=50.0,
        capital_account_id=cap.id,
        current_account_id=cur.id,
        advance_account_id=adv.id,
        is_active=True,
        created_at=datetime.datetime.now(),
        company_id=co_a.id,
    )
    db.add(partner)
    worker = models.Worker(
        name="Staff P11",
        role="Cashier",
        is_active=True,
        created_at=datetime.datetime.now(),
        company_id=co_a.id,
    )
    db.add(worker)

    bank_a = models.BankAccount(
        name="Main Bank",
        currency="TRY",
        company_id=co_a.id,
        is_active=True,
        balance=5000.0,
        kind="bank",
    )
    db.add(bank_a)
    db.flush()
    stmt_import = models.BankStatementImport(
        company_id=co_a.id,
        bank_account_id=bank_a.id,
        file_name="stmt.csv",
        file_hash="p11hash",
        file_size=10,
        file_path="/tmp/stmt.csv",
        status="staging",
        import_date=POST_DATE,
        start_date=FROM_DATE,
        end_date=TO_DATE,
        starting_balance=5000.0,
        ending_balance=5100.0,
        row_count=1,
        valid_count=1,
        flagged_count=0,
        error_count=0,
        currency="TRY",
        created_at=datetime.datetime.now(),
    )
    db.add(stmt_import)
    db.flush()
    stmt_row = models.BankStatementRow(
        bank_statement_import_id=stmt_import.id,
        status="staging",
        import_row_index=1,
        date=POST_DATE,
        description="Deposit",
        credit_amount=100.0,
        amount=100.0,
        currency="TRY",
        original_amount=100.0,
        parsed_successfully=True,
        created_at=datetime.datetime.now(),
    )
    fiscal_period = models.FiscalPeriod(
        name="H1 2026",
        start_date=FROM_DATE,
        end_date=TO_DATE,
        is_closed=False,
        company_id=co_a.id,
    )
    profit_alloc = models.PartnerProfitAllocation(
        fiscal_period_id=None,
        allocated_at=datetime.datetime.now(),
        total_net_income=150.0,
        is_void=False,
        created_at=datetime.datetime.now(),
        company_id=co_a.id,
    )
    db.add(fiscal_period)
    db.flush()
    profit_alloc.fiscal_period_id = fiscal_period.id
    db.add_all([stmt_row, profit_alloc])
    db.commit()

    credit_sale = (
        db.query(models.Sale)
        .filter_by(company_id=co_a.id, invoice_number="INV-A1")
        .one()
    )

    cash_b = (
        db.query(models.ChartOfAccounts)
        .filter_by(company_id=co_b.id, account_name="Cash")
        .one()
    )
    return {
        "owner_id": owner.id,
        "owner": owner,
        "cashier_id": cashier.id,
        "cashier": cashier,
        "viewer_id": viewer.id,
        "viewer": viewer,
        "company_a_id": co_a.id,
        "company_b_id": co_b.id,
        "cash_account_a_id": cash_a.id,
        "cash_account_b_id": cash_b.id,
        "partner_id": partner.id,
        "worker_id": worker.id,
        "vendor_a_id": vendor_a.id,
        "statement_row_id": stmt_row.id,
        "fiscal_period_id": fiscal_period.id,
        "credit_sale_id": credit_sale.id,
        "profit_allocation_id": profit_alloc.id,
        "from_date_iso": FROM_DATE.isoformat(),
        "to_date_iso": TO_DATE.isoformat(),
        "budget_year": FROM_DATE.year,
        "budget_month": FROM_DATE.month,
    }


READ_ENDPOINTS = [
    (
        "ledger",
        "/api/v1/ledger",
        {"account_id": "cash_account_a_id"},
        read_ledger.compute_ledger_page,
        ledger_page_to_dict,
        lambda db, tenant: {
            "company_id": tenant["company_a_id"],
            "account_id": tenant["cash_account_a_id"],
        },
    ),
    (
        "receivables",
        "/api/v1/receivables",
        {},
        read_ar_ap.compute_receivables_page,
        receivables_page_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "payables",
        "/api/v1/payables",
        {},
        read_ar_ap.compute_payables_page,
        payables_page_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "banking_readiness",
        "/api/v1/banking/readiness",
        {},
        read_reconciliation.compute_company_statement_readiness,
        statement_readiness_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"], "limit": 10},
    ),
    (
        "recon_health",
        "/api/v1/reconciliation/health",
        {},
        read_recon_health.compute_recon_health,
        recon_health_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "opening_balances_status",
        "/api/v1/opening-balances",
        {},
        read_opening_balances.compute_opening_balances_status,
        opening_balances_status_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "audit_log_list",
        "/api/v1/audit-log",
        {},
        read_audit_log.compute_audit_log_list,
        audit_log_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "company_members",
        "/api/v1/members",
        {},
        read_company_members.compute_company_members_page,
        company_members_page_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "products_list",
        "/api/v1/products",
        {},
        read_products.compute_products_list,
        products_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "permission_members",
        "/api/v1/permissions/members",
        {},
        read_permissions.compute_permission_members_page,
        permission_members_page_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "effective_permissions",
        "/api/v1/permissions/effective",
        {"user_id": "owner_id"},
        read_permissions.compute_effective_permissions_page,
        effective_permissions_page_to_dict,
        lambda db, tenant: {
            "company_id": tenant["company_a_id"],
            "user_id": tenant["owner_id"],
        },
    ),
    (
        "company_settings",
        "/api/v1/company-settings",
        {},
        read_company_settings.compute_company_settings_page,
        company_settings_page_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "backup_status",
        "/api/v1/backup-status",
        {},
        read_backup_status.compute_backup_status_page,
        backup_status_page_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "my_account",
        "/api/v1/my-account",
        {},
        read_my_account.compute_my_account_page,
        my_account_page_to_dict,
        lambda db, tenant: {
            "user_id": tenant["owner_id"],
            "company_id": tenant["company_a_id"],
            "company_role": "owner",
        },
    ),
    (
        "cash_flow",
        "/api/v1/reports/cash-flow",
        {"start_date": "from_date_iso", "end_date": "to_date_iso"},
        read_reports.compute_cash_flow,
        cash_flow_to_dict,
        lambda db, tenant: {
            "company_id": tenant["company_a_id"],
            "start_date": FROM_DATE,
            "end_date": TO_DATE,
        },
    ),
    (
        "trial_balance",
        "/api/v1/reports/trial-balance",
        {},
        read_trial_balance.compute_trial_balance,
        trial_balance_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "budget_vs_actual",
        "/api/v1/reports/budget-vs-actual",
        {"year": "budget_year", "month": "budget_month"},
        read_budget.compute_budget_vs_actual,
        budget_vs_actual_to_dict,
        lambda db, tenant: {
            "company_id": tenant["company_a_id"],
            "year": tenant["budget_year"],
            "month": tenant["budget_month"],
        },
    ),
    (
        "transactions",
        "/api/v1/transactions",
        {"start_date": "from_date_iso", "end_date": "to_date_iso"},
        read_transaction_history.compute_transaction_history_page,
        transaction_history_page_to_dict,
        lambda db, tenant: {
            "company_id": tenant["company_a_id"],
            "start_date": FROM_DATE,
            "end_date": TO_DATE,
        },
    ),
    (
        "chart_of_accounts",
        "/api/v1/chart-of-accounts",
        {},
        read_coa.compute_chart_of_accounts_list,
        coa_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "partners_list",
        "/api/v1/partners",
        {},
        read_partners.compute_partners_list,
        partners_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "bank_accounts_list",
        "/api/v1/bank-accounts",
        {},
        read_bank_accounts.compute_bank_accounts_list,
        bank_accounts_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "workers_list",
        "/api/v1/workers",
        {},
        read_workers.compute_workers_list,
        workers_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "bank_statement_rows_list",
        "/api/v1/bank-statement-rows",
        {},
        read_bank_statement_rows.compute_bank_statement_rows_list,
        bank_statement_rows_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "fiscal_periods_list",
        "/api/v1/fiscal-periods",
        {},
        read_fiscal_periods.compute_fiscal_periods_list,
        fiscal_periods_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "year_end_closes_list",
        "/api/v1/year-end-closes",
        {},
        read_year_end_closes.compute_year_end_closes_list,
        year_end_closes_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "journal_entries_list",
        "/api/v1/journal-entries",
        {},
        read_journal_entries.compute_journal_entries_list,
        journal_entries_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "vendors_list",
        "/api/v1/vendors",
        {},
        read_vendors.compute_vendors_list,
        vendors_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "customers_list",
        "/api/v1/customers",
        {},
        read_customers.compute_customers_list,
        customers_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "receivable_sales_list",
        "/api/v1/receivable-sales",
        {},
        read_receivable_sales.compute_receivable_sales_list,
        receivable_sales_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "sales_list",
        "/api/v1/sales",
        {},
        read_sales.compute_sales_list,
        sales_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "expenses_list",
        "/api/v1/expenses",
        {},
        read_expenses.compute_expenses_list,
        expenses_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "purchases_list",
        "/api/v1/purchases",
        {},
        read_purchases.compute_purchases_list,
        purchases_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
    (
        "profit_allocations_list",
        "/api/v1/profit-allocations",
        {},
        read_profit_allocations.compute_profit_allocations_list,
        profit_allocations_list_to_dict,
        lambda db, tenant: {"company_id": tenant["company_a_id"]},
    ),
]


class TestReadEndpointsReturnJson:
    @pytest.mark.parametrize("name,path,extra_params,compute_fn,to_dict,kwargs_fn", READ_ENDPOINTS)
    def test_endpoint_returns_service_dto_json(
        self,
        api_client,
        db,
        seeded_tenant,
        name,
        path,
        extra_params,
        compute_fn,
        to_dict,
        kwargs_fn,
    ):
        params = {
            key: seeded_tenant[param_key]
            for key, param_key in extra_params.items()
        }
        compute_kwargs = kwargs_fn(db, seeded_tenant)
        result = compute_fn(db, **compute_kwargs)
        if name == "banking_readiness":
            expected = to_dict(result, limit=compute_kwargs["limit"])
        else:
            expected = to_dict(result)
        resp = api_client.get(
            path,
            params=params,
            headers=api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["company_a_id"],
            ),
        )
        assert resp.status_code == 200
        assert resp.json() == expected

    def test_partner_statement_returns_service_dto_json(
        self, api_client, db, seeded_tenant
    ):
        expected = partner_statement_to_dict(
            read_partner_statement.compute_partner_statement(
                db,
                company_id=seeded_tenant["company_a_id"],
                partner_id=seeded_tenant["partner_id"],
                from_date=FROM_DATE,
                to_date=TO_DATE,
            )
        )
        resp = api_client.get(
            f"/api/v1/partners/{seeded_tenant['partner_id']}/statement",
            params={"from_date": FROM_DATE.isoformat(), "to_date": TO_DATE.isoformat()},
            headers=api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["company_a_id"],
            ),
        )
        assert resp.status_code == 200
        assert resp.json() == expected
        assert resp.json()["partner_name"] == "Alice Partner"


_DATE_PARAMS = {
    "start_date": FROM_DATE.isoformat(),
    "end_date": TO_DATE.isoformat(),
}
_BUDGET_PARAMS = {"year": FROM_DATE.year, "month": FROM_DATE.month}


class TestReadEndpointGuards:
    @pytest.mark.parametrize(
        "path,params",
        [
            ("/api/v1/ledger", {"account_id": 1}),
            ("/api/v1/chart-of-accounts", {}),
            ("/api/v1/receivables", {}),
            ("/api/v1/payables", {}),
            ("/api/v1/partners", {}),
            ("/api/v1/bank-accounts", {}),
            ("/api/v1/bank-statement-rows", {}),
            ("/api/v1/fiscal-periods", {}),
            ("/api/v1/year-end-closes", {}),
            ("/api/v1/journal-entries", {}),
            ("/api/v1/vendors", {}),
            ("/api/v1/customers", {}),
            ("/api/v1/sales", {}),
            ("/api/v1/expenses", {}),
            ("/api/v1/purchases", {}),
            ("/api/v1/receivable-sales", {}),
            ("/api/v1/profit-allocations", {}),
            ("/api/v1/workers", {}),
            ("/api/v1/banking/readiness", {}),
            ("/api/v1/reconciliation/health", {}),
            ("/api/v1/opening-balances", {}),
            ("/api/v1/audit-log", {}),
            ("/api/v1/members", {}),
            ("/api/v1/products", {}),
            ("/api/v1/permissions/members", {}),
            ("/api/v1/permissions/effective", {"user_id": 1}),
            ("/api/v1/company-settings", {}),
            ("/api/v1/backup-status", {}),
            ("/api/v1/my-account", {}),
            ("/api/v1/reports/cash-flow", _DATE_PARAMS),
            ("/api/v1/reports/trial-balance", {}),
            ("/api/v1/reports/budget-vs-actual", _BUDGET_PARAMS),
            ("/api/v1/transactions", _DATE_PARAMS),
            (
                "/api/v1/partners/1/statement",
                {"from_date": FROM_DATE.isoformat(), "to_date": TO_DATE.isoformat()},
            ),
        ],
    )
    def test_missing_user_header_rejected(self, api_client, seeded_tenant, path, params):
        resp = api_client.get(
            path,
            params=params,
            headers={"X-Company-Id": str(seeded_tenant["company_a_id"])},
        )
        assert resp.status_code == 401

    @pytest.mark.parametrize(
        "path,params",
        [
            ("/api/v1/ledger", {"account_id": 1}),
            ("/api/v1/chart-of-accounts", {}),
            ("/api/v1/receivables", {}),
            ("/api/v1/payables", {}),
            ("/api/v1/partners", {}),
            ("/api/v1/bank-accounts", {}),
            ("/api/v1/bank-statement-rows", {}),
            ("/api/v1/fiscal-periods", {}),
            ("/api/v1/year-end-closes", {}),
            ("/api/v1/journal-entries", {}),
            ("/api/v1/vendors", {}),
            ("/api/v1/customers", {}),
            ("/api/v1/sales", {}),
            ("/api/v1/expenses", {}),
            ("/api/v1/purchases", {}),
            ("/api/v1/receivable-sales", {}),
            ("/api/v1/profit-allocations", {}),
            ("/api/v1/workers", {}),
            ("/api/v1/banking/readiness", {}),
            ("/api/v1/reconciliation/health", {}),
            ("/api/v1/opening-balances", {}),
            ("/api/v1/audit-log", {}),
            ("/api/v1/members", {}),
            ("/api/v1/products", {}),
            ("/api/v1/permissions/members", {}),
            ("/api/v1/permissions/effective", {"user_id": 1}),
            ("/api/v1/company-settings", {}),
            ("/api/v1/backup-status", {}),
            ("/api/v1/my-account", {}),
            ("/api/v1/reports/cash-flow", _DATE_PARAMS),
            ("/api/v1/reports/trial-balance", {}),
            ("/api/v1/reports/budget-vs-actual", _BUDGET_PARAMS),
            ("/api/v1/transactions", _DATE_PARAMS),
            (
                "/api/v1/partners/1/statement",
                {"from_date": FROM_DATE.isoformat(), "to_date": TO_DATE.isoformat()},
            ),
        ],
    )
    def test_missing_company_header_rejected(
        self, api_client, seeded_tenant, path, params
    ):
        resp = api_client.get(
            path,
            params=params,
            headers=api_headers(seeded_tenant["owner"]),
        )
        assert resp.status_code == 400
        assert "active_company_id" in resp.json()["detail"]

    @pytest.mark.parametrize(
        "path,params",
        [
            ("/api/v1/ledger", {"account_id": 1}),
            ("/api/v1/chart-of-accounts", {}),
            ("/api/v1/receivables", {}),
            ("/api/v1/payables", {}),
            ("/api/v1/partners", {}),
            ("/api/v1/fiscal-periods", {}),
            ("/api/v1/year-end-closes", {}),
            ("/api/v1/profit-allocations", {}),
            ("/api/v1/workers", {}),
            ("/api/v1/banking/readiness", {}),
            ("/api/v1/reconciliation/health", {}),
            ("/api/v1/opening-balances", {}),
            ("/api/v1/audit-log", {}),
            ("/api/v1/members", {}),
            ("/api/v1/products", {}),
            ("/api/v1/permissions/members", {}),
            ("/api/v1/permissions/effective", {"user_id": 1}),
            ("/api/v1/company-settings", {}),
            ("/api/v1/backup-status", {}),
            ("/api/v1/reports/cash-flow", _DATE_PARAMS),
            ("/api/v1/reports/trial-balance", {}),
            ("/api/v1/reports/budget-vs-actual", _BUDGET_PARAMS),
            ("/api/v1/transactions", _DATE_PARAMS),
            (
                f"/api/v1/partners/{{partner_id}}/statement",
                {"from_date": FROM_DATE.isoformat(), "to_date": TO_DATE.isoformat()},
            ),
        ],
    )
    def test_permission_denied_for_cashier(
        self, api_client, seeded_tenant, path, params
    ):
        if "{partner_id}" in path:
            path = path.format(partner_id=seeded_tenant["partner_id"])
        if path == "/api/v1/ledger":
            params = {"account_id": seeded_tenant["cash_account_a_id"]}
        user = seeded_tenant["cashier"]
        if path == "/api/v1/banking/readiness":
            user = seeded_tenant["viewer"]
        resp = api_client.get(
            path,
            params=params,
            headers=api_headers(
                user,
                company_id=seeded_tenant["company_a_id"],
            ),
        )
        assert resp.status_code == 403


class TestMyAccountAllRolesAccess:
    def test_cashier_can_read_my_account(self, api_client, seeded_tenant):
        resp = api_client.get(
            "/api/v1/my-account",
            headers=api_headers(
                seeded_tenant["cashier"],
                company_id=seeded_tenant["company_a_id"],
            ),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == seeded_tenant["cashier"].username
        assert body["company_role"] == "cashier"


class TestReadEndpointNoCommit:
    @pytest.mark.parametrize(
        "path,params",
        [
            ("/api/v1/ledger", None),
            ("/api/v1/receivables", {}),
            ("/api/v1/payables", {}),
            ("/api/v1/banking/readiness", {}),
            ("/api/v1/chart-of-accounts", {}),
            ("/api/v1/partners", {}),
            ("/api/v1/bank-accounts", {}),
            ("/api/v1/bank-statement-rows", {}),
            ("/api/v1/fiscal-periods", {}),
            ("/api/v1/year-end-closes", {}),
            ("/api/v1/journal-entries", {}),
            ("/api/v1/vendors", {}),
            ("/api/v1/customers", {}),
            ("/api/v1/sales", {}),
            ("/api/v1/expenses", {}),
            ("/api/v1/purchases", {}),
            ("/api/v1/receivable-sales", {}),
            ("/api/v1/profit-allocations", {}),
            ("/api/v1/workers", {}),
            ("/api/v1/banking/readiness", {}),
            ("/api/v1/reconciliation/health", {}),
            ("/api/v1/opening-balances", {}),
            ("/api/v1/audit-log", {}),
            ("/api/v1/members", {}),
            ("/api/v1/products", {}),
            ("/api/v1/permissions/members", {}),
            ("/api/v1/permissions/effective", {"user_id": 1}),
            ("/api/v1/company-settings", {}),
            ("/api/v1/backup-status", {}),
            ("/api/v1/my-account", {}),
            ("/api/v1/reports/cash-flow", _DATE_PARAMS),
            ("/api/v1/reports/trial-balance", {}),
            ("/api/v1/reports/budget-vs-actual", _BUDGET_PARAMS),
            ("/api/v1/transactions", _DATE_PARAMS),
            ("/api/v1/partners/{partner_id}/statement", None),
        ],
    )
    def test_get_performs_no_session_commit(
        self, api_client, db, seeded_tenant, path, params
    ):
        if "{partner_id}" in path:
            path = path.format(partner_id=seeded_tenant["partner_id"])
        if params is None and "ledger" in path:
            params = {"account_id": seeded_tenant["cash_account_a_id"]}
        elif params is None:
            params = {
                "from_date": FROM_DATE.isoformat(),
                "to_date": TO_DATE.isoformat(),
            }
        elif params == _DATE_PARAMS:
            params = dict(_DATE_PARAMS)
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get(
                path,
                params=params,
                headers=api_headers(
                    seeded_tenant["owner"],
                    company_id=seeded_tenant["company_a_id"],
                ),
            )
        assert resp.status_code == 200
        assert mock_commit.call_count == 0


class TestCompanyIsolation:
    def test_ledger_scoped_to_company(self, api_client, seeded_tenant):
        resp_a = api_client.get(
            "/api/v1/ledger",
            params={"account_id": seeded_tenant["cash_account_a_id"]},
            headers=api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["company_a_id"],
            ),
        )
        resp_b = api_client.get(
            "/api/v1/ledger",
            params={"account_id": seeded_tenant["cash_account_b_id"]},
            headers=api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["company_a_id"],
            ),
        )
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        assert resp_a.json()["row_count"] == 1
        assert resp_b.json()["row_count"] == 0

    def test_receivables_scoped_to_company(self, api_client, seeded_tenant):
        resp_a = api_client.get(
            "/api/v1/receivables",
            headers=api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["company_a_id"],
            ),
        )
        resp_b = api_client.get(
            "/api/v1/receivables",
            headers=api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["company_b_id"],
            ),
        )
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        assert len(resp_a.json()["rows"]) == 1
        assert len(resp_b.json()["rows"]) == 1
        assert resp_a.json()["rows"][0]["invoice_number"] == "INV-A1"
        assert resp_b.json()["rows"][0]["invoice_number"] == "INV-B1"

    def test_payables_scoped_to_company(self, api_client, seeded_tenant):
        resp_a = api_client.get(
            "/api/v1/payables",
            headers=api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["company_a_id"],
            ),
        )
        resp_b = api_client.get(
            "/api/v1/payables",
            headers=api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["company_b_id"],
            ),
        )
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        assert resp_a.json()["rows"][0]["vendor_name"] == "Vendor A"
        assert resp_b.json()["rows"][0]["vendor_name"] == "Vendor B"


class TestDateValidation:
    def test_partner_statement_rejects_invalid_date(self, api_client, seeded_tenant):
        resp = api_client.get(
            f"/api/v1/partners/{seeded_tenant['partner_id']}/statement",
            params={"from_date": "not-a-date", "to_date": TO_DATE.isoformat()},
            headers=api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["company_a_id"],
            ),
        )
        assert resp.status_code == 422

    def test_ledger_accepts_iso_date_filters(self, api_client, seeded_tenant):
        resp = api_client.get(
            "/api/v1/ledger",
            params={
                "account_id": seeded_tenant["cash_account_a_id"],
                "start_date": FROM_DATE.isoformat(),
                "end_date": TO_DATE.isoformat(),
            },
            headers=api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["company_a_id"],
            ),
        )
        assert resp.status_code == 200
        assert resp.json()["filters"]["start_date"] == FROM_DATE.isoformat()

    def test_ledger_rejects_invalid_start_date(self, api_client, seeded_tenant):
        resp = api_client.get(
            "/api/v1/ledger",
            params={
                "account_id": seeded_tenant["cash_account_a_id"],
                "start_date": "bad-date",
            },
            headers=api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["company_a_id"],
            ),
        )
        assert resp.status_code == 422
