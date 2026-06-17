"""UI-SYSTEM-02-S5 — frozen React design contract (tokens + components).

Machine-readable mirror of ``docs/UI_SYSTEM_02_REACT_DESIGN_CONTRACT.md``.
No runtime UI change — governs FastAPI/React migration and deprecates
Streamlit-only CSS selector patterns for the React port.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ui import section as section_module
from ui.design_tokens import (
    CARD_GRAMMAR_TOKEN_KEYS,
    CHIP_GRAMMAR_EXTENSION_KEYS,
    CHIP_TOKEN_KEYS,
    COMPONENT_GRAMMAR_TOKENS,
    DEPRECATED_ROLE_TOKEN_KEYS,
    LAYOUT_TOKENS,
    MOBILE_HEADER_LAYOUT_TOKENS,
    NAV_GRAMMAR_TOKEN_KEYS,
    RADIUS_TOKENS,
    SHADOW_TOKENS,
    SPACING_TOKENS,
    TABLE_GRAMMAR_TOKEN_KEYS,
    TYPOGRAPHY_TOKENS,
    build_dark_root_vars,
    build_light_root_vars,
    grammar_values_reference_only,
)

GRAMMAR_CONTRACT_VERSION: Final[str] = "MONO-THEME-01-S7"

CONTRACT_DOC = "docs/UI_SYSTEM_02_REACT_DESIGN_CONTRACT.md"


@dataclass(frozen=True)
class PropSpec:
    name: str
    type: str
    required: bool = True
    default: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class ReactComponentSpec:
    name: str
    streamlit_source: str
    css_classes: tuple[str, ...]
    props: tuple[PropSpec, ...]
    ds04_ref: str = ""
    streamlit_only: bool = False


@dataclass(frozen=True)
class StreamlitOnlySelector:
    """CSS/DOM pattern that must not be copied into the React SPA."""

    selector_id: str
    pattern: str
    reason: str
    react_replacement: str


# ── Portable components (section.py + shared CSS) ─────────────────────────────

_PORTABLE: tuple[ReactComponentSpec, ...] = (
    ReactComponentSpec(
        "SectionHeader",
        "section_header_html",
        ("erp-section-hdr",),
        (
            PropSpec("title", "string"),
            PropSpec("accent", "'info' | 'success' | 'warning' | 'danger'", False, "info"),
        ),
        "ERP_DS_04 §1",
    ),
    ReactComponentSpec(
        "PageBanner",
        "page_report_banner_html",
        ("erp-page-banner",),
        (
            PropSpec("title", "string"),
            PropSpec("subtitle", "string", False, ""),
            PropSpec("variant", "'primary' | 'neutral'", False, "primary"),
        ),
        "ERP_DS_04 §1",
    ),
    ReactComponentSpec(
        "FinSectionHeader",
        "financial_section_header_html",
        ("erp-fin-section-hdr",),
        (
            PropSpec("title", "string"),
            PropSpec("total", "string", False, ""),
            PropSpec("accent", "string", False, "info"),
        ),
        "ERP_DS_04 §1",
    ),
    ReactComponentSpec(
        "FinTable",
        "financial_statement_table_html",
        ("erp-fin-table",),
        (
            PropSpec("columns", "FinColumn[]"),
            PropSpec("rows", "Record<string, unknown>[]"),
            PropSpec("currency", "string", False, ""),
        ),
        "ERP_DS_04 §5.2",
    ),
    ReactComponentSpec(
        "DataTable",
        "readable_dataframe_table_html",
        ("erp-data-table",),
        (
            PropSpec("columns", "string[]"),
            PropSpec("rows", "Record<string, unknown>[]"),
        ),
        "ERP_DS_04 §5",
    ),
    ReactComponentSpec(
        "KpiChip",
        "mobile_kpi_chip_html",
        ("erp-mob-kpi-chip", "erp-mob-kpi-label", "erp-mob-kpi-value"),
        (
            PropSpec("label", "string"),
            PropSpec("value", "string"),
            PropSpec(
                "variant",
                "'success' | 'danger' | 'info' | 'warning' | 'neutral' | ''",
                False,
                "",
            ),
        ),
        "ERP_DS_04 §5.1",
    ),
    ReactComponentSpec(
        "KpiGrid",
        "mobile_kpi_grid_html",
        ("erp-mob-kpi-grid",),
        (
            PropSpec("children", "ReactNode[]"),
            PropSpec(
                "modifier",
                "string",
                False,
                "",
                "BEM modifier e.g. reports-cf → erp-mob-kpi-grid--reports-cf",
            ),
        ),
        "ERP_DS_04 §5.1",
    ),
    ReactComponentSpec(
        "ListRow",
        "mobile_list_row_html",
        ("erp-mob-list-row",),
        (
            PropSpec("title", "string"),
            PropSpec("subtitle", "string", False, ""),
            PropSpec("amount", "string", False, ""),
            PropSpec("amountVariant", "'in' | 'out' | 'pos' | 'neg' | 'success' | 'danger'", False, ""),
            PropSpec("iconBlock", "ReactNode", False, ""),
            PropSpec("metaSub", "string", False, ""),
        ),
        "ERP_DS_04 §5.8",
    ),
    ReactComponentSpec(
        "StatusPill",
        "mobile_status_pill_html",
        ("erp-mob-status-pill",),
        (
            PropSpec("label", "string"),
            PropSpec("variant", "'success' | 'danger' | 'warning' | 'info' | 'neutral'", False, "neutral"),
        ),
        "ERP_DS_04 §5.7",
    ),
    ReactComponentSpec(
        "EmptyState",
        "mobile_empty_state_html",
        ("erp-mob-empty",),
        (PropSpec("message", "string"),),
        "ERP_DS_04 §5.9",
    ),
    ReactComponentSpec(
        "SummaryBanner",
        "mobile_highlight_banner_html",
        ("erp-mob-highlight-banner",),
        (
            PropSpec("title", "string"),
            PropSpec("value", "string"),
            PropSpec("subtitle", "string", False, ""),
            PropSpec("variant", "'success' | 'danger' | 'warning' | 'info'", False, "success"),
        ),
        "ERP_DS_04 §5.12",
    ),
    ReactComponentSpec(
        "ScreenTitle",
        "mobile_screen_title_html",
        ("erp-mob-screen-title",),
        (PropSpec("title", "string"),),
        "ERP_DS_04 §1",
    ),
    ReactComponentSpec(
        "SectionLabel",
        "mobile_section_label_html",
        ("erp-mob-section-label",),
        (PropSpec("label", "string"),),
        "ERP_DS_04 §1",
    ),
    ReactComponentSpec(
        "RolePill",
        "mono_role_pill_html",
        ("erp-mono-pill",),
        (PropSpec("label", "string"),),
        "ERP_DS_04 §7",
    ),
    ReactComponentSpec(
        "AgingBuckets",
        "aging_buckets_html",
        ("erp-aging-grid", "erp-aging-bucket"),
        (
            PropSpec("buckets", "{label: string; amount: string}[]"),
            PropSpec("currency", "string", False, ""),
        ),
        "ERP_DS_04 §7",
    ),
    ReactComponentSpec(
        "ThemeTable",
        "theme_table_html",
        ("erp-data-table",),
        (
            PropSpec("headers", "string[]"),
            PropSpec("rows", "string[][]"),
        ),
        "ERP_DS_04 §5",
    ),
    ReactComponentSpec(
        "TabPanelIntro",
        "tab_panel_intro",
        ("erp-tab-intro",),
        (
            PropSpec("title", "string"),
            PropSpec("body", "string", False, ""),
        ),
        "ERP_DS_04 §5",
    ),
)

# ── Shell / layout (Streamlit scaffolding → React layouts) ────────────────────

_SHELL: tuple[ReactComponentSpec, ...] = (
    ReactComponentSpec(
        "ThemeProvider",
        "ui/theme.py:inject_theme_css",
        ("erp-theme-root",),
        (
            PropSpec("mode", "'light' | 'dark' | 'system'"),
            PropSpec("tokens", "DesignTokenBundle"),
        ),
        "ERP_DS_04 §2",
        streamlit_only=False,
    ),
    ReactComponentSpec(
        "AppShell",
        "theme.css + mobile_shell.css + mobile_header.css",
        ("erp-hdr-shell", "erp-mob-shell"),
        (
            PropSpec("layout", "'desktop' | 'mobile'"),
            PropSpec("header", "ReactNode"),
            PropSpec("sidebar", "ReactNode", False),
            PropSpec("bottomNav", "ReactNode", False),
            PropSpec("children", "ReactNode"),
        ),
        "ERP_DS_05 §3",
        streamlit_only=True,
    ),
    ReactComponentSpec(
        "SidebarNav",
        "app.py:_render_navigation_tree",
        ("erp-nav-item", "erp-nav-section-hdr", "nav-grp-hdr-mark"),
        (
            PropSpec("layout", "SidebarLayoutEntry[]"),
            PropSpec("activeKey", "string"),
            PropSpec("onNavigate", "(key: string) => void"),
            PropSpec("role", "Role"),
        ),
        "ERP_DS_05 §3",
        streamlit_only=True,
    ),
    ReactComponentSpec(
        "MobileBottomNav",
        "app.py:_mobile_bottom_nav",
        ("erp-mob-bottom-bar",),
        (
            PropSpec("items", "MobileNavItem[]"),
            PropSpec("activeKey", "string"),
            PropSpec("onNavigate", "(key: string) => void"),
        ),
        "ERP_DS_05 §3",
        streamlit_only=True,
    ),
    ReactComponentSpec(
        "HubSheet",
        "app.py:_mobile_hub_sheet",
        ("erp-mob-hub-sheet",),
        (
            PropSpec("hubKey", "string"),
            PropSpec("open", "boolean"),
            PropSpec("onClose", "() => void"),
            PropSpec("children", "ReactNode"),
        ),
        "ERP_DS_05 §3",
        streamlit_only=True,
    ),
    ReactComponentSpec(
        "PageHeader",
        "app.py:render_top_header",
        ("erp-hdr-app-title", "erp-hdr-co-subtitle"),
        (
            PropSpec("companyName", "string"),
            PropSpec("pageTitle", "string", False, ""),
            PropSpec("search", "ReactNode", False),
            PropSpec("toolbar", "ReactNode", False),
        ),
        "ERP_DS_04 §1",
        streamlit_only=True,
    ),
    ReactComponentSpec(
        "ChipSelector",
        "widgets.css chip grammar",
        ("erp-chip",),
        (
            PropSpec("options", "{value: string; label: string}[]"),
            PropSpec("value", "string"),
            PropSpec("onChange", "(value: string) => void"),
        ),
        "ERP_DS_04 §5.6",
        streamlit_only=False,
    ),
    ReactComponentSpec(
        "ExportMenu",
        "app.py:render_export_buttons",
        ("st.popover",),
        (
            PropSpec("formats", "('excel' | 'pdf')[]"),
            PropSpec("onExport", "(format: string) => void"),
            PropSpec("filenameStem", "string"),
        ),
        "ERP_DS_04 §7",
        streamlit_only=True,
    ),
)

REACT_COMPONENTS: Final[tuple[ReactComponentSpec, ...]] = _PORTABLE + _SHELL

COMPONENT_BY_STREAMLIT_HELPER: Final[dict[str, ReactComponentSpec]] = {
    spec.streamlit_source: spec
    for spec in _PORTABLE
    if spec.streamlit_source in section_module.__all__
}

KPI_GRID_MODIFIERS: Final[frozenset[str]] = frozenset({"reports-cf"})

# Retired for React — do not port these Streamlit DOM coupling patterns.
STREAMLIT_ONLY_SELECTORS: Final[tuple[StreamlitOnlySelector, ...]] = (
    StreamlitOnlySelector(
        "UI-02-S5-S1",
        '[class*="st-key-"]',
        "Streamlit widget keys leak into CSS selectors for layout hooks.",
        "Component props + data attributes owned by React components.",
    ),
    StreamlitOnlySelector(
        "UI-02-S5-S2",
        '[data-testid="stSidebar"]',
        "Streamlit sidebar DOM is not present in SPA.",
        "SidebarNav in DesktopShell layout slot.",
    ),
    StreamlitOnlySelector(
        "UI-02-S5-S3",
        '[data-testid="stMain"]',
        "Main scoping via Streamlit layout wrapper.",
        "Outlet / page content region in AppShell.",
    ),
    StreamlitOnlySelector(
        "UI-02-S5-S4",
        '[data-testid="stHorizontalBlock"]',
        "Column hacks for Streamlit flex bugs.",
        "CSS grid/flex on erp/* components (MOBILE-14 ownership).",
    ),
    StreamlitOnlySelector(
        "UI-02-S5-S5",
        '[data-testid="stColumn"]',
        "Forced column widths for Streamlit blocks.",
        "Component-level responsive grid templates.",
    ),
    StreamlitOnlySelector(
        "UI-02-S5-S6",
        "html.erp-mobile",
        "Cookie + iframe viewport detector toggles document class.",
        "useMediaQuery / CSS breakpoints (968px per theme.py).",
    ),
    StreamlitOnlySelector(
        "UI-02-S5-S7",
        ".erp-*-host",
        "Empty host marker divs anchor Streamlit keyed containers.",
        "Named layout slots (no phantom hosts).",
    ),
    StreamlitOnlySelector(
        "UI-02-S5-S8",
        "inject_mobile_viewport_detector",
        "iframe cookie bridge for mobile class.",
        "Client-side breakpoint hook + ThemeProvider.",
    ),
    StreamlitOnlySelector(
        "UI-02-S5-S9",
        "sidebar_group session_state",
        "Button tree + session_state for desktop nav groups.",
        "Controlled SidebarNav accordion state.",
    ),
)

DEPRECATED_REACT_TOKEN_KEYS: Final[frozenset[str]] = DEPRECATED_ROLE_TOKEN_KEYS


def react_token_bundle() -> dict[str, object]:
    """JSON-serializable token export for React ThemeProvider bootstrap."""
    return {
        "version": "UI-SYSTEM-02-S5",
        "light": build_light_root_vars(),
        "dark": build_dark_root_vars(),
        "layout": dict(LAYOUT_TOKENS),
        "mobileHeaderLayout": dict(MOBILE_HEADER_LAYOUT_TOKENS),
        "spacing": dict(SPACING_TOKENS),
        "radius": dict(RADIUS_TOKENS),
        "shadow": dict(SHADOW_TOKENS),
        "typography": dict(TYPOGRAPHY_TOKENS),
        "chipKeys": list(CHIP_TOKEN_KEYS),
        "deprecated": sorted(DEPRECATED_REACT_TOKEN_KEYS),
        "kpiGridModifiers": sorted(KPI_GRID_MODIFIERS),
        "grammarVersion": GRAMMAR_CONTRACT_VERSION,
        "componentGrammar": dict(COMPONENT_GRAMMAR_TOKENS),
        "navGrammarKeys": list(NAV_GRAMMAR_TOKEN_KEYS),
        "cardGrammarKeys": list(CARD_GRAMMAR_TOKEN_KEYS),
        "chipGrammarExtensionKeys": list(CHIP_GRAMMAR_EXTENSION_KEYS),
        "tableGrammarKeys": list(TABLE_GRAMMAR_TOKEN_KEYS),
    }


def react_component_rows() -> list[tuple[str, str, str]]:
    """(react_name, streamlit_source, primary_css_class) for doc/tests."""
    return [
        (spec.name, spec.streamlit_source, spec.css_classes[0] if spec.css_classes else "")
        for spec in REACT_COMPONENTS
    ]


def validate_react_design_contract() -> None:
    """Raise ValueError if the frozen contract drifts from code."""
    names = [spec.name for spec in REACT_COMPONENTS]
    if len(names) != len(set(names)):
        dupes = {n for n in names if names.count(n) > 1}
        raise ValueError(f"Duplicate React component names: {sorted(dupes)}")

    for helper, spec in COMPONENT_BY_STREAMLIT_HELPER.items():
        if helper not in section_module.__all__:
            raise ValueError(f"streamlit helper {helper!r} missing from section.__all__")
        fn = getattr(section_module, helper, None)
        if not callable(fn):
            raise ValueError(f"section.{helper} is not callable")

    portable_helpers = {spec.streamlit_source for spec in _PORTABLE}
    missing = portable_helpers - set(section_module.__all__)
    if missing:
        raise ValueError(f"Portable helpers missing from section.__all__: {sorted(missing)}")

    if not DEPRECATED_REACT_TOKEN_KEYS <= DEPRECATED_ROLE_TOKEN_KEYS:
        raise ValueError("DEPRECATED_REACT_TOKEN_KEYS must be subset of design token registry")

    if "reports-cf" not in KPI_GRID_MODIFIERS:
        raise ValueError("KPI_GRID_MODIFIERS must include reports-cf (cash flow mobile row)")

    bundle = react_token_bundle()
    for key in (
        "grammarVersion",
        "componentGrammar",
        "navGrammarKeys",
        "cardGrammarKeys",
        "chipGrammarExtensionKeys",
        "tableGrammarKeys",
    ):
        if key not in bundle:
            raise ValueError(f"react_token_bundle missing grammar export key: {key!r}")

    if bundle["grammarVersion"] != GRAMMAR_CONTRACT_VERSION:
        raise ValueError("grammarVersion drift vs GRAMMAR_CONTRACT_VERSION")

    grammar = bundle["componentGrammar"]
    if set(grammar) != set(COMPONENT_GRAMMAR_TOKENS):
        raise ValueError("componentGrammar keys drift vs COMPONENT_GRAMMAR_TOKENS")

    if not grammar_values_reference_only():
        raise ValueError("COMPONENT_GRAMMAR_TOKENS must reference existing tokens only (no raw hex)")
