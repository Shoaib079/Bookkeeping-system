"""VIEWPORT-SYNC-01 — JS mobile detector and CSS @media threshold agreement."""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import app as erp
from ui import theme

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "ui"

_MEDIA_OPENER_RE = re.compile(
    r"@media\s*\(max-width:\s*968px\)[\s\S]*?\)\s*\{",
    re.MULTILINE,
)


def _normalize_media_opener(opener: str) -> str:
    return re.sub(r"\s+", " ", opener.strip())


def _canonical_opener() -> str:
    arms = ", ".join(theme.MOBILE_VIEWPORT_MEDIA_QUERY_ARMS)
    return _normalize_media_opener(f"@media {arms} {{")


def _extract_mobile_media_openers(css: str) -> list[str]:
    return [_normalize_media_opener(m.group(0)) for m in _MEDIA_OPENER_RE.finditer(css)]


def test_js_detector_thresholds_match_theme_constants():
    src = inspect.getsource(theme.inject_mobile_viewport_detector)
    assert f"vw <= {theme.MOBILE_VIEWPORT_NARROW_MAX_PX}" in src
    assert f"vw <= {theme.MOBILE_VIEWPORT_TOUCH_TABLET_MAX_PX}" in src
    assert f"vh <= {theme.MOBILE_VIEWPORT_PHONE_LANDSCAPE_MAX_PX}" in src
    assert "touchTablet = coarse && vw <=" in src
    assert "phoneLandscape = coarse && vh <=" in src


def test_css_touch_tablet_arm_matches_js_1366_not_1024():
    canonical = _canonical_opener()
    assert "1366px" in canonical
    assert "1024px" not in canonical
    for filename in theme.MOBILE_VIEWPORT_CSS_OWNER_FILES:
        css = (UI / filename).read_text(encoding="utf-8")
        assert "((max-width: 1024px)" not in css, f"stale 1024px arm in {filename}"
        openers = _extract_mobile_media_openers(css)
        assert openers, f"no mobile @media opener in {filename}"
        for opener in openers:
            assert "1366px" in opener, f"{filename} missing 1366px touch-tablet arm"


def test_mobile_css_files_use_identical_media_header():
    canonical = _canonical_opener()
    seen: dict[str, list[str]] = {}
    for filename in theme.MOBILE_VIEWPORT_CSS_OWNER_FILES:
        css = (UI / filename).read_text(encoding="utf-8")
        openers = _extract_mobile_media_openers(css)
        seen[filename] = openers
        for opener in openers:
            assert opener == canonical, (
                f"{filename} media opener drift:\n  got:  {opener}\n  want: {canonical}"
            )


def test_viewport_sync_owner_file_list_covers_mobile_layers():
    for name in (
        "mobile_shell.css",
        "mobile_txn.css",
        "mobile_header.css",
        "mobile_reports.css",
        "mobile_txn_history.css",
        "widgets.css",
    ):
        assert name in theme.MOBILE_VIEWPORT_CSS_OWNER_FILES


def test_ua_cookie_hint_pinned_in_detector_and_sync():
    detector = inspect.getsource(theme.inject_mobile_viewport_detector)
    assert 'erp_mobile_ui=' in detector
    assert "erp_mobile_ui" in inspect.getsource(erp._sync_mobile_ui_flag_from_cookie)
