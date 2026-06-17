"""FASTAPI-REACT-07 — PG boundary matrix contract + optional PostgreSQL parity."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from services import commit_modes
from services.commit_modes import CommitMode

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_07_PG_BOUNDARY_MATRIX_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "pg_boundary_contract.py"
    spec = importlib.util.spec_from_file_location("pg_boundary_contract", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pg_boundary_contract"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_commit_contract():
    path = ROOT / "registry" / "commit_boundary_contract.py"
    spec = importlib.util.spec_from_file_location("commit_boundary_contract_fr07", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["commit_boundary_contract_fr07"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()
commit_contract = _load_commit_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Commit ownership modes",
    "API boundary matrix",
    "PostgreSQL optional matrix",
    "Remaining risks",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-07 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("item", contract.REMAINING_RISKS)
def test_audit_documents_remaining_risks(audit_text, item):
    assert item.lower() in audit_text.lower(), item


@pytest.mark.parametrize("item", contract.DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text


def test_default_commit_mode_is_internal():
    for family in commit_contract.ALL_BOUNDARY_FAMILIES:
        assert commit_modes.get_commit_mode(family) is CommitMode.INTERNAL


@pytest.mark.parametrize("module_path", contract.API_WRITE_MODULES)
def test_api_write_modules_wire_boundary_mode(module_path):
    src = (ROOT / module_path).read_text(encoding="utf-8")
    assert "is_boundary_mode" in src, module_path
    assert "boundary_commit_scope" in src, module_path


def test_posting_boundary_module_exports_scopes():
    src = (ROOT / contract.POSTING_BOUNDARY_MODULE).read_text(encoding="utf-8")
    for scope in contract.POSTING_BOUNDARY_SCOPES:
        assert scope in src, scope



@pytest.mark.parametrize(
    "spec",
    commit_contract.COMMIT_FAMILY_CHARACTERIZATION,
    ids=[s.family for s in commit_contract.COMMIT_FAMILY_CHARACTERIZATION],
)
def test_p0_characterization_test_file_exists(spec):
    assert (ROOT / spec.characterization_test).is_file(), spec.characterization_test


@pytest.mark.parametrize("test_file", contract.P2_BOUNDARY_COMMIT_TEST_FILES)
def test_p2_boundary_commit_test_files_exist(test_file):
    assert (ROOT / test_file).is_file(), test_file


@pytest.mark.parametrize("marker", contract.P2_BOUNDARY_TEST_CLASS_MARKERS)
def test_p2_boundary_commit_classes_documented(marker):
    found = False
    for test_file in contract.P2_BOUNDARY_COMMIT_TEST_FILES:
        if marker in (ROOT / test_file).read_text(encoding="utf-8"):
            found = True
            break
    assert found, marker


def test_api_matrix_helper_exists():
    assert (ROOT / contract.API_MATRIX_HELPER).is_file()
    assert (ROOT / contract.API_MATRIX_TEST).is_file()


def test_postgres_optional_env_documented(audit_text):
    assert contract.POSTGRES_OPTIONAL_ENV in audit_text
    assert (ROOT / contract.POSTGRES_OPTIONAL_DOC).is_file()


def test_roadmap_lists_fastapi_react_07_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-07" in roadmap
    assert "fastapi-react-07-pg-boundary-matrix" in roadmap


@pytest.mark.optional_postgres
class TestPostgresOptionalBoundaryMatrix:
    def test_boundary_cash_sale_sqlite_postgres_parity(self):
        from postgres_utils import get_test_postgres_url

        if get_test_postgres_url() is None:
            pytest.skip("ERP_TEST_POSTGRES_URL not set")

        import datetime

        import models
        from services import commit_modes
        from services import write_sales as write_sales_svc
        from services.commit_modes import POST_CASH_SALE_FAMILY, CommitMode
        from tests.helpers.commit_parity import DEFAULT_TABLES
        from tests.p3_dual_run_utils import (
            AMOUNT,
            POST_DATE,
            ParitySeed,
            dual_engine_parity,
        )

        def flow(session, seed: ParitySeed) -> None:
            commit_modes.reset_commit_modes_for_tests()
            commit_modes.set_commit_mode_for_tests(
                POST_CASH_SALE_FAMILY, CommitMode.BOUNDARY
            )
            write_sales_svc.create_and_post_sale(
                session,
                company_id=seed.company_id,
                user_id=1,
                performed_by="pg-matrix",
                entry_date=POST_DATE,
                amount=AMOUNT,
                currency="TRY",
                payment_method="Cash",
                notes="pg boundary cash sale",
            )

        sqlite_summary, postgres_summary = dual_engine_parity(
            flow, tables=DEFAULT_TABLES
        )
        assert postgres_summary is not None
        assert sqlite_summary["journal"]["balanced"] is True
        assert sqlite_summary == postgres_summary

    def test_boundary_void_sale_sqlite_postgres_parity(self):
        from postgres_utils import get_test_postgres_url

        if get_test_postgres_url() is None:
            pytest.skip("ERP_TEST_POSTGRES_URL not set")

        from services import commit_modes
        from services import write_sales as write_sales_svc
        from services import write_voids as write_voids_svc
        from services.commit_modes import POST_CASH_SALE_FAMILY, VOID_CASCADE_FAMILY, CommitMode
        from tests.helpers.commit_parity import VOID_CASCADE_TABLES
        from tests.p3_dual_run_utils import AMOUNT, POST_DATE, ParitySeed, dual_engine_parity

        def flow(session, seed: ParitySeed) -> None:
            commit_modes.reset_commit_modes_for_tests()
            result = write_sales_svc.create_and_post_sale(
                session,
                company_id=seed.company_id,
                user_id=1,
                performed_by="pg-matrix",
                entry_date=POST_DATE,
                amount=AMOUNT,
                currency="TRY",
                payment_method="Cash",
            )
            commit_modes.set_commit_mode_for_tests(
                VOID_CASCADE_FAMILY, CommitMode.BOUNDARY
            )
            write_voids_svc.void_record(
                session,
                company_id=seed.company_id,
                performed_by="pg-matrix",
                target_type="Sale",
                target_id=result.sale_id,
                reason="pg matrix void",
            )

        sqlite_summary, postgres_summary = dual_engine_parity(
            flow, tables=VOID_CASCADE_TABLES
        )
        assert postgres_summary is not None
        assert sqlite_summary["void_counts"]["sales"] == 1
        assert sqlite_summary == postgres_summary
