"""ICON-MODERNIZE-01 — inline SVG icon system contracts."""

from __future__ import annotations

import re
from pathlib import Path

import app as erp
from registry.icon_svg import PAGE_ICON, TXH_ACTION_LABELS, icon_svg, nav_page_icon_html
from registry.modules_catalog import MODULES, NAV_PAGES_IN_APP
from registry.nav_keys import (
    NAV_CHART_OF_ACCOUNTS,
    NAV_FISCAL_PERIODS,
    NAV_GENERAL_LEDGER,
    NAV_JOURNAL_ENTRIES,
    NAV_TXN_LEDGER,
    ALL_NAV_PAGE_KEYS,
)
from registry.nav_labels import NAV_PAGE_I18N

ROOT = Path(__file__).resolve().parents[1]

CRITICAL_RUNTIME_FILES = (
    ROOT / "app.py",
    ROOT / "registry" / "nav_keys.py",
    ROOT / "registry" / "icon_svg.py",
    ROOT / "registry" / "modules_catalog.py",
    ROOT / "registry" / "nav_labels.py",
)

# Scoped nav/action surfaces — must not use emoji (VS16 workaround not acceptable).
SCOPED_NAV_KEYS = (
    NAV_TXN_LEDGER,
    NAV_GENERAL_LEDGER,
    NAV_FISCAL_PERIODS,
    NAV_JOURNAL_ENTRIES,
    NAV_CHART_OF_ACCOUNTS,
)

EMOJI_IN_STRING = re.compile(
    r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]"
)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_scoped_nav_keys_are_text_only():
    for key in SCOPED_NAV_KEYS:
        assert key in ALL_NAV_PAGE_KEYS
        assert not EMOJI_IN_STRING.search(key), f"{key!r} must not contain emoji"


def test_critical_nav_pages_have_svg_icon_mapping():
    for key in SCOPED_NAV_KEYS:
        assert key in PAGE_ICON, f"missing PAGE_ICON for {key!r}"
        html_out = nav_page_icon_html(key)
        assert "<svg" in html_out
        assert "currentColor" in html_out
        assert "erp-nav-icon" in html_out


def test_txh_actions_use_plain_text_labels_not_emoji():
    bind = _read(ROOT / "app.py")
    start = bind.index("def _txh_bind_action_buttons")
    end = bind.index("def _txh_render_mobile_actions")
    block = bind[start:end]
    for const in (
        "TXH_ACTION_VIEW",
        "TXH_ACTION_EDIT",
        "TXH_ACTION_REPEAT",
        "TXH_ACTION_DUPLICATE",
        "TXH_ACTION_VOID",
    ):
        assert const in block
    assert TXH_ACTION_LABELS == {
        "view": "View",
        "edit": "Edit",
        "repeat": "Repeat",
        "duplicate": "Copy",
        "void": "Void",
    }
    for label in TXH_ACTION_LABELS.values():
        assert label.isascii()
        assert not EMOJI_IN_STRING.search(label)
    # TXH-ACTION-LABEL-01 — keys and handlers unchanged
    assert 'key=f"txh_v_{row_key}"' in block
    assert 'key=f"txh_e_{row_key}"' in block
    assert 'key=f"txh_r_{row_key}"' in block
    assert 'key=f"txh_d_{row_key}"' in block
    assert 'key=f"txh_vd_{row_key}"' in block
    assert "_txh_apply_repeat_prefill" in block


def test_modules_catalog_nav_pages_aligned_with_nav_keys():
    mapped = {m.nav_page for m in MODULES if m.nav_page and not m.planned}
    for key in SCOPED_NAV_KEYS:
        assert key in mapped
        assert key in NAV_PAGES_IN_APP
        assert key in NAV_PAGE_I18N


def test_app_wires_nav_page_button_and_icon_svg():
    src = _read(ROOT / "app.py")
    assert "def _nav_page_button" in src
    assert "nav_page_icon_html" in src
    assert "normalize_nav_key" in src
    assert erp.NAV_GENERAL_LEDGER == NAV_GENERAL_LEDGER
    assert erp._TXN_LEDGER_PAGE_KEY == NAV_TXN_LEDGER


def test_icon_svg_injected_in_theme_css():
    from ui import theme

    css = theme.load_theme_css()
    assert ".erp-icon" in css
    assert ".erp-nav-icon" in css


def test_partner_tab_labels_have_no_emoji():
    from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR

    for key in (
        "partner.tab_owner_equity",
        "partner.tab_partners",
        "partner.tab_movements",
        "partner.tab_allocations",
        "partner.tab_summary",
        "partner.tab_statement",
    ):
        for catalog in (TRANSACTIONAL_EN, TRANSACTIONAL_TR):
            val = catalog[key]
            assert not EMOJI_IN_STRING.search(val), f"{key} emoji in locale: {val!r}"


def test_icon_svg_helper_uses_current_color():
    svg = icon_svg("home", size="nav")
    assert 'stroke="currentColor"' in svg
    assert "http://www.w3.org/2000/svg" in svg
