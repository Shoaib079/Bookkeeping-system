"""Theme tokens and CSS injection — Phase 16A/16B."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_THEME_CSS_PATH = Path(__file__).with_name("theme.css")
_WIDGETS_CSS_PATH = Path(__file__).with_name("widgets.css")
_MOBILE_SHELL_CSS_PATH = Path(__file__).with_name("mobile_shell.css")
_MOBILE_TXN_CSS_PATH = Path(__file__).with_name("mobile_txn.css")
_MOBILE_REPORTS_CSS_PATH = Path(__file__).with_name("mobile_reports.css")
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
    "--hdr-bg": "#1E293B",
    "--theme-bg": "#0B1220",
    "--theme-card": "#0F1724",
    "--theme-border": "#1F2937",
    "--theme-text": "#E6EEF6",
    "--theme-muted": "#94A3B8",
    "--theme-success": "#10B981",
    "--theme-danger": "#F87171",
    "--theme-warning": "#F59E0B",
    "--theme-info": "#60A5FA",
    "--theme-purple": "#A78BFA",
    "--theme-teal": "#2DD4BF",
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
    )
    if _CSS_CACHE is None or _CSS_MTIME != mtime:
        base = _THEME_CSS_PATH.read_text(encoding="utf-8")
        widgets = _WIDGETS_CSS_PATH.read_text(encoding="utf-8")
        mobile = _MOBILE_SHELL_CSS_PATH.read_text(encoding="utf-8")
        mobile_txn = _MOBILE_TXN_CSS_PATH.read_text(encoding="utf-8")
        mobile_reports = _MOBILE_REPORTS_CSS_PATH.read_text(encoding="utf-8")
        _CSS_CACHE = f"{base}\n\n{widgets}\n\n{mobile}\n\n{mobile_txn}\n\n{mobile_reports}"
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


def inject_theme_css(dark_mode: bool) -> None:
    """Override :root for the user's saved light/dark preference."""
    vars_map = DARK_ROOT_VARS if dark_mode else LIGHT_ROOT_VARS
    st.markdown(f"<style>{_vars_to_css_block(vars_map)}</style>", unsafe_allow_html=True)


def role_accent_css_var(role: str | None) -> str:
    """CSS var for profile avatar background (16C: use in header HTML)."""
    key = ROLE_CSS_VARS.get((role or "").lower(), "--role-default")
    return f"var({key})"


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
