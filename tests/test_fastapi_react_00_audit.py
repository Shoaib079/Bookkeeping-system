"""FASTAPI-REACT-00 — migration baseline audit contract tests (audit only)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "FASTAPI_REACT_00_AUDIT.md"

REQUIRED_SECTIONS = (
    "Executive summary",
    "What is already FastAPI-ready",
    "What is already React-ready",
    "What still blocks React",
    "What must NOT change",
    "Recommended phased roadmap",
    "Risk matrix",
    "Test plan",
    "Implementation boundaries",
    "Recommendation",
)

FROZEN_CONTRACT_REFS = (
    "ui/react_design_contract.py",
    "registry/navigation.py",
    "api/main.py",
    "NAV_ARCH_REACT_ROUTE_CONTRACT",
    "UI_SYSTEM_02_REACT_DESIGN_CONTRACT",
    "ERP_DS_05_REACT_ARCHITECTURE",
    "MONO_THEME_02_VISUAL_CONTRACT",
)

FUTURE_SLICES = (
    "fastapi-react-01",
    "fastapi-react-05",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"FASTAPI-REACT-00 audit missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists_and_nonempty():
    assert DOC_PATH.stat().st_size > 0


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing section: {section!r}"


def test_audit_only_no_implementation_authorization(doc_text):
    low = doc_text.lower()
    assert "audit only" in low
    assert "authorize production" in low or "no implementation" in low
    assert "no react repo bootstrap" in low or "no `package.json`" in low


def test_fastapi_partial_react_not_started(doc_text):
    low = doc_text.lower()
    assert "partial" in low
    assert "not started" in low
    assert "streamlit remains" in low or "streamlit primary" in low


@pytest.mark.parametrize("ref", FROZEN_CONTRACT_REFS)
def test_frozen_contracts_cited(doc_text, ref):
    assert ref in doc_text, f"Audit must cite {ref!r}"


@pytest.mark.parametrize("slice_id", FUTURE_SLICES)
def test_future_slices_documented(doc_text, slice_id):
    assert slice_id in doc_text.lower(), f"Future slice plan missing: {slice_id}"


def test_blockers_cited(doc_text):
    for needle in ("TD-PS-01", "P2-HARDEN-01", "MONEY-DECIMAL-01", "AUTH-SESSION-02"):
        assert needle in doc_text, f"Blocker missing: {needle}"


def test_recommendation_proceed_with_hardening_first(doc_text):
    low = doc_text.lower()
    assert "proceed" in low
    assert "fastapi-react-01" in low
    assert "defer" in low or "before" in low


def test_referenced_artifacts_exist():
    assert (ROOT / "api" / "main.py").is_file()
    assert (ROOT / "ui" / "react_design_contract.py").is_file()
    assert (ROOT / "registry" / "navigation.py").is_file()
    fastapi_tests = list((ROOT / "tests").glob("test_fastapi_*.py"))
    assert len(fastapi_tests) >= 30


def test_roadmap_lists_fastapi_react_00():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-00" in roadmap
