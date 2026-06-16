"""Theme tokens and CSS injection — Phase 16A/16B."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import streamlit as st

_log = logging.getLogger(__name__)

_THEME_CSS_PATH = Path(__file__).with_name("theme.css")
_WIDGETS_CSS_PATH = Path(__file__).with_name("widgets.css")
_MOBILE_COMPONENTS_CSS_PATH = Path(__file__).with_name("mobile_components.css")
_MOBILE_SHELL_CSS_PATH = Path(__file__).with_name("mobile_shell.css")
_MOBILE_TXN_CSS_PATH = Path(__file__).with_name("mobile_txn.css")
_MOBILE_REPORTS_CSS_PATH = Path(__file__).with_name("mobile_reports.css")
_MOBILE_TXN_HISTORY_CSS_PATH = Path(__file__).with_name("mobile_txn_history.css")
_DESKTOP_TXN_HISTORY_CSS_PATH = Path(__file__).with_name("desktop_txn_history.css")
_DESKTOP_REPORTS_CSS_PATH = Path(__file__).with_name("desktop_reports.css")
_BANKING_CSS_PATH = Path(__file__).with_name("banking.css")
_SETUP01_WIZARD_CSS_PATH = Path(__file__).with_name("setup01_wizard.css")
_MOBILE_HEADER_CSS_PATH = Path(__file__).with_name("mobile_header.css")
_AUTH_CSS_PATH = Path(__file__).with_name("auth.css")
_ICONS_CSS_PATH = Path(__file__).with_name("icons.css")
_CSS_CACHE: str | None = None
_CSS_MTIME: float | None = None

# VIEWPORT-SYNC-01 — mobile boundaries (must match @media in mobile_*.css + widgets.css)
MOBILE_VIEWPORT_NARROW_MAX_PX = 968
MOBILE_VIEWPORT_TOUCH_TABLET_MAX_PX = 1366
MOBILE_VIEWPORT_PHONE_LANDSCAPE_MAX_PX = 520
MOBILE_VIEWPORT_MEDIA_QUERY_ARMS: tuple[str, ...] = (
    "(max-width: 968px)",
    "((max-width: 1366px) and (hover: none) and (pointer: coarse))",
    "((max-height: 520px) and (hover: none) and (pointer: coarse))",
)
MOBILE_VIEWPORT_CSS_OWNER_FILES: tuple[str, ...] = (
    "mobile_shell.css",
    "mobile_txn.css",
    "mobile_header.css",
    "mobile_reports.css",
    "mobile_txn_history.css",
    "widgets.css",
)

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
    "--erp-primary-fill": "#2563EB",
    "--erp-primary-fill-hover": "#1D4ED8",
    "--theme-success-text": "#15803D",
    "--theme-warning-text": "#B45309",
    "--theme-danger-text": "#B91C1C",
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
    "--erp-primary-fill": "#2563EB",
    "--erp-primary-fill-hover": "#1D4ED8",
    "--theme-success-text": "#4ADE80",
    "--theme-warning-text": "#FBBF24",
    "--theme-danger-text": "#F87171",
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
        _MOBILE_COMPONENTS_CSS_PATH.stat().st_mtime,
        _MOBILE_SHELL_CSS_PATH.stat().st_mtime,
        _MOBILE_TXN_CSS_PATH.stat().st_mtime,
        _MOBILE_REPORTS_CSS_PATH.stat().st_mtime,
        _MOBILE_TXN_HISTORY_CSS_PATH.stat().st_mtime,
        _DESKTOP_TXN_HISTORY_CSS_PATH.stat().st_mtime,
        _DESKTOP_REPORTS_CSS_PATH.stat().st_mtime,
        _BANKING_CSS_PATH.stat().st_mtime,
        _SETUP01_WIZARD_CSS_PATH.stat().st_mtime,
        _MOBILE_HEADER_CSS_PATH.stat().st_mtime,
        _AUTH_CSS_PATH.stat().st_mtime,
        _ICONS_CSS_PATH.stat().st_mtime,
    )
    if _CSS_CACHE is None or _CSS_MTIME != mtime:
        base = _THEME_CSS_PATH.read_text(encoding="utf-8")
        widgets = _WIDGETS_CSS_PATH.read_text(encoding="utf-8")
        mobile_components = _MOBILE_COMPONENTS_CSS_PATH.read_text(encoding="utf-8")
        mobile = _MOBILE_SHELL_CSS_PATH.read_text(encoding="utf-8")
        mobile_header = _MOBILE_HEADER_CSS_PATH.read_text(encoding="utf-8")
        auth = _AUTH_CSS_PATH.read_text(encoding="utf-8")
        mobile_txn = _MOBILE_TXN_CSS_PATH.read_text(encoding="utf-8")
        mobile_reports = _MOBILE_REPORTS_CSS_PATH.read_text(encoding="utf-8")
        mobile_txn_history = _MOBILE_TXN_HISTORY_CSS_PATH.read_text(encoding="utf-8")
        desktop_txn_history = _DESKTOP_TXN_HISTORY_CSS_PATH.read_text(encoding="utf-8")
        desktop_reports = _DESKTOP_REPORTS_CSS_PATH.read_text(encoding="utf-8")
        banking = _BANKING_CSS_PATH.read_text(encoding="utf-8")
        setup01_wizard = _SETUP01_WIZARD_CSS_PATH.read_text(encoding="utf-8")
        icons = _ICONS_CSS_PATH.read_text(encoding="utf-8")
        _CSS_CACHE = (
            f"{base}\n\n{widgets}\n\n{mobile_components}\n\n{mobile}\n\n{mobile_header}\n\n{auth}\n\n{mobile_txn}\n\n"
            f"{mobile_reports}\n\n{mobile_txn_history}\n\n{desktop_txn_history}\n\n"
            f"{desktop_reports}\n\n{banking}\n\n{setup01_wizard}\n\n{icons}"
        )
        _CSS_MTIME = mtime
    return _CSS_CACHE


def _vars_to_css_block(vars_map: dict[str, str]) -> str:
    body = "".join(f"{k}:{v};" for k, v in vars_map.items())
    return f":root{{{body}}}"


def _strip_first_root_block(css: str) -> str:
    """Remove the leading :root{} block from theme.css (first in the bundle)."""
    s = css.lstrip()
    if not s.startswith(":root"):
        return css
    brace = s.find("{")
    if brace < 0:
        return css
    depth = 0
    for i in range(brace, len(s)):
        ch = s[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1 :].lstrip()
    return css


def _resolve_bootstrap_root_css(theme_mode: str) -> tuple[str, str]:
    """Resolved :root prefix for the first style bundle (THEME-FLASH-01)."""
    if theme_mode == "light":
        return _vars_to_css_block(LIGHT_ROOT_VARS), ""
    if theme_mode == "dark":
        return _vars_to_css_block(DARK_ROOT_VARS), _DARK_MONO_KPI_CSS
    os_inject = _system_theme_injection_dark()
    if os_inject is None:
        return "", ""
    vars_map = DARK_ROOT_VARS if os_inject else LIGHT_ROOT_VARS
    extra = _DARK_MONO_KPI_CSS if os_inject else ""
    return _vars_to_css_block(vars_map), extra


def _theme_authority_script(theme_mode: str) -> str:
    """Synchronous script stamping html[data-erp-theme] before CSS parses."""
    safe = theme_mode if theme_mode in ("light", "dark", "system") else "system"
    mode_js = json.dumps(safe)
    return (
        f"""<script>
        (function() {{
          const root = (window.top || window.parent).document.documentElement;
          root.setAttribute("data-erp-theme", {mode_js});
        }})();
        </script>"""
    )


def _inject_style_html(css: str) -> None:
    """Inject CSS via st.html — style-only blocks go to the event container (Streamlit 1.58+)."""
    st.html(f"<style>{css}</style>")


def render_global_style(
    *,
    root_prefix: str = "",
    extra_css: str = "",
    theme_mode: str | None = None,
) -> None:
    """Inject base stylesheet (tokens + layout + legacy hex overrides)."""
    css = load_theme_css()
    if root_prefix:
        css = root_prefix + "\n" + _strip_first_root_block(css)
    if extra_css:
        css = css + "\n" + extra_css
    if theme_mode:
        st.html(_theme_authority_script(theme_mode), unsafe_allow_javascript=True)
    _inject_style_html(css)


def inject_mobile_viewport_detector() -> None:
    """Tag html.erp-mobile on phones/tablets (portrait + landscape) for shell CSS.

    Boundaries must stay aligned with MOBILE_VIEWPORT_MEDIA_QUERY_ARMS / mobile CSS @media.
    """
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
            const osDark = w.matchMedia("(prefers-color-scheme: dark)").matches;
            root.setAttribute("data-erp-os-dark", osDark ? "1" : "0");
            try {
              w.document.cookie =
                "erp_mobile_ui=" + (mobile ? "1" : "0") +
                ";path=/;max-age=3600;SameSite=Lax";
              w.document.cookie =
                "erp_os_dark=" + (osDark ? "1" : "0") +
                ";path=/;max-age=3600;SameSite=Lax";
            } catch (e) {}
          }
          apply();
          w.addEventListener("resize", apply);
          w.addEventListener("orientationchange", apply);
          w.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", apply);
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
    _inject_style_html(f"{_vars_to_css_block(vars_map)}{extra}")


def role_accent_css_var(role: str | None) -> str:
    """Mono profile avatar background — role shown in label text, not per-role color."""
    return "color-mix(in srgb, var(--theme-info) 16%, var(--theme-card) 84%)"


def _os_dark_from_client_hint() -> bool | None:
    """First-request fallback when the viewport cookie is not on the wire yet."""
    try:
        hint = (st.context.headers.get("Sec-CH-Prefers-Color-Scheme") or "").strip().lower()
    except (AttributeError, TypeError):
        return None
    if hint == "dark":
        return True
    if hint == "light":
        return False
    return None


def _os_dark_preferred_signal() -> bool | None:
    """OS scheme from cookie or client hint only (no session guesses)."""
    try:
        cookie = str(st.context.cookies.get("erp_os_dark") or "").strip()
    except (AttributeError, TypeError):
        cookie = ""
    if cookie == "1":
        return True
    if cookie == "0":
        return False
    return _os_dark_from_client_hint()


def get_theme_mode() -> str:
    """User theme preference: light | dark | system (THEME-AUTHORITY-01)."""
    mode = st.session_state.get("theme_mode", "system")
    return mode if mode in ("light", "dark", "system") else "system"


def _system_theme_injection_dark() -> bool | None:
    """Known OS scheme for system-mode CSS injection; None → @media only."""
    signal = _os_dark_preferred_signal()
    if signal is not None:
        return signal
    prev = st.session_state.get("_erp_os_dark_from_cookie")
    if isinstance(prev, bool):
        return prev
    return None


def sync_os_dark_flag_from_cookie() -> bool:
    """Mirror OS scheme for system mode only (charts + server hints).

    Explicit light/dark ignore erp_os_dark cookie and sticky OS session.
    Order (system only): erp_os_dark cookie → Sec-CH hint → sticky session → light default.
    """
    mode = get_theme_mode()
    if mode == "light":
        st.session_state["_erp_os_dark"] = False
        return False
    if mode == "dark":
        st.session_state["_erp_os_dark"] = True
        return True
    signal = _os_dark_preferred_signal()
    if signal is not None:
        st.session_state["_erp_os_dark_from_cookie"] = signal
        flag = signal
    elif isinstance(st.session_state.get("_erp_os_dark_from_cookie"), bool):
        flag = st.session_state["_erp_os_dark_from_cookie"]
    else:
        flag = False
    st.session_state["_erp_os_dark"] = flag
    return flag


def resolve_effective_dark(*, dark: bool | None = None) -> bool:
    """Single authority: is the effective visual theme dark right now?"""
    if dark is not None:
        return dark
    mode = get_theme_mode()
    if mode == "light":
        return False
    if mode == "dark":
        return True
    return sync_os_dark_flag_from_cookie()


def _resolve_chart_dark(dark: bool | None = None) -> bool:
    """Chart palette resolver — delegates to resolve_effective_dark."""
    return resolve_effective_dark(dark=dark)


def sync_derived_dark_mode() -> bool:
    """Keep st.session_state['dark_mode'] as a derived mirror of the authoritative theme mode.

    dark_mode must not be used as theme authority.
    """
    mode = get_theme_mode()
    if mode == "light":
        effective_dark = False
    elif mode == "dark":
        effective_dark = True
    else:
        effective_dark = bool(resolve_effective_dark())
    st.session_state["dark_mode"] = bool(effective_dark)
    return bool(effective_dark)


def inject_theme_authority_marker(theme_mode: str) -> None:
    """Stamp html[data-erp-theme] so CSS @media cannot override explicit prefs."""
    st.markdown(_theme_authority_script(theme_mode), unsafe_allow_html=True)


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
    """Apply ERP axis/title/legend tokens; background transparent (card shell in CSS)."""
    import altair as alt

    tokens = chart_theme_tokens(dark=dark)
    return chart.configure(
        background="transparent",
        view=alt.ViewConfig(stroke=tokens["border"], fill="transparent"),
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

    chart_dark = _resolve_chart_dark()
    chart = (
        alt.Chart(df)
        .mark_bar(color=chart_accent_color(dark=chart_dark))
        .encode(
            x=alt.X(f"{x_col}:{x_type}", sort=None, title=None),
            y=alt.Y(f"{y_col}:Q", title=None),
            tooltip=[x_col, y_col],
        )
        .properties(height=height)
    )
    st.altair_chart(apply_altair_theme(chart, dark=chart_dark), use_container_width=True)


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
    chart_dark = _resolve_chart_dark()
    palette = chart_palette(dark=chart_dark)
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
    st.altair_chart(apply_altair_theme(chart, dark=chart_dark), use_container_width=True)


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
    chart_dark = _resolve_chart_dark()
    palette = chart_palette(dark=chart_dark)
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
    st.altair_chart(apply_altair_theme(chart, dark=chart_dark), use_container_width=True)


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
    sync_derived_dark_mode()
    return val


def bootstrap_theme(session_factory, auth_user: dict | None) -> None:
    """Call once at start of main(): base CSS + DB theme + injection (THEME-AUTHORITY-01)."""
    if auth_user and auth_user.get("id"):
        try:
            with session_factory() as session:
                if apply_user_theme_from_db(session, auth_user["id"]) is None:
                    st.session_state.setdefault("theme_mode", "system")
        except Exception:
            _log.debug("bootstrap_theme: failed to load user theme", exc_info=True)
            st.session_state.setdefault("theme_mode", "system")
    else:
        st.session_state.setdefault("theme_mode", "system")

    sync_derived_dark_mode()
    theme_mode = get_theme_mode()
    root_prefix, mono_extra = _resolve_bootstrap_root_css(theme_mode)
    render_global_style(
        root_prefix=root_prefix,
        extra_css=mono_extra,
        theme_mode=theme_mode,
    )
    inject_mobile_viewport_detector()
    sync_os_dark_flag_from_cookie()


__all__ = (
    "apply_altair_theme",
    "apply_user_theme_from_db",
    "bootstrap_theme",
    "chart_accent_color",
    "chart_palette",
    "chart_reference_color",
    "chart_series_color",
    "chart_theme_tokens",
    "get_theme_mode",
    "inject_theme_css",
    "load_theme_css",
    "render_global_style",
    "render_themed_bar",
    "render_themed_grouped_bar",
    "render_themed_line",
    "resolve_effective_dark",
    "role_accent_css_var",
    "sync_derived_dark_mode",
    "sync_os_dark_flag_from_cookie",
)
