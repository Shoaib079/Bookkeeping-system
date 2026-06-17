"""UI-SYSTEM-02-S1 — ERP-wide UI & theme audit doc + live guardrails.

Audit-only slice: no CSS or runtime UI changes. Verifies docs/UI_SYSTEM_02_AUDIT.md
and key live invariants for the modernization track.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import pytest

import app as erp
from registry.navigation import NAV_ACCORDION_GROUPS, build_nav_direct_pages
from ui.theme import (
    MOBILE_VIEWPORT_MEDIA_QUERY_ARMS,
    MOBILE_VIEWPORT_NARROW_MAX_PX,
    load_theme_css,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "UI_SYSTEM_02_AUDIT.md"
THEME_PY = ROOT / "ui" / "theme.py"
APP_PATH = ROOT / "app.py"

REQUIRED_SECTIONS = (
    "CSS ownership",
    "Theme tokens",
    "Layout shell",
    "Sidebar visual readiness",
    "Desktop/mobile parity",
    "React migration readiness",
    "Dead / duplicate UI code",
    "Safe modernization plan",
)

EXPECTED_CSS_FILES = (
    "theme.css",
    "widgets.css",
    "mobile_shell.css",
    "mobile_txn.css",
    "mobile_components.css",
    "mobile_header.css",
    "auth.css",
    "banking.css",
    "desktop_reports.css",
    "desktop_txn_history.css",
    "mobile_reports.css",
    "mobile_txn_history.css",
    "setup01_wizard.css",
    "icons.css",
)


def _app_line(marker: str) -> int:
    for i, line in enumerate(APP_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if marker in line:
            return i
    raise AssertionError(f"Marker not found in app.py: {marker!r}")


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"UI-SYSTEM-02 audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


# ── Doc contract ──────────────────────────────────────────────────────────────


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_doc_status_and_slices(doc_text):
    low = doc_text.lower()
    assert "ui-system-02-s1" in low and "complete" in low
    for slug in (
        "ui-system-02-s2",
        "ui-system-02-s3",
        "ui-system-02-s4",
        "ui-system-02-s5",
    ):
        assert slug in low, f"Cleanup plan must reference {slug}"


def test_doc_avoids_duplicate_fixes_link(doc_text):
    low = doc_text.lower()
    assert "mobile-14" in low
    assert "css-01" in low or "css-02" in low
    assert "avoid-duplicate" in low or "does not re-propose" in low


def test_inventory_lists_css_files_and_bundle(doc_text):
    low = doc_text.lower()
    assert "load_theme_css" in low
    assert "bootstrap_theme" in low
    for name in ("theme.css", "widgets.css", "mobile_shell.css"):
        assert name in low
    assert "app.py" in low


def test_sidebar_visual_readiness_documented(doc_text):
    low = doc_text.lower()
    assert "_render_navigation_tree" in low
    assert "sidebar_layout" in low or "sidebar layout" in low
    assert "_nav_direct_pages" in low


def test_react_readiness_documented(doc_text):
    low = doc_text.lower()
    assert "st-key-" in low or "streamlit-only" in low
    assert "react_route" in low or "nav-arch" in low
    assert "appshell" in low or "sidebarnav" in low


def test_no_change_statement(doc_text):
    low = doc_text.lower()
    assert "no-change statement" in low
    assert "no visual redesign" in low


# ── Live guardrails ───────────────────────────────────────────────────────────


def test_all_css_files_exist():
    ui = ROOT / "ui"
    for name in EXPECTED_CSS_FILES:
        assert (ui / name).exists(), f"Missing ui/{name}"


def test_theme_py_loads_all_css_files():
    src = THEME_PY.read_text(encoding="utf-8")
    for name in EXPECTED_CSS_FILES:
        assert name in src, f"theme.py must reference {name}"


def test_load_theme_css_bundle_contains_owners():
    bundle = load_theme_css()
    assert "Accounting ERP — global theme" in bundle
    assert "Phase 16B — Streamlit native widgets" in bundle
    assert "Mobile shell" in bundle
    assert len(bundle) > 50_000


def test_app_has_no_inline_style_blocks():
    src = APP_PATH.read_text(encoding="utf-8")
    assert "<style>" not in src
    assert "</style>" not in src


def test_viewport_constants_align_with_mobile_shell():
    shell = (ROOT / "ui" / "mobile_shell.css").read_text(encoding="utf-8")
    assert f"(max-width: {MOBILE_VIEWPORT_NARROW_MAX_PX}px)" in shell
    for arm in MOBILE_VIEWPORT_MEDIA_QUERY_ARMS:
        assert arm in shell, f"mobile_shell.css missing media arm {arm!r}"


def test_theme_tokens_triple_source_documented_in_css_and_py():
    theme_css = (ROOT / "ui" / "theme.css").read_text(encoding="utf-8")
    assert ":root" in theme_css
    assert "--theme-bg" in theme_css
    assert "--erp-chip-active-bg" in theme_css
    theme_py = THEME_PY.read_text(encoding="utf-8")
    assert "LIGHT_ROOT_VARS" in theme_py
    assert "DARK_ROOT_VARS" in theme_py
    assert "@media (prefers-color-scheme: dark)" in theme_css


def test_nav_direct_pages_derived_but_render_tree_uses_layout_registry():
    """S3: layout registry drives render; _NAV_DIRECT_PAGES remains metadata-only."""
    direct = build_nav_direct_pages()
    assert erp._NAV_DIRECT_PAGES == direct
    src = APP_PATH.read_text(encoding="utf-8")
    tree_start = src.index("def _render_navigation_tree(")
    tree_block = src[tree_start : tree_start + 4000]
    assert "SIDEBAR_LAYOUT" in tree_block
    assert "for section in SIDEBAR_LAYOUT" in tree_block


def test_nav_group_keys_match_registry_group_keys():
    registry_keys = {g.group_key for g in NAV_ACCORDION_GROUPS}
    assert set(erp._NAV_GROUP_KEYS) == registry_keys


def test_duplicate_class_selectors_bounded():
    """Cross-file class overlap should stay within known audit budget (regression guard)."""
    class_pat = re.compile(r"(?:^|[,{}\s])(\.[a-zA-Z0-9_-]+)")
    by_sel: dict[str, set[str]] = defaultdict(set)
    for f in (ROOT / "ui").glob("*.css"):
        for m in class_pat.finditer(f.read_text(encoding="utf-8")):
            sel = m.group(1).split(":")[0].split("[")[0]
            by_sel[sel].add(f.name)
    multi = {k: v for k, v in by_sel.items() if len(v) > 1}
    assert len(multi) <= 20, f"Unexpected cross-file selector growth: {len(multi)}"


def test_dead_report_filters_duplicate_removed_in_s4():
    """UI-02-D1 resolved in S4 — only desktop hide rule remains."""
    theme = (ROOT / "ui" / "theme.css").read_text(encoding="utf-8")
    assert theme.count(".erp-mobile-report-filters") == 1


def test_hdr_h_mobile_conflict_resolved():
    """UI-02-C1 resolved in S2 — theme.css desktop 60px only; mobile_header owns 56px."""
    theme = (ROOT / "ui" / "theme.css").read_text(encoding="utf-8")
    header = (ROOT / "ui" / "mobile_header.css").read_text(encoding="utf-8")
    mobile_chunk = theme.split("@media (max-width: 968px)", 1)[-1][:5000]
    for line in mobile_chunk.splitlines():
        stripped = line.strip()
        if stripped.startswith("/*") or stripped.startswith("*"):
            continue
        assert "--hdr-h: 120px" not in stripped
    assert "--hdr-h: 56px" in header
    assert (ROOT / "ui" / "design_tokens.py").exists()


def test_chip_tokens_owned_by_theme_not_duplicated_in_mobile_reports():
    widgets = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    reports = (ROOT / "ui" / "mobile_reports.css").read_text(encoding="utf-8")
    assert "--erp-chip-active-bg" in widgets
    assert "var(--erp-chip-active-bg)" not in reports
