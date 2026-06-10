"""Theme tokens and CSS injection — Phase 16A/16B."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_THEME_CSS_PATH = Path(__file__).with_name("theme.css")
_WIDGETS_CSS_PATH = Path(__file__).with_name("widgets.css")
_MOBILE_SHELL_CSS_PATH = Path(__file__).with_name("mobile_shell.css")
_MOBILE_TXN_CSS_PATH = Path(__file__).with_name("mobile_txn.css")
_MOBILE_REPORTS_CSS_PATH = Path(__file__).with_name("mobile_reports.css")
_MOBILE_TXN_HISTORY_CSS_PATH = Path(__file__).with_name("mobile_txn_history.css")
_DESKTOP_TXN_HISTORY_CSS_PATH = Path(__file__).with_name("desktop_txn_history.css")
_SETUP01_WIZARD_CSS_PATH = Path(__file__).with_name("setup01_wizard.css")
_MOBILE_HEADER_CSS_PATH = Path(__file__).with_name("mobile_header.css")
_CSS_CACHE: str | None = None
_CSS_MTIME: float | None = None

# Injected after theme.css; wins over @media (prefers-color-scheme).
LIGHT_ROOT_VARS: dict[str, str] = {
    "--hdr-bg": "#EEF2F7",
    "--theme-bg": "#F8FAFC",
    "--theme-card": "#FFFFFF",
    "--theme-border": "#E6E9EE",
    "--theme-text": "#0F172A",
    "--theme-muted": "#475569",
    "--theme-caption": "#475569",
    "--theme-success": "#16A34A",
    "--theme-danger": "#DC2626",
    "--theme-warning": "#D97706",
    "--theme-info": "#2563EB",
    "--theme-purple": "#6D28D9",
    "--theme-teal": "#0EA5A4",
    "--theme-input-border": "#CBD5E1",
    "--theme-focus": "#2563EB",
    "--theme-banner-primary-start": "#1e3a8a",
    "--theme-banner-primary-end": "#2563eb",
    "--theme-shadow": "rgba(0,0,0,0.08)",
}

DARK_ROOT_VARS: dict[str, str] = {
    "--hdr-bg": "#1A2332",
    "--theme-bg": "#0B1220",
    "--theme-card": "#141C2B",
    "--theme-border": "#2D3A4D",
    "--theme-text": "#E8EDF4",
    "--theme-muted": "#9CA8B8",
    "--theme-caption": "#B8C4D0",
    "--theme-success": "#4ADE80",
    "--theme-danger": "#F87171",
    "--theme-warning": "#FBBF24",
    "--theme-info": "#3B82F6",
    "--theme-purple": "#8B5CF6",
    "--theme-teal": "#14B8A6",
    "--theme-input-border": "#334155",
    "--theme-focus": "#60A5FA",
    "--theme-banner-primary-start": "#1e3a8a",
    "--theme-banner-primary-end": "#3b82f6",
    "--theme-shadow": "rgba(0,0,0,0.35)",
}

ROLE_CSS_VARS: dict[str, str] = {
    "owner": "--role-owner",
    "manager": "--role-manager",
    "cashier": "--role-cashier",
    "partner": "--role-partner",
    "viewer": "--role-viewer",
}


def load_theme_css() -> str:
    global _CSS_CACHE, _CSS_MTIME
    mtime = max(
        _THEME_CSS_PATH.stat().st_mtime,
        _WIDGETS_CSS_PATH.stat().st_mtime,
        _MOBILE_SHELL_CSS_PATH.stat().st_mtime,
        _MOBILE_TXN_CSS_PATH.stat().st_mtime,
        _MOBILE_REPORTS_CSS_PATH.stat().st_mtime,
        _MOBILE_TXN_HISTORY_CSS_PATH.stat().st_mtime,
        _DESKTOP_TXN_HISTORY_CSS_PATH.stat().st_mtime,
        _SETUP01_WIZARD_CSS_PATH.stat().st_mtime,
        _MOBILE_HEADER_CSS_PATH.stat().st_mtime,
    )
    if _CSS_CACHE is None or _CSS_MTIME != mtime:
        base = _THEME_CSS_PATH.read_text(encoding="utf-8")
        widgets = _WIDGETS_CSS_PATH.read_text(encoding="utf-8")
        mobile = _MOBILE_SHELL_CSS_PATH.read_text(encoding="utf-8")
        mobile_header = _MOBILE_HEADER_CSS_PATH.read_text(encoding="utf-8")
        mobile_txn = _MOBILE_TXN_CSS_PATH.read_text(encoding="utf-8")
        mobile_reports = _MOBILE_REPORTS_CSS_PATH.read_text(encoding="utf-8")
        mobile_txn_history = _MOBILE_TXN_HISTORY_CSS_PATH.read_text(encoding="utf-8")
        desktop_txn_history = _DESKTOP_TXN_HISTORY_CSS_PATH.read_text(encoding="utf-8")
        setup01_wizard = _SETUP01_WIZARD_CSS_PATH.read_text(encoding="utf-8")
        _CSS_CACHE = (
            f"{base}\n\n{widgets}\n\n{mobile}\n\n{mobile_header}\n\n{mobile_txn}\n\n"
            f"{mobile_reports}\n\n{mobile_txn_history}\n\n{desktop_txn_history}\n\n"
            f"{setup01_wizard}"
        )
        _CSS_MTIME = mtime
    return _CSS_CACHE


def _vars_to_css_block(vars_map: dict[str, str]) -> str:
    body = "".join(f"{k}:{v};" for k, v in vars_map.items())
    return f":root{{{body}}}"


def render_global_style() -> None:
    """Inject base stylesheet (tokens + layout + legacy hex overrides)."""
    st.markdown(f"<style>{load_theme_css()}</style>", unsafe_allow_html=True)


def inject_mobile_viewport_detector() -> None:
    """Tag html.erp-mobile on phones (portrait + landscape) for shell CSS."""
    st.iframe(
        """
        <script>
        (function () {
          const w = window.top || window.parent;
          const root = w.document.documentElement;
          const frame = window.frameElement;
          if (frame) {
            frame.style.cssText =
              "position:fixed;width:0;height:0;border:0;opacity:0;pointer-events:none;overflow:hidden;";
          }
          function apply() {
            const vw = w.innerWidth;
            const vh = w.innerHeight;
            const coarse = w.matchMedia("(pointer: coarse)").matches;
            const touchTablet = coarse && vw <= 1366;
            const narrow = vw <= 968;
            const phoneLandscape = coarse && vh <= 520;
            const mobile = narrow || touchTablet || phoneLandscape;
            root.classList.toggle("erp-mobile", mobile);
            try {
              w.document.cookie =
                "erp_mobile_ui=" + (mobile ? "1" : "0") +
                ";path=/;max-age=3600;SameSite=Lax";
            } catch (e) {}
          }
          apply();
          w.addEventListener("resize", apply);
          w.addEventListener("orientationchange", apply);
        })();
        </script>
        """,
        height=1,
        width=1,
    )


_DARK_MONO_KPI_CSS = """
/* Dark mode: KPI amounts stay mono — status color reserved for void/danger actions */
.kpi-value.kpi-success,.kpi-value.kpi-danger,.kpi-value.kpi-warning,
.kpi-value.kpi-info,.kpi-value.kpi-purple,.kpi-value.kpi-teal {
  color: var(--theme-text) !important;
}
"""

def inject_theme_css(dark_mode: bool) -> None:
    """Override :root for the user's saved light/dark preference."""
    vars_map = DARK_ROOT_VARS if dark_mode else LIGHT_ROOT_VARS
    extra = _DARK_MONO_KPI_CSS if dark_mode else ""
    st.markdown(f"<style>{_vars_to_css_block(vars_map)}{extra}</style>", unsafe_allow_html=True)


def role_accent_css_var(role: str | None) -> str:
    """Mono profile avatar background — role shown in label text, not per-role color."""
    return "color-mix(in srgb, var(--theme-info) 16%, var(--theme-card) 84%)"


def _resolve_chart_dark(dark: bool | None = None) -> bool:
    """Resolve ERP chart palette: explicit light/dark, else session dark_mode (system → OS via CSS)."""
    if dark is not None:
        return dark
    mode = st.session_state.get("theme_mode", "system")
    if mode == "dark":
        return True
    if mode == "light":
        return False
    return bool(st.session_state.get("dark_mode", False))


def chart_theme_tokens(*, dark: bool | None = None) -> dict[str, str]:
    """ERP chart colours derived from LIGHT/DARK_ROOT_VARS (CHART-01)."""
    palette = DARK_ROOT_VARS if _resolve_chart_dark(dark) else LIGHT_ROOT_VARS
    return {
        "bg": palette["--theme-bg"],
        "card": palette["--theme-card"],
        "text": palette["--theme-text"],
        "muted": palette["--theme-muted"],
        "border": palette["--theme-border"],
        "info": palette["--theme-info"],
        "success": palette["--theme-success"],
        "warning": palette["--theme-warning"],
    }


def chart_accent_color(*, dark: bool | None = None) -> str:
    """Primary series colour — --theme-info."""
    return chart_theme_tokens(dark=dark)["info"]


def chart_palette(*, dark: bool | None = None) -> list[str]:
    """Mono-safe multi-series palette (max 4 series)."""
    tokens = chart_theme_tokens(dark=dark)
    return [tokens["info"], tokens["muted"], tokens["success"], tokens["warning"]]


def chart_series_color() -> str:
    """Neutral Altair series color aligned with --theme-muted."""
    return chart_theme_tokens()["muted"]


def chart_reference_color() -> str:
    """Neutral Altair reference/rule color aligned with --theme-border."""
    return chart_theme_tokens()["border"]


def apply_altair_theme(chart, *, dark: bool | None = None):
    """Apply ERP background, axis, title, and legend tokens to an Altair chart."""
    import altair as alt

    tokens = chart_theme_tokens(dark=dark)
    return chart.configure(
        background=tokens["card"],
        view=alt.ViewConfig(stroke=tokens["border"], fill=tokens["card"]),
        axis=alt.AxisConfig(
            labelColor=tokens["muted"],
            titleColor=tokens["text"],
            gridColor=tokens["border"],
            domainColor=tokens["border"],
            tickColor=tokens["border"],
        ),
        title=alt.TitleConfig(color=tokens["text"], anchor="start"),
        legend=alt.LegendConfig(labelColor=tokens["text"], titleColor=tokens["text"]),
    )


def render_themed_bar(
    df,
    x_col: str,
    y_col: str,
    *,
    x_type: str = "N",
    height: int = 300,
) -> None:
    """Single-series bar chart using ERP theme tokens."""
    import altair as alt

    chart = (
        alt.Chart(df)
        .mark_bar(color=chart_accent_color())
        .encode(
            x=alt.X(f"{x_col}:{x_type}", sort=None, title=None),
            y=alt.Y(f"{y_col}:Q", title=None),
            tooltip=[x_col, y_col],
        )
        .properties(height=height)
    )
    st.altair_chart(apply_altair_theme(chart), use_container_width=True)


def render_themed_grouped_bar(
    df,
    x_col: str,
    series_cols: list[str],
    *,
    height: int = 300,
) -> None:
    """Grouped bar chart from wide DataFrame columns."""
    import altair as alt

    df_long = df[[x_col, *series_cols]].melt(
        id_vars=[x_col], var_name="Series", value_name="Value"
    )
    palette = chart_palette()
    chart = (
        alt.Chart(df_long)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_col}:N", sort=None, title=None),
            y=alt.Y("Value:Q", title=None),
            color=alt.Color(
                "Series:N",
                scale=alt.Scale(range=palette),
                legend=alt.Legend(title=None),
            ),
            xOffset="Series:N",
            tooltip=[x_col, "Series:N", "Value:Q"],
        )
        .properties(height=height)
    )
    st.altair_chart(apply_altair_theme(chart), use_container_width=True)


def render_themed_line(
    df,
    x_col: str,
    y_cols: list[str],
    *,
    x_type: str = "N",
    height: int = 300,
) -> None:
    """Multi-series line chart using ERP palette."""
    import altair as alt

    df_long = df[[x_col, *y_cols]].melt(
        id_vars=[x_col], var_name="Series", value_name="Value"
    )
    palette = chart_palette()
    chart = (
        alt.Chart(df_long)
        .mark_line(point=True)
        .encode(
            x=alt.X(f"{x_col}:{x_type}", sort=None, title=None),
            y=alt.Y("Value:Q", title=None),
            color=alt.Color(
                "Series:N",
                scale=alt.Scale(range=palette[: len(y_cols)]),
                legend=alt.Legend(title=None),
            ),
            tooltip=[x_col, "Series:N", "Value:Q"],
        )
        .properties(height=height)
    )
    st.altair_chart(apply_altair_theme(chart), use_container_width=True)


def apply_user_theme_from_db(session, user_id: int) -> str | None:
    """Load theme preference into session; returns light | dark | system, or None."""
    from models import AppSetting

    row = session.get(AppSetting, f"user_pref_{user_id}_theme")
    if not row or not row.value:
        return None
    val = row.value.strip().lower()
    if val not in ("light", "dark", "system"):
        val = "light"
    st.session_state["theme_mode"] = val
    st.session_state["dark_mode"] = val == "dark"
    return val


def bootstrap_theme(session_factory, auth_user: dict | None) -> None:
    """Call once at start of main(): base CSS + DB theme + injection."""
    render_global_style()
    inject_mobile_viewport_detector()
    if auth_user and auth_user.get("id"):
        try:
            with session_factory() as session:
                if apply_user_theme_from_db(session, auth_user["id"]) is None:
                    st.session_state.setdefault("theme_mode", "system")
                    st.session_state.setdefault("dark_mode", False)
        except Exception:
            st.session_state.setdefault("theme_mode", "system")
            st.session_state.setdefault("dark_mode", False)
    else:
        st.session_state.setdefault("theme_mode", "system")
        st.session_state.setdefault("dark_mode", False)

    theme_mode = st.session_state.get("theme_mode", "system")
    if theme_mode != "system":
        inject_theme_css(bool(st.session_state.get("dark_mode", False)))
