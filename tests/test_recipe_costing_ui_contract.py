"""RC-P1b UI contract — Recipe Costing renderers."""

from __future__ import annotations

import ast
import inspect
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ING_UI = ROOT / "ui" / "recipe_costing.py"
APP_PATH = ROOT / "app.py"

SERVICE_CALLS = (
    "list_ingredients",
    "create_ingredient",
    "update_ingredient",
    "update_ingredient_cost",
    "activate_ingredient",
    "deactivate_ingredient",
    "list_recipes",
    "get_recipe",
    "save_recipe",
    "compute_recipe_cost",
    "units_for_dimension",
    "list_menu_items",
    "create_menu_item",
    "update_menu_item",
    "deactivate_menu_item",
    "set_menu_price",
    "list_menu_profitability",
)

FORBIDDEN_UI_TOKENS = (
    "to_base_units",
    "from_base_units",
    "_compute_recipe_cost_pure",
    "create_journal_entry",
    "post_cash_sale",
    "post_purchase",
    "inventory_transactions",
    "gross_to_net_price",
    "compute_food_cost_pct",
    "compute_markup_pct",
    "compute_suggested_gross_price",
    "compute_menu_profitability_metrics",
)


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.fixture()
def ui_src() -> str:
    return _read(ING_UI)


@pytest.fixture()
def app_src() -> str:
    return _read(APP_PATH)


def test_renderer_module_exists():
    assert ING_UI.is_file()
    from ui.recipe_costing import (
        render_recipe_cost_breakdown,
        render_recipe_ingredients,
        render_recipe_menu_items,
        render_recipe_recipes,
    )

    for fn in (
        render_recipe_ingredients,
        render_recipe_recipes,
        render_recipe_cost_breakdown,
        render_recipe_menu_items,
    ):
        assert callable(fn)


def test_renderer_calls_service_only(ui_src: str):
    assert "services import recipe_costing" in ui_src or "services.recipe_costing" in ui_src
    for fn in SERVICE_CALLS:
        assert fn in ui_src, f"Expected service call {fn!r} in UI renderer"
    for token in FORBIDDEN_UI_TOKENS:
        assert token not in ui_src, f"Forbidden token {token!r} in UI renderer"


def test_no_costing_math_in_ui(ui_src: str):
    assert "cost_per_base_unit *" not in ui_src
    assert "effective_qty" not in ui_src
    assert "_compute_recipe_cost_pure" not in ui_src


def test_restaurant_friendly_labels(ui_src: str):
    assert "_recipe_tree_markdown" in ui_src
    assert "rc.field.pick_ingredient" in ui_src
    assert 'st.text_input("ingredient_id"' not in ui_src


def test_app_dispatches_to_ui_renderers(app_src: str):
    assert "render_recipe_ingredients" in app_src
    assert "render_recipe_recipes" in app_src
    assert "render_recipe_cost_breakdown" in app_src
    assert "render_recipe_menu_items" in app_src
    assert "NAV_RC_INGREDIENTS: render_recipe_ingredients" in app_src
    assert "NAV_RC_RECIPES: render_recipe_recipes" in app_src
    assert "NAV_RC_COST_BREAKDOWN: render_recipe_cost_breakdown" in app_src
    assert "NAV_RC_MENU_ITEMS: render_recipe_menu_items" in app_src


def test_nav_wired_under_recipe_costing(app_src: str):
    idx = app_src.find('"recipe_costing", "Recipe Costing"')
    assert idx != -1
    snippet = app_src[idx : idx + 500]
    assert "NAV_RC_INGREDIENTS" in snippet
    assert "NAV_RC_RECIPES" in snippet
    assert "NAV_RC_COST_BREAKDOWN" in snippet
    assert "NAV_RC_MENU_ITEMS" in snippet


def test_permissions_registered(app_src: str):
    for perm in ("view_recipe_costing", "manage_recipe_costing"):
        assert perm in app_src


def test_renderer_passes_explicit_company_id(ui_src: str):
    assert "current_company_required" in ui_src
    assert "company_id" in ui_src


def test_renderer_public_signatures():
    from ui.recipe_costing import (
        render_recipe_cost_breakdown,
        render_recipe_ingredients,
        render_recipe_menu_items,
        render_recipe_recipes,
    )

    for fn in (
        render_recipe_ingredients,
        render_recipe_recipes,
        render_recipe_cost_breakdown,
        render_recipe_menu_items,
    ):
        params = list(inspect.signature(fn).parameters)
        assert params == ["session"]


def test_section_header_html_title_only(ui_src: str):
    """section_header_html(title) — subtitle via st.caption, not a second positional arg."""
    tree = ast.parse(ui_src)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "section_header_html":
            assert len(node.args) <= 1, (
                "section_header_html accepts title only; render subtitle with st.caption"
            )

    for subtitle_key in (
        "rc.ingredients.subtitle",
        "rc.recipes.subtitle",
        "rc.cost.subtitle",
        "rc.menu.subtitle",
    ):
        assert f'st.caption(erp._t("{subtitle_key}")' in ui_src
