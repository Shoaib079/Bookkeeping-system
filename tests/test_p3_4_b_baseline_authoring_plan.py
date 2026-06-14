"""P3.4-B — contract test for the Alembic baseline (0001) authoring plan.

Doc-only guard: verifies the authoring plan exists, carries the required sections,
pins the safety invariants, and that NO migration revision file has been created.
No DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "P3_4_B_BASELINE_AUTHORING_PLAN.md"

REQUIRED_SECTIONS = (
    "Generation approach",
    "Manual reconciliation",
    "predicate normalization",
    "Naming convention",
    "Review checklist",
    "Acceptance gate",
    "Rollout",
    "No-change decisions",
)

ACCOUNTING_UNIQUES = (
    "uq_yec_year",
    "uq_palloc_period",
    "uq_eod_date_active",
    "uq_esv_active",
    "uq_coa_code_company",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Authoring plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Authoring plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Authoring plan doc is empty"


def test_no_migration_revision_file_created():
    """Rule: do not create migration revision files yet."""
    version_files: list[Path] = []
    for versions_dir in ROOT.glob("**/versions"):
        if versions_dir.is_dir():
            version_files.extend(p for p in versions_dir.glob("*.py") if p.name != "__init__.py")
    # Also catch a stray baseline revision anywhere in the tree.
    baseline_like = [
        p for p in ROOT.glob("**/*.py")
        if "0001" in p.name and ("baseline" in p.name.lower() or "alembic" in str(p).lower())
    ]
    offenders = version_files + baseline_like
    assert not offenders, f"No migration revision file should exist yet, found: {offenders}"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_no_blind_autogenerate(doc_text):
    assert "no blind autogenerate" in doc_text.lower(), "Plan must forbid blind autogenerate"


def test_empty_db_generation(doc_text):
    lowered = doc_text.lower()
    assert "empty database" in lowered or "empty db" in lowered, (
        "Plan must require generation against an empty DB"
    )


@pytest.mark.parametrize("constraint", ACCOUNTING_UNIQUES)
def test_accounting_critical_uniques_listed(doc_text, constraint):
    assert constraint in doc_text, f"Missing accounting-critical unique: {constraint}"


def test_products_company_sku_unique_listed(doc_text):
    lowered = doc_text.lower()
    assert "products" in lowered and "sku" in lowered, (
        "Plan must include the products (company_id, sku) unique"
    )


def test_is_void_is_false_normalization(doc_text):
    assert "is_void is false" in doc_text.lower(), (
        "Plan must normalize partial predicate to is_void IS FALSE"
    )


def test_coalesce_branch_location_handled(doc_text):
    assert "coalesce(branch_location, '')" in doc_text.lower(), (
        "Plan must handle uq_esv_active COALESCE(branch_location, '')"
    )


def test_baseline_equivalence_test_required(doc_text):
    assert "baseline-equivalence test" in doc_text.lower(), (
        "Plan must require a baseline-equivalence acceptance gate"
    )


def test_migrate_schema_remains_active(doc_text):
    lowered = doc_text.lower()
    assert "migrate_schema" in lowered and "active" in lowered, (
        "Plan must state migrate_schema remains active"
    )


def test_no_float_to_decimal(doc_text):
    lowered = doc_text.lower()
    assert "float" in lowered and "decimal" in lowered, (
        "Plan must state no Float → Decimal conversion"
    )
