"""PRODUCTION-HARDENING-01-PH03 — PG matrix execution + launch checklist tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "PRODUCTION_HARDENING_01_PH03_PG_MATRIX_EXECUTION_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "pg_matrix_execution_contract.py"
    spec = importlib.util.spec_from_file_location(
        "pg_matrix_execution_contract_ph03", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pg_matrix_execution_contract_ph03"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "PostgreSQL optional matrix inventory",
    "Launch-readiness checklist",
    "Operator execution guide",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"PH-03 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def roadmap_text() -> str:
    return (ROOT / "ROADMAP.md").read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("item", contract.PH03_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text


@pytest.mark.parametrize("flow", contract.PG_BOUNDARY_MATRIX_FLOWS)
def test_audit_documents_pg_boundary_flows(audit_text, flow):
    assert flow.flow_id in audit_text
    assert flow.family in audit_text
    assert flow.write_path in audit_text


@pytest.mark.parametrize("rel_path", contract.OPTIONAL_POSTGRES_TEST_FILES)
def test_optional_postgres_test_files_exist(rel_path):
    assert (ROOT / rel_path).is_file(), rel_path


@pytest.mark.parametrize("rel_path", contract.OPTIONAL_POSTGRES_TEST_FILES)
def test_optional_postgres_marker_present(rel_path):
    src = (ROOT / rel_path).read_text(encoding="utf-8")
    assert contract.OPTIONAL_POSTGRES_MARKER in src, rel_path


@pytest.mark.parametrize("label,_status", contract.STREAMLIT_LAUNCH_CHECKLIST)
def test_audit_documents_streamlit_launch_checklist(audit_text, label, _status):
    assert label in audit_text


@pytest.mark.parametrize("label,_status", contract.API_WRITE_LAUNCH_CHECKLIST)
def test_audit_documents_api_write_launch_checklist(audit_text, label, _status):
    assert label in audit_text


def test_audit_documents_postgres_env_and_operator_docs(audit_text):
    assert contract.POSTGRES_OPTIONAL_ENV in audit_text
    assert contract.POSTGRES_OPTIONAL_DOC.split("/")[-1] in audit_text
    assert contract.POSTGRES_OPERATOR_DOC.split("/")[-1] in audit_text


def test_roadmap_lists_ph03_complete(roadmap_text):
    assert contract.PH03_SLICE_ID in roadmap_text
    assert contract.PH03_TAG in roadmap_text


@pytest.mark.optional_postgres
class TestPostgresOptionalBoundaryMatrix:
    def test_boundary_bank_deposit_sqlite_postgres_parity(self):
        from postgres_utils import get_test_postgres_url

        if get_test_postgres_url() is None:
            pytest.skip("ERP_TEST_POSTGRES_URL not set")

        import datetime

        from services import commit_modes
        from services import write_banking as write_banking_svc
        from services.commit_modes import POST_BANK_TRANSACTION_FAMILY, CommitMode
        from tests.helpers.commit_parity import BANKING_TABLES
        from tests.p3_dual_run_utils import AMOUNT, POST_DATE, ParitySeed, dual_engine_parity

        def flow(session, seed: ParitySeed) -> None:
            commit_modes.reset_commit_modes_for_tests()
            commit_modes.set_commit_mode_for_tests(
                POST_BANK_TRANSACTION_FAMILY, CommitMode.BOUNDARY
            )
            write_banking_svc.create_manual_bank_transaction(
                session,
                company_id=seed.company_id,
                performed_by="pg-matrix",
                entry_date=POST_DATE,
                amount=AMOUNT,
                transaction_type="deposit",
                bank_account_id=seed.bank_account_id,
                currency="TRY",
                notes="ph03 boundary bank deposit",
            )

        sqlite_summary, postgres_summary = dual_engine_parity(
            flow, tables=BANKING_TABLES
        )
        assert postgres_summary is not None
        assert sqlite_summary["journal"]["balanced"] is True
        assert sqlite_summary["counts"]["bank_transactions"] == 1
        assert sqlite_summary == postgres_summary

    def test_boundary_equity_contribution_sqlite_postgres_parity(self):
        from postgres_utils import get_test_postgres_url

        if get_test_postgres_url() is None:
            pytest.skip("ERP_TEST_POSTGRES_URL not set")

        import datetime

        import app
        import models
        from reconciliation.company_card import apply_account_balance_delta
        from services import commit_modes
        from services.commit_modes import POST_EQUITY_MOVEMENT_FAMILY, CommitMode
        from services.unit_of_work import boundary_commit_scope
        from tests.helpers.commit_parity import BANKING_TABLES
        from tests.p3_dual_run_utils import AMOUNT, POST_DATE, ParitySeed, dual_engine_parity

        app.DEVELOPMENT_MODE = True
        app.DEV_MODE = True

        def flow(session, seed: ParitySeed) -> None:
            commit_modes.reset_commit_modes_for_tests()
            commit_modes.set_commit_mode_for_tests(
                POST_EQUITY_MOVEMENT_FAMILY, CommitMode.BOUNDARY
            )
            bank = session.get(models.BankAccount, seed.bank_account_id)
            with boundary_commit_scope(session, POST_EQUITY_MOVEMENT_FAMILY):
                btxn = models.BankTransaction(
                    account_id=bank.id,
                    date=POST_DATE,
                    amount=AMOUNT,
                    type="deposit",
                    description="Capital Contribution #TBD",
                    company_id=seed.company_id,
                )
                session.add(btxn)
                session.flush()
                btxn.description = f"Capital Contribution #{btxn.id}"
                apply_account_balance_delta(bank, "deposit", AMOUNT)
                app.post_capital_contribution(
                    session,
                    btxn.id,
                    AMOUNT,
                    POST_DATE,
                    "Bank",
                    currency="TRY",
                    company_id=seed.company_id,
                )
                app.log_audit(
                    session,
                    "Create",
                    "EquityMovement",
                    btxn.id,
                    f"Capital Contribution #{btxn.id} · {AMOUNT:,.2f} TRY → {bank.name}",
                    company_id=seed.company_id,
                )

        sqlite_summary, postgres_summary = dual_engine_parity(
            flow, tables=BANKING_TABLES
        )
        assert postgres_summary is not None
        assert sqlite_summary["journal"]["balanced"] is True
        assert sqlite_summary["counts"]["bank_transactions"] == 1
        assert sqlite_summary == postgres_summary
