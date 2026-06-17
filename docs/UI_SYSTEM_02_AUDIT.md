# UI-SYSTEM-02 — ERP-Wide UI & Theme Audit

**Mode:** Audit only (UI-SYSTEM-02-S1). **No visual redesign.** No CSS/runtime changes in this slice.

**Goal:** Prepare ERP-wide UI/theme modernization after NAV-ARCH completion and before Banking UX. Target: one professional SaaS ERP on desktop and mobile; React migration-ready; no rainbow accents.

**Avoid-duplicate-fixes note:** This audit **builds on** prior work — [CSS-01](../ROADMAP.md#css-01--theme-ownership-consolidation), [CSS-02](../ROADMAP.md#css-02--erp-wide-ui-ownership-standard), [MOBILE-14](../ROADMAP.md#mobile-14--mobile-theme-ownership-cleanup) (closed), [MOBILE_UI_SYSTEM.md](./MOBILE_UI_SYSTEM.md), [UI_STYLE_GUIDE.md](./UI_STYLE_GUIDE.md), [NAV_ARCH_AUDIT.md](./NAV_ARCH_AUDIT.md). It does **not** re-propose MOBILE-14 M1–M6 fixes already shipped; it records **remaining gaps** for UI-SYSTEM-02 S2–S5.

**UI-SYSTEM-02-S1 status:** ✅ **Complete** — `docs/UI_SYSTEM_02_AUDIT.md` + `tests/test_ui_system_02_audit.py`.

---

## 1. CSS ownership

### 1.1 File inventory (14 files · 7,379 lines)

| File | Lines | Role (canonical owner per CSS-01/CSS-02) |
|------|------:|------------------------------------------|
| `ui/theme.css` | 2,206 | Global tokens, desktop shell, sidebar, dashboard, shared tables/banners |
| `ui/widgets.css` | 1,181 | Generic Streamlit widget behaviour, chip grammar, keyed suppression |
| `ui/mobile_shell.css` | 1,053 | Mobile shell, bottom nav, hub sheet, sidebar hide |
| `ui/mobile_txn.css` | 1,120 | Mobile Add Transaction panel, pickers, `--mob-at-*` aliases |
| `ui/mobile_components.css` | 323 | Shared mobile layout grids (KPI, TXH filter rows) |
| `ui/mobile_txn_history.css` | 319 | Mobile transaction history layout |
| `ui/desktop_txn_history.css` | 290 | Desktop transaction history |
| `ui/auth.css` | 296 | Login / company picker (`erp-auth-*`) |
| `ui/mobile_header.css` | 168 | Mobile header height, toolbar, `block-container` top inset |
| `ui/setup01_wizard.css` | 204 | Setup wizard |
| `ui/mobile_reports.css` | 100 | Mobile reports layout (not chip colours) |
| `ui/desktop_reports.css` | 30 | Desktop report chip selector layout |
| `ui/banking.css` | 30 | Banking page hooks (minimal) |
| `ui/icons.css` | 59 | Nav/icon SVG sizing |

**Bundle injection** — `ui/theme.py` `load_theme_css()` concatenates all 14 files in fixed order (`theme.py:110–147`). Entry point: `bootstrap_theme()` called from `app.py:26094`.

**`app.py` inline CSS:** No `<style>` blocks or markdown style injections found. UI hosts use `unsafe_allow_html=True` for structural `<div class="…">` markers and tables from `ui/section.py` helpers — not for ad-hoc CSS.

### 1.2 Ownership health (post MOBILE-14)

| Domain | Owner | Status |
|--------|-------|--------|
| `--theme-*` / `--erp-chip-*` tokens | `theme.css :root` + `ui/theme.py` injection | ✅ Dual but intentional (THEME-AUTHORITY-01) |
| Desktop sidebar chrome | `theme.css` (`stSidebar` rules ~849–1458, nav hierarchy ~2099–2140) | ✅ Single owner |
| Mobile sidebar hide | `mobile_shell.css` only | ✅ M6 closed — redundant hide removed from `theme.css:875–876` |
| Mobile header height | `mobile_header.css` (`--hdr-h: 56px`) | ⚠️ **Conflict** — see §2 |
| Bottom nav + FAB + hub | `mobile_shell.css` | ✅ |
| Chip active/idle grammar | `widgets.css` | ✅ UI-1 / MOBILE-14 E8 |
| Dashboard / KPI | `theme.css` (`.erp-kpi-section`, `.kpi-grid`, `.erp-dash-*`) | ✅ M5 closed |
| Banking visual | `banking.css` + shared `theme.css` | ⚠️ No `mobile_banking.css` yet (ROADMAP planned) |

### 1.3 Cross-file selector overlap (16 classes in 2+ files)

Automated scan (class selectors only): **390** unique classes; **16** appear in multiple files. Highest-risk overlaps:

| Selector | Files | Risk |
|----------|-------|------|
| `.block-container` | 6 files | Medium — padding-top ownership split (`mobile_header.css` canonical; others layout-specific) |
| `.erp-hdr-mobile-title` | `theme.css`, `mobile_header.css`, `mobile_shell.css` | Medium — header presentation leak |
| `.st-key-hdr_notif_pop`, `.st-key-hdr_toolbar_row` | `theme.css`, `mobile_header.css`, `widgets.css` | Low — suppression vs layout |
| `.erp-mobile-report-filters` | `theme.css`, `mobile_reports.css` | Low — **dead duplicate** in `theme.css:1106–1108` |
| `.erp-mob-kpi-grid`, `.erp-mob-kpi-value` | `mobile_components.css`, `mobile_reports.css`, `mobile_txn.css` | Medium — KPI grid grammar not unified |
| `.erp-nav-icon` | `icons.css`, `mobile_shell.css` | Low — size vs placement |
| `.erp-txh-*` shared | `desktop_txn_history.css`, `mobile_txn_history.css`, `mobile_components.css` | Low — intentional cross-surface naming |

### 1.4 Conflicting ownership (open)

| ID | Issue | Location | Severity |
|----|-------|----------|----------|
| UI-02-C1 | Mobile `--hdr-h` **120px** in `theme.css` `@media (max-width: 968px)` vs **56px** canonical in `mobile_header.css` | `theme.css:868–869`, `mobile_header.css:10` | **High** — cascade order puts `theme.css` first; mobile_header should win but dual definition violates CSS-02 rule 1 |
| UI-02-C2 | `.erp-mobile-report-filters { display: block }` redundant inside mobile `@media`; desktop hide at `theme.css:1353–1355` is live | `theme.css:1106–1108` | Low — dead copy |
| UI-02-C3 | Header mobile column rules duplicated between `theme.css` (`867–920`) and `mobile_shell.css` (`40–80`) | Both files | Medium — maintenance drag |
| UI-02-C4 | `_NAV_GROUP_KEYS` / `_NAV_GROUP_HINTS` duplicate registry `NAV_ACCORDION_GROUPS` labels | `app.py:3049–3063` vs `registry/navigation.py:101–110` | Low — presentation drift risk |

---

## 2. Theme tokens

### 2.1 Colour tokens (present)

| Family | CSS vars | Python mirror | Dark/light |
|--------|----------|---------------|------------|
| Surface | `--theme-bg`, `--theme-card`, `--theme-border`, `--hdr-bg` | `LIGHT_ROOT_VARS` / `DARK_ROOT_VARS` in `theme.py:49–99` | ✅ Injection + `@media (prefers-color-scheme: dark)` on `html[data-erp-theme="system"]` (`theme.css:72–98`) |
| Text | `--theme-text`, `--theme-muted`, `--theme-caption` | Same | ✅ |
| Semantic | `--theme-success`, `--theme-warning`, `--theme-danger`, `--theme-info` | Same | ✅ |
| Semantic text | `--theme-success-text`, `--theme-warning-text`, `--theme-danger-text` | Same | ✅ THEME-CONTRAST-01 |
| Primary CTA | `--erp-primary-fill`, `--erp-primary-fill-hover`, `--erp-on-primary` | Same | ✅ |
| Accent (limited) | `--theme-purple`, `--theme-teal` | Same | ⚠️ Use sparingly; KPI dark-mode forced mono (`theme.py:275–280`) |
| Chips | `--erp-chip-active-*`, `--erp-chip-idle-*` | CSS only (`theme.css:39–45`) | ✅ |
| Role badges | `--role-owner` … `--role-viewer` | CSS only (`theme.css:46–52`) | ⚠️ **Stale** — `role_accent_css_var()` uses mono mix (`theme.py:290–292`); role hue tokens unused in avatars |

**Triple source of truth:** `theme.css :root` defaults · `ui/theme.py` user-preference injection · `@media (prefers-color-scheme: dark)` system fallback. Governed by THEME-AUTHORITY-01 + `tests/test_theme_authority01.py`. **S2 should centralize into a token registry** (JSON/Python) with CSS generation or single `:root` block.

### 2.2 Spacing, radius, shadows (gaps)

| Token | Current state | Gap |
|-------|---------------|-----|
| Layout widths | `--side-nav-w`, `--erp-sidebar-w` (244px), `--bottom-nav-h`, `--mob-fab-size` | Partial — shell only |
| Header | `--hdr-h`, `--hdr-h-search`, `--hdr-toolbar-*` | **Split owners** (UI-02-C1) |
| Radius | `--erp-field-radius: 8px`; ad-hoc `6px`, `8px`, `50%` in components | No `--erp-radius-sm/md/lg` scale |
| Shadows | `--theme-shadow` only | No elevation scale (`--erp-shadow-sm/md/lg`) |
| Spacing | Ad-hoc `px`/`rem` per component | No `--erp-space-*` scale |
| Typography | Implicit Streamlit + section helpers | No `--erp-font-*` / line-height scale |

**Professional SaaS alignment:** Palette is already restrained (slate + single blue primary). Rainbow risk is mainly **legacy role hue tokens** and **per-KPI colour classes** (`.kpi-success`, etc.) — dark mode correctly suppresses KPI rainbow (`theme.css:99–107`).

---

## 3. Layout shell

### 3.1 Top header

| Surface | Owner | Mechanism |
|---------|-------|-----------|
| Desktop | `theme.css` | Fixed `hdr_shell_row` at `--hdr-h: 60px`; brand + search + toolbar |
| Mobile | `mobile_header.css` + `mobile_shell.css` | Compact 56px toolbar; company selector + bell + profile; search expands to 86px |
| Bootstrap | `app.py` `render_top_header` | Keyed columns `hdr_shell_inner`, `hdr_toolbar_row`, etc. |

**Page title patterns:** `st.title` / `st.header` themed in `widgets.css:28–40`; rich banners via `ui/section.py` → `.erp-page-banner*` (`theme.css:601–633`).

### 3.2 Desktop sidebar

- Render: `_render_navigation_tree()` — `app.py:3187–3279`
- Style: `theme.css` `stSidebar` + `.nav-grp-*` / `.nav-item-*` hierarchy (`theme.css:2099–2140`)
- Width: 244px; always visible ≥969px; Streamlit collapse controls hidden

### 3.3 Mobile shell

- Detection: `inject_mobile_viewport_detector()` iframe + `html.erp-mobile` (`theme.py:227–272`)
- Boundaries: `MOBILE_VIEWPORT_*` constants (`theme.py:31–46`) aligned with `@media` arms in `mobile_shell.css:11–13`
- Bottom nav: 5 slots from registry (`_MOBILE_BOTTOM_NAV`); FAB center
- Hub sheets: `mobile_shell.css` (money/reports/people/more)
- Sidebar: hidden on mobile — **no drawer**; navigation via bottom bar + hubs + More accordions

### 3.4 Dashboard

- All `.erp-dash-*` in `theme.css` (~lines 1205–1904)
- Desktop: welcome card, KPI grid, alerts, activity feed, expense bars
- Mobile: greeting strip, horizontal KPI scroll, AR/AP host markers
- **Debt:** 96 rules `.erp-dash-expense-bar-fill[data-pct="N"]` (`theme.css:1789–1884`) — static width ladder; React should use inline `width: N%` or CSS `attr()` 

### 3.5 Forms, cards, tables, dialogs

| Pattern | Implementation |
|---------|----------------|
| Form sections | `ui/section.py` (`render_section`, accent policy UI-1); Streamlit widgets in `widgets.css` |
| Cards / KPIs | `.erp-kpi-section`, `.kpi-grid`, `.erp-card-label`; mobile chips in `mobile_components.css` |
| Tables | `.erp-data-table`, `.erp-fin-table` (`theme.css`); `theme_table_html()` in section helpers |
| Expanders | Streamlit native + `widgets.css` border-container rules |
| Mobile sheets / pickers | `mobile_shell.css` (hub), `mobile_txn.css` (AT pickers), `mobile_header.css` (co switch) |
| Dialogs / void confirm | Keyed `st-key-erp_void_*` danger styling in `widgets.css` |

---

## 4. Sidebar visual readiness (grouping only — no route changes)

Navigation **routes** are registry-driven (NAV-ARCH complete). **Visual render order** remains hand-authored in `_render_navigation_tree` and **does not consume** `_NAV_DIRECT_PAGES` for layout.

### 4.1 Registry metadata vs rendered tree

**Registry direct pages** (`build_nav_direct_pages()` order): Home → New Transaction → Transaction Ledger → Inventory → Banking → Reports.

**Rendered tree** (`app.py:3263–3279`):

```
Home, New Transaction, Transaction Ledger          [direct — matches registry top]
── section "Work" ──
  Record transactions [accordion]
  Banking [direct — inserted here, not at registry position 4]
  Customers & suppliers [accordion]
  Inventory [direct]
  Recipe Costing [accordion]
── section "Reports" ──
  Financial Statements [accordion]
  Reports [direct]
  Closings [accordion]
── section "Advanced" ──
  Books [accordion — 9 items]
  Team & partners [accordion]
  Settings [accordion — 5 items]
```

### 4.2 Visual clutter / inconsistency findings

| ID | Finding | Impact |
|----|---------|--------|
| UI-02-S1 | **8 accordion groups** + **3 section captions** + **6 direct links** = long sidebar scroll on owner role | High cognitive load before S3 modernization |
| UI-02-S2 | **Banking** visually sits in "Work" between transactions and people; registry `sidebar_direct_order=4` implies after Inventory | Visual/metadata drift |
| UI-02-S3 | **Financial Statements** accordion + **Reports** direct link in same section — two report entry styles adjacent | Confusing hierarchy |
| UI-02-S4 | **Closings** accordion after Reports in "Reports" section — EOD close + cash recon grouped away from daily "Work" flows | Workflow disconnect |
| UI-02-S5 | **Books** accordion has **9 pages** (GL, COA, TB, JE, fiscal, YEC, budget, recon health, opening balances) — heaviest group | Needs visual sub-grouping in S3 |
| UI-02-S6 | Accordion open state uses text chevrons (`▸`/`▾`) on `secondary`/`primary` Streamlit buttons — functional but not SaaS-polished | S3 visual target |
| UI-02-S7 | Nav row = icon column (12%) + button (88%) + invisible marker divs — Streamlit-specific; works but fragile for React port | Document as temporary |

**S3 scope (future):** Visual grouping, spacing, icons, section headers, accordion chrome — **without** moving routes or changing `_PAGE_DISPATCH`.

---

## 5. Desktop/mobile parity

| Dimension | Desktop | Mobile | Parity |
|-----------|---------|--------|--------|
| Workflows | Full sidebar + header search | Bottom nav + hubs + page-native flows | ✅ Same routes; different chrome |
| Tokens | Shared `--theme-*` | Same injection | ✅ |
| Breakpoint | ≥969px desktop sidebar | ≤968px / touch tablet / phone landscape | ✅ VIEWPORT-SYNC-01 |
| Header height | 60px | 56px (86px with search) | ⚠️ UI-02-C1 leak |
| Sidebar | Fixed 244px | Hidden | ✅ Intentional |
| KPI presentation | Grid cards | Horizontal scroll chips | ⚠️ Different component language — S4 unification |
| Reports filters | Desktop picker in page | `.erp-mobile-report-filters` host | ✅ Dual hosts, one workflow |
| CSS leaks | `theme.css` mobile `@media` block (~867–1360) overlaps `mobile_shell.css` | Same | Medium — S4 shell pass |

**Contract tests guarding parity:** `tests/test_mobile_layout_contract.py`, `tests/test_shell_stabilization.py`, `tests/test_mobile14_ownership_contract.py`, `tests/test_ui1_design_language.py`.

---

## 6. React migration readiness

### 6.1 Portable to React (keep semantics)

| Asset | Notes |
|-------|-------|
| `--theme-*` / `--erp-chip-*` tokens | Map to CSS variables or design-token JSON (S2) |
| `.erp-*` component classes | BEM-like; become React component classNames |
| `ui/section.py` HTML builders | Templates for `PageBanner`, `DataTable`, `AgingBuckets`, `MonoPill` |
| `registry/icon_svg.py` + `icons.css` | SVG nav icons already registry-keyed |
| `chart_theme_tokens()` | Chart palette already token-derived |
| NAV-ARCH `react_route` contract | Route paths frozen — shell components bind to same paths |

### 6.2 Streamlit-only (temporary)

| Hack | Why temporary |
|------|---------------|
| `st-key-*` / `[data-testid="st*"]` selectors | Streamlit DOM coupling — replace with component props |
| Host marker `<div class="erp-…">` empty divs | Streamlit layout hooks — replace with layout slots |
| `inject_mobile_viewport_detector()` iframe | Cookie + `html.erp-mobile` — replace with responsive CSS + JS in SPA |
| Keyed `st.columns` + CSS grid rules | `tests/test_mobile_layout_contract.py` enforced — React uses flex/grid in components |
| Sidebar = `st.sidebar` button tree | Replace with `SidebarNav` React component consuming `registry/navigation.py` |
| Accordion = session_state `sidebar_group` + buttons | Replace with controlled accordion state |

### 6.3 Future React components (S5 design contract)

| Component | Source today |
|-----------|--------------|
| `AppShell` | `theme.css` + `mobile_shell.css` + header split |
| `SidebarNav` | `_render_navigation_tree` + `theme.css` nav hierarchy |
| `MobileBottomNav` + `HubSheet` | `mobile_shell.css` + registry mobile config |
| `PageHeader` / `PageBanner` | `render_top_header` + `.erp-page-banner` |
| `KpiGrid` / `KpiScroll` | `theme.css` + `mobile_components.css` |
| `ChipSelector` | `widgets.css` chip grammar |
| `DataTable` / `FinTable` | `theme.css` tables + `section.py` |
| `FormSection` | `ui/section.py` |
| `ThemeProvider` | `ui/theme.py` authority chain |

---

## 7. Dead / duplicate UI code

| ID | Item | Location | Action (future slice) |
|----|------|----------|----------------------|
| UI-02-D1 | `.erp-mobile-report-filters` visibility duplicate | `theme.css:1106–1108` | Remove in S4 (line 1353 is live) |
| UI-02-D2 | 96× `[data-pct]` expense bar width rules | `theme.css:1789–1884` | Replace with dynamic width in S4 |
| UI-02-D3 | `--role-*` hue tokens unused for mono avatar policy | `theme.css:46–52` | Deprecate in S2 token registry |
| UI-02-D4 | `_NAV_GROUP_KEYS` duplicates registry group i18n keys | `app.py:3049–3058` | Derive from registry in S3 |
| UI-02-D5 | Header mobile layout duplicated | `theme.css` + `mobile_shell.css` | Consolidate to `mobile_header.css` in S4 |
| UI-02-D6 | `.erp-mob-kpi-grid` in 3 files | mobile_components/reports/txn | Unify KPI grid owner in S4 |
| UI-02-D7 | `banking.css` stub (30 lines) | `ui/banking.css` | Expand in Banking UX epic, not here |

**Not dead (confirmed in use):** `.nav-grp-hdr-mark`, `.nav-item-active-mark`, `.erp-dash-*`, `.erp-co-switch-confirm-host`, chip `st-key-mob_rpt_sel_*` rules.

---

## 8. Safe modernization plan (NOT implemented in S1)

| Slice | Scope | Status |
|-------|--------|--------|
| **UI-SYSTEM-02-S0 — Guardrails** | Audit-only; no CSS without doc/test; CSS-02 remains law | ✅ Active |
| **UI-SYSTEM-02-S1 — Audit** | This document + contract tests | ✅ **Complete** |
| **UI-SYSTEM-02-S2 — Design token registry** | Centralize colour/spacing/radius/shadow/typography; deprecate stale role hues; resolve UI-02-C1 `--hdr-h` | 📋 Planned |
| **UI-SYSTEM-02-S3 — Sidebar modernization** | Visual grouping polish; derive section layout from registry; no route moves | 📋 Planned |
| **UI-SYSTEM-02-S4 — Unified shell/component pass** | Dedupe header/sidebar mobile rules; KPI grid single owner; expense bar ladder; desktop/mobile component parity | 📋 Planned |
| **UI-SYSTEM-02-S5 — Theme governance / React design contract** | `docs/UI_SYSTEM_02_REACT_DESIGN_CONTRACT.md`; component prop map; retire Streamlit selector list | 📋 Planned |

**Recommended next slice:** **UI-SYSTEM-02-S2** (design token registry) — unblocks S3–S5 and resolves UI-02-C1 without visual redesign risk.

---

## 9. S1 guardrails (tests)

| Guard | Test module |
|-------|-------------|
| Audit doc contract | `tests/test_ui_system_02_audit.py` |
| Theme authority | `tests/test_theme_authority01.py` |
| UI-1 design language | `tests/test_ui1_design_language.py` |
| Mobile layout keys | `tests/test_mobile_layout_contract.py` |
| MOBILE-14 ownership | `tests/test_mobile14_ownership_contract.py` |
| Phase 16A theme | `tests/test_phase16a_theme.py` |
| Shell stabilization | `tests/test_shell_stabilization.py` |

---

## No-change statement (UI-SYSTEM-02-S1)

- **No visual redesign.** No CSS file edits. No accounting, database, business-logic, or navigation route changes. Sidebar render order unchanged. ROADMAP and TECH_DEBT updated only.

---

*Audit dated 2026-06-05. Post NAV-ARCH S0–S4; pre Banking UX and UI-SYSTEM-02-S2.*
