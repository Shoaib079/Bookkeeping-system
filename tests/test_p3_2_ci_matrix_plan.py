"""P3.2-E — contract tests for the CI matrix plan document.

Doc-only guard: verifies the plan exists and carries required sections.
Does not require PostgreSQL or a GitHub Actions workflow file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "P3_2_CI_MATRIX_PLAN.md"
WORKFLOWS_DIR = PROJECT_ROOT / ".github" / "workflows"

REQUIRED_SECTIONS = (
    "Purpose",
    "Current local test behavior",
    "SQLite default CI job",
    "Optional PostgreSQL CI job",
    "Required env vars",
    "Safety rules",
    "ERP_TEST_POSTGRES_URL",
    "optional_postgres",
    "Future GitHub Actions outline",
    "Why PostgreSQL remains optional",
    "Exit criteria",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"CI matrix plan missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_ci_matrix_plan_doc_exists():
    assert DOC_PATH.exists(), f"CI matrix plan missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_doc_references_erp_test_postgres_url(doc_text):
    assert "ERP_TEST_POSTGRES_URL" in doc_text


def test_doc_references_optional_postgres_marker(doc_text):
    assert "optional_postgres" in doc_text


def test_doc_states_postgresql_remains_optional(doc_text):
    lowered = doc_text.lower()
    assert "postgresql remains optional" in lowered or "remains optional" in lowered
    assert "optional" in lowered and "postgresql" in lowered


def test_doc_states_sqlite_remains_default(doc_text):
    lowered = doc_text.lower()
    assert "sqlite" in lowered and "default" in lowered


def test_doc_states_no_workflow_required_this_phase(doc_text):
    lowered = doc_text.lower()
    assert "not implemented" in lowered or "not added" in lowered or "deferred" in lowered
    assert "github actions" in lowered or ".github/workflows" in lowered


def test_no_github_workflow_mandated_by_contract():
    """P3.2-E is plan-only; absence of .github/workflows is acceptable."""
    if WORKFLOWS_DIR.is_dir():
        # If workflows exist from other work, this slice still does not require adding one.
        pytest.skip(".github/workflows present — P3.2-E does not mandate a new workflow file")
    assert not WORKFLOWS_DIR.exists(), (
        "P3.2-E phase: no .github/workflows directory expected unless added elsewhere"
    )


def test_doc_lists_which_tests_run_per_job(doc_text):
    lowered = doc_text.lower()
    assert "test_p3_2_dual_run_parity" in lowered or "dual-run" in lowered
    assert "test_p3_2_postgres_fixture" in lowered or "postgres_fixture" in lowered
