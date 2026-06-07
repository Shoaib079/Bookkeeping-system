# UI Shell Specification

**Accounting ERP — Streamlit design system**

This document is the single source of truth for UI work in the app. All future pages, widgets, and styling must follow these contracts.

**Platform:** Streamlit only. Do not introduce React, custom SPA shells, or alternate renderers for the app chrome.

**Implementation homes:**

| Concern | Location |
|--------|----------|
| Global layout, header, sidebar, tokens | `ui/theme.css` |
| Main-area Streamlit widgets | `ui/widgets.css` |
| Token injection & bootstrap | `ui/theme.py` → `bootstrap_theme()` |
| Section headers | `ui/section.py` → `section_header_html()` |
| Top header & nav wiring | `app.py` → `render_top_header()`, `main()` sidebar block |
| Nav i18n keys | `registry/nav_labels.py`, `registry/locales/` |
| KPI cards | `app.py` → `render_kpi_grid()` |
| Paginated tables | `app.py` → `render_paginated_table()` |
| Monetary inputs | `app.py` → `amount_input()` |
| Exports | `exports.py` + `render_export_buttons()` |

---

## 1. Header contract

The header is a **fixed app bar** rendered once per authenticated request via `render_top_header()`. It lives in the main content area (not the sidebar).

**DOM (Phase A):** `st.container(key="hdr_shell_row")` wraps the bar. CSS fixes `[class*="st-key-hdr_shell_row"]` (`position: fixed; top: 0; z-index: 10050`). A hidden marker div `.erp-hdr-shell-host.erp-hdr-appname` inside the shell row carries search-open state (`.erp-hdr-shell-search-open`).

### Structure (three columns)

| Zone | Key | Content |
|------|-----|---------|
| Left | `hdr_col_left` | Desktop brand (`hdr_desktop_brand`) only — collapsed on mobile |
| Center | `hdr_col_center` | Mobile title (`hdr_mobile_title`) + search (`hdr_search_panel`) |
| Right | `hdr_col_right` | Toolbar (`hdr_toolbar_row` via `slot="desktop_right"`) |

Inner layout: `st.container(key="hdr_shell_inner")` → `st.columns([2.8, 5.4, 2.8])`. **Single toolbar** in the right column (no duplicate left/mobile toolbar). On mobile (≤968px): hide brand + theme toggle; show title, bell, profile, 🔍.

### Left — brand block

Required markup classes:

- `.erp-hdr-appname` — wrapper
- `.erp-hdr-brand-block` — flex row (logo + identity)
- `.erp-hdr-logo` — gradient icon tile (📊)
- `.erp-hdr-identity` — column stack
- `.erp-hdr-app-title` — **product name** (i18n key `header.app_name`, currently “Accounting ERP”)
- `.erp-hdr-co-subtitle` — **active company display name**

Rules:

- App title is primary (17px, weight 800, `--theme-text`).
- Company name is subtitle (12px, weight 500, `--theme-muted`).
- Both lines truncate with ellipsis; do not wrap in the bar.
- All user-facing strings must be HTML-escaped before `unsafe_allow_html=True`.
- Do **not** duplicate user name, role pill, or company name in the left zone.

### Center — global search

- Widget key: `global_search` (fixed, global).
- `label_visibility="collapsed"`.
- Pill-shaped input (36px height, search icon, max-width 480px).
- Placeholder and label from i18n (`header.search_ph`, `header.search_label`).

### Right — toolbar

Toolbar MUST use a horizontal Streamlit container:

```python
st.container(
    horizontal=True,
    gap="small",
    vertical_alignment="center",
    horizontal_alignment="right",
    width="content",
    key="hdr_toolbar_row",
)
```

Child widgets (order left → right):

| Widget | Key | Type |
|--------|-----|------|
| Role/notification marker | *(markdown only)* | Hidden span for CSS `:has()` |
| Notifications | `hdr_notif_pop` | `st.popover` |
| Theme toggle | `hdr_dark_toggle` | `st.button` (☀️ / 🌙) |
| Profile | `hdr_profile_pop` | `st.popover` (initials label) |

Hidden marker span (required):

```html
<span class="erp-hdr-role-marker erp-hdr-role-{role} [erp-hdr-notif-active]"></span>
```

- `role` ∈ `owner`, `manager`, `cashier`, `partner`, `viewer`.
- Add `erp-hdr-notif-active` when notification count > 0.

Toolbar sizing: bell/theme 36×36px (`border-radius: 10px`); profile 36×36px circle with role-colored background; gap 6px.

Profile popover: profile card → company caption → divider → My Account → company switch → sign out. Popover actions use `use_container_width=True`.

### Header dimensions

| Token / rule | Value |
|--------------|-------|
| `--hdr-h` | 60px desktop; 64px mobile (`max-width: 968px`); 104px when search open |
| `--hdr-bg` | Light `#EEF2F7` / Dark `#1E293B` |
| z-index | 10050 on `hdr_shell_row` |
| Breakpoint | Mobile ≤968px · Desktop ≥969px (`ui/shell.py`) |
| Streamlit native header/toolbar | Hidden |

Main `.block-container` keeps `padding-top: var(--hdr-h)` (plus 8px on mobile).

### Header prohibitions

- No React or iframe header.
- No second fixed bar.
- No hardcoded hex in header HTML.
- Do not move primary navigation into the header.

---

## 2. Sidebar contract

Native Streamlit sidebar (`[data-testid="stSidebar"]`), navigation built in `main()`.

**Planned change (AD-UI-001):** Sidebar and navigation redesign is approved (high priority) but **not started**. Complete [docs/NAVIGATION_AUDIT.md](./docs/NAVIGATION_AUDIT.md) before altering `_NAV_ACCORDION`, mobile hubs, or Reports IA.

### Layout

| Viewport | Behavior |
|----------|----------|
| ≥969px | Always visible, min-width 244px, below header |
| ≤968px | Hidden; bottom tab bar + hub sheets instead |

Surface: `--theme-card` background, `1px solid var(--theme-border)` right border.

### Nav control types

1. **Direct page** — `_nav_direct(page_key)`
2. **Accordion group** — `_nav_group(gkey, pages)`
3. **Section caption** — `_nav_section_caption(i18n_key)`

### Accordion markup (required)

```html
<div class="nav-grp-hdr-mark"></div>
<!-- group header button -->
<div class="nav-ch-open"></div>
<!-- child buttons -->
<div class="nav-ch-close"></div>
```

### Button states

| State | `type` | Visual |
|-------|--------|--------|
| Inactive | `secondary` | Transparent, `--theme-text` |
| Active page | `primary` | Info tint, weight 600 |
| Group header (closed, child active) | `primary` | Highlights collapsed group |
| Group header (otherwise) | `secondary` | Uppercase muted via CSS |

### Session state

| Key | Purpose |
|-----|---------|
| `nav_selection` | Canonical page key (e.g. `"🏠 Home"`) |
| `sidebar_group` | Open accordion id or `None` |

Transient keys (`confirm_*`, `void_*`, `paying_*`, etc.) clear on page change.

### Contextual sidebar

Only **Reports** adds extra filters (`render_sidebar_filters()`).

### Mobile chrome (≤968px only)

Desktop sidebar (≥969px) is unchanged. Mobile uses fixed chrome in `app.py` after page dispatch; CSS in `ui/widgets.css`, `ui/mobile_shell.css`, and `ui/theme.css`.

**People hub:** opened from **More → People** (`open_hub` entry); sheet uses `_MOBILE_HUB_CONFIG["people"]`. Not a bottom-tab item.

**Reports deep-links:** mobile hub sets `mob_reports_tab`; `render_reports()` uses `_render_mobile_reports_tab_bar()` + `_reports_tab_scope()` instead of `st.tabs`.

| Layer | Marker class | Height token |
|-------|----------------|--------------|
| Header | `.erp-hdr-shell-host` | `--hdr-h` (64px mobile; taller when search open) |
| Bottom bar | `.erp-bottom-nav-host` | `--bottom-nav-h` (62px) |
| Hub sheet | `.erp-mobile-hub-host` | Above bottom bar; max-height accounts for header + bottom chrome |

**Bottom bar (5 items):** Home, New (center FAB), Banking, Reports, More — hubs open a sheet above the bottom bar. People pages live under **More**. Sheets filter items with the same `_allowed` set as the desktop sidebar.

**Mobile header:** company name + current page title (center); bell + profile + search toggle (right). Replaces duplicate `st.title` on ≤768px.

**More hub:** Books (accounting pages), Transaction history (Sales / Expenses / Purchases / Recurring — review only), Inventory, Company Settings, Backup, Audit Log.

**Session state:** `mobile_hub_open` — hub key (`banking` \| `reports` \| `people` \| `more`) or `None`. Optional `mob_reports_tab` for Reports deep-link hints.

Main content `.block-container` uses `padding-top: calc(var(--hdr-h) + 8px)` and `padding-bottom: calc(var(--bottom-nav-h) + safe-area + 12px)` on mobile.

### Mobile Add Transaction (Phase 18-MUX — complete)

Calculator / POS-style entry on ≤968px (`erp-at-mobile-host` / `erp_mob_at_panel`). Desktop form unchanged (`erp_at_desktop_host`, hidden via CSS + `_sync_mobile_ui_flag_from_cookie()`). Single save path: `_at_save`. CSS: `ui/mobile_txn.css`. See [ROADMAP.md](./ROADMAP.md) § Phase 18-MUX.

**Dual-host rule:** Mobile widgets use `mob_at_*` keys; desktop uses `at_*`. Never reuse desktop Streamlit keys in the mobile host (both hosts render on every request; CSS hides one).

**Panel flow (bottom sheet):** type tabs → payment/context chips → amount display + SAVE + keypad. Amount uses `at_amount_display` buffer (no `st.text_input` on mobile). Keypad + amount row run inside `@st.fragment` (`_mob_at_render_amount_keypad_fragment`) so digit taps rerun only that fragment; SAVE sets `mob_at_save_clicked` and triggers `st.rerun(scope="app")`.

**Searchable pickers:** Long lists open `mob_at_picker` bottom sheet (`_mob_at_render_grid_picker_sheet`). Kinds: `expense_cat`, `expense_subcat`, `sale_cat`, `sale_subcat`, `purchase_cat`, `purchase_subcat`, `vendor`, `invoice`, `payable`, `bank_acct`, `card_bank`, `bank_pay`.

**Named bank tracking:** When payment method is Bank (Expense, Purchase, Salary, Supplier/Customer Payment), `mob_at_bank_pay_trigger` → `bank_pay` picker sets `at_bank_pay_acct`. Card sales use `card_bank`. `_at_save` calls `_record_named_bank_movement` so Banking page ledger reflects the chosen account.

**Keyed layout rows (CSS grid contract):** `mob_at_topbar`, `mob_at_tabs`, `mob_at_amount_row`, `mob_at_keypad`, `mob_at_pm2`, `mob_at_pm3`, `mob_at_cat_trigger`, `mob_at_subcat_trigger`, `mob_at_vendor_trigger`, `mob_at_picker_hdr`, `mob_at_picker_grid` — see `tests/test_mobile_layout_contract.py`.

**Smoke script:** `scripts/browser_mobile_at_keypad.py` (Playwright, requires `streamlit run app.py` on `:8501`).

---

## 3. Navigation hierarchy

### Canonical page keys

Routing uses stable strings (emoji + English name). Display text is localized via `registry/nav_labels.py`.

**Never** change a canonical key without migrating `nav_selection` and `_PAGE_DISPATCH`.

### Sidebar order

```
🏠 Home                          [direct]
➕ New Transaction               [direct]
── nav.sidebar.section_work ──
  ▸ Record transactions          [transactions]
🏦 Banking                       [direct]
  ▸ Customers & suppliers        [people]
📦 Inventory                     [direct, module-gated]
── nav.sidebar.section_reports ──
📊 Reports                       [direct]
  ▸ Close your day               [close_day]
── nav.sidebar.section_advanced ──
  ▸ Books & accounting           [accounting]
  ▸ Team & partners              [team]
  ▸ Settings                     [settings]
```

### Accordion groups

| Group key | Label i18n | Pages |
|-----------|------------|-------|
| `transactions` | `nav.group.transactions` | Sales, Expenses, Purchases, Recurring Expenses |
| `people` | `nav.group.people` | Customers, Vendors, Receivables, Payables |
| `close_day` | `nav.group.close_day` | Cash Reconciliation, End-of-Day Close |
| `accounting` | `nav.group.accounting` | GL, COA, Journal, Trial Balance, Fiscal Periods, Year-End Close, Budget, Recon Health, Opening Balances |
| `team` | `nav.group.team` | Partner Accounts, Workers |
| `settings` | `nav.group.settings` | Company Settings, Members, Audit Log, Backup & Restore |

### Header-only

`👤 My Account` — profile popover, not sidebar.

### Role gating

`_ROLE_PAGES` by `active_company_role`. Invalid selection resets to `🏠 Home`.

### Module gating

Hide nav when disabled: Inventory, Partner Accounts, Budget (`get_module_state`). Posting unchanged.

### In-page sub-nav

Use session keys (`banking_section`, `advanced_subpage`, `my_account_tab`). Do not replace sidebar keys.

---

## 4. Card styles

### Generic card (`.card`)

Background `--theme-card`, border `1px solid var(--theme-border)`, radius 10px, padding 12px.

### KPI card (`render_kpi_grid`)

| Element | Style |
|---------|-------|
| Grid | `minmax(240px, 1fr)`, gap 12px |
| `.kpi-label` | 11px, 600, `--theme-muted` |
| `.kpi-value` | 22px, 800; use `variant` not hex |
| `.kpi-sub` | 10px, `--theme-muted` |

Variants: `success`, `danger`, `warning`, `info`, `purple`, `teal`.

### Section header (`section_header_html`)

4px left border, 12px uppercase, `--theme-muted`, margin-bottom 16px. Accents: `info`, `success`, `danger`, `warning`, `purple`, `teal`.

### Banner (`.banner`)

`.banner-primary` or `.banner-info` gradient; padding 18px 24px, radius 14px.

### Bordered container

`st.container(border=True)` → card surface, radius 10px, padding `0.75rem 1rem`.

### Transaction panels

Use `.txn-type-badge`, `.txn-tip-box`, `.txn-details-icon` with variants (`sale`, `expense`, `purchase`, etc.).

### Prohibitions

No `#ffffff` / light-only pastels. Use `color-mix(..., var(--theme-card))`.

---

## 5. Button hierarchy

| Kind | Use |
|------|-----|
| `type="primary"` | Submit, save, post, active nav |
| `type="secondary"` | Cancel, back, destructive, inactive nav |
| `use_container_width=True` | Sidebar, popovers, full-width forms |

Destructive: secondary + confirmation dialog; never primary blue.

Header toolbar: 36px icon buttons. Sidebar: transparent/primary tint, not main-area blue fill.

Exports: `render_export_buttons(df, prefix)`.

One primary per logical form section.

---

## 6. Table standards

### `render_paginated_table(df, key_prefix)`

| Control | Key suffix |
|---------|------------|
| Sort | `{key_prefix}_sort_cols` |
| Ascending | `{key_prefix}_asc` |
| Page size | `{key_prefix}_page_size` (10/20/50/100) |
| Page | `{key_prefix}_page` |

Display: `st.dataframe(..., use_container_width=True)` + `table.showing_rows` caption.

Empty: `st.info(_t("table.no_records"))`.

### Amount classes

`.table-amount`, `.amt-pos`, `.amt-neg`, `.amt-zero`.

### Exports

`df_to_excel_bytes` / `df_to_pdf_bytes` via `render_export_buttons`.

---

## 7. Theme tokens

Source: `ui/theme.py` + `ui/theme.css`. Use only `var(--token)`.

### Core

| Token | Light | Dark |
|-------|-------|------|
| `--hdr-bg` | `#EEF2F7` | `#1E293B` |
| `--theme-bg` | `#F8FAFC` | `#0B1220` |
| `--theme-card` | `#FFFFFF` | `#0F1724` |
| `--theme-border` | `#E6E9EE` | `#1F2937` |
| `--theme-text` | `#0F172A` | `#E6EEF6` |
| `--theme-muted` | `#475569` | `#94A3B8` |

### Semantic

`--theme-success`, `--theme-danger`, `--theme-warning`, `--theme-info`, `--theme-purple`, `--theme-teal`

### Inputs

`--theme-input-border`, `--theme-focus`, `--theme-shadow`, `--theme-banner-primary-start/end`

### Roles

`--role-owner`, `--role-manager`, `--role-cashier`, `--role-partner`, `--role-viewer`, `--role-default`

### Layout

`--hdr-h`: 60px

New tokens: add to `theme.py`, `theme.css`, and tests.

---

## 8. Spacing standards

| Element | Value |
|---------|-------|
| Header padding | 16px horizontal |
| Toolbar gap | 6px |
| Sidebar width (desktop) | 244px min |
| Card padding | 12px (14px KPI) |
| Section margin-bottom | 16px |
| Banner margin-bottom | 18px |
| Main vertical block gap | 0.5rem |

### Radii

Buttons 8px; cards/forms 10px; banners 14px; search pill 99px; profile circle 50%.

### Page rhythm

Dev stripe → title/banner → section header + KPIs → content → expanders.

---

## 9. Light / dark mode rules

### Priority

1. `st.session_state["dark_mode"]` (header toggle)
2. DB: `user_pref_{user_id}_theme`
3. `inject_theme_css()` (wins over CSS)
4. `prefers-color-scheme` fallback

### Bootstrap

`bootstrap_theme()` on every `main()`: load CSS → DB pref → inject vars.

### Authoring

| Do | Don't |
|----|-------|
| `var(--theme-*)` | Hardcode `#fff` / `#f3f4f6` |
| `color-mix` tints | Light-only pastel blocks |
| Test both modes | Assume white cards |

Portaled widgets (select, popover) styled globally in `widgets.css`.

---

## 10. Widget key naming conventions

CSS hooks: `[class*="st-key-{key}"]` (Streamlit ≥1.58).

**Streamlit 1.58 layout DOM:** `st.columns` children use `[data-testid="stColumn"]` (not legacy `div[data-testid="column"]`). Row flex parents still expose `[data-testid="stHorizontalBlock"]`. Shell CSS in `ui/theme.css`, `ui/mobile_shell.css`, and `ui/widgets.css` must target `stColumn` or keyed containers — otherwise mobile header chrome lays out off-screen.

### Reserved globals

| Key | Scope |
|-----|-------|
| `global_search` | Header |
| `hdr_*` | Header toolbar & profile |
| `nav_btn_{page_key}` | Sidebar pages |
| `grp_btn_{gkey}` | Accordion headers |

### Page-scoped

```
{page}_{entity}_{action}
{key_prefix}_sort_cols | _asc | _page_size | _page
```

Examples: `sales_void_confirm_42`, `banking_import_page_size`, `upload_form_sale_15`.

### Transient (cleared on nav)

`confirm_`, `void_`, `paying_`, `deactivate_`, `edit_`, `txh_void_*`, `um_*`

### Rules

1. Lowercase snake_case
2. Include entity id for row actions
3. Unique per render path
4. No PII in keys
5. `hdr_*` and `nav_btn_*` reserved for shell
6. Monetary fields: `amount_input(..., key=...)` not `st.number_input`

---

## Compliance checklist

- [ ] Streamlit only for shell
- [ ] Tokens in both light/dark
- [ ] Canonical nav keys + i18n
- [ ] Role + module gating
- [ ] `render_paginated_table` / `amount_input` / `section_header_html`
- [ ] Widget keys follow conventions
- [ ] No new inline hex

---

| Spec version | 1.1 |
| Phase | 16A–18-MUX |
| Updated | 2026-06-05 |
