"""Phase 18-MVP-1 — Card Sales Clearing foundation + banking toggles."""

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Streamlit must be a mock with a real dict session_state BEFORE importing app,
# so _current_company_id() reads a plain dict rather than a MagicMock attribute.
if "streamlit" not in sys.modules or isinstance(sys.modules["streamlit"], MagicMock) is False:
    sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit"].session_state = {}

from db import Base
from utc_datetime import utc_now_naive
import models
import app as erp_app
from registry.coa_seed import ensure_accounts_for_company
from registry.service import get_setting, set_setting
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    # Reset the mocked session_state to a fresh dict for each test.
    erp_app.st.session_state = {}
    with Session() as session:
        yield session


def _make_company(db, slug="acme"):
    co = models.Company(
        name="Acme Ltd",
        slug=slug,
        is_active=True,
        created_at=utc_now_naive(),
    )
    db.add(co)
    db.commit()
    return co


def _activate(co):
    erp_app.st.session_state["active_company_id"] = co.id


def _acct(db, co, name):
    return (
        db.query(models.ChartOfAccounts)
        .filter_by(company_id=co.id, account_name=name)
        .first()
    )


def _net_debit(db, account_id):
    lines = db.query(models.JournalEntryLine).filter_by(account_id=account_id).all()
    return round(sum((l.debit or 0) - (l.credit or 0) for l in lines), 2)


# ── Schema ───────────────────────────────────────────────────────────────────
class TestSchema:
    def test_bank_transaction_has_phase18_columns(self):
        cols = set(models.BankTransaction.__table__.columns.keys())
        assert {"is_reconciled", "statement_ref", "charge_subtype"} <= cols


# ── Settings defaults ──────────────────────────────────────────────────────────
class TestSettingsDefaults:
    def test_banking_toggles_default_off(self, db):
        co = _make_company(db)
        for key in (
            "banking.reconciliation_enabled",
            "banking.company_card_enabled",
            "banking.bank_charges_enabled",
            "banking.card_settlement_enabled",
        ):
            assert get_setting(db, key, company_id=co.id) is False
        assert (
            get_setting(db, "banking.card_sales_clearing_backfill", company_id=co.id)
            == "none"
        )


# ── Chart of Accounts ──────────────────────────────────────────────────────────
class TestAccounts:
    def test_ensure_accounts_creates_then_idempotent(self, db):
        co = _make_company(db)
        # Pre-Phase-18 company: only a couple of accounts, no 1150 / 5800.
        db.add(
            models.ChartOfAccounts(
                account_code="1010",
                account_name="Bank",
                account_type="Asset",
                company_id=co.id,
            )
        )
        db.commit()

        created = ensure_accounts_for_company(db, co.id)
        db.commit()
        assert created == 2
        assert _acct(db, co, "Card Sales Clearing") is not None
        assert _acct(db, co, "Bank Charges") is not None

        # Second run inserts nothing.
        assert ensure_accounts_for_company(db, co.id) == 0

    def test_ensure_phase18_accounts_startup_task(self, db):
        co = _make_company(db)
        erp_app.ensure_phase18_accounts(db)
        assert _acct(db, co, "Card Sales Clearing") is not None
        assert _acct(db, co, "Bank Charges") is not None
        # Flag guards re-run.
        assert (
            db.query(models.MigrationFlag)
            .filter_by(name="ensure_phase18_accounts_v1")
            .first()
            is not None
        )


# ── Posting paths ──────────────────────────────────────────────────────────────
class TestPosting:
    def _seed_coa(self, db, co):
        for code, name, atype in (
            ("1010", "Bank", "Asset"),
            ("1150", "Card Sales Clearing", "Asset"),
            ("4000", "Sales Revenue", "Income"),
        ):
            db.add(
                models.ChartOfAccounts(
                    account_code=code,
                    account_name=name,
                    account_type=atype,
                    company_id=co.id,
                )
            )
        db.commit()

    def test_card_sale_default_hits_bank(self, db):
        co = _make_company(db)
        _activate(co)
        self._seed_coa(db, co)

        erp_app.post_card_sale(db, sale_id=1, amount=100.0, sale_date=datetime.date.today())

        assert _net_debit(db, _acct(db, co, "Bank").id) == 100.0
        assert _net_debit(db, _acct(db, co, "Card Sales Clearing").id) == 0.0
        assert _net_debit(db, _acct(db, co, "Sales Revenue").id) == -100.0

    def test_card_sale_settlement_hits_clearing(self, db):
        co = _make_company(db)
        _activate(co)
        self._seed_coa(db, co)
        set_setting(db, "banking.card_settlement_enabled", True, company_id=co.id)
        db.commit()

        erp_app.post_card_sale(db, sale_id=1, amount=100.0, sale_date=datetime.date.today())

        assert _net_debit(db, _acct(db, co, "Card Sales Clearing").id) == 100.0
        assert _net_debit(db, _acct(db, co, "Bank").id) == 0.0
        assert _net_debit(db, _acct(db, co, "Sales Revenue").id) == -100.0


# ── Historical reclassification ──────────────────────────────────────────────────
class TestReclassify:
    def _seed_coa(self, db, co):
        for code, name, atype in (
            ("1010", "Bank", "Asset"),
            ("1150", "Card Sales Clearing", "Asset"),
            ("4000", "Sales Revenue", "Income"),
        ):
            db.add(
                models.ChartOfAccounts(
                    account_code=code,
                    account_name=name,
                    account_type=atype,
                    company_id=co.id,
                )
            )
        db.commit()

    def test_reclassify_moves_bank_to_clearing(self, db):
        co = _make_company(db)
        _activate(co)
        self._seed_coa(db, co)

        # Historical card sale posted straight to Bank (settlement was OFF).
        sale = models.Sale(
            date=datetime.date.today(),
            invoice_number="INV-1",
            customer_name="Walk-in",
            amount=100.0,
            sale_type="Card",
            status="Paid",
            is_void=False,
            company_id=co.id,
        )
        db.add(sale)
        db.commit()
        erp_app.post_card_sale(db, sale_id=sale.id, amount=100.0, sale_date=sale.date)

        # Paired named-bank deposit + cached balance.
        ba = models.BankAccount(name="Main", balance=100.0, company_id=co.id)
        db.add(ba)
        db.commit()
        db.add(
            models.BankTransaction(
                account_id=ba.id,
                date=sale.date,
                amount=100.0,
                type="deposit",
                description="Card Sale INV-1",
                is_void=False,
                company_id=co.id,
            )
        )
        db.commit()

        result = erp_app.reclassify_card_sales_to_clearing(db, co.id)
        assert result["migrated"] == 1
        assert result.get("already") is False

        # GL: Bank net back to 0, clearing holds the 100.
        assert _net_debit(db, _acct(db, co, "Bank").id) == 0.0
        assert _net_debit(db, _acct(db, co, "Card Sales Clearing").id) == 100.0

        # Adjusting entry is balanced.
        reclass = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="CardSaleReclass", reference_id=sale.id)
            .first()
        )
        assert reclass is not None
        tot_d = sum(l.debit or 0 for l in reclass.lines)
        tot_c = sum(l.credit or 0 for l in reclass.lines)
        assert round(tot_d - tot_c, 2) == 0.0

        # Named deposit voided + bank balance reduced.
        dep = db.query(models.BankTransaction).filter_by(description="Card Sale INV-1").first()
        assert dep.is_void is True
        db.refresh(ba)
        assert ba.balance == 0.0

    def test_reclassify_idempotent(self, db):
        co = _make_company(db)
        _activate(co)
        self._seed_coa(db, co)
        sale = models.Sale(
            date=datetime.date.today(),
            invoice_number="INV-2",
            customer_name="Walk-in",
            amount=50.0,
            sale_type="Card",
            status="Paid",
            is_void=False,
            company_id=co.id,
        )
        db.add(sale)
        db.commit()
        erp_app.post_card_sale(db, sale_id=sale.id, amount=50.0, sale_date=sale.date)

        first = erp_app.reclassify_card_sales_to_clearing(db, co.id)
        assert first["migrated"] == 1
        second = erp_app.reclassify_card_sales_to_clearing(db, co.id)
        assert second["migrated"] == 0
        assert second["already"] is True
        # Clearing not double-counted.
        assert _net_debit(db, _acct(db, co, "Card Sales Clearing").id) == 50.0


# ── i18n parity ──────────────────────────────────────────────────────────────────
class TestI18n:
    def test_banking_label_keys_en_tr_parity(self):
        banking_keys = {k for k in TRANSACTIONAL_EN if k.startswith("settings.banking.")}
        assert banking_keys, "expected settings.banking.* keys"
        for k in banking_keys:
            assert k in TRANSACTIONAL_TR, f"missing TR key: {k}"

    def test_full_transactional_keyset_parity(self):
        assert set(TRANSACTIONAL_EN) == set(TRANSACTIONAL_TR)
