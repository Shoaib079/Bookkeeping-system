"""App startup — registry.navigation import contract (UI-SYSTEM-02-S3 guard)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import app as erp  # noqa: F401 — bootstrap full import graph

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"


def _navigation_names_imported_by_app() -> set[str]:
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "registry.navigation":
            return {alias.name for alias in node.names}
    raise AssertionError("app.py must import from registry.navigation")


@pytest.fixture(scope="module")
def navigation_import_names() -> set[str]:
    return _navigation_names_imported_by_app()


def test_app_imports_navigation_symbols(navigation_import_names):
    import registry.navigation as navigation

    missing = sorted(
        name for name in navigation_import_names if not hasattr(navigation, name)
    )
    assert not missing, f"registry.navigation missing exports: {missing}"


def test_nav_group_hints_exported_from_navigation():
    from registry.navigation import NAV_GROUP_HINTS

    assert NAV_GROUP_HINTS["close_day"] == "nav.group.close_day_hint"
    assert NAV_GROUP_HINTS["accounting"] == "nav.group.accounting_hint"


def test_app_nav_group_hints_alias_matches_registry():
    from registry.navigation import NAV_GROUP_HINTS

    assert erp._NAV_GROUP_HINTS is NAV_GROUP_HINTS


def test_import_app_module():
    assert erp.render_dashboard is not None
