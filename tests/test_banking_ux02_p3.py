"""BANKING-UX-02 P3 — Unsettled card sales list."""
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
import models
from reconciliation.clearing import fetch_unsettled_card_sales_for_visibility
from reconciliation.clearing_visibility import compute_clearing_visibility
from reconciliation.pos_settlement_preview import compute_pos_settlement_preview
from reconciliation.unsettled_card_sales_list import (
    DEFAULT_LIST_LIMIT,
    apply_list_limit,
    enrich_unsettled_sale_row,
    list_total_mismatch,
    sum_unsettled_card_sales,
)
from registry.coa_seed import ensure_accounts_for_company
from registry.i18n import t
from registry.locales.messages import MESSAGES
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR
from registry.service import set_setting

MATCH_POST = Path(__file__).resolve().parents[1] / "reconciliation" / "match_post.py"

_P3_KEYS = (
    "banking.unsettled_card_sales.section_title",
    "banking.unsettled_card_sales.empty",
    "banking.unsettled_card_sales.warn_total_mismatch",
    "banking.unsettled_card_sales.filter_from",
    "banking.unsettled_card_sales.filter_to",
    "banking.unsettled_card_sales.show_all",
    "banking.unsettled_card_sales.latest_limit",
    "banking.unsettled_card_sales.col.date",
    "banking.unsettled_card_sales.col.reference",
    "banking.unsettled_card_sales.col.amount",
    "banking.unsettled_card_sales.col.currency",
    "banking.unsettled_card_sales.col.payment_method",
    "banking.unsettled_card_sales.col.notes",
    "banking.unsettled_card_sales.col.status",
    "banking.unsettled_card_sales.status.unsettled",
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
        created_at=datetime.datetime.utcnow(),
    )
    db.add(co)
    db.commit()
    erp.st.session_state["active_company_id"] = co.id
    _seed_coa(db, co)
    ensure_accounts_for_company(db, co.id)
    set_setting(db, "banking.card_settlement_enabled", True, company_id=co.id)
    db.commit()
    return co


class TestListHelpers:
    def test_sum_matches_visibility_source(self, db):
        co = _company(db)
        sale = models.Sale(
            date=datetime.date.today(),
            invoice_number="INV-9",
            customer_name="Walk-in",
            amount=125.0,
            sale_type="Card",
            status="Paid",
            company_id=co.id,
        )
        db.add(sale)
        db.commit()
        erp.post_card_sale(db, sale.id, 125.0, sale.date, currency="TRY")
        rows = fetch_unsettled_card_sales_for_visibility(
            db,
            co.id,
            get_unsettled_card_sales=erp.get_unsettled_card_sales,
            get_account_by_name=erp.get_account_by_name,
        )
        acct = erp.get_account_by_name(db, "Card Sales Clearing")
        snap = compute_clearing_visibility(
            db,
            co.id,
            clearing_account_id=acct.id,
            current_clearing_balance=erp.calculate_account_balance(db, acct),
            get_unsettled_card_sales=erp.get_unsettled_card_sales,
            get_account_by_name=erp.get_account_by_name,
        )
        assert sum_unsettled_card_sales(rows) == snap.unsettled_card_sales_total
        assert list_total_mismatch(sum_unsettled_card_sales(rows), snap.unsettled_card_sales_total) is False

    def test_mismatch_warning_helper(self):
        assert list_total_mismatch(100.0, 50.0) is True
        assert list_total_mismatch(100.0, 100.0) is False
        assert list_total_mismatch(100.005, 100.0) is False

    def test_apply_list_limit_latest_fifty(self):
        rows = [{"sale_id": i, "amount": 1.0} for i in range(60)]
        limited, truncated = apply_list_limit(rows, show_all=False, limit=50)
        assert len(limited) == 50
        assert truncated is True
        assert limited[0]["sale_id"] == 10

    def test_enrich_row_includes_reference_and_notes(self, db):
        co = _company(db)
        sale = models.Sale(
            date=datetime.date.today(),
            invoice_number="INV-42",
            customer_name="Ali",
            description="POS lunch",
            amount=40.0,
            sale_type="Card",
            status="Paid",
            currency="TRY",
            company_id=co.id,
        )
        db.add(sale)
        db.commit()
        enriched = enrich_unsettled_sale_row(
            db,
            {
                "sale_id": sale.id,
                "date": sale.date,
                "amount": 40.0,
                "invoice": sale.invoice_number,
                "customer": sale.customer_name,
            },
            default_currency="TRY",
        )
        assert enriched["reference"] == "INV-42"
        assert enriched["notes"] == "POS lunch"
        assert enriched["currency"] == "TRY"
        assert enriched["settlement_status"] == "unsettled"


class TestUiWiring:
    def test_list_below_visibility_panel(self):
        src = inspect.getsource(erp._render_bsi_deposit_clearing)
        assert "_render_card_sales_clearing_visibility_block" in src
        assert "_render_unsettled_card_sales_list_block" in src
        assert src.index("_render_card_sales_clearing_visibility_block") < src.index(
            "_render_unsettled_card_sales_list_block"
        )

    def test_list_uses_same_fetch_helper_as_p2(self):
        from reconciliation.clearing import fetch_unsettled_card_sales_for_visibility
        from reconciliation.clearing_visibility import compute_clearing_visibility

        list_src = inspect.getsource(erp._render_unsettled_card_sales_list_block)
        vis_src = inspect.getsource(compute_clearing_visibility)
        fetch_src = inspect.getsource(fetch_unsettled_card_sales_for_visibility)
        assert "fetch_unsettled_card_sales_for_visibility" in list_src
        assert "fetch_unsettled_card_sales_for_visibility" in vis_src
        assert "UNSETTLED_DATE_MIN" in fetch_src

    def test_list_is_read_only(self):
        src = inspect.getsource(erp._render_unsettled_card_sales_list_block)
        assert "_render_readable_df" in src
        assert "post_deposit_clearing_match" not in src
        assert "st.button" not in src

    def test_empty_state_locale(self):
        src = inspect.getsource(erp._render_unsettled_card_sales_list_block)
        assert 'banking.unsettled_card_sales.empty' in src
        assert TRANSACTIONAL_EN["banking.unsettled_card_sales.empty"] == (
            "No unsettled card sales found."
        )

    def test_mismatch_warning_in_ui(self):
        src = inspect.getsource(erp._render_unsettled_card_sales_list_block)
        assert "list_total_mismatch" in src
        assert "banking.unsettled_card_sales.warn_total_mismatch" in src


class TestPostingUnchanged:
    def test_match_post_unchanged(self):
        src = MATCH_POST.read_text(encoding="utf-8")
        assert "def post_deposit_clearing_match" in src

    def test_p1_preview_unchanged(self):
        p = compute_pos_settlement_preview(1000.0, 400.0, 390.0)
        assert p.remaining_clearing == 600.0


class TestLocales:
    def test_p3_locale_keys_en_tr(self):
        for key in _P3_KEYS:
            assert key in TRANSACTIONAL_EN, f"missing EN: {key}"
            assert key in TRANSACTIONAL_TR, f"missing TR: {key}"
            assert TRANSACTIONAL_EN[key].strip()
            assert TRANSACTIONAL_TR[key].strip()

    def test_p3_keys_resolve_not_raw(self):
        for key in _P3_KEYS:
            text = t(
                key,
                "en",
                currency="TRY",
                list_total="0.00",
                visibility_total="0.00",
                limit=DEFAULT_LIST_LIMIT,
                total=0,
            )
            assert text != key
            assert not text.startswith("banking.unsettled_card_sales.")

    def test_empty_state_tr(self):
        assert TRANSACTIONAL_TR["banking.unsettled_card_sales.empty"] == (
            "Bekleyen kart satışı bulunamadı."
        )
        assert MESSAGES["tr"]["banking.unsettled_card_sales.empty"] == (
            TRANSACTIONAL_TR["banking.unsettled_card_sales.empty"]
        )
