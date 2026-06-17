"""BANKING-SERVICE-01 BS-02 — match_post account resolution regression guard.

Pins ``services.posting.get_account_by_name(..., company_id=...)`` resolution per
``match_post`` posting branch after BS-02 removed ``_app().get_account_by_name``.

BS-02-CHAR pre-migration tests established baseline behavior; this module guards
the posting-service lookup path.
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event, func
from sqlalchemy.orm import sessionmaker

import app as erp_app
from db import Base
import models
from reconciliation.match_post import (
    MatchPostError,
    post_bank_charge_outflow,
    post_deposit_clearing_match,
    post_equity_statement_match,
    post_generic_deposit,
    post_partner_statement_match,
    post_vendor_outflow,
    post_worker_statement_match,
)
from registry.coa_seed import ensure_accounts_for_company, seed_chart_of_accounts_for_company
from registry.service import set_setting
from services import posting as posting_svc

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True

MATCH_POST_SRC = (
    Path(__file__).resolve().parents[1] / "reconciliation" / "match_post.py"
).read_text(encoding="utf-8")

CHAR_MARKER = "BS-02 regression guard"

# All posting kernels use posting-service lookups; worker advance balance uses posting service.
_APP_POSTING_FUNCTIONS = (
    "post_deposit_clearing_match",
    "post_generic_deposit",
    "post_partner_statement_match",
    "post_worker_statement_match",
    "post_equity_statement_match",
    "post_vendor_outflow",
    "post_bank_charge_outflow",
)
_WORKER_ONLY_APP_FUNCTION = "post_worker_statement_match"

# Distinct account-resolution scenarios exercised below (BS-02 pre-migration inventory).
RESOLUTION_BRANCHES: tuple[dict, ...] = (
    {
        "id": "deposit_clearing_no_fee",
        "function": "post_deposit_clearing_match",
        "accounts": (
            ("Bank", "TRY"),
            ("Card Sales Clearing", None),
        ),
    },
    {
        "id": "deposit_clearing_with_fee",
        "function": "post_deposit_clearing_match",
        "accounts": (
            ("Bank", "TRY"),
            ("Card Sales Clearing", None),
            ("Bank Charges", None),
        ),
    },
    {
        "id": "generic_deposit",
        "function": "post_generic_deposit",
        "accounts": (("Bank", "TRY"), ("Sales Revenue", "TRY")),
    },
    {
        "id": "partner_drawing",
        "function": "post_partner_statement_match",
        "accounts": (("Bank", "TRY"),),
    },
    {
        "id": "worker_salary",
        "function": "post_worker_statement_match",
        "accounts": (
            ("Salary Expense", None),
            ("Employee Advances", None),
            ("Bank", "TRY"),
        ),
    },
    {
        "id": "worker_advance",
        "function": "post_worker_statement_match",
        "accounts": (
            ("Salary Expense", None),
            ("Employee Advances", None),
            ("Bank", "TRY"),
        ),
    },
    {
        "id": "equity_owner_drawing",
        "function": "post_equity_statement_match",
        "accounts": (("Bank", "TRY"), ("Owner Drawings", None)),
    },
    {
        "id": "equity_owner_capital",
        "function": "post_equity_statement_match",
        "accounts": (("Bank", "TRY"), ("Owner Capital", None)),
    },
    {
        "id": "equity_loan_payment",
        "function": "post_equity_statement_match",
        "accounts": (("Bank", "TRY"), ("Loans", None)),
    },
    {
        "id": "equity_loan_receipt",
        "function": "post_equity_statement_match",
        "accounts": (("Bank", "TRY"), ("Loans", None)),
    },
    {
        "id": "vendor_payable",
        "function": "post_vendor_outflow",
        "accounts": (("Bank", "TRY"), ("Accounts Payable", None)),
    },
    {
        "id": "bank_charge",
        "function": "post_bank_charge_outflow",
        "accounts": (("Bank Charges", None), ("Bank", "TRY")),
    },
)

MISSING_ACCOUNT_CASES: tuple[tuple[str, str, str], ...] = (
    (
        "deposit_clearing_bank",
        "Bank",
        "Bank or Card Sales Clearing GL account missing",
    ),
    (
        "deposit_clearing_fee",
        "Bank Charges",
        "Bank Charges GL account missing",
    ),
    ("generic_deposit", "Bank", "GL accounts not found for deposit posting"),
    ("worker_salary", "Salary Expense", "Salary Expense account missing"),
    ("worker_advance", "Employee Advances", "Employee Advances account missing"),
    ("equity_drawing", "Owner Drawings", "Owner Drawings account missing"),
    ("equity_capital", "Owner Capital", "Owner Capital account missing"),
    ("equity_loan", "Loans", "Loans account missing"),
    ("vendor_payable", "Accounts Payable", "Accounts Payable GL missing"),
    ("bank_charge", "Bank Charges", "Bank Charges or Bank GL account missing"),
)


class AccountResolutionPin(Exception):
    """Stop match_post after GL account resolution, before posting side effects."""


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(erp_app._DEV_USER)
    sys.modules["streamlit"].session_state["auth_expires"] = (
        datetime.datetime.now() + datetime.timedelta(hours=24)
    )


def _set_active(company_id: int):
    sys.modules["streamlit"].session_state["active_company_id"] = company_id


@pytest.fixture(autouse=True)
def _clear_streamlit_state():
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

    with Session() as session:
        yield session


def _company(db, *, slug: str = "bs02_char"):
    co = models.Company(
        name=f"BS02 {slug}",
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.flush()
    seed_chart_of_accounts_for_company(db, co.id)
    ensure_accounts_for_company(db, co.id)
    set_setting(db, "banking.card_settlement_enabled", True, company_id=co.id)
    set_setting(db, "banking.bank_charges_enabled", True, company_id=co.id)
    _set_active(co.id)
    return co


def _bank(db, company_id, *, balance: float = 5000.0):
    ba = models.BankAccount(
        name="Main TRY",
        currency="TRY",
        company_id=company_id,
        is_active=True,
        balance=balance,
    )
    db.add(ba)
    db.flush()
    return ba


def _stmt_row(
    db,
    company_id,
    bank_account_id,
    *,
    credit: bool = True,
    amount: float = 100.0,
    description: str = "BS02 char row",
):
    imp = models.BankStatementImport(
        company_id=company_id,
        bank_account_id=bank_account_id,
        file_name="bs02.csv",
        file_hash=f"hash-{bank_account_id}-{amount}",
        file_size=10,
        file_path="/tmp/bs02.csv",
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
    db.flush()
    return row, imp


def _snapshot(db, row_id: int, bank_account_id: int) -> dict:
    row = db.get(models.BankStatementRow, row_id)
    ba = db.get(models.BankAccount, bank_account_id)
    return {
        "row_status": row.status,
        "row_match_type": row.match_type,
        "row_je_id": row.posted_journal_entry_id,
        "row_btxn_id": row.bank_transaction_id,
        "bank_balance": round(float(ba.balance), 2),
        "je_count": db.query(func.count()).select_from(models.JournalEntry).scalar(),
        "btxn_count": db.query(func.count()).select_from(models.BankTransaction).scalar(),
    }


def _assert_no_posting_side_effects(db, before: dict, after: dict):
    assert after == before


def _remove_account(db, company_id: int, account_name: str):
    acct = (
        db.query(models.ChartOfAccounts)
        .filter_by(account_name=account_name, company_id=company_id)
        .one()
    )
    db.delete(acct)
    db.flush()


def _expected_codes(db, company_id: int) -> dict[str, str]:
    rows = (
        db.query(models.ChartOfAccounts)
        .filter_by(company_id=company_id, is_active=True)
        .all()
    )
    return {r.account_name: r.account_code for r in rows}


def _install_resolution_tracker(monkeypatch) -> list[dict]:
    calls: list[dict] = []
    real_lookup = posting_svc.get_account_by_name

    def tracking_get_account_by_name(session, name, currency=None, *, company_id=None):
        acct = real_lookup(session, name, currency=currency, company_id=company_id)
        calls.append(
            {
                "name": name,
                "currency": currency,
                "company_id": company_id,
                "account_id": acct.id if acct else None,
                "account_code": acct.account_code if acct else None,
                "resolved_company_id": acct.company_id if acct else None,
            }
        )
        return acct

    monkeypatch.setattr(
        "reconciliation.match_post._posting_get_account_by_name",
        tracking_get_account_by_name,
    )
    monkeypatch.setattr(
        "reconciliation.match_post._create_bank_txn",
        lambda *args, **kwargs: (_ for _ in ()).throw(AccountResolutionPin()),
    )
    return calls


def _card_sale(db, company_id, amount: float = 100.0):
    sale = models.Sale(
        date=datetime.date.today(),
        invoice_number=f"BS02-{amount}",
        customer_name="Walk-in",
        amount=amount,
        sale_type="Card",
        status="Paid",
        company_id=company_id,
    )
    db.add(sale)
    db.flush()
    erp_app.post_card_sale(db, sale.id, amount, sale.date, currency="TRY")
    db.flush()
    return sale


class TestCharacterizationContract:
    def test_module_docstring_marks_bs02_regression_guard(self):
        doc = Path(__file__).read_text(encoding="utf-8")
        assert CHAR_MARKER in doc
        assert "BS-02" in doc

    def test_match_post_uses_posting_service_not_app_for_account_lookup(self):
        assert "def _get_account_by_name(" in MATCH_POST_SRC
        assert "_posting_get_account_by_name" in MATCH_POST_SRC
        assert "app.get_account_by_name(session" not in MATCH_POST_SRC
        assert MATCH_POST_SRC.count("app = _app()") == 0
        assert "def _app(" not in MATCH_POST_SRC
        assert "_posting_get_worker_advance_balance" in MATCH_POST_SRC
        assert f"def {_WORKER_ONLY_APP_FUNCTION}" in MATCH_POST_SRC

    def test_resolution_branch_inventory_matches_match_post_functions(self):
        branch_functions = {b["function"] for b in RESOLUTION_BRANCHES}
        assert branch_functions == set(_APP_POSTING_FUNCTIONS)


class TestBranchInventory:
    @pytest.mark.parametrize("branch", RESOLUTION_BRANCHES, ids=lambda b: b["id"])
    def test_branch_declares_expected_account_names(self, branch):
        names = [name for name, _currency in branch["accounts"]]
        assert names
        if branch["function"] == "post_generic_deposit":
            assert "credit_account_name" in MATCH_POST_SRC
            assert '_get_account_by_name(session, "Bank"' in MATCH_POST_SRC
            return
        for name in names:
            assert f'"{name}"' in MATCH_POST_SRC or f"'{name}'" in MATCH_POST_SRC


class TestCompanyScopedResolution:
    def test_explicit_company_id_scopes_posting_service_lookup(self, db):
        co_a = _company(db, slug="bs02_co_a")
        co_b = _company(db, slug="bs02_co_b")
        db.commit()
        _set_active(co_a.id)

        bank_b = (
            db.query(models.ChartOfAccounts)
            .filter_by(account_name="Bank", company_id=co_b.id, currency="TRY")
            .one()
        )
        resolved = posting_svc.get_account_by_name(
            db, "Bank", currency="TRY", company_id=co_b.id
        )
        assert resolved is not None
        assert resolved.id == bank_b.id
        assert resolved.account_code == "1010"
        assert resolved.company_id == co_b.id

    def test_app_shim_matches_posting_service_when_ambient_equals_company(self, db):
        co = _company(db, slug="bs02_parity")
        db.commit()
        _set_active(co.id)

        for name, currency in (
            ("Bank", "TRY"),
            ("Card Sales Clearing", None),
            ("Bank Charges", None),
            ("Salary Expense", None),
            ("Employee Advances", None),
            ("Owner Drawings", None),
            ("Owner Capital", None),
            ("Loans", None),
            ("Accounts Payable", None),
            ("Sales Revenue", None),
        ):
            app_acct = erp_app.get_account_by_name(db, name, currency=currency)
            svc_acct = posting_svc.get_account_by_name(
                db, name, currency=currency, company_id=co.id
            )
            assert app_acct is not None, name
            assert svc_acct is not None, name
            assert app_acct.id == svc_acct.id, name

    def test_match_post_passes_explicit_company_id_not_ambient(self, db, monkeypatch):
        co_a = _company(db, slug="bs02_amb_a")
        co_b = _company(db, slug="bs02_amb_b")
        ba = _bank(db, co_b.id)
        row, _imp = _stmt_row(db, co_b.id, ba.id, credit=True, amount=250.0)
        db.commit()
        _set_active(co_a.id)

        calls = _install_resolution_tracker(monkeypatch)
        with pytest.raises(AccountResolutionPin):
            post_generic_deposit(
                db,
                row_id=row.id,
                company_id=co_b.id,
                credit_account_name="Sales Revenue",
                user_id=1,
            )

        db.rollback()
        bank_calls = [c for c in calls if c["name"] == "Bank"]
        assert bank_calls
        assert all(c["company_id"] == co_b.id for c in calls)
        assert bank_calls[-1]["resolved_company_id"] == co_b.id


class TestAccountResolutionCalls:
    def test_deposit_clearing_resolves_bank_and_clearing_without_posting(self, db, monkeypatch):
        co = _company(db, slug="bs02_clear")
        ba = _bank(db, co.id)
        sale = _card_sale(db, co.id, amount=100.0)
        row, _imp = _stmt_row(db, co.id, ba.id, credit=True, amount=100.0)
        db.commit()

        calls = _install_resolution_tracker(monkeypatch)
        before = _snapshot(db, row.id, ba.id)
        codes = _expected_codes(db, co.id)

        with pytest.raises(AccountResolutionPin):
            post_deposit_clearing_match(
                db,
                row_id=row.id,
                company_id=co.id,
                sale_ids=[sale.id],
                user_id=1,
            )

        db.rollback()
        after = _snapshot(db, row.id, ba.id)
        _assert_no_posting_side_effects(db, before, after)

        resolved = {(c["name"], c["currency"]) for c in calls}
        assert ("Bank", "TRY") in resolved
        assert ("Card Sales Clearing", None) in resolved
        bank_calls = [c for c in calls if c["name"] == "Bank"]
        assert bank_calls[-1]["account_code"] == codes["Bank"]
        assert bank_calls[-1]["company_id"] == co.id

    def test_deposit_clearing_with_fee_resolves_bank_charges(self, db, monkeypatch):
        co = _company(db, slug="bs02_fee")
        ba = _bank(db, co.id)
        sale = _card_sale(db, co.id, amount=100.0)
        row, _imp = _stmt_row(db, co.id, ba.id, credit=True, amount=97.0)
        db.commit()

        calls = _install_resolution_tracker(monkeypatch)
        before = _snapshot(db, row.id, ba.id)

        with pytest.raises(AccountResolutionPin):
            post_deposit_clearing_match(
                db,
                row_id=row.id,
                company_id=co.id,
                sale_ids=[sale.id],
                user_id=1,
                confirm_inferred_fee=True,
            )

        db.rollback()
        _assert_no_posting_side_effects(db, before, _snapshot(db, row.id, ba.id))

        names = [c["name"] for c in calls]
        assert "Bank Charges" in names
        assert names.count("Bank Charges") >= 1

    def test_generic_deposit_resolves_bank_and_credit_accounts(self, db, monkeypatch):
        co = _company(db, slug="bs02_dep")
        ba = _bank(db, co.id)
        row, _imp = _stmt_row(db, co.id, ba.id, credit=True, amount=250.0)
        db.commit()

        calls = _install_resolution_tracker(monkeypatch)
        before = _snapshot(db, row.id, ba.id)
        codes = _expected_codes(db, co.id)

        with pytest.raises(AccountResolutionPin):
            post_generic_deposit(
                db,
                row_id=row.id,
                company_id=co.id,
                credit_account_name="Sales Revenue",
                user_id=1,
            )

        db.rollback()
        _assert_no_posting_side_effects(db, before, _snapshot(db, row.id, ba.id))

        pairs = [(c["name"], c["currency"]) for c in calls]
        assert ("Bank", "TRY") in pairs
        assert ("Sales Revenue", "TRY") in pairs
        bank_call = next(c for c in reversed(calls) if c["name"] == "Bank")
        credit_call = next(c for c in reversed(calls) if c["name"] == "Sales Revenue")
        assert bank_call["account_code"] == codes["Bank"]
        assert credit_call["account_code"] == codes["Sales Revenue"]

    def test_partner_drawing_resolves_bank_only(self, db, monkeypatch):
        co = _company(db, slug="bs02_partner")
        ba = _bank(db, co.id)
        pid, err = erp_app.create_partner(db, "Pat", 0.0)
        assert err == ""
        row, _imp = _stmt_row(db, co.id, ba.id, credit=False, amount=400.0)
        db.commit()

        calls = _install_resolution_tracker(monkeypatch)
        before = _snapshot(db, row.id, ba.id)

        with pytest.raises(AccountResolutionPin):
            post_partner_statement_match(
                db,
                row_id=row.id,
                company_id=co.id,
                partner_id=pid,
                movement_type="Drawing",
                user_id=1,
            )

        db.rollback()
        _assert_no_posting_side_effects(db, before, _snapshot(db, row.id, ba.id))
        assert [c["name"] for c in calls if c["name"] != "Card Sales Clearing"] == ["Bank"]

    def test_worker_salary_resolves_expense_advances_and_bank(self, db, monkeypatch):
        co = _company(db, slug="bs02_worker_sal")
        ba = _bank(db, co.id)
        wid, err = erp_app.create_worker(db, "Ali", role="Sales")
        assert err == ""
        row, _imp = _stmt_row(db, co.id, ba.id, credit=False, amount=1000.0)
        db.commit()

        calls = _install_resolution_tracker(monkeypatch)
        before = _snapshot(db, row.id, ba.id)
        codes = _expected_codes(db, co.id)

        with pytest.raises(AccountResolutionPin):
            post_worker_statement_match(
                db,
                row_id=row.id,
                company_id=co.id,
                worker_id=wid,
                movement_type="Salary",
                user_id=1,
                gross_salary=1000.0,
                deductions=0.0,
                advance_recovery=0.0,
                pay_period="2026-06",
            )

        db.rollback()
        _assert_no_posting_side_effects(db, before, _snapshot(db, row.id, ba.id))

        names = [c["name"] for c in calls]
        assert names == ["Salary Expense", "Employee Advances", "Bank"]
        assert calls[0]["account_code"] == codes["Salary Expense"]
        assert calls[1]["account_code"] == codes["Employee Advances"]
        assert calls[2]["account_code"] == codes["Bank"]

    def test_worker_advance_resolves_advances_and_bank(self, db, monkeypatch):
        co = _company(db, slug="bs02_worker_adv")
        ba = _bank(db, co.id)
        wid, err = erp_app.create_worker(db, "Veli", role="Ops")
        assert err == ""
        row, _imp = _stmt_row(db, co.id, ba.id, credit=False, amount=500.0)
        db.commit()

        calls = _install_resolution_tracker(monkeypatch)
        before = _snapshot(db, row.id, ba.id)

        with pytest.raises(AccountResolutionPin):
            post_worker_statement_match(
                db,
                row_id=row.id,
                company_id=co.id,
                worker_id=wid,
                movement_type="Advance",
                user_id=1,
            )

        db.rollback()
        _assert_no_posting_side_effects(db, before, _snapshot(db, row.id, ba.id))
        assert [c["name"] for c in calls] == [
            "Salary Expense",
            "Employee Advances",
            "Bank",
        ]

    @pytest.mark.parametrize(
        "equity_kind,credit,expected_second",
        [
            ("owner_drawing", False, "Owner Drawings"),
            ("owner_capital", True, "Owner Capital"),
            ("loan_payment", False, "Loans"),
            ("loan_receipt", True, "Loans"),
        ],
    )
    def test_equity_match_resolves_bank_and_equity_accounts(
        self, db, monkeypatch, equity_kind, credit, expected_second
    ):
        co = _company(db, slug=f"bs02_eq_{equity_kind}")
        ba = _bank(db, co.id)
        row, _imp = _stmt_row(
            db, co.id, ba.id, credit=credit, amount=750.0, description=equity_kind
        )
        db.commit()

        calls = _install_resolution_tracker(monkeypatch)
        before = _snapshot(db, row.id, ba.id)
        codes = _expected_codes(db, co.id)

        with pytest.raises(AccountResolutionPin):
            post_equity_statement_match(
                db,
                row_id=row.id,
                company_id=co.id,
                equity_kind=equity_kind,
                user_id=1,
            )

        db.rollback()
        _assert_no_posting_side_effects(db, before, _snapshot(db, row.id, ba.id))

        names = [c["name"] for c in calls]
        assert names[0] == "Bank"
        assert names[1] == expected_second
        assert calls[1]["account_code"] == codes[expected_second]

    def test_vendor_payable_resolves_bank_and_ap(self, db, monkeypatch):
        co = _company(db, slug="bs02_vendor")
        ba = _bank(db, co.id)
        vendor = models.Vendor(name="Supplier", company_id=co.id, is_active=True)
        db.add(vendor)
        db.flush()
        payable = models.Payable(
            vendor_id=vendor.id,
            amount=120.0,
            balance=120.0,
            paid_amount=0.0,
            date=datetime.date.today(),
            due_date=datetime.date.today(),
            company_id=co.id,
        )
        db.add(payable)
        row, _imp = _stmt_row(db, co.id, ba.id, credit=False, amount=120.0)
        db.commit()

        calls = _install_resolution_tracker(monkeypatch)
        before = _snapshot(db, row.id, ba.id)
        codes = _expected_codes(db, co.id)

        with pytest.raises(AccountResolutionPin):
            post_vendor_outflow(
                db,
                row_id=row.id,
                company_id=co.id,
                vendor_id=vendor.id,
                user_id=1,
                payable_id=payable.id,
            )

        db.rollback()
        _assert_no_posting_side_effects(db, before, _snapshot(db, row.id, ba.id))

        names = [c["name"] for c in calls]
        assert names == ["Bank", "Accounts Payable"]
        assert calls[0]["account_code"] == codes["Bank"]
        assert calls[1]["account_code"] == codes["Accounts Payable"]

    def test_bank_charge_resolves_charges_and_bank(self, db, monkeypatch):
        co = _company(db, slug="bs02_charge")
        ba = _bank(db, co.id)
        row, _imp = _stmt_row(
            db,
            co.id,
            ba.id,
            credit=False,
            amount=12.5,
            description="POS commission fee",
        )
        db.commit()

        calls = _install_resolution_tracker(monkeypatch)
        before = _snapshot(db, row.id, ba.id)
        codes = _expected_codes(db, co.id)

        with pytest.raises(AccountResolutionPin):
            post_bank_charge_outflow(
                db,
                row_id=row.id,
                company_id=co.id,
                user_id=1,
            )

        db.rollback()
        _assert_no_posting_side_effects(db, before, _snapshot(db, row.id, ba.id))

        names = [c["name"] for c in calls]
        assert names == ["Bank Charges", "Bank"]
        assert calls[0]["account_code"] == codes["Bank Charges"]
        assert calls[1]["account_code"] == codes["Bank"]


class TestMissingAccountErrors:
    @pytest.mark.parametrize("case_id,missing_name,message", MISSING_ACCOUNT_CASES)
    def test_missing_account_raises_match_post_error_without_side_effects(
        self, db, case_id, missing_name, message
    ):
        co = _company(db, slug=f"bs02_miss_{case_id}")
        ba = _bank(db, co.id)
        _remove_account(db, co.id, missing_name)

        if case_id.startswith("deposit_clearing"):
            sale = _card_sale(db, co.id, amount=100.0)
            amount = 97.0 if case_id.endswith("fee") else 100.0
            row, _imp = _stmt_row(db, co.id, ba.id, credit=True, amount=amount)
            db.commit()
            before = _snapshot(db, row.id, ba.id)
            kwargs = {
                "row_id": row.id,
                "company_id": co.id,
                "sale_ids": [sale.id],
                "user_id": 1,
            }
            if case_id.endswith("fee"):
                kwargs["confirm_inferred_fee"] = True
            with pytest.raises(MatchPostError, match=message):
                post_deposit_clearing_match(db, **kwargs)
        elif case_id == "generic_deposit":
            row, _imp = _stmt_row(db, co.id, ba.id, credit=True, amount=200.0)
            db.commit()
            before = _snapshot(db, row.id, ba.id)
            with pytest.raises(MatchPostError, match=message):
                post_generic_deposit(
                    db,
                    row_id=row.id,
                    company_id=co.id,
                    credit_account_name="Sales Revenue",
                    user_id=1,
                )
        elif case_id == "worker_salary":
            wid, _ = erp_app.create_worker(db, "Sal", role="Sales")
            row, _imp = _stmt_row(db, co.id, ba.id, credit=False, amount=1000.0)
            db.commit()
            before = _snapshot(db, row.id, ba.id)
            with pytest.raises(MatchPostError, match=message):
                post_worker_statement_match(
                    db,
                    row_id=row.id,
                    company_id=co.id,
                    worker_id=wid,
                    movement_type="Salary",
                    user_id=1,
                    gross_salary=1000.0,
                )
        elif case_id == "worker_advance":
            wid, _ = erp_app.create_worker(db, "Adv", role="Ops")
            row, _imp = _stmt_row(db, co.id, ba.id, credit=False, amount=500.0)
            db.commit()
            before = _snapshot(db, row.id, ba.id)
            with pytest.raises(MatchPostError, match=message):
                post_worker_statement_match(
                    db,
                    row_id=row.id,
                    company_id=co.id,
                    worker_id=wid,
                    movement_type="Advance",
                    user_id=1,
                )
        elif case_id.startswith("equity_"):
            kind = {
                "equity_drawing": "owner_drawing",
                "equity_capital": "owner_capital",
                "equity_loan": "loan_payment",
            }[case_id]
            credit = kind in ("owner_capital",)
            row, _imp = _stmt_row(
                db, co.id, ba.id, credit=credit, amount=300.0, description=kind
            )
            db.commit()
            before = _snapshot(db, row.id, ba.id)
            with pytest.raises(MatchPostError, match=message):
                post_equity_statement_match(
                    db,
                    row_id=row.id,
                    company_id=co.id,
                    equity_kind=kind,
                    user_id=1,
                )
        elif case_id == "vendor_payable":
            vendor = models.Vendor(name="V", company_id=co.id, is_active=True)
            db.add(vendor)
            db.flush()
            payable = models.Payable(
                vendor_id=vendor.id,
                amount=80.0,
                balance=80.0,
                paid_amount=0.0,
                date=datetime.date.today(),
                due_date=datetime.date.today(),
                company_id=co.id,
            )
            db.add(payable)
            row, _imp = _stmt_row(db, co.id, ba.id, credit=False, amount=80.0)
            db.commit()
            before = _snapshot(db, row.id, ba.id)
            with pytest.raises(MatchPostError, match=message):
                post_vendor_outflow(
                    db,
                    row_id=row.id,
                    company_id=co.id,
                    vendor_id=vendor.id,
                    user_id=1,
                    payable_id=payable.id,
                )
        elif case_id == "bank_charge":
            row, _imp = _stmt_row(
                db,
                co.id,
                ba.id,
                credit=False,
                amount=9.0,
                description="commission",
            )
            db.commit()
            before = _snapshot(db, row.id, ba.id)
            with pytest.raises(MatchPostError, match=message):
                post_bank_charge_outflow(
                    db,
                    row_id=row.id,
                    company_id=co.id,
                    user_id=1,
                )
        else:
            raise AssertionError(f"unhandled case {case_id}")

        db.rollback()
        _assert_no_posting_side_effects(db, before, _snapshot(db, row.id, ba.id))

    def test_deposit_clearing_missing_clearing_raises_unavailable_not_compound(self, db):
        co = _company(db, slug="bs02_miss_clearing")
        ba = _bank(db, co.id)
        sale = models.Sale(
            date=datetime.date.today(),
            invoice_number="BS02-no-clear",
            customer_name="Walk-in",
            amount=100.0,
            sale_type="Card",
            status="Paid",
            company_id=co.id,
        )
        db.add(sale)
        db.flush()
        _remove_account(db, co.id, "Card Sales Clearing")
        row, _imp = _stmt_row(db, co.id, ba.id, credit=True, amount=100.0)
        db.commit()
        before = _snapshot(db, row.id, ba.id)

        with pytest.raises(MatchPostError, match="is not available for settlement"):
            post_deposit_clearing_match(
                db,
                row_id=row.id,
                company_id=co.id,
                sale_ids=[sale.id],
                user_id=1,
            )

        db.rollback()
        _assert_no_posting_side_effects(db, before, _snapshot(db, row.id, ba.id))

    def test_missing_bank_on_withdrawal_raises_before_posting(self, db):
        co = _company(db, slug="bs02_miss_bank")
        ba = _bank(db, co.id)
        _remove_account(db, co.id, "Bank")
        row, _imp = _stmt_row(db, co.id, ba.id, credit=False, amount=50.0)
        db.commit()
        before = _snapshot(db, row.id, ba.id)

        with pytest.raises(MatchPostError, match="Bank Charges or Bank GL account missing"):
            post_bank_charge_outflow(
                db,
                row_id=row.id,
                company_id=co.id,
                user_id=1,
            )

        db.rollback()
        _assert_no_posting_side_effects(db, before, _snapshot(db, row.id, ba.id))
