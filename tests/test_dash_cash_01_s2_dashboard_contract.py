"""DASH-CASH-01-S2 — GL liquid funds dashboard contract tests."""

from __future__ import annotations

import datetime
import inspect
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app as erp
from db import Base
import models
from services import read_balances as rb

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock


def _dashboard_src() -> str:
    return inspect.getsource(erp.render_dashboard)


class TestDashboardLiquidStructural:
    def test_uses_compute_liquid_position(self):
        src = _dashboard_src()
        assert "_compute_liquid_position" in src
        assert "current_company_required()" in src
        assert "as_of=today" in src

    def test_no_subledger_cash_positions(self):
        src = _dashboard_src()
        assert "_cash_positions" not in src
        assert "Cash & Bank" not in src
        assert "txn.no_bank_accounts" not in src

    def test_no_bank_account_balance_on_liquid_path(self):
        src = _dashboard_src()
        assert "_ba.balance" not in src
        assert "_all_bank_accts" not in src

    def test_three_gl_kpi_labels(self):
        src = _dashboard_src()
        assert 'dash.kpi.cash_in_hand' in src
        assert 'dash.kpi.bank_balance' in src
        assert 'dash.kpi.total_liquid' in src
        assert src.count("render_kpi_grid") >= 1

    def test_renders_without_empty_guard(self):
        src = _dashboard_src()
        assert "_dash_liquid_primary_amount" in src
        assert "if _cash_positions" not in src

    def test_mobile_cash_bank_navigation(self):
        src = _dashboard_src()
        assert "mob_dash_cash" in src
        assert "mob_dash_bank" in src
        assert "NAV_CASH_RECONCILIATION" in src
        assert "NAV_BANKING" in src


class TestDashLiquidHelpers:
    def test_primary_zero_when_missing_currency(self):
        assert erp._dash_liquid_primary_amount({}, "TRY") == 0.0
        assert erp._dash_liquid_primary_amount({"USD": 50.0}, "TRY") == 0.0

    def test_secondary_chips_exclude_primary(self):
        chips = erp._dash_liquid_secondary_chips(
            {"TRY": 100.0, "USD": 50.0, "EUR": 25.0},
            "TRY",
        )
        assert "TRY" not in chips
        assert "USD $50.00" in chips
        assert "EUR €25.00" in chips

    def test_total_equals_cash_plus_bank_in_service(self):
        engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as db:
            co = models.Company(
                name="Co",
                slug="co",
                is_active=True,
                created_at=datetime.datetime.now(),
            )
            db.add(co)
            db.flush()
            cash = models.ChartOfAccounts(
                account_code="1000",
                account_name="Cash",
                account_type="Asset",
                currency="TRY",
                company_id=co.id,
                is_active=True,
            )
            bank = models.ChartOfAccounts(
                account_code="1010",
                account_name="Bank",
                account_type="Asset",
                currency="TRY",
                company_id=co.id,
                is_active=True,
            )
            db.add_all([cash, bank])
            db.flush()
            je = models.JournalEntry(
                entry_date=datetime.date(2026, 1, 10),
                description="seed",
                reference_type="Sale",
                reference_id=1,
                company_id=co.id,
            )
            db.add(je)
            db.flush()
            db.add(
                models.JournalEntryLine(
                    journal_entry_id=je.id,
                    account_id=cash.id,
                    debit=300.0,
                    credit=0.0,
                    company_id=co.id,
                )
            )
            db.add(
                models.JournalEntryLine(
                    journal_entry_id=je.id,
                    account_id=bank.id,
                    debit=500.0,
                    credit=0.0,
                    company_id=co.id,
                )
            )
            db.commit()
            pos = rb.compute_liquid_position(
                db,
                company_id=co.id,
                as_of=datetime.date(2026, 1, 31),
            )
            assert pos.cash_by_currency["TRY"] == pytest.approx(300.0)
            assert pos.bank_by_currency["TRY"] == pytest.approx(500.0)
            assert pos.total_by_currency["TRY"] == pytest.approx(800.0)

    def test_company_scoped_via_explicit_company_id(self):
        src = _dashboard_src()
        assert "company_id=current_company_required()" in src
