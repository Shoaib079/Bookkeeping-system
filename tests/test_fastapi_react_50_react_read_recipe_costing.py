"""FASTAPI-REACT-50 — recipe costing read pages contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_50_REACT_READ_RECIPE_COSTING_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "react_pages_contract.py"
    spec = importlib.util.spec_from_file_location("react_pages_contract_fr50", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_pages_contract_fr50"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Page inventory",
    "Feature flag",
    "What must NOT change",
    "Test plan",
)

PAGE_API_PATHS = {
    "recipe_ingredients": contract.RECIPE_INGREDIENTS_READ_API_PATHS,
    "recipes": contract.RECIPES_READ_API_PATHS,
    "recipe_cost_breakdown": contract.RECIPE_COST_BREAKDOWN_READ_API_PATHS,
    "recipe_menu_items": contract.RECIPE_MENU_ITEMS_READ_API_PATHS,
}

PAGE_COMPONENTS = {
    "/recipes/ingredients": "RecipeIngredientsPage",
    "/recipes": "RecipesPage",
    "/recipes/cost-breakdown": "RecipeCostBreakdownPage",
    "/recipes/menu-items": "RecipeMenuItemsPage",
}


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-50 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("path,component,_key", contract.FR50_REAL_PAGE_ROUTES)
def test_real_page_routes_documented_in_audit(audit_text, path, component, _key):
    assert path in audit_text
    assert component in audit_text


@pytest.mark.parametrize("path,component,_key", contract.FR50_REAL_PAGE_ROUTES)
def test_real_page_routes_have_page_files(path, component, _key):
    assert (ROOT / f"frontend/src/pages/{component}.tsx").is_file(), component


def test_app_router_wires_fr50_read_pages():
    router_src = (ROOT / "frontend/src/routes/AppRouter.tsx").read_text(
        encoding="utf-8"
    )
    for _path, component, _key in contract.FR50_REAL_PAGE_ROUTES:
        assert component in router_src


@pytest.mark.parametrize("path,component,key", contract.FR50_REAL_PAGE_ROUTES)
def test_fr50_pages_call_p1_read_api(path, component, key):
    src = (ROOT / f"frontend/src/pages/{component}.tsx").read_text(encoding="utf-8")
    for api_path in PAGE_API_PATHS[key]:
        assert api_path in src, api_path
    assert "companyScoped: true" in src


@pytest.mark.parametrize(
    "api_paths",
    [
        contract.RECIPE_INGREDIENTS_READ_API_PATHS,
        contract.RECIPES_READ_API_PATHS,
        contract.RECIPE_COST_BREAKDOWN_READ_API_PATHS,
        contract.RECIPE_MENU_ITEMS_READ_API_PATHS,
    ],
)
def test_fr50_api_paths_are_frozen_read_contract(api_paths):
    read_contract_path = ROOT / contract.READ_CONTRACT
    spec = importlib.util.spec_from_file_location(
        "api_read_contract_fr50", read_contract_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for api_path in api_paths:
        assert api_path in mod.READ_API_PATHS, api_path


def test_roadmap_lists_fastapi_react_50_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-50" in roadmap
    assert "fastapi-react-50-react-read-recipe-costing" in roadmap


@pytest.mark.parametrize("item", contract.FR50_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text
