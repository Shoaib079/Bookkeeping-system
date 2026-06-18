"""PRODUCTION-HARDENING-01-PH01 — register cleanup contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "PRODUCTION_HARDENING_01_PH01_REGISTER_CLEANUP_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "production_hardening_contract.py"
    spec = importlib.util.spec_from_file_location(
        "production_hardening_contract_ph01", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["production_hardening_contract_ph01"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_pages_contract():
    path = ROOT / "registry" / "react_pages_contract.py"
    spec = importlib.util.spec_from_file_location(
        "react_pages_contract_ph01", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_pages_contract_ph01"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_write_contract():
    path = ROOT / "registry" / "react_write_contract.py"
    spec = importlib.util.spec_from_file_location(
        "react_write_contract_ph01", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_write_contract_ph01"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_pg_contract():
    path = ROOT / "registry" / "pg_boundary_contract.py"
    spec = importlib.util.spec_from_file_location("pg_boundary_contract_ph01", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pg_boundary_contract_ph01"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()
pages_contract = _load_pages_contract()
write_contract = _load_write_contract()
pg_contract = _load_pg_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "ROADMAP gaps closed",
    "Stale contract deferred cleanup",
    "PRODUCTION-HARDENING-01 epic plan",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"PH-01 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def roadmap_text() -> str:
    return (ROOT / "ROADMAP.md").read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("item", contract.PH01_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text


@pytest.mark.parametrize("slice_id", contract.PH01_ROADMAP_EPIC_ROWS_ADDED)
def test_roadmap_epic_table_lists_missing_fr_write_slices(roadmap_text, slice_id):
    assert slice_id in roadmap_text
    assert "✅" in roadmap_text.split(slice_id, 1)[1].split("\n", 1)[0]


def test_roadmap_lists_production_hardening_epic(roadmap_text):
    assert contract.EPIC_ID in roadmap_text
    assert contract.PH01_SLICE_ID in roadmap_text
    assert contract.PH01_TAG in roadmap_text


@pytest.mark.parametrize("stale", contract.PH01_STALE_GLOBAL_DEFERRED_REMOVED)
def test_stale_deferred_removed_from_active_contracts(stale):
    if stale == "FASTAPI-REACT-42":
        assert stale not in pages_contract.DEFERRED_ITEMS
        assert stale not in write_contract.DEFERRED_ITEMS
    if stale == "React write pages":
        assert stale not in pg_contract.DEFERRED_ITEMS


def test_active_pages_deferred_points_at_ph02():
    assert "PRODUCTION-HARDENING-02" in pages_contract.DEFERRED_ITEMS


def test_active_write_deferred_points_at_ph02():
    assert "PRODUCTION-HARDENING-02" in write_contract.DEFERRED_ITEMS


def test_roadmap_react_migration_status_updated(roadmap_text):
    react_line = next(
        line for line in roadmap_text.splitlines() if "**React migration**" in line
    )
    assert "Not started" not in react_line
    assert "42" in react_line or "read" in react_line.lower()


def test_fr50_frozen_deferred_unchanged():
    assert "FASTAPI-REACT-51" in pages_contract.FR50_DEFERRED_ITEMS
