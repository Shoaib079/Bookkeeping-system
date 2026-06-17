"""Phase UI-1 — unified design language contract tests."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def test_style_guide_exists():
    guide = _read("docs", "UI_STYLE_GUIDE.md")
    assert "Primary Button" in guide
    assert "Selected Chip" in guide
    assert "Mobile FAB" in guide
    assert "docs/ui_style_guide_preview.html" in guide


def test_erp_chip_tokens_in_theme():
    theme = _read("ui", "theme.css")
    assert "--erp-chip-active-bg" in theme
    assert "--erp-chip-idle-border" in theme


def test_ui1_global_secondary_and_danger_rules():
    widgets = _read("ui", "widgets.css")
    assert "UI-1 — Global secondary" in widgets
    assert "UI-1 — Danger actions" in widgets
    assert "st-key-erp_void_" in widgets
    assert "st-key-erp_danger_" in widgets


def test_ui1_chip_primary_unified():
    widgets = _read("ui", "widgets.css")
    assert "UI-1 — Selected chip" in widgets
    assert "st-key-mob_rpt_sel_" in widgets
    assert "var(--erp-chip-active-bg)" in widgets


def test_mobile_reports_chips_use_tinted_not_solid():
    """Report chips use ERP chip tokens (widgets.css); mobile_reports.css is layout only."""
    widgets = _read("ui", "widgets.css")
    reports = _read("ui", "mobile_reports.css")
    assert "st-key-mob_rpt_sel_" in widgets
    assert "st-key-mob_rpt_main_tabs" in widgets
    assert "var(--erp-chip-active-bg)" in widgets
    assert "var(--erp-chip-active-fg)" in widgets
    assert "var(--erp-chip-idle-bg)" in widgets
    assert "var(--erp-chip-idle-fg)" in widgets
    # CSS-01 / E8a–E8b: chip colour grammar not duplicated in mobile_reports.css.
    assert "var(--erp-chip-active-bg)" not in reports
    assert "var(--erp-chip-active-fg)" not in reports
    assert "var(--erp-chip-idle-bg)" not in reports
    assert "var(--erp-chip-idle-fg)" not in reports
    # No solid theme-info CTA styling in report layout sheet.
    assert "background: var(--theme-info) !important" not in reports.split("mob_rpt")[1]


def test_mob_at_chips_alias_erp_tokens():
    widgets = _read("ui", "widgets.css")
    css = _read("ui", "mobile_txn.css")
    # CSS-01 / E9: --mob-at-* tokens owned solely by mobile_txn.css :root.
    assert "--mob-at-chip-active-bg:" not in widgets
    assert css.count("--mob-at-chip-active-bg:") == 1
    assert "--mob-at-chip-active-bg: var(--erp-chip-active-bg)" in css


def test_sidebar_primary_uses_nav_grammar_tokens():
    theme = _read("ui", "theme.css")
    sidebar_block = theme.split("Sidebar nav buttons")[1].split("Sidebar form")[0]
    assert "var(--erp-nav-active-bg)" in sidebar_block
    assert "var(--erp-nav-active-fg)" in sidebar_block


def test_section_accent_policy_documented():
    section = _read("ui", "section.py")
    assert "UI-1 accent policy" in section


def test_mono_sweep3_helpers_in_section_and_theme():
    section = _read("ui", "section.py")
    theme = _read("ui", "theme.css")
    for name in ("aging_buckets_html", "page_report_banner_html", "mono_role_pill_html"):
        assert name in section
    for cls in (".erp-aging-bucket", ".erp-mono-pill", ".erp-page-banner"):
        assert cls in theme


def test_mono_sweep3_no_banned_colorful_patterns_in_app():
    src = _read("app.py")
    banned = (
        '"color": "#111827"',
        '"color": "#2563eb"',
        '_aging_colors = {"Current": "#10b981"',
        "linear-gradient(135deg,#14532d",
        "linear-gradient(135deg,#1e40af",
        "_MEMBER_ROLE_COLORS",
        "mark_bar(color='#8b5cf6')",
        "mark_line(point=True, color='#3b82f6')",
        '_role_colors = {"owner": "#1e40af"',
        'accent="purple"',
        'accent="teal"',
    )
    for pattern in banned:
        assert pattern not in src, f"colorful UI pattern still in app.py: {pattern}"


def test_mono_sweep3_documented_in_style_guide():
    guide = _read("docs", "UI_STYLE_GUIDE.md")
    assert "Mono Design Enforcement" in guide


def test_dropdown_visibility_css_contract():
    """Selectbox virtual dropdown + BaseWeb listbox option text must use theme tokens."""
    widgets = _read("ui", "widgets.css")
    assert "stSelectboxVirtualDropdown" in widgets
    assert '[role="option"]' in widgets
    assert "var(--theme-text)" in widgets
    assert "color-mix(in srgb, var(--theme-info) 14%, var(--theme-card) 86%)" in widgets


def test_dropdown_visibility_documented_in_style_guide():
    guide = _read("docs", "UI_STYLE_GUIDE.md")
    assert "Dropdown and Selectbox Visibility Rules" in guide


def test_form_widget_visibility_css_contract():
    """Form submit, file uploader, number input, and progress use theme tokens."""
    widgets = _read("ui", "widgets.css")
    assert "stFormSubmitButton" in widgets
    assert "secondaryFormSubmit" in widgets
    assert "stFileUploaderDropzone" in widgets
    assert "stNumberInputStepDown" in widgets
    assert "stProgressBarTrack" in widgets
    assert "var(--theme-text)" in widgets


def test_form_widget_visibility_documented_in_style_guide():
    guide = _read("docs", "UI_STYLE_GUIDE.md")
    assert "Form Controls and Widget Visibility Rules" in guide


def test_selectbox_popover_click_through_css_contract():
    """Closed BaseWeb portal shells must not trap clicks after a selectbox pick."""
    widgets = _read("ui", "widgets.css")
    assert re.search(
        r'div\[data-baseweb="popover"\]\s*\{[^}]*pointer-events:\s*none\s*!important',
        widgets,
        re.S,
    )
    assert "stSelectboxVirtualDropdown" in widgets
    assert "pointer-events: auto !important" in widgets


def test_st_popover_not_globally_pointer_events_none():
    """Streamlit st.popover triggers (header bell/profile) must remain clickable."""
    widgets = _read("ui", "widgets.css")
    assert not re.search(
        r'\[data-testid="stPopover"\]\s*\{[^}]*pointer-events:\s*none',
        widgets,
        re.S,
    )
    assert not re.search(
        r'\[data-testid="stPopover"\][^{]*\{[^}]*pointer-events:\s*none',
        widgets,
        re.S,
    )


def test_header_popover_trigger_css_contract():
    """Header popover keys retain trigger + open-panel button styling."""
    widgets = _read("ui", "widgets.css")
    app_src = _read("app.py")
    assert 'key="hdr_notif_pop"' in app_src or 'key=_notif_key' in app_src
    assert "hdr_notif_pop" in app_src
    assert "hdr_profile_pop" in app_src
    assert '[class*="st-key-hdr_notif_pop"] [data-testid="stPopover"] > button' in widgets
    assert '[class*="st-key-hdr_profile_pop"] [data-testid="stPopover"] > button' in widgets
    assert (
        '[class*="st-key-hdr_notif_pop"] [data-testid="stPopover"] [data-testid="stButton"] button'
        in widgets
    )
    assert (
        '[class*="st-key-hdr_profile_pop"] [data-testid="stPopover"] [data-testid="stButton"] button'
        in widgets
    )


def test_desktop_skips_mobile_at_host():
    src = _read("app.py")
    assert "if _is_mobile_at:" in src
    assert '_at_clear_stale_mobile_overlay_state()' in src
    assert 'with st.container(key="erp_at_mobile_screen")' in src


def test_desktop_mobile_host_non_interactive_css():
    css = _read("ui", "mobile_txn.css")
    block = css.split("@media (min-width: 969px)")[1]
    assert "erp_at_mobile_screen" in block
    assert "pointer-events: none !important" in block
