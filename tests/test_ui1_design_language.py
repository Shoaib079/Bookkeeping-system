"""Phase UI-1 — unified design language contract tests."""

from __future__ import annotations

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
    css = _read("ui", "mobile_reports.css")
    assert "var(--erp-chip-active-bg)" in css
    assert "background: var(--theme-info) !important" not in css.split("mob_rpt")[1]


def test_mob_at_chips_alias_erp_tokens():
    css = _read("ui", "mobile_txn.css")
    assert "--mob-at-chip-active-bg: var(--erp-chip-active-bg)" in css


def test_sidebar_primary_uses_chip_tokens():
    theme = _read("ui", "theme.css")
    assert "var(--erp-chip-active-bg)" in theme
    sidebar_block = theme.split("Sidebar nav buttons")[1].split("Sidebar form")[0]
    assert "--erp-chip-active-bg" in sidebar_block


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
