"""UI-SYSTEM-02-S3 — sidebar modernization contract tests."""

from __future__ import annotations

import inspect
from pathlib import Path

import app as erp
from registry.nav_keys import (
    NAV_BANKING,
    NAV_HOME,
    NAV_INVENTORY,
    NAV_NEW_TRANSACTION,
    NAV_REPORTS,
    NAV_TXN_LEDGER,
)
from registry.navigation import NAV_ACCORDION_GROUPS, NAV_GROUP_HINTS
from registry.sidebar_layout import (
    SIDEBAR_LAYOUT,
    build_nav_group_keys as layout_group_keys,
    flatten_sidebar_layout_keys,
    validate_sidebar_layout,
)

ROOT = Path(__file__).resolve().parents[1]
THEME_CSS = ROOT / "ui" / "theme.css"


def test_sidebar_layout_module_exists():
    assert (ROOT / "registry" / "sidebar_layout.py").exists()


def test_validate_sidebar_layout_passes():
    validate_sidebar_layout()


def test_nav_group_keys_derived_from_registry():
    registry_keys = {g.group_key: g.label_i18n for g in NAV_ACCORDION_GROUPS}
    assert layout_group_keys() == registry_keys
    assert erp._NAV_GROUP_KEYS == registry_keys


def test_nav_group_hints_from_navigation():
    assert erp._NAV_GROUP_HINTS == NAV_GROUP_HINTS


def test_frozen_sidebar_render_order():
    """Layout order must match pre-S3 desktop sidebar sequence."""
    keys = flatten_sidebar_layout_keys()
    assert keys[0:3] == [
        ("direct", NAV_HOME),
        ("direct", NAV_NEW_TRANSACTION),
        ("direct", NAV_TXN_LEDGER),
    ]
    work_idx = keys.index(("section", "nav.sidebar.section_work"))
    reports_idx = keys.index(("section", "nav.sidebar.section_reports"))
    advanced_idx = keys.index(("section", "nav.sidebar.section_advanced"))
    assert work_idx < reports_idx < advanced_idx
    assert keys[work_idx + 1 : work_idx + 6] == [
        ("accordion", "transactions"),
        ("direct", NAV_BANKING),
        ("accordion", "people"),
        ("direct", NAV_INVENTORY),
        ("accordion", "recipe_costing"),
    ]
    stmt_idx = keys.index(("accordion", "statements"))
    reports_direct_idx = keys.index(("direct", NAV_REPORTS))
    assert stmt_idx < reports_direct_idx


def test_render_tree_uses_sidebar_layout():
    src = inspect.getsource(erp._render_navigation_tree)
    assert "SIDEBAR_LAYOUT" in src
    assert "for section in SIDEBAR_LAYOUT" in src
    assert "_nav_section_header" in src
    assert "erp-nav-section-hdr" in src
    assert '_nav_section_caption("nav.sidebar.section_work")' not in src
    assert "  {chevron}" not in src and "chevron" not in src


def test_section_header_css_uses_design_tokens():
    css = THEME_CSS.read_text(encoding="utf-8")
    assert ".erp-nav-section-hdr" in css
    assert "var(--erp-font-caption)" in css.split(".erp-nav-section-hdr")[1][:400]
    assert "var(--erp-space-4)" in css.split(".erp-nav-section-hdr")[1][:400]


def test_accordion_chevron_css_not_inline_text():
    css = THEME_CSS.read_text(encoding="utf-8")
    assert "nav-grp-open" in css and "button::after" in css
    assert 'content: "▾"' in css or "content: \"▾\"" in css


def test_banking_stays_in_work_section_not_registry_direct_order():
    """Visual placement: Banking between transactions and people (not sidebar_direct_order 4)."""
    keys = flatten_sidebar_layout_keys()
    banking_idx = keys.index(("direct", NAV_BANKING))
    trans_idx = keys.index(("accordion", "transactions"))
    people_idx = keys.index(("accordion", "people"))
    inventory_idx = keys.index(("direct", NAV_INVENTORY))
    assert trans_idx < banking_idx < people_idx < inventory_idx


def test_close_day_and_accounting_hints_in_layout():
    hints = {
        item.hint_i18n
        for section in SIDEBAR_LAYOUT
        for item in section.items
        if item.hint_i18n
    }
    assert NAV_GROUP_HINTS["close_day"] in hints
    assert NAV_GROUP_HINTS["accounting"] in hints
