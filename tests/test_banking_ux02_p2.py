"""BANKING-UX-02 P2 — Card Sales Clearing visibility."""
from __future__ import annotations

import datetime
import inspect
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit"].session_state = {}

import app as erp
from db import Base
from utc_datetime import utc_now_naive
import models
from reconciliation.clearing_visibility import compute_clearing_visibility
from reconciliation.pos_settlement_preview import compute_pos_settlement_preview
from registry.coa_seed import ensure_accounts_for_company
from registry.i18n import t
from registry.locales.messages import MESSAGES
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR
from registry.service import set_setting

MATCH_POST = Path(__file__).resolve().parents[1] / "reconciliation" / "match_post.py"

_P2_KEYS = (
    "banking.clearing_visibility.section_title",
    "banking.clearing_visibility.explainer",
    "banking.clearing_visibility.current_balance",
    "banking.clearing_visibility.unsettled_sales",
    "banking.clearing_visibility.settlements_posted",
    "banking.clearing_visibility.remaining_clearing",
    "banking.clearing_visibility.warn_reconciliation",
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    erp.st.session_state = {}
    with Session() as session:
        yield session


def _seed_coa(db, co):
    for code, name, atype in (
        ("1010", "Bank", "Asset"),
        ("1150", "Card Sales Clearing", "Asset"),
        ("4000", "Sales Revenue", "Income"),
        ("5800", "Bank Charges", "Expense"),
    ):
        db.add(
            models.ChartOfAccounts(
                account_code=code,
                account_name=name,
                account_type=atype,
                currency="TRY" if name == "Bank" else None,
                company_id=co.id,
            )
        )
    db.commit()


def _company(db):
    co = models.Company(
        name="Acme",
        slug="acme",
        is_active=True,
        created_at=utc_now_naive(),
    )
    db.add(co)
    db.commit()
    erp.st.session_state["active_company_id"] = co.id
    _seed_coa(db, co)
    ensure_accounts_for_company(db, co.id)
    set_setting(db, "banking.card_settlement_enabled", True, company_id=co.id)
    db.commit()
    return co


def _clearing_acct(db):
    return erp.get_account_by_name(db, "Card Sales Clearing")


class TestComputeClearingVisibility:
    def test_zero_balance_clean(self, db):
        co = _company(db)
        acct = _clearing_acct(db)
        snap = compute_clearing_visibility(
            db,
            co.id,
            clearing_account_id=acct.id,
            current_clearing_balance=0.0,
            get_unsettled_card_sales=erp.get_unsettled_card_sales,
            get_account_by_name=erp.get_account_by_name,
        )
        assert snap.current_clearing_balance == 0.0
        assert snap.unsettled_card_sales_total == 0.0
        assert snap.settlements_posted_total == 0.0
        assert snap.remaining_clearing == 0.0
        assert snap.reconciliation_mismatch is False

    def test_current_clearing_balance_from_card_sale(self, db):
        co = _company(db)
        acct = _clearing_acct(db)
        sale = models.Sale(
            date=datetime.date.today(),
            invoice_number="INV-1",
            customer_name="Walk-in",
            amount=150.0,
            sale_type="Card",
            status="Paid",
            company_id=co.id,
        )
        db.add(sale)
        db.commit()
        erp.post_card_sale(db, sale.id, 150.0, sale.date, currency="TRY")
        balance = erp.calculate_account_balance(db, acct)
        snap = compute_clearing_visibility(
            db,
            co.id,
            clearing_account_id=acct.id,
            current_clearing_balance=balance,
            get_unsettled_card_sales=erp.get_unsettled_card_sales,
            get_account_by_name=erp.get_account_by_name,
        )
        assert snap.current_clearing_balance == 150.0
        assert snap.unsettled_card_sales_total == 150.0
        assert snap.settlements_posted_total == 0.0
        assert snap.remaining_clearing == 150.0
        assert snap.reconciliation_mismatch is False

    def test_remaining_clearing_after_settlement(self, db):
        co = _company(db)
        acct = _clearing_acct(db)
        ba = models.BankAccount(
            name="Main TRY",
            currency="TRY",
            company_id=co.id,
            is_active=True,
            balance=0.0,
        )
        db.add(ba)
        db.commit()
        sale = models.Sale(
            date=datetime.date.today(),
            invoice_number="INV-2",
            customer_name="Walk-in",
            amount=200.0,
            sale_type="Card",
            status="Paid",
            company_id=co.id,
        )
        db.add(sale)
        db.commit()
        erp.post_card_sale(db, sale.id, 200.0, sale.date, currency="TRY")
        imp = models.BankStatementImport(
            company_id=co.id,
            bank_account_id=ba.id,
            file_name="t.csv",
            file_hash="abc",
            file_size=10,
            file_path="/tmp/t.csv",
            status="staging",
            import_date=datetime.date.today(),
            row_count=1,
            valid_count=1,
            flagged_count=0,
            error_count=0,
            currency="TRY",
            created_at=utc_now_naive(),
        )
        db.add(imp)
        db.flush()
        row = models.BankStatementRow(
            bank_statement_import_id=imp.id,
            status="staging",
            import_row_index=1,
            date=datetime.date.today(),
            description="POS deposit",
            credit_amount=200.0,
            debit_amount=None,
            amount=200.0,
            currency="TRY",
            original_amount=200.0,
            parsed_successfully=True,
            created_at=utc_now_naive(),
        )
        db.add(row)
        db.commit()
        from reconciliation.match_post import post_deposit_clearing_match

        post_deposit_clearing_match(
            db,
            row_id=row.id,
            company_id=co.id,
            sale_ids=[sale.id],
            user_id=1,
        )
        balance = erp.calculate_account_balance(db, acct)
        snap = compute_clearing_visibility(
            db,
            co.id,
            clearing_account_id=acct.id,
            current_clearing_balance=balance,
            get_unsettled_card_sales=erp.get_unsettled_card_sales,
            get_account_by_name=erp.get_account_by_name,
        )
        assert balance == 0.0
        assert snap.remaining_clearing == 0.0
        assert snap.settlements_posted_total == 200.0
        assert snap.unsettled_card_sales_total == 0.0
        assert snap.reconciliation_mismatch is False

    def test_reconciliation_warning_on_mismatch(self, db):
        co = _company(db)
        acct = _clearing_acct(db)
        snap = compute_clearing_visibility(
            db,
            co.id,
            clearing_account_id=acct.id,
            current_clearing_balance=50.0,
            get_unsettled_card_sales=erp.get_unsettled_card_sales,
            get_account_by_name=erp.get_account_by_name,
        )
        assert snap.reconciliation_mismatch is True


class TestUiWiring:
    def test_visibility_below_settlement_preview(self):
        src = inspect.getsource(erp._render_bsi_deposit_clearing)
        assert "_render_pos_settlement_preview_block" in src
        assert "_render_card_sales_clearing_visibility_block" in src
        assert src.index("_render_pos_settlement_preview_block") < src.index(
            "_render_card_sales_clearing_visibility_block"
        )
        assert src.index("_render_card_sales_clearing_visibility_block") < src.index(
            "post_deposit_clearing_match"
        )

    def test_visibility_is_read_only(self):
        src = inspect.getsource(erp._render_card_sales_clearing_visibility_block)
        assert "st.button" not in src
        assert "post_deposit_clearing_match" not in src
        assert "create_journal_entry" not in src
        assert "compute_clearing_visibility" in src

    def test_settlement_preview_unchanged(self):
        p = compute_pos_settlement_preview(5000.0, 1000.0, 970.0)
        assert p.expected_bank_deposit == 970.0
        assert p.remaining_clearing == 4000.0


class TestPostingUnchanged:
    def test_match_post_settlement_lines_unchanged(self):
        src = MATCH_POST.read_text(encoding="utf-8")
        assert "je_lines = [(bank_gl.id, deposit_amt, 0)]" in src
        assert "je_lines.append((clearing_gl.id, 0, clearing_total))" in src


class TestLocales:
    def test_p2_locale_keys_en_tr(self):
        for key in _P2_KEYS:
            assert key in TRANSACTIONAL_EN, f"missing EN: {key}"
            assert key in TRANSACTIONAL_TR, f"missing TR: {key}"
            assert TRANSACTIONAL_EN[key].strip()
            assert TRANSACTIONAL_TR[key].strip()

    def test_p2_keys_resolve_not_raw(self):
        for key in _P2_KEYS:
            for loc in ("en", "tr"):
                text = t(key, loc, currency="TRY", remaining="0.00", current="0.00")
                assert text != key
                assert not text.startswith("banking.clearing_visibility.")

    def test_section_title_copy(self):
        assert TRANSACTIONAL_EN["banking.clearing_visibility.section_title"] == (
            "Card Sales Clearing (1150)"
        )
        assert TRANSACTIONAL_TR["banking.clearing_visibility.section_title"] == (
            "Kart Satış Takası (1150)"
        )
        assert MESSAGES["en"]["banking.clearing_visibility.section_title"] == (
            TRANSACTIONAL_EN["banking.clearing_visibility.section_title"]
        )
