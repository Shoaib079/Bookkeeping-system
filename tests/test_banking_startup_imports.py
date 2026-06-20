"""Regression: app.py startup imports and ui.banking export contract."""
from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[1]

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

_BANKING_CHAIN_SOURCES = (
    _ROOT / "ui" / "banking.py",
    _ROOT / "reconciliation" / "__init__.py",
    _ROOT / "reconciliation" / "clearing.py",
    _ROOT / "services" / "__init__.py",
    _ROOT / "services" / "read_balances.py",
    _ROOT / "models.py",
)


def _app_banking_import_names() -> list[str]:
    src = (_ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "ui.banking":
            for alias in node.names:
                names.append(alias.name)
    return names


class TestStartupImports:
    def test_app_imports_successfully(self):
        importlib.invalidate_caches()
        erp_app = importlib.import_module("app")
        assert erp_app is not None

    def test_ui_banking_exports_all_app_imports(self):
        import ui.banking as banking_ui

        missing = [
            name
            for name in _app_banking_import_names()
            if not hasattr(banking_ui, name)
        ]
        assert missing == [], f"ui.banking missing exports: {missing}"

    def test_banking_apply_default_import_tab_exported(self):
        import ui.banking as banking_ui

        assert hasattr(banking_ui, "banking_apply_default_import_tab")
        assert callable(banking_ui.banking_apply_default_import_tab)

    def test_direct_import_chain_without_app_bootstrap(self):
        """OBS-012: ui.banking must import in a fresh interpreter (no app warmup)."""
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import ui.banking; import services.read_balances; "
                "import reconciliation.clearing; print('ok')",
            ],
            cwd=_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        assert "ok" in result.stdout

    def test_services_package_does_not_eager_import_read_balances(self):
        src = (_ROOT / "services" / "__init__.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        eager = [
            ast.unparse(node)
            for node in tree.body
            if isinstance(node, ast.ImportFrom)
            and (node.module or "").startswith("services.read_balances")
        ]
        assert eager == [], (
            "services.__init__ must not eager-import read_balances "
            "(circular import during models/db startup)"
        )

    def test_banking_chain_has_no_malformed_import_statements(self):
        """Guard against corrupted ``from X importY`` typos in the import chain."""
        for path in _BANKING_CHAIN_SOURCES:
            raw = path.read_text(encoding="utf-8")
            assert "importfetch" not in raw, f"{path}: malformed import token"
            assert "importget" not in raw, f"{path}: malformed import token"
            tree = ast.parse(raw)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    assert node.module, f"{path}: ImportFrom missing module"
                    assert node.names, f"{path}: ImportFrom missing names"
