"""MOBILE-NAV-ICON-01 — bottom navigation SVG icon contracts.

The mobile bottom nav renders icons from registry/icon_svg.py (inline SVG,
currentColor) overlaid on the button's blank first line. These contracts pin:
no emoji in the nav definition, registry-backed icon names, the overlay render
path, shell-owned CSS (including active state), and the untouched FAB.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from registry.icon_svg import _ICON_PATHS, icon_svg  # noqa: E402

APP = (ROOT / "app.py").read_text(encoding="utf-8")
SHELL = (ROOT / "ui" / "mobile_shell.css").read_text(encoding="utf-8")

_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF☀-➿⬀-⯿①-⓿☰⏻]"
)


def _nav_tuple_block() -> str:
    m = re.search(r"_MOBILE_BOTTOM_NAV = \((.*?)\n\)", APP, flags=re.S)
    assert m, "_MOBILE_BOTTOM_NAV tuple not found"
    return m.group(1)


def _render_fn_block() -> str:
    m = re.search(
        r"def _render_mobile_bottom_nav\(.*?\n\ndef ", APP, flags=re.S
    )
    assert m, "_render_mobile_bottom_nav not found"
    return m.group(0)


def test_bottom_nav_definition_has_no_emoji():
    block = _nav_tuple_block()
    hits = _EMOJI_RE.findall(block)
    assert not hits, f"emoji literals back in _MOBILE_BOTTOM_NAV: {hits}"


def test_bottom_nav_icons_exist_in_svg_registry():
    block = _nav_tuple_block()
    icons = re.findall(r',\s*"([a-z][a-z0-9-]*)"\)', block)
    assert icons, "no icon names parsed from _MOBILE_BOTTOM_NAV"
    expected = {"home", "landmark", "plus", "bar-chart", "menu"}
    assert set(icons) == expected, f"unexpected mapping: {icons}"
    for name in icons:
        assert name in _ICON_PATHS, f"icon {name!r} missing from icon_svg registry"
        svg = icon_svg(name)
        assert svg.startswith("<svg"), f"icon_svg({name!r}) did not render"
        assert "currentColor" in svg


def test_bottom_nav_renders_svg_overlay_not_emoji_label():
    fn = _render_fn_block()
    assert "erp-mob-bar-ico" in fn, "SVG overlay markdown missing from bottom nav"
    assert "icon_svg(icon" in fn, "bottom nav must render icons via icon_svg()"
    hits = _EMOJI_RE.findall(fn)
    assert not hits, f"emoji in bottom nav render fn: {hits}"
    # Blank first line preserves the two-line button box / touch target.
    assert "​\\n" in APP or "​\n" in APP, "zero-width first line missing from _mob_bar_btn_label"


def test_shell_css_owns_icon_overlay_and_active_state():
    assert ".erp-mob-bar-ico" in SHELL
    assert "pointer-events: none" in SHELL.split("erp-mob-bar-ico", 1)[1][:1200]
    # Active tab: icon follows label into theme-info via :has(primary button).
    active = re.search(
        r':has\(button\[kind="primary"\].*?\)\s*\.erp-mob-bar-ico\s*\{([^}]*)\}',
        SHELL,
        flags=re.S,
    )
    assert active, "active-state icon rule missing from mobile_shell.css"
    assert "var(--theme-info)" in active.group(1)


def test_fab_unchanged():
    fn = _render_fn_block()
    assert '"+"' in fn, "FAB label must remain the plain + glyph"
    assert "mob_bar_new" in SHELL and "border-radius: 50%" in SHELL.split("mob_bar_new", 1)[1][:1500], (
        "FAB circle styling must remain in mobile_shell.css"
    )
