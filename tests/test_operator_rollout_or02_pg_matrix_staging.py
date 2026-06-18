"""OPERATOR-ROLLOUT-OR02 — PostgreSQL boundary matrix staging gate tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "OPERATOR_ROLLOUT_OR02_PG_MATRIX_STAGING.md"


def _load_rollout_contract():
    path = ROOT / "registry" / "operator_rollout_contract.py"
    spec = importlib.util.spec_from_file_location(
        "operator_rollout_contract_or02", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["operator_rollout_contract_or02"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_pg_contract():
    path = ROOT / "registry" / "pg_matrix_execution_contract.py"
    spec = importlib.util.spec_from_file_location("pg_matrix_contract_or02", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pg_matrix_contract_or02"] = mod
    spec.loader.exec_module(mod)
    return mod


rollout = _load_rollout_contract()
pg = _load_pg_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Matrix execution results",
    "Gate verification",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"OR-02 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("item", rollout.OR02_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text


def test_or02_stage_in_rollout_contract():
    stage = rollout.ROLLOUT_STAGES[1]
    assert stage.stage_id == "OPERATOR-ROLLOUT-OR02"
    assert stage.tag == "operator-rollout-or02-pg-matrix-staging"


def test_staging_postgres_env_template_exists():
    path = ROOT / "config/staging/postgres.env.example"
    text = path.read_text(encoding="utf-8")
    assert pg.POSTGRES_OPTIONAL_ENV in text
    assert "erp_pytest" in text
    assert "postgres@" in text


@pytest.mark.parametrize("flow", pg.PG_BOUNDARY_MATRIX_FLOWS)
def test_audit_documents_matrix_flows(audit_text, flow):
    assert flow.flow_id in audit_text
    assert flow.family in audit_text


def test_audit_records_matrix_pass(audit_text):
    assert "4 passed" in audit_text
