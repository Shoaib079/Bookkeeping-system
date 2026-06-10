"""Mobile layout contract — keyed st.columns rows must have CSS grid rules."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Exact Streamlit keys used with st.columns on mobile-critical surfaces.
# Concept C (MOB-AT-C1): mob_at_tabs and mob_at_pm3 replaced by mob_at_row1;
# mob_at_c_cat_row and mob_at_save_row added.
_MOBILE_COLUMN_ROW_KEYS = frozenset({
    "erp_mob_bottom_bar",
    "erp_mob_quick_create",
    "mob_at_amount_row",
    # Concept C Row 1 (replaces mob_at_tabs)
    "mob_at_row1",
    # Concept C category row (replaces inline mob_at_cat_trigger in main panel)
    "mob_at_c_cat_row",
    # Concept C full-width Save row (replaces side-column Save in fragment)
    "mob_at_save_row",
    # mob_at_pm2 still used for Bank Transaction subtype buttons
    "mob_at_pm2",
    # mob_at_cat_trigger still defined in _mob_at_render_category_trigger (used by pickers)
    "mob_at_cat_trigger",
    "mob_at_subcat_trigger",
    "mob_at_vendor_trigger",
    "mob_at_picker_hdr",
    "mob_at_picker_grid",
    "mob_at_keypad",
    "mob_hub_hdr",
    "erp_mob_rpt_filters",
    "mob_at_topbar",
    "mob_rpt_cf_kpi",
    "txh_filter_row1",
    "txh_filter_row2",
    "txh_result_hdr",
    "hdr_shell_inner",
})

# Prefixes for dynamic keys (mob_rpt_sel_rpt_exec_sel, txh_actions_Sale_1, …).
_MOBILE_COLUMN_ROW_PREFIXES = (
    "mob_rpt_sel_",
    "txh_actions_",
)

_CSS_FILES = (
    ROOT / "ui" / "mobile_shell.css",
    ROOT / "ui" / "mobile_txn.css",
    ROOT / "ui" / "mobile_txn_history.css",
    ROOT / "ui" / "mobile_reports.css",
    ROOT / "ui" / "widgets.css",
    ROOT / "ui" / "theme.css",
)


def _css_blob() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in _CSS_FILES if p.exists())


def test_mobile_column_row_keys_documented():
    """Every keyed mobile row in this set should stay in sync with app.py usage."""
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    for key in _MOBILE_COLUMN_ROW_KEYS:
        assert f'key="{key}"' in app_src or f"key='{key}'" in app_src, (
            f"Contract key {key!r} missing from app.py — update contract or restore widget"
        )


def test_mobile_column_row_prefixes_used():
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    for prefix in _MOBILE_COLUMN_ROW_PREFIXES:
        assert f'key="{prefix}' in app_src or f"f\"{prefix}" in app_src or f"f'{prefix}" in app_src, (
            f"Expected dynamic key prefix {prefix!r} in app.py"
        )


def test_mobile_column_rows_have_grid_css():
    """Each keyed row must have stHorizontalBlock + grid in mobile CSS."""
    css = _css_blob()
    missing = []
    for key in _MOBILE_COLUMN_ROW_KEYS:
        if key == "hdr_shell_inner":
            needle = "st-key-hdr_shell_inner"
        else:
            needle = f"st-key-{key}"
        block = re.search(
            rf"{re.escape(needle)}[^\{{]*\{{[^}}]*stHorizontalBlock",
            css,
        )
        layout_near = re.search(
            rf"{re.escape(needle)}[\s\S]{{0,1200}}?(?:grid-template-columns|flex-direction:\s*row)",
            css,
        )
        if not block and not layout_near:
            missing.append(key)
    for prefix in _MOBILE_COLUMN_ROW_PREFIXES:
        if not re.search(
            rf"st-key-{re.escape(prefix)}[\s\S]{{0,1200}}?grid-template-columns",
            css,
        ):
            missing.append(f"{prefix}*")
    assert not missing, f"Missing mobile grid CSS for: {', '.join(missing)}"


def test_no_html_module_shadowing_in_app():
    """Avoid `html = ...` locals in app.py (shadows import html → UnboundLocalError)."""
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    offenders = []
    for i, line in enumerate(app_src.splitlines(), 1):
        if re.match(r"\s+html\s*=", line):
            offenders.append(i)
    assert not offenders, f"app.py assigns local `html` at lines: {offenders}"
