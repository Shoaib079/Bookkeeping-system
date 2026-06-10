"""NOTIF-THEME-01 — notification bell active state + popover body tokens."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_CANONICAL_ACTIVE = (
    '[data-testid="stMain"] .st-key-hdr_toolbar_row:has(.erp-hdr-notif-active) '
    ".st-key-hdr_notif_pop [data-testid=\"stPopover\"] > button"
)
_BRITTLE = (
    ":has(.erp-hdr-notif-active) > div > [data-testid=\"stHorizontalBlock\"] > "
    "[data-testid=\"stColumn\"]:first-child [data-testid=\"stPopover\"]"
)


def test_no_brittle_first_child_notification_selector():
    theme = (ROOT / "ui" / "theme.css").read_text(encoding="utf-8")
    widgets = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    assert _BRITTLE not in theme
    assert _BRITTLE not in widgets


def test_desktop_canonical_active_selector_in_theme_css():
    theme = (ROOT / "ui" / "theme.css").read_text(encoding="utf-8")
    assert "NOTIF-THEME-01" in theme
    assert _CANONICAL_ACTIVE in theme
    assert "var(--theme-warning)" in theme
    assert "@media (min-width: 969px)" in theme.split(_CANONICAL_ACTIVE, 1)[0][-200:]


def test_mobile_active_selector_remains_in_mobile_header():
    mobile = (ROOT / "ui" / "mobile_header.css").read_text(encoding="utf-8")
    assert (
        ".st-key-hdr_toolbar_row:has(.erp-hdr-notif-active) .st-key-hdr_notif_pop"
        in mobile
    )
    assert "var(--theme-warning)" in mobile


def test_active_selector_in_widgets_beats_neutral_reset():
    widgets = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    assert _CANONICAL_ACTIVE in widgets
    assert ":not(:has(.erp-hdr-notif-active)) .st-key-hdr_notif_pop" in widgets
    active_idx = widgets.index(_CANONICAL_ACTIVE)
    neutral_idx = widgets.index(":not(:has(.erp-hdr-notif-active)) .st-key-hdr_notif_pop")
    assert active_idx > neutral_idx


def test_st_popover_body_uses_theme_tokens():
    widgets = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    block = widgets.split('[data-testid="stPopoverBody"]', 1)[1].split("/* ── Header toolbar", 1)[0]
    assert "var(--theme-card)" in block
    assert "var(--theme-border)" in block
    assert "var(--theme-text)" in block
