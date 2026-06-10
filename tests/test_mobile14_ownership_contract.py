"""MOBILE-14 Phase 1 — CSS ownership contract tests (no CSS movement).

Contracts pin target ownership before M1–M6 dedupe. Tests marked xfail document
violations that remain in the codebase today; remove xfail when the matching
M-step lands.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "ui"

_HDR_H_APPROVED_OWNERS = frozenset({"theme.css", "mobile_header.css"})
_HDR_H_FORBIDDEN_DEFINITION_FILES = frozenset({
    "widgets.css",
    "mobile_shell.css",
    "mobile_txn.css",
    "mobile_reports.css",
})

# Post-M6 lock: mobile_shell.css is the sole sidebar-hide owner. Its two rules are
# intentional (viewport media rule + html.erp-mobile JS-detection fallback), not dupes.
_SIDEBAR_HIDE_BASELINE: dict[str, int] = {
    "theme.css": 0,
    "mobile_shell.css": 2,
}
_SIDEBAR_HIDE_TARGET_OWNER = "mobile_shell.css"

_HDR_H_DEF_RE = re.compile(r"(?<!/)--hdr-h\s*:")
_GRID_LAYOUT_RE = re.compile(
    r"grid-template-columns|(?:display\s*:\s*grid)",
    re.IGNORECASE,
)


def _read_css(filename: str) -> str:
    return (UI / filename).read_text(encoding="utf-8")


def _hdr_h_definition_lines(css: str) -> list[int]:
    """Line numbers where --hdr-h is assigned (not comment-only)."""
    lines: list[int] = []
    for i, line in enumerate(css.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("/*") or stripped.startswith("*"):
            continue
        if _HDR_H_DEF_RE.search(line):
            lines.append(i)
    return lines


def _selector_blocks_hiding_sidebar(css: str) -> int:
    """Count CSS rule blocks that hide [data-testid=\"stSidebar\"] on mobile."""
    return len(
        re.findall(
            r'\[data-testid="stSidebar"\][^{]*\{[^}]*display\s*:\s*none',
            css,
            flags=re.DOTALL | re.IGNORECASE,
        )
    )


def _widgets_layout_grids_for_key_prefix(prefix: str) -> list[str]:
    """Return matching selector snippets that pair a key prefix with grid layout."""
    widgets = _read_css("widgets.css")
    hits: list[str] = []
    for match in re.finditer(
        rf"st-key-{re.escape(prefix)}[\s\S]{{0,800}}?\}}",
        widgets,
        flags=re.IGNORECASE,
    ):
        block = match.group(0)
        if _GRID_LAYOUT_RE.search(block):
            snippet = block.split("{", 1)[0].strip().splitlines()[-1][:120]
            hits.append(snippet)
    return hits


def _widgets_mentions_any(patterns: tuple[str, ...]) -> list[str]:
    widgets = _read_css("widgets.css")
    return [p for p in patterns if p in widgets]


# ── 1. Header token ownership (--hdr-h) ─────────────────────────────────────


def test_mobile14_hdr_h_defined_in_approved_owners():
    """current-pass — --hdr-h definitions live in theme.css + mobile_header.css."""
    for filename in _HDR_H_APPROVED_OWNERS:
        lines = _hdr_h_definition_lines(_read_css(filename))
        assert lines, f"Expected --hdr-h definition in {filename}"


def test_mobile14_hdr_h_not_defined_in_forbidden_files():
    """current-pass — forbidden shells must not define --hdr-h (usage via var() is OK)."""
    violations: list[str] = []
    for filename in _HDR_H_FORBIDDEN_DEFINITION_FILES:
        lines = _hdr_h_definition_lines(_read_css(filename))
        if lines:
            violations.append(f"{filename}: lines {lines}")
    assert not violations, (
        "--hdr-h must only be defined in theme.css and mobile_header.css; found: "
        + "; ".join(violations)
    )


def test_mobile14_hdr_h_theme_dedup():
    """current-pass — theme.css: one desktop base + one mobile override definition max (M1)."""
    lines = _hdr_h_definition_lines(_read_css("theme.css"))
    assert len(lines) <= 2, f"theme.css defines --hdr-h {len(lines)}× (lines {lines})"


def test_mobile14_hdr_h_mobile_header_dedup():
    """current-pass — mobile_header.css: one base + one search-variant definition max (M1)."""
    lines = _hdr_h_definition_lines(_read_css("mobile_header.css"))
    assert len(lines) <= 2, f"mobile_header.css defines --hdr-h {len(lines)}× (lines {lines})"


def test_mobile14_m2_mobile_shell_no_block_container_padding_top():
    """current-pass — M2: dead E2 padding-top removed; mobile_header.css owns top inset."""
    shell = _read_css("mobile_shell.css")
    for block in re.findall(r"\.block-container\s*\{[^}]*\}", shell, flags=re.DOTALL | re.IGNORECASE):
        assert not re.search(r"padding-top\s*:", block, re.IGNORECASE), (
            "mobile_shell.css must not set block-container padding-top: "
            + block[:160]
        )
    header = _read_css("mobile_header.css")
    assert re.search(
        r"\.block-container[\s\S]{0,200}?padding-top\s*:",
        header,
        flags=re.IGNORECASE,
    ), "mobile_header.css must own mobile block-container padding-top"


# ── 2. Bottom nav / FAB / hub ownership ───────────────────────────────────────


def test_mobile14_bottom_nav_fab_hub_owned_by_mobile_shell():
    """current-pass — mobile_shell.css owns bottom bar, FAB, and hub sheet chrome."""
    shell = _read_css("mobile_shell.css")
    for needle in (
        "st-key-erp_mob_bottom_bar",
        "erp-mob-bar-cap-fab",
        "st-key-erp_mob_hub_sheet",
        "erp-mobile-hub-grab",
    ):
        assert needle in shell, f"Expected {needle!r} in mobile_shell.css"


@pytest.mark.xfail(
    strict=False,
    reason="MOBILE-14 M3 — bottom-nav/FAB/hub suppress rules still in widgets.css",
)
def test_mobile14_bottom_nav_fab_hub_not_in_widgets():
    """future-target — widgets.css must not reference bottom bar, FAB, or hub sheets."""
    patterns = (
        "erp_mob_bottom_bar",
        "erp_mob_hub_sheet",
        "erp-mobile-hub-host",
        "erp-mobile-hub-grab",
    )
    found = _widgets_mentions_any(patterns)
    assert not found, f"widgets.css still owns mobile chrome selectors: {found}"


# ── 3. Profile / company switch sheet ownership ─────────────────────────────


def test_mobile14_profile_coswitch_owned_by_mobile_shell():
    """current-pass — E13 sheet shell chrome lives in mobile_shell.css."""
    shell = _read_css("mobile_shell.css")
    for marker in (
        "/* E13 — mobile profile sheet",
        "/* E13 — mobile company switch sheet",
        "erp_mob_profile_sheet",
        "erp_mob_co_switch_sheet",
        "erp-mobile-profile-title",
        "erp-mobile-co-switch-title",
    ):
        assert marker in shell, f"Expected {marker!r} in mobile_shell.css"


@pytest.mark.xfail(
    strict=False,
    reason="MOBILE-14 M4 — profile/co-switch suppress selectors still in widgets.css",
)
def test_mobile14_profile_coswitch_not_in_widgets():
    """future-target — sheet selectors must not remain in widgets.css."""
    patterns = (
        "erp_mob_profile_sheet",
        "erp_mob_co_switch_sheet",
    )
    found = _widgets_mentions_any(patterns)
    assert not found, f"widgets.css still references sheet selectors: {found}"


# ── 4. KPI / dashboard ownership ────────────────────────────────────────────


def test_mobile14_kpi_dashboard_owned_by_theme():
    """current-pass — KPI grid + dashboard mobile layout rules live in theme.css."""
    theme = _read_css("theme.css")
    for needle in (
        ".erp-kpi-section",
        ".kpi-grid",
        "erp-dash-mobile-kpi-scroll",
    ):
        assert needle in theme, f"Expected {needle!r} in theme.css"


def test_mobile14_kpi_dashboard_not_in_widgets():
    """current-pass — M5: widgets.css must not own erp-kpi / kpi-grid / dashboard KPI layout."""
    widgets = _read_css("widgets.css")
    violations: list[str] = []
    if "erp-kpi" in widgets:
        violations.append("erp-kpi")
    if "kpi-grid" in widgets:
        violations.append("kpi-grid")
    if "erp-dash-mobile-kpi" in widgets:
        violations.append("erp-dash-mobile-kpi")
    assert not violations, f"widgets.css still owns dashboard KPI rules: {violations}"


# ── 5. Sidebar hide ownership ───────────────────────────────────────────────


def test_mobile14_sidebar_hide_rule_count_documented():
    """post-M6 lock — mobile_shell.css owns both intentional hide rules; theme.css owns none."""
    counts = {
        "theme.css": _selector_blocks_hiding_sidebar(_read_css("theme.css")),
        "mobile_shell.css": _selector_blocks_hiding_sidebar(_read_css("mobile_shell.css")),
    }
    assert counts == _SIDEBAR_HIDE_BASELINE, (
        "Sidebar hide ownership changed after M6 — both mobile_shell.css rules are "
        "intentional (media rule + html.erp-mobile fallback); theme.css must own none: "
        f"got {counts}, expected {_SIDEBAR_HIDE_BASELINE}"
    )


def test_mobile14_sidebar_hide_single_owner():
    """post-M6 lock — only mobile_shell.css hides the mobile sidebar."""
    counts = {
        filename: _selector_blocks_hiding_sidebar(_read_css(filename))
        for filename in ("theme.css", "mobile_shell.css", "widgets.css")
    }
    non_target = {
        f: n for f, n in counts.items()
        if f != _SIDEBAR_HIDE_TARGET_OWNER and n > 0
    }
    assert not non_target, (
        f"Sidebar hide must be owned only by {_SIDEBAR_HIDE_TARGET_OWNER!r}; "
        f"other files still hide: {non_target}"
    )
    assert counts[_SIDEBAR_HIDE_TARGET_OWNER] >= 1


# ── 6. Transaction surface layout grids (regression guard E4–E6) ────────────


def test_mobile14_widgets_no_mob_at_mob_rpt_layout_grids():
    """current-pass — mob_at_ / mob_rpt_ column grids moved to mobile_txn / mobile_reports."""
    for prefix in ("mob_at_", "mob_rpt_"):
        hits = _widgets_layout_grids_for_key_prefix(prefix)
        assert not hits, (
            f"widgets.css must not own {prefix} layout grids; found: {hits}"
        )


def test_mobile14_widgets_no_txh_layout_grids():
    """current-pass — TXH micro-step: txh_ column grids owned by mobile_txn_history.css only."""
    hits = _widgets_layout_grids_for_key_prefix("txh_")
    assert not hits, f"widgets.css must not own txh_ layout grids; found: {hits}"


# ── 7. Notification rules — permanent two-owner contract (M6 closed) ─────────


def test_mobile14_notification_rule_liveness_pin():
    """permanent two-owner contract — M6 re-audit confirmed BOTH copies are live.

    widgets.css owns the legacy desktop toolbar rules (`hdr_toolbar_row` is still
    rendered by app.py's `_legacy_desktop` slot); mobile_header.css owns the mobile
    slot copies; theme.css owns the shared NOTIF-THEME-01 tokens. This is a valid
    desktop/mobile split along the same boundary the rest of the codebase uses —
    neither copy may be deleted.
    """
    pins = {
        "widgets.css": (
            "NOTIF-THEME-01",
            "erp-hdr-notif-active",
            "st-key-hdr_notif_pop",
        ),
        "mobile_header.css": (
            "erp-hdr-notif-active",
            "st-key-hdr_notif_pop",
        ),
        "theme.css": (
            "NOTIF-THEME-01",
            "erp-hdr-notif-active",
        ),
    }
    missing: list[str] = []
    for filename, needles in pins.items():
        css = _read_css(filename)
        for needle in needles:
            if needle not in css:
                missing.append(f"{filename}: {needle}")
    assert not missing, (
        "Notification liveness pin failed — do not delete rules before M6 audit: "
        + "; ".join(missing)
    )
