# UI-SYSTEM-02-S5 — React Design Contract

**Status:** ✅ **Frozen (UI-SYSTEM-02-S5)**  
**Source of truth:** `ui/react_design_contract.py` + `ui/design_tokens.py`  
**Route contract (separate):** [NAV_ARCH_REACT_ROUTE_CONTRACT.md](./NAV_ARCH_REACT_ROUTE_CONTRACT.md)  
**Tests:** `tests/test_ui_system_02_s5_react_design_contract.py`

## Purpose

This document freezes the **ERP-wide UI design contract** for the FastAPI + React migration:

1. **Design tokens** — exportable JSON bundle for `ThemeProvider`
2. **Component map** — Streamlit helpers → React component names + props
3. **Streamlit-only selectors** — retired patterns the React SPA must **not** replicate

Streamlit continues to use `st-key-*` / `data-testid="st*"` CSS until DS-6 deprecation. React uses component props and layout slots instead.

## Contract rules

1. **Token authority** — `ui/design_tokens.py` is the SSOT; `ui/theme.py` injects colours; `ui/theme.css` mirrors scales. React imports `react_token_bundle()` — do not fork hex values.
2. **Component parity** — every portable helper in `ui/section.py` maps 1:1 to a React component in `REACT_COMPONENTS` with documented props.
3. **Mono policy** — one accent (`--theme-info` / `--primary`); no per-role hue chrome; `--role-*` tokens are **deprecated** (compat only).
4. **No Streamlit selector port** — patterns in `STREAMLIT_ONLY_SELECTORS` are **retired for React**; they remain in Streamlit CSS only.
5. **Route binding** — shell components consume `registry/navigation.py` `react_route` paths ([NAV-ARCH-S4](./NAV_ARCH_REACT_ROUTE_CONTRACT.md)).
6. **Change policy** — any edit requires updating `ui/react_design_contract.py`, this doc, and S5 tests.

## Token governance

### Authority chain

```
ui/design_tokens.py  →  ui/theme.py (LIGHT/DARK_ROOT_VARS injection)
                    →  ui/theme.css (:root scales + chip grammar)
                    →  ui/mobile_components.css (--mob-space-* aliases --erp-space-*)
```

### React ThemeProvider export

```python
from ui.react_design_contract import react_token_bundle
bundle = react_token_bundle()  # JSON-serializable; version UI-SYSTEM-02-S5
```

| Bundle key | Contents |
|------------|----------|
| `light` / `dark` | Injectable colour tokens |
| `layout` | Desktop shell (`--hdr-h`, `--side-nav-w`, …) |
| `mobileHeaderLayout` | Mobile header overrides (`mobile_header.css` owner) |
| `spacing` / `radius` / `shadow` / `typography` | ERP scale tokens |
| `chipKeys` | Chip grammar variable names (CSS color-mix) |
| `deprecated` | `--role-*` keys — **do not use in new React UI** |
| `kpiGridModifiers` | BEM modifiers e.g. `reports-cf` |
| `grammarVersion` | MONO-THEME grammar slice id (`MONO-THEME-01-S7`) |
| `componentGrammar` | Shared `--erp-nav-*` / `--erp-card-*` / `--erp-chip-*` ext / `--erp-table-*` values from `COMPONENT_GRAMMAR_TOKENS` |
| `navGrammarKeys` | Nav active grammar variable names |
| `cardGrammarKeys` | Card shell grammar variable names |
| `chipGrammarExtensionKeys` | Chip radius/padding/border extensions (semantic chip colours remain in `chipKeys`) |
| `tableGrammarKeys` | Dense table grammar variable names |

### MONO-THEME-01 shared grammar (S7)

MONO-THEME-01-S2–S6 migrated desktop and mobile CSS to a **single component-grammar token layer**. S7 records that layer in `react_token_bundle()` so the React `ThemeProvider` can bootstrap nav/card/chip/table shells without forking Streamlit CSS.

```python
bundle = react_token_bundle()
assert bundle["grammarVersion"] == "MONO-THEME-01-S7"
nav_bg = bundle["componentGrammar"]["--erp-nav-active-bg"]
```

React rule: import grammar values from the bundle; do **not** re-derive color-mix strings in the SPA. Semantic colours (`--theme-success`, `--theme-danger`, …) remain in `light`/`dark` and are unchanged.

**Tests:** `tests/test_mono_theme_01_s7_react_contract_cleanup.py`

### Deprecated tokens (governance)

| Token family | Status | React rule |
|--------------|--------|------------|
| `--role-owner` … `--role-default` | Deprecated S2/S5 | Use `mono_role_pill` / `<RolePill>` with `--theme-info` mix |
| `ROLE_CSS_VARS` in `ui/theme.py` | Legacy compat | Do not map to React theme |

## Frozen component map

Portable components (`ui/section.py` → `components/erp/`):

| React component | Streamlit helper | Primary CSS |
|-----------------|------------------|-------------|
| SectionHeader | `section_header_html` | `.erp-section-hdr` |
| PageBanner | `page_report_banner_html` | `.erp-page-banner` |
| FinSectionHeader | `financial_section_header_html` | `.erp-fin-section-hdr` |
| FinTable | `financial_statement_table_html` | `.erp-fin-table` |
| DataTable | `readable_dataframe_table_html` | `.erp-data-table` |
| ThemeTable | `theme_table_html` | `.erp-data-table` |
| KpiChip | `mobile_kpi_chip_html` | `.erp-mob-kpi-chip` |
| KpiGrid | `mobile_kpi_grid_html` | `.erp-mob-kpi-grid` |
| ListRow | `mobile_list_row_html` | `.erp-mob-list-row` |
| StatusPill | `mobile_status_pill_html` | `.erp-mob-status-pill` |
| EmptyState | `mobile_empty_state_html` | `.erp-mob-empty` |
| SummaryBanner | `mobile_highlight_banner_html` | `.erp-mob-highlight-banner` |
| ScreenTitle | `mobile_screen_title_html` | `.erp-mob-screen-title` |
| SectionLabel | `mobile_section_label_html` | `.erp-mob-section-label` |
| RolePill | `mono_role_pill_html` | `.erp-mono-pill` |
| AgingBuckets | `aging_buckets_html` | `.erp-aging-grid` |
| TabPanelIntro | `tab_panel_intro` | `.erp-tab-intro` |

Shell / layout (Streamlit scaffolding → React layouts):

| React component | Streamlit source | Notes |
|-----------------|------------------|-------|
| ThemeProvider | `ui/theme.py` | Injects tokens + loads CSS bundle |
| AppShell | `theme.css` + `mobile_shell.css` + `mobile_header.css` | Desktop + mobile chrome |
| SidebarNav | `app.py:_render_navigation_tree` | Consumes `SIDEBAR_LAYOUT` |
| MobileBottomNav | `app.py:_mobile_bottom_nav` | 5-slot bottom bar |
| HubSheet | `app.py:_mobile_hub_sheet` | Money/Reports/People/More hubs |
| PageHeader | `app.py:render_top_header` | Company + toolbar |
| ChipSelector | `widgets.css` chip grammar | `--erp-chip-*` tokens |
| ExportMenu | `app.py:render_export_buttons` | Excel/PDF popover |

**DS-4 reference:** [ERP_DS_04_MASTER_DESIGN_SYSTEM.md](./ERP_DS_04_MASTER_DESIGN_SYSTEM.md)  
**Architecture:** [ERP_DS_05_REACT_ARCHITECTURE.md](./ERP_DS_05_REACT_ARCHITECTURE.md)

### KpiGrid modifiers

| Modifier | Class | Use |
|----------|-------|-----|
| `reports-cf` | `.erp-mob-kpi-grid--reports-cf` | Cash flow mobile KPI row (14px values) |

## Streamlit-only selectors (retired for React)

These patterns are **documented and frozen** as Streamlit-only. Do **not** copy into the React SPA.

| ID | Pattern | React replacement |
|----|---------|-------------------|
| UI-02-S5-S1 | `[class*="st-key-"]` | Component props + owned data attributes |
| UI-02-S5-S2 | `[data-testid="stSidebar"]` | `SidebarNav` layout slot |
| UI-02-S5-S3 | `[data-testid="stMain"]` | `AppShell` outlet region |
| UI-02-S5-S4 | `[data-testid="stHorizontalBlock"]` | Component flex/grid |
| UI-02-S5-S5 | `[data-testid="stColumn"]` | Responsive grid templates |
| UI-02-S5-S6 | `html.erp-mobile` | `useMediaQuery` / 968px breakpoint |
| UI-02-S5-S7 | `.erp-*-host` | Named layout slots (no phantom hosts) |
| UI-02-S5-S8 | `inject_mobile_viewport_detector` | Client breakpoint hook |
| UI-02-S5-S9 | `sidebar_group` session_state | Controlled accordion state |

## Validation

```python
from ui.react_design_contract import validate_react_design_contract
validate_react_design_contract()  # raises ValueError on drift
```

## No-change statement

UI-SYSTEM-02-S5 froze the migration contract without changing Streamlit runtime UI. **MONO-THEME-01-S7** extends the token export only and removes deprecated per-role hue styling from `auth.css` (mono role chips). No nav/posting/accounting change.

## Related documents

| Doc | Role |
|-----|------|
| [UI_SYSTEM_02_AUDIT.md](./UI_SYSTEM_02_AUDIT.md) | S1–S5 epic audit |
| [MONO_THEME_01_AUDIT.md](./MONO_THEME_01_AUDIT.md) | Shared grammar tokens S2–S7 |
| [NAV_ARCH_REACT_ROUTE_CONTRACT.md](./NAV_ARCH_REACT_ROUTE_CONTRACT.md) | Route paths |
| [ERP_DS_04_MASTER_DESIGN_SYSTEM.md](./ERP_DS_04_MASTER_DESIGN_SYSTEM.md) | Visual spec |
| [ERP_DS_05_REACT_ARCHITECTURE.md](./ERP_DS_05_REACT_ARCHITECTURE.md) | SPA architecture |

*Frozen 2026-06-05. UI-SYSTEM-02 epic S1–S5 complete. MONO-THEME-01-S7 grammar export added 2026-06-05.*
