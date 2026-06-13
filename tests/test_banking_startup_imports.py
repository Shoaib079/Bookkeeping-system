"""Regression: app.py startup imports and ui.banking export contract."""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[1]

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock


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
        import importlib

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
