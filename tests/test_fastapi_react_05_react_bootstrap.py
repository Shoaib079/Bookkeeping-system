"""FASTAPI-REACT-05 — React bootstrap contract tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_05_REACT_BOOTSTRAP_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "react_bootstrap_contract.py"
    spec = importlib.util.spec_from_file_location("react_bootstrap_contract", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_bootstrap_contract"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Bootstrap layout",
    "Token governance",
    "Route governance",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-05 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("rel_path", contract.REQUIRED_FRONTEND_FILES)
def test_required_frontend_files_exist(rel_path):
    assert (ROOT / rel_path).is_file(), rel_path


def test_package_json_lists_core_dependencies():
    pkg = json.loads((ROOT / contract.PACKAGE_JSON).read_text(encoding="utf-8"))
    deps = pkg.get("dependencies", {})
    for name in contract.REQUIRED_PACKAGE_DEPS:
        assert name in deps, name


def test_export_script_regenerates_assets_matching_python_ssot():
    subprocess.run(
        [sys.executable, str(ROOT / contract.EXPORT_SCRIPT)],
        check=True,
        cwd=str(ROOT),
    )
    from ui.react_design_contract import react_token_bundle

    tokens_path = ROOT / "frontend/src/generated/design-tokens.json"
    routes_path = ROOT / "frontend/src/generated/routes.json"
    exported_tokens = json.loads(tokens_path.read_text(encoding="utf-8"))
    exported_routes = json.loads(routes_path.read_text(encoding="utf-8"))

    assert exported_tokens == react_token_bundle()
    assert exported_tokens["grammarVersion"] is not None
    assert exported_routes["version"] == "NAV-ARCH-S4"

    import app as _erp  # noqa: F401 — production import order

    from registry.navigation import react_route_contract_rows

    rows = react_route_contract_rows()
    assert len(exported_routes["routes"]) == len(rows)
    exported_paths = {row["path"] for row in exported_routes["routes"]}
    assert exported_paths == {path for _key, path in rows}


def test_theme_provider_imports_generated_bundle():
    src = (ROOT / "frontend/src/theme/ThemeProvider.tsx").read_text(encoding="utf-8")
    assert "design-tokens.json" in src
    assert "componentGrammar" in src


def test_app_router_uses_route_manifest():
    src = (ROOT / "frontend/src/routes/AppRouter.tsx").read_text(encoding="utf-8")
    assert "routeSpecs" in src
    assert "PlaceholderPage" in src


def test_frontend_has_no_accounting_kernel_strings():
    src_root = ROOT / "frontend/src"
    combined = "\n".join(
        p.read_text(encoding="utf-8")
        for p in src_root.rglob("*")
        if p.suffix in {".ts", ".tsx", ".css"}
    ).lower()
    for pattern in contract.FORBIDDEN_FRONTEND_PATTERNS:
        assert pattern.lower() not in combined, pattern


def test_roadmap_lists_fastapi_react_05_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-05" in roadmap
    assert "fastapi-react-05-react-bootstrap" in roadmap


@pytest.mark.parametrize("item", contract.DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text
