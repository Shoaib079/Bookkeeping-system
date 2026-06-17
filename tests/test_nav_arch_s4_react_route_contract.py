"""NAV-ARCH-S4 — frozen React route contract."""

from __future__ import annotations

from pathlib import Path

import pytest

import app as erp  # noqa: F401 — ensure app/registry import order matches production

from registry.nav_keys import LEGACY_NAV_ALIASES
from registry.navigation import (
    NAV_PAGES,
    REACT_ROUTE_SAFE_RE,
    react_route_contract_rows,
    react_routes,
    validate_react_route_contract,
)
from tests.nav_ux_02_contract import (
    SETTINGS_ADMIN_REACT_ROUTES,
    STAFF_EXPENSE_REACT_ROUTE,
    STATEMENT_REACT_ROUTES,
)

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "NAV_ARCH_REACT_ROUTE_CONTRACT.md"

REQUIRED_SECTIONS = (
    "Purpose",
    "Contract rules",
    "Frozen mapping",
    "Legacy aliases",
    "No-change statement",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"React route contract doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing section: {section!r}"


def test_doc_lists_all_registry_routes(doc_text):
    for route_key, react_route in react_route_contract_rows():
        assert route_key in doc_text
        assert react_route in doc_text


def test_validate_react_route_contract_passes():
    validate_react_route_contract()


def test_every_route_has_react_route():
    for page in NAV_PAGES:
        assert page.react_route
        assert page.react_route.startswith("/")


def test_react_routes_unique():
    paths = list(react_routes().values())
    assert len(paths) == len(set(paths))


def test_react_route_safe_naming():
    for page in NAV_PAGES:
        assert REACT_ROUTE_SAFE_RE.match(page.react_route), page.route_key


def test_home_is_only_root_path():
    roots = [path for path in react_routes().values() if path == "/"]
    assert roots == ["/"]


def test_statement_contract_aligned_with_registry():
    registry = react_routes()
    for route_key, path in STATEMENT_REACT_ROUTES.items():
        assert registry[route_key] == path


def test_settings_admin_contract_aligned_with_registry():
    registry = react_routes()
    for route_key, path in SETTINGS_ADMIN_REACT_ROUTES.items():
        assert registry[route_key] == path
        assert path.startswith("/settings/")


def test_staff_expense_contract_aligned_with_registry():
    from registry.nav_keys import NAV_STAFF_EXPENSE_CAPTURE

    assert react_routes()[NAV_STAFF_EXPENSE_CAPTURE] == STAFF_EXPENSE_REACT_ROUTE
    assert "/people/" not in STAFF_EXPENSE_REACT_ROUTE


def test_no_retired_today_summary_react_path():
    assert "/today" not in react_routes().values()


def test_legacy_aliases_resolve_to_canonical_react_routes():
    routes = react_routes()
    for _alias, canonical in LEGACY_NAV_ALIASES.items():
        assert canonical in routes, f"Alias target {canonical!r} missing from react_routes()"


def test_legacy_aliases_that_differ_from_canonical_are_not_dispatch_keys():
    """Emoji/legacy alias strings are not separate dispatch route_keys."""
    routes = react_routes()
    for alias, canonical in LEGACY_NAV_ALIASES.items():
        if alias != canonical:
            assert alias not in routes


def test_today_summary_alias_targets_reports_path():
    routes = react_routes()
    from registry.nav_keys import NAV_REPORTS

    assert LEGACY_NAV_ALIASES["Today's Summary"] == NAV_REPORTS
    assert routes[NAV_REPORTS] == "/reports"


def test_doc_mentions_registry_source_of_truth(doc_text):
    low = doc_text.lower()
    assert "registry/navigation.py" in low
    assert "frozen" in low
