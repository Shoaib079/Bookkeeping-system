"""BANKING-UX-03 P2.1 — read-only Reconciliation Cockpit MVP."""
from __future__ import annotations

import datetime
import inspect
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app as erp_app
import ui.banking as banking_ui
from reconciliation.company_card import compute_cc_payable_recon_health
from reconciliation.match_post import get_postable_rows
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR
from registry.service import set_setting
from ui.banking import (
    banking_cockpit_drill_to,
    banking_recon_cockpit_summary,
    render_banking_recon_cockpit,
)

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True

_P21_KEYS = (
    "bank.section.cockpit",
    "banking.cockpit.title",
    "banking.cockpit.desc",
    "banking.cockpit.gate_disabled",
    "banking.cockpit.tile.import_health",
    "banking.cockpit.tile.postable_queue",
    "banking.cockpit.tile.recent_imports",
    "banking.cockpit.tile.bank_balance",
    "banking.cockpit.tile.settlement",
    "banking.cockpit.open_queue",
    "banking.cockpit.open_review",
    "banking.cockpit.open_history",
)


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(erp_app._DEV_USER)
    sys.modules["streamlit"].session_state["auth_expires"] = (
        datetime.datetime.now() + datetime.timedelta(hours=24)
    )


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    _seed_dev_auth_user()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        erp_app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        yield s


def _company(db, *, slug: str, name: str | None = None):
    co = models.Company(
        name=name or slug.title(),
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()
    return co


def _activate(db, co):
    sys.modules["streamlit"].session_state["active_company_id"] = co.id
    set_setting(db, "banking.reconciliation_enabled", True, company_id=co.id)
    set_setting(db, "banking.card_settlement_enabled", True, company_id=co.id)
    set_setting(db, "banking.company_card_enabled", True, company_id=co.id)


def _seed_coa(db, co):
    for code, name, atype in (
        ("1010", "Bank", "Asset"),
        ("1150", "Card Sales Clearing", "Asset"),
        ("2110", "Credit Card Payable", "Liability"),
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


def _bank(db, co, *, name="Main TRY", balance=5000.0):
    ba = models.BankAccount(
        name=name,
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=balance,
        kind="bank",
    )
    db.add(ba)
    db.commit()
    return ba


def _import_with_rows(
    db,
    co,
    ba,
    *,
    valid=2,
    errors=1,
    flagged=1,
    file_hash="p21",
):
    imp = models.BankStatementImport(
        company_id=co.id,
        bank_account_id=ba.id,
        file_name="stmt.csv",
        file_hash=file_hash,
        file_size=10,
        file_path="/tmp/stmt.csv",
        status="staging",
        import_date=datetime.date(2025, 6, 1),
        row_count=valid + errors + flagged,
        valid_count=valid,
        flagged_count=flagged,
        error_count=errors,
        currency="TRY",
        created_at=datetime.datetime.now(),
    )
    db.add(imp)
    db.flush()
    idx = 1
    for _ in range(valid):
        db.add(
            models.BankStatementRow(
                bank_statement_import_id=imp.id,
                import_row_index=idx,
                date=datetime.date(2025, 6, 1),
                description="Deposit",
                credit_amount=100.0,
                debit_amount=None,
                amount=100.0,
                currency="TRY",
                original_amount=100.0,
                parsed_successfully=True,
                status="staging",
                created_at=datetime.datetime.now(),
            )
        )
        idx += 1
    for _ in range(flagged):
        db.add(
            models.BankStatementRow(
                bank_statement_import_id=imp.id,
                import_row_index=idx,
                date=datetime.date(2025, 6, 2),
                description="Dup",
                credit_amount=50.0,
                debit_amount=None,
                amount=50.0,
                currency="TRY",
                original_amount=50.0,
                parsed_successfully=True,
                status="duplicate_flagged",
                created_at=datetime.datetime.now(),
            )
        )
        idx += 1
    db.commit()
    return imp


class TestAggregateCorrectness:
    def test_postable_count_matches_get_postable_rows(self, session):
        co = _company(session, slug="acme")
        _activate(session, co)
        ba = _bank(session, co)
        _import_with_rows(session, co, ba)
        summary = banking_recon_cockpit_summary(session, co.id)
        assert summary["postable_count"] == len(get_postable_rows(session, co.id))

    def test_import_health_reflects_recent_import_counts(self, session):
        co = _company(session, slug="acme2")
        _activate(session, co)
        ba = _bank(session, co)
        _import_with_rows(session, co, ba, valid=3, errors=2, flagged=1)
        summary = banking_recon_cockpit_summary(session, co.id)
        assert summary["import_totals"]["valid"] == 3
        assert summary["import_totals"]["error"] == 2
        assert summary["import_totals"]["flagged"] == 1
        assert len(summary["recent_imports"]) == 1

    def test_bank_balance_uses_stored_active_bank_accounts(self, session):
        co = _company(session, slug="bankco")
        _activate(session, co)
        _bank(session, co, name="Main", balance=1200.0)
        _bank(session, co, name="USD", balance=300.0)
        summary = banking_recon_cockpit_summary(session, co.id)
        assert summary["bank_total_stored"] == 1500.0
        assert len(summary["bank_accounts"]) == 2


class TestDefinitionParity:
    def test_cc_difference_matches_compute_cc_payable_recon_health(self, session):
        co = _company(session, slug="ccco")
        _activate(session, co)
        _seed_coa(session, co)
        health = compute_cc_payable_recon_health(session, co.id)
        summary = banking_recon_cockpit_summary(session, co.id)
        assert summary["settlement"] is not None
        assert (
            summary["settlement"]["cc_health"]["difference"]
            == health["difference"]
        )


class TestTileGating:
    def test_settlement_tile_hidden_when_card_settings_off(self, session):
        co = _company(session, slug="nogate")
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        set_setting(session, "banking.reconciliation_enabled", True, company_id=co.id)
        set_setting(session, "banking.card_settlement_enabled", False, company_id=co.id)
        set_setting(session, "banking.company_card_enabled", False, company_id=co.id)
        summary = banking_recon_cockpit_summary(session, co.id)
        assert summary["show_settlement_tile"] is False
        assert summary["settlement"] is None

    def test_cockpit_section_gated_on_reconciliation_enabled(self):
        src = inspect.getsource(erp_app.render_banking)
        assert "cockpit" in src
        assert "_banking_reconciliation_on" in src


class TestCompanyIsolation:
    def test_metrics_scoped_to_active_company(self, session):
        co_a = _company(session, slug="coa")
        co_b = _company(session, slug="cob")
        _activate(session, co_a)
        ba_a = _bank(session, co_a, balance=1000.0)
        _import_with_rows(session, co_a, ba_a, file_hash="a")
        _activate(session, co_b)
        ba_b = _bank(session, co_b, balance=9999.0)
        _import_with_rows(session, co_b, ba_b, valid=5, file_hash="b")

        _activate(session, co_a)
        summary_a = banking_recon_cockpit_summary(session, co_a.id)
        assert summary_a["company_id"] == co_a.id
        assert summary_a["bank_total_stored"] == 1000.0
        assert summary_a["import_totals"]["valid"] == 2

        _activate(session, co_b)
        summary_b = banking_recon_cockpit_summary(session, co_b.id)
        assert summary_b["company_id"] == co_b.id
        assert summary_b["bank_total_stored"] == 9999.0
        assert summary_b["import_totals"]["valid"] == 5


class TestReadOnly:
    def test_summary_creates_zero_journal_entries(self, session):
        co = _company(session, slug="readonly")
        _activate(session, co)
        ba = _bank(session, co)
        _import_with_rows(session, co, ba)
        before = session.query(models.JournalEntry).count()
        banking_recon_cockpit_summary(session, co.id)
        assert session.query(models.JournalEntry).count() == before

    def test_cockpit_ui_has_no_posting_calls(self):
        src = inspect.getsource(render_banking_recon_cockpit)
        assert "post_deposit_clearing_match" not in src
        assert "create_journal_entry" not in src
        assert "log_audit" not in src


class TestDrillThrough:
    def test_drill_to_match_sets_import_and_match_sections(self):
        banking_cockpit_drill_to("match")
        assert sys.modules["streamlit"].session_state["banking_section"] == "import"
        assert sys.modules["streamlit"].session_state["bsi_section"] == "match"

    def test_drill_to_review_and_history(self):
        banking_cockpit_drill_to("review")
        assert sys.modules["streamlit"].session_state["bsi_section"] == "review"
        banking_cockpit_drill_to("history")
        assert sys.modules["streamlit"].session_state["bsi_section"] == "history"

    def test_render_includes_drill_buttons(self):
        src = inspect.getsource(render_banking_recon_cockpit)
        assert "banking_cockpit_drill_to" in src
        assert "banking.cockpit.open_queue" in src
        assert "banking.cockpit.open_review" in src
        assert "banking.cockpit.open_history" in src


class TestBankingWiring:
    def test_render_banking_exposes_cockpit_section(self):
        render_src = inspect.getsource(erp_app.render_banking)
        opts_src = inspect.getsource(banking_ui.banking_build_section_options)
        assert "render_banking_recon_cockpit" in render_src or (
            "_render_banking_recon_cockpit" in render_src
        )
        assert '("cockpit", "bank.section.cockpit")' in opts_src


class TestLocales:
    @pytest.mark.parametrize("key", _P21_KEYS)
    def test_en_and_tr_keys_exist(self, key):
        assert key in TRANSACTIONAL_EN
        assert key in TRANSACTIONAL_TR
        assert TRANSACTIONAL_EN[key].strip()
        assert TRANSACTIONAL_TR[key].strip()
