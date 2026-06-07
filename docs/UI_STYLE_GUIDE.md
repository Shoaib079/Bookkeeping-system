# ERP UI Style Guide

**Phase UI-1 reference** — one visual language for the Accounting ERP.  
**Theme direction:** One primary brand color (`--theme-info`). Status colors only when required.

Open `docs/ui_style_guide_preview.html` in a browser for a visual specimen sheet.

---

## Design tokens (source of truth)

| Token | Role |
|---|---|
| `--theme-info` | Primary brand / CTAs / selected chip text |
| `--theme-text` | Body, secondary button text |
| `--theme-muted` | Labels, captions, idle nav |
| `--theme-card` | Cards, inputs, secondary fill |
| `--theme-bg` | Page background |
| `--theme-border` | Borders |
| `--theme-success` | Positive amounts, success states |
| `--theme-danger` | Void, delete, negative amounts |
| `--theme-warning` | Pending, dev banner, caution |
| `--erp-on-primary` | Text on solid primary buttons |
| `--erp-chip-active-bg` | Selected chip background |
| `--erp-chip-active-fg` | Selected chip text |
| `--erp-chip-active-border` | Selected chip border |
| `--erp-chip-idle-bg` | Unselected chip background |
| `--erp-chip-idle-fg` | Unselected chip text |
| `--erp-chip-idle-border` | Unselected chip border |
| `--erp-field-radius` | Inputs & buttons (8px) |

---

## 1. Primary Button

**When:** Save, Pay, Confirm, Post, Create, Form submit, Restore (confirmed).

| Property | Value |
|---|---|
| Fill | Solid `--theme-info` |
| Text | `--erp-on-primary` |
| Border | 1px `--theme-info` |
| Radius | 8px (12px mobile calculator Save only) |
| Weight | 700–800 |
| Min height | 36px desktop / 48–56px mobile hero |

**Not primary:** Sidebar active item, selected chips, selected tabs, bottom-nav active label — use **Selected Chip** or **Active Tab**.

**Streamlit:** `st.button(..., type="primary")` in CTA contexts only.

---

## 2. Secondary Button

**When:** Cancel, Back, Close, View, Export trigger, hub list rows, inactive actions.

| Property | Value |
|---|---|
| Fill | `--theme-card` |
| Text | `--theme-text` |
| Border | 1px `--theme-border` |
| Radius | 8px |
| Weight | 600 |

**Streamlit:** `st.button(..., type="secondary")` or default where appropriate.

---

## 3. Danger Button

**When:** Void, Delete, destructive confirm.

| Property | Value |
|---|---|
| Fill | `color-mix(danger 8%, card 92%)` |
| Text | `--theme-danger` |
| Border | 1px danger mix |
| Radius | 8px |
| Weight | 700 |

**Streamlit convention (UI-2):** `key="erp_void_*"` or `key="erp_danger_*"` on button container.

---

## 4. Selected Chip

**When:** Transaction type, payment method, currency, report picker, filter toggles, sidebar active nav.

| Property | Value |
|---|---|
| Fill | `--erp-chip-active-bg` (14% info + card) |
| Text | `--erp-chip-active-fg` (`--theme-info`) |
| Border | `--erp-chip-active-border` |
| Radius | 8px |
| Height | Min 36px desktop / 30–40px mobile dense rows |
| Font | 11–12px, weight 700 |

**Streamlit:** `type="primary"` inside chip rows only (not Save).

**Idle chip:** `--erp-chip-idle-*` tokens.

---

## 5. Active Tab

**Desktop `st.tabs`:**

| State | Style |
|---|---|
| Idle | Card bg, border, muted text |
| Active | Selected chip tokens + 2px bottom accent |
| Hover | Border moves toward chip-active |

**Mobile tab bars:** Button chips — same as **Selected Chip** (not solid fill).

---

## 6. Page Banner

**Component:** `section_header_html(title)` → `.erp-section-hdr`

| Property | Value |
|---|---|
| Left bar | 4px `--theme-info` (default) |
| Text | 12px, uppercase, weight 700, `--theme-muted` |
| Spacing | 16px margin below |
| Caption | One `st.caption` line under banner |

**Accent variants** (`accent-success`, `accent-warning`, etc.): workflow/status sections only — not default page titles (UI-2 sweep).

---

## 7. Section Header

**In-page sections:** `.erp-section-hdr` or `st.container(border=True)` + bold title.

Same typography as page banner when using `section_header_html` without replacing page banner.

**Tab intro:** `.erp-tab-intro` — tinted strip below tab bar (Reports, Recon, EOD pattern).

---

## 8. Card

| Property | Value |
|---|---|
| Background | `--theme-card` |
| Border | 1px `--theme-border` |
| Radius | 10px |
| Padding | 12–16px |
| Shadow | None or `--theme-shadow` subtle |

**KPI metrics:** `render_kpi_grid()` → `.erp-kpi-section` + `.kpi-grid` + `.kpi-card` — 16px gap, 76px min-height, 20px section margin; no inline HTML KPI blocks.

**Streamlit:** `st.container(border=True)` or `.card` class.

---

## 9. Table

| Element | Standard |
|---|---|
| Wrapper | Bordered card or themed `stDataFrame` border |
| Header | Muted uppercase 10–11px |
| Body | `--theme-text` |
| Actions | Secondary view/edit; Danger void |
| Export | `render_export_buttons` popover |

---

## 10. Form

| Element | Standard |
|---|---|
| Section wrap | `st.container(border=True)` |
| Labels | Themed `stWidgetLabel`, muted 11px optional micro-labels |
| Fields | 8px radius, `--theme-input-border`, focus ring `--theme-focus` |
| Submit | **Primary Button** at section bottom |
| Spacing | 16px between sections, 8px between fields |

---

## 11. Mobile Action Button

**When:** Row actions in Transaction History, picker grids, quick-create tiles.

| Property | Value |
|---|---|
| Style | Secondary or chip idle |
| Min height | 44px touch |
| Grid | 3–4 column action row at card foot |

**Selected state in pickers:** Selected Chip.

---

## 12. Mobile FAB

**When:** Bottom nav center `+` (New Transaction).

| Property | Value |
|---|---|
| Size | 56px circle |
| Fill | Solid `--theme-info` |
| Icon | `+`, `--erp-on-primary`, 30px |
| Border | 4px `--theme-card` ring |
| Shadow | Info-tinted elevation |

**Bottom nav tabs (not FAB):** Transparent bg; active = `--theme-info` text only; idle = `--theme-muted`.

---

## Frozen references (do not redesign)

Header · Sidebar · Mobile bottom nav · Mobile calculator · Transaction History · Reports Hub · Company Settings

UI-1 aligns **tokens and button/chip grammar** without moving controls on these surfaces.

---

## CSS implementation map (UI-1)

| Concern | File |
|---|---|
| Global tokens | `ui/theme.css` |
| Buttons, chips, tabs, forms | `ui/widgets.css` |
| Mobile AT chips | `ui/mobile_txn.css` (aliases `--erp-chip-*`) |
| Mobile Reports chips | `ui/mobile_reports.css` |
| Bottom nav / FAB | `ui/widgets.css`, `ui/mobile_shell.css` |
| Sidebar nav chips | `ui/theme.css` |
| Section headers | `ui/theme.css`, `ui/section.py` |
| KPI grids | `ui/theme.css` (`.kpi-grid`), `render_kpi_grid()` in `app.py` |
| Token-themed tables | `ui/theme.css` (`.erp-data-table`), `theme_table_html()` in `ui/section.py` |
| Financial statement tables | `ui/theme.css` (`.erp-fin-*`), `financial_statement_table_html()` in `ui/section.py` |

---

## Dark mode visual checklist (manual regression)

Run with **Settings → Theme → Dark** (or system dark). No automated screenshot tests yet — verify these surfaces after any theme/CSS change:

| Surface | What to check |
|---|---|
| Dashboard KPIs | Full currency values visible; muted labels readable |
| New Transaction | Type chips, inputs, labels, flash messages |
| Sales / Expenses / Purchases | Tables, filters, void/danger buttons |
| Banking | Statement import panels, match metrics, bordered cards |
| Recon Health | AR/AP/CC KPI grid shows full TRY amounts; card breakdown table header/body contrast |
| Reports | Tab chips, filter cards, export popover |
| General Ledger / Trial Balance | Dataframe headers not light-gray flash |
| Settings | Selectboxes, toggles, captions |
| Mobile (≤968px) | Bottom nav, hub sheets, calculator — no invisible chip text |

**Token targets (dark):** `--theme-text` body, `--theme-muted` labels, `--theme-card` elevated from `--theme-bg`, borders visible at `--theme-border`. One primary accent (`--theme-info`) for CTAs/chips only.

**Dark mode policy:** Readable and **mono** — same card/border/typography grammar as light mode. KPI amounts and alerts use `--theme-text` on `--theme-card`; reserve `--theme-success` / `--theme-warning` / `--theme-danger` for void/danger buttons and explicit workflow warnings only (not metric tinting or alert backgrounds).

**Anti-patterns:** `st.columns(4)` + `st.metric` for long currency strings (use `render_kpi_grid`); Glide `st.dataframe` where contrast fails (use `theme_table_html` / `_render_theme_df_table` for small read-only breakdowns); hardcoded `#9ca3af` / `#6b7280` meta text (use `var(--theme-muted)`); tinted alert/metric backgrounds in dark mode.

**Glide dataframe tokens:** `widgets.css` + dark `inject_theme_css` set `--gdg-*` vars on `[data-testid="stDataFrame"]`. `.streamlit/config.toml` `[theme.dark]` aligns native Streamlit dataframe chrome when OS dark is active.

---

## Global Readability and Financial Statement Rules

**Policy:** Important financial data must be readable in **both** light and dark mode without hover, without clipping, and without relying on Glide `st.dataframe` defaults.

### Tokens

| Token | Role |
|---|---|
| `--theme-text` | Account names, amounts, body |
| `--theme-caption` | Labels, captions, column headers, codes (readable muted — not faint gray) |
| `--theme-muted` | Legacy alias; prefer `--theme-caption` for UI labels |

### Financial tables (required pattern)

Use `financial_statement_table_html()` from `ui/section.py` — **not** `st.dataframe` — for:

- Balance Sheet, P&L, Trial Balance, General Ledger, Chart of Accounts
- Any read-only table where **code + name + amount** must always show

**HTML classes (styled in `ui/theme.css`):**

| Class | Rule |
|---|---|
| `.erp-fin-table` | Full-width table, zebra rows, horizontal scroll on narrow screens |
| `.erp-fin-code` | Monospace account code; never clipped |
| `.erp-fin-name` | `word-break` / `overflow-wrap`; never ellipsis |
| `.erp-fin-amount` | Right-aligned, tabular nums, `white-space: nowrap` |
| `.erp-fin-row-total` | Bold row, top border — totals distinct from detail |

**Section headers:** `financial_section_header_html()` → `.erp-fin-section-hdr` (token tints only; mono).

**Cash flow activity lines:** `.erp-fin-cf-row` with `.erp-fin-cf-desc` / `.erp-fin-cf-amt`.

### KPI cards

- Use `render_kpi_grid()` — values use `white-space: normal` + `word-break` (no ellipsis).
- Dark mode: KPI amounts stay `--theme-text` (mono); variants do not tint metric values.

### Generic read-only tables

- Small breakdowns (Recon Health card list): `theme_table_html()` → `.erp-data-table`
- Large interactive grids: `st.dataframe` only when sort/filter needed; `widgets.css` enforces cell min-height and wrap

### Forms & chrome

- Labels: `--theme-text` (`widgets.css`)
- Captions: `--theme-caption` (not washed-out gray)
- Selectbox selected value: `--theme-text` on `--theme-card`
- Alerts: mono card (`--theme-card` bg, `--theme-text` body) — status color on border/icon only

### Do not

- Hide account names behind ellipsis or fixed narrow Glide columns
- Use per-page hex colors for financial rows
- Use `st.metric` in tight `st.columns(4)` for long currency strings
- Rely on hover for primary financial figures

---

## Operational Table Readability Rules

**Policy (Sweep 2):** All read-only operational and management-report tables use the same readable HTML path as financial statements. **`st.dataframe` is not used in `app.py`** for display tables.

### Standard helper

```python
_render_readable_df(df, total_last_row=False, status_col="Status")
```

Backed by `readable_dataframe_table_html()` in `ui/section.py`:

- Infers column kinds via `infer_column_kind()` (code / name / amount / text)
- Renders `.erp-fin-table` with wrap-friendly name cells and right-aligned amounts
- Optional `status_col` → row classes `erp-fin-row-over` | `erp-fin-row-ok` | `erp-fin-row-warn`
- Optional `total_last_row=True` → `erp-fin-row-total` on last row (e.g. Trial Balance)

### Paginated tables

`render_paginated_table()` keeps **sort + page controls**; the visible page renders via `_render_readable_df()` (not Glide).

### Small breakdowns

`theme_table_html()` / `_render_theme_df_table()` remain valid for fixed-column Recon Health-style grids.

### Intentional non-table UI (not converted)

| UI | Why kept |
|---|---|
| `st.bar_chart` / `st.line_chart` / Altair | Charts, not tabular data |
| `st.altair_chart` on cash recon variance | Histogram visualization |
| Per-row `st.container` + `st.write` on AR/AP manage sections | Interactive void/pay actions beside each row |

### Column kind inference (summary)

| Kind | Typical columns |
|---|---|
| `code` | Code, ID, JE# |
| `name` | Customer, Vendor, Account, Description, Party, Warnings |
| `amount` | Total, Amount, Debit, Credit, Balance, Budgeted, Actual, Count |
| `text` | Date, Month, Status, Type, Active |
