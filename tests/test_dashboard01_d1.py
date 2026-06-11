"""DASHBOARD-01 D1 + D2 — dashboard surface contracts."""
from __future__ import annotations

import inspect
from pathlib import Path

import app as erp

ROOT = Path(__file__).resolve().parents[1]


def _read_css(name: str) -> str:
    return (ROOT / "ui" / name).read_text(encoding="utf-8")


def _dashboard_src() -> str:
    return inspect.getsource(erp.render_dashboard)


def test_dashboard_no_legacy_gradient_welcome_banner():
    src = _dashboard_src()
    assert "banner banner-primary" not in src
    assert "banner-primary" not in src


def test_dashboard_welcome_uses_flat_card_class():
    src = _dashboard_src()
    assert "erp-dash-welcome-card" in src
    theme = _read_css("theme.css")
    assert ".erp-dash-welcome-card" in theme
    assert "linear-gradient" not in theme.split(".erp-dash-welcome-card")[1].split("/*")[0]
    assert "var(--theme-card)" in theme.split(".erp-dash-welcome-card")[1].split(".erp-dash-welcome-hi")[0]
    assert "var(--theme-border)" in theme.split(".erp-dash-welcome-card")[1].split(".erp-dash-welcome-hi")[0]


def test_dashboard_no_inline_styles_d2():
    src = _dashboard_src()
    assert 'style="' not in src
    assert "style='" not in src


def test_dashboard_named_alert_card_not_inline_border():
    src = _dashboard_src()
    assert "erp-dash-alert-card" in src
    assert "border-left:3px" not in src
    assert 'class="card"' not in src
    theme = _read_css("theme.css")
    assert ".erp-dash-alert-card" in theme


def test_dashboard_semantic_classes_in_theme_css():
    theme = _read_css("theme.css")
    for cls in (
        ".erp-dash-pct--up",
        ".erp-dash-status-row",
        ".erp-dash-cash-row",
        ".erp-dash-activity-row",
        ".erp-dash-insight-row",
        ".erp-dash-expense-bar-row",
        "DASHBOARD-01 D2",
    ):
        assert cls in theme, f"missing {cls!r} in theme.css"


def test_render_kpi_grid_variant_only_no_color_escape():
    src = inspect.getsource(erp.render_kpi_grid)
    assert 'it.get("color"' not in src
    assert 'style="color:' not in src
    assert "_KPI_VARIANTS" in inspect.getsource(erp)
    assert "kpi-muted" in _read_css("theme.css")


def test_theme_contrast_suite_still_importable():
    from tests import test_theme_contrast  # noqa: F401
