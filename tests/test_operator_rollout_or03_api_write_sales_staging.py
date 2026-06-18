"""OPERATOR-ROLLOUT-OR03 — API write sales staging enable gate tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "OPERATOR_ROLLOUT_OR03_API_WRITE_SALES_STAGING.md"


def _load_rollout_contract():
    path = ROOT / "registry" / "operator_rollout_contract.py"
    spec = importlib.util.spec_from_file_location(
        "operator_rollout_contract_or03", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["operator_rollout_contract_or03"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_write_contract():
    path = ROOT / "registry/react_write_contract.py"
    spec = importlib.util.spec_from_file_location("react_write_contract_or03", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_write_contract_or03"] = mod
    spec.loader.exec_module(mod)
    return mod


rollout = _load_rollout_contract()
write = _load_write_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Staging enablement",
    "Gate verification",
    "What must NOT change",
    "Test plan",
)

OTHER_WRITE_FLAG_PREFIXES = (
    "VITE_ERP_REACT_WRITE_EXPENSES",
    "VITE_ERP_REACT_WRITE_VOIDS",
    "VITE_ERP_REACT_WRITE_PURCHASES",
    "VITE_ERP_REACT_WRITE_RECEIVABLE_PAYMENTS",
    "VITE_ERP_REACT_WRITE_BANKING",
    "VITE_ERP_REACT_WRITE_PARTNER_WORKER",
    "VITE_ERP_REACT_WRITE_RECONCILIATION",
    "VITE_ERP_REACT_WRITE_CLOSING",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"OR-03 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def frontend_env_text() -> str:
    return (ROOT / rollout.STAGING_FRONTEND_ENV).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def api_env_text() -> str:
    return (ROOT / rollout.STAGING_API_ENV).read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("item", rollout.OR03_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text


def test_or03_stage_in_rollout_contract():
    stage = rollout.ROLLOUT_STAGES[2]
    assert stage.stage_id == "OPERATOR-ROLLOUT-OR03"
    assert stage.tag == "operator-rollout-or03-api-write-sales-staging"


@pytest.mark.parametrize("flag_line", rollout.OR03_WRITE_FLAGS_ENABLED)
def test_staging_env_enables_sales_write_flags(
    frontend_env_text, api_env_text, flag_line
):
    if flag_line.startswith("VITE_"):
        assert flag_line in frontend_env_text
    else:
        assert flag_line in api_env_text


def test_staging_frontend_keeps_other_write_flags_off(frontend_env_text):
    assert "VITE_ERP_REACT_WRITE_SALES=1" in frontend_env_text
    for line in frontend_env_text.splitlines():
        stripped = line.strip()
        for prefix in OTHER_WRITE_FLAG_PREFIXES:
            if stripped.startswith(prefix):
                assert stripped.startswith("#"), stripped


def test_staging_api_keeps_other_write_flags_off(api_env_text):
    assert "ERP_API_WRITE_SALES=1" in api_env_text
    for line in api_env_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("ERP_API_WRITE_") and not stripped.startswith(
            "ERP_API_WRITE_SALES"
        ):
            assert stripped.startswith("#"), stripped


def test_write_contract_paths_documented(audit_text):
    assert write.WRITE_SALES_FLAG_ENV in audit_text
    assert write.API_WRITE_SALES_ENV in audit_text
    assert write.WRITE_API_PATHS[0] in audit_text


def test_p2_and_react_write_gate_tests_exist():
    assert (ROOT / write.P2_SALES_WRITE_TEST).is_file()
    assert (ROOT / "tests/test_fastapi_react_08_react_write.py").is_file()


def test_default_commit_mode_unchanged():
    from services import commit_modes
    from services.commit_modes import CommitMode

    commit_modes.reset_commit_modes_for_tests()
    assert commit_modes.get_commit_mode("post_cash_sale") is CommitMode.INTERNAL
