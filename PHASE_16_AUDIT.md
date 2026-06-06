# Phase 16 — UI / theme audit

**Status:** 16A–16E complete (June 2026) — phase done  
**Companion:** `ui/theme.css`, `ui/theme.py`, `ui/section.py`, `.streamlit/config.toml`

---

## 16A delivered

| Item | Location |
|------|----------|
| Extracted global CSS | `ui/theme.css` (~430 lines) |
| Token injection + DB theme load | `ui/theme.py` — `bootstrap_theme()`, `LIGHT_ROOT_VARS` / `DARK_ROOT_VARS` |
| Section header helper (for 16C) | `ui/section.py` — `section_header_html()` |
| Streamlit baseline theme | `.streamlit/config.toml` |
| App wiring | `app.py` — `bootstrap_theme()` at start of `main()` |
| Tests | `tests/test_phase16a_theme.py` |

---

## Design recommendations (apply in 16B–16D)

### High impact — do in 16B

1. **Theme native widgets** — Add CSS blocks for `stTextInput`, `stSelectbox`, `stNumberInput`, `stTabs`, `stExpander`, and `[data-testid="stVerticalBlockBorderWrapper"]` (bordered containers) using `--theme-card`, `--theme-border`, `--theme-text`. Today only dataframes and header search are themed; forms still flash Streamlit defaults.

2. **Pin Streamlit version** — Layout CSS relies on `:has()` and `data-testid` values (e.g. `stSidebarCollapsed`). Pin `streamlit>=1.28,<2` in `requirements.txt` and re-run visual smoke after upgrades.

3. **“System” theme (16D)** — Add third option in My Account: Light / Dark / System. Map System to `@media (prefers-color-scheme)` only when user has not toggled manually this session.

### High impact — do in 16C

4. **Replace inline section headers** — ~82 blocks use `border-left:4px solid #3b82f6` + `#6b7280`. Migrate to:

   ```python
   st.markdown(section_header_html(_t("company_setup.title")), unsafe_allow_html=True)
   ```

   Accents: `info` (blue), `success` (green), `danger` (red), `purple` (equity), `teal` (banking).

5. **Stop adding new hex in `app.py`** — Grep gate in review: prefer `var(--theme-*)` or helper classes (`.amt-pos`, `.kpi-card`).

6. **Login + company picker** — Apply `bootstrap_theme` on those screens (already runs before gate). **Recommendation:** add a light branded card layout for login (centered, max-width 400px) — looks more professional than full-width defaults.

### Header / sidebar — 16D

7. **Restore company + user in header** — Left column is emoji-only today. **Suggestion:** `📊 Accounting ERP · {company} · {user}` with truncation on narrow widths — helps multi-company users.

8. **Mobile sidebar** — Fixed 244px + hidden collapse hurts phones. **Recommendation:** drawer (hamburger) below 768px; keep desktop “always open”.

9. **DEVELOPMENT_MODE banner** — Style as `st.status` or a slim top stripe below the app bar, not a floating caption in content.

### Lower priority

10. **PDF exports** — `exports.py` uses ReportLab with its own colors; audit separately in 16E.

11. **Pandas Styler (Budget)** — Attribute overrides exist; verify after 16B widget pass.

12. **KPI min width** — `minmax(240px, 1fr)` is good on desktop; 16D should add `@media (max-width: 640px) { .kpi-grid { grid-template-columns: 1fr; } }`.

---

## Page audit matrix

Tier = priority for 16C screenshot pass. **Hex** = approximate `#` count in `render_*` function body (grep Jun 2026).

| Tier | Function | Nav / area | Hex~ | Notes |
|------|----------|------------|------|-------|
| P0 | `render_dashboard` | Home | high | KPI grid, banners, charts |
| P0 | `render_sales` | Sales | med | Forms, void |
| P0 | `render_expenses` | Expenses | med | Payment labels |
| P0 | `render_add_transaction` | Add Transaction | high | `st.title` + type badge (Jun 2026); form hex remains for 16C |
| P0 | `render_reports` | Reports hub | high | Tabs, many sub-reports |
| P0 | `render_general_ledger` | GL | low | Tables |
| P0 | `render_trial_balance` | Trial Balance | low | |
| P0 | `render_banking` | Banking | med | CSV import |
| P1 | `render_purchases` | Purchases | med | |
| P1 | `render_payables` | Payables | med | |
| P1 | `render_receivables` | Receivables | med | |
| P1 | `render_customers` | Customers | med | |
| P1 | `render_vendors` | Vendors | med | |
| P1 | `render_cash_reconciliation` | Cash recon | high | 4 tabs |
| P1 | `render_end_of_day_close` | EOD | med | |
| P1 | `render_transaction_history` | Txn history | high | Detail panel |
| P2 | `render_year_end_close` | YEC | med | |
| P2 | `render_fiscal_periods` | Fiscal | med | |
| P2 | `render_opening_balances` | OB | med | |
| P2 | `render_partner_accounts` | Partners | med | |
| P2 | `render_equity_movements` | Equity | med | |
| P2 | `render_chart_of_accounts` | COA | low | |
| P2 | `render_budget` | Budget | med | Styler rows |
| P2 | `render_inventory` | Inventory | med | |
| P2 | `render_journal_entries` | JE | low | |
| P2 | `render_audit_log` | Audit | low | |
| P2 | `render_company_settings` | Company Setup | med | Section headers |
| P2 | `render_user_management` | Members | med | |
| P2 | `render_backup_restore` | Backup | low | |
| P2 | `render_my_account` | My Account | low | |
| P2 | `render_settings` | Legacy settings | med | |
| P2 | `render_advanced` | Advanced | low | |
| P2 | `render_login` | Auth | low | Pre-theme bootstrap |
| P2 | `render_company_picker` | Picker | low | |

**Shared helpers (all tiers):** `render_kpi_grid`, `render_export_buttons`, `render_paginated_table`, `render_global_style` → moved to `ui/`.

---

## Token reference

| Token | Light | Dark | Use |
|-------|-------|------|-----|
| `--theme-bg` | #F8FAFC | #0B1220 | Page |
| `--theme-card` | #FFFFFF | #0F1724 | Cards, inputs |
| `--theme-border` | #E6E9EE | #1F2937 | Dividers |
| `--theme-text` | #0F172A | #E6EEF6 | Body |
| `--theme-muted` | #475569 | #94A3B8 | Captions, section labels |
| `--theme-info` | #2563EB | #60A5FA | Links, primary accent |
| `--theme-input-border` | #CBD5E1 | #334155 | Search, fields (16B extend) |
| `--theme-banner-primary-*` | blue gradient | blue gradient | Dashboard banners |

Full list in `ui/theme.css` `:root` and `ui/theme.py` `LIGHT_ROOT_VARS` / `DARK_ROOT_VARS`.

---

### Phase 16B — Native widgets ✅

| Item | Location |
|------|----------|
| Widget stylesheet | `ui/widgets.css` — inputs, selects, tabs, expanders, forms, alerts, metrics, bordered containers |
| Bundled in inject | `ui/theme.py` `load_theme_css()` (hot-reloads on file change) |
| Streamlit pin | `requirements.txt` — `streamlit>=1.28,<2` |
| Tests | `tests/test_phase16a_theme.py` (widgets bundle checks) |

**16B follow-up fixes (dark-mode contrast):**

- **Critical selector fix** — Streamlit 1.58 main area is `data-testid="stMain"`, not `section.main`. All 98 widget rules were no-ops until corrected → fixed invisible labels / dropdown text app-wide.
- **st.title / headings** forced to `--theme-text` (config.toml ships a static light textColor).
- **Header search** uses `--theme-bg` + placeholder/focus styling for header-bar contrast.
- **DEVELOPMENT_MODE** banner → themed `.dev-mode-stripe` (was invisible `st.caption`).
- **Expander headers** — global `summary, summary *` color so labels show at rest (were hover-only).
- **Add Partner** — converted expander → section header + bordered form (no hover dependency).
- **Add Transaction** — `txn-type-badge` / `txn-tip-box` / `txn-details-icon` classes replace light-only inline backgrounds.
- Warning hex (`#f59e0b` etc.) added to legacy color map.

### Phase 16C — Page sweep + header migration ✅

| Item | Location |
|------|----------|
| Page banners → `section_header_html()` | 18 blocks across audit, txn history, partner, equity, opening balances, add-txn recent, advanced, recon, EOD, reports, members, wizard, company setup, settings + 3 sub-headers |
| Section-label helpers (`_section`/`_sec`) | `color:#6b7280` → `var(--theme-muted)` (accent border kept) |
| Muted caption labels | partner/equity card captions, audit/JE diff rows |
| Dark text on theme bg | `#111827` txn party names + `#374151` login heading / audit detail → `var(--theme-text)` / `var(--theme-muted)` |
| Neutral KPI values | 13 `"color": "#6b7280"` dict entries → `var(--theme-muted)` |

**Deliberately left as-is (hardcoded light pastel backgrounds — dark text is correct on them; full bg theming is a future enhancement):**

- Aging-bucket chips (payables/receivables) — `background:#f0fdf4 / #fef9c3 / #fee2e2`.
- P&L / cash-flow statement section headers — `#f0fdf4 / #fef2f2 / #eff6ff` banners with dark-green/red/blue text + `#6b7280` in/out subtitles.
- Status badges (`#d1fae5/#065f46`, `#fee2e2/#991b1b`) and white-on-color pills/avatars/banners.
- Budget pandas `Styler` row tints (`#fee2e2/#f0fdf4`) — tracked under audit item 11 / 16E.
- `#9ca3af` footnote text — legible in both modes; left for a later consistency pass.

**Known i18n gaps surfaced (not theming):** "Recent Transactions" and "Net Owner Equity Movement" are still hardcoded English (no locale key).

### Phase 16D — Header text, responsive layout ✅

| Item | Location |
|------|----------|
| Header identity restored | `render_top_header` left zone → `📊 Accounting ERP · {company} · {user}` (HTML-escaped) using `.erp-hdr-brand/.erp-hdr-co/.erp-hdr-user-name` |
| Progressive truncation | `.erp-hdr-co/.erp-hdr-user-name` ellipsis; `@media` drops user ≤900px, company + brand ≤640px |
| Responsive KPI grid | `@media (max-width: 640px) { .kpi-grid { grid-template-columns: 1fr; } }` |
| Mobile sidebar drawer | desktop rules scoped `@media (min-width: 769px)`; `@media (max-width: 768px)` makes sidebar a fixed overlay + re-enables Streamlit's native expand control |
| DEVELOPMENT_MODE banner | already slim themed stripe (16B) |

> **Device note:** mobile drawer relies on Streamlit's native collapse control testids (`stSidebarCollapsedControl` / `collapsedControl`); verify on a real ≤768px viewport after Streamlit upgrades.

### Phase 16E — Pastel-banner theming + sign-off ✅

| Item | Location |
|------|----------|
| Aging-bucket chips | payables + receivables → `color-mix(... var(--theme-card))` tint, accent border, `var(--theme-text)`/`var(--theme-muted)` text |
| P&L section headers | income → success tint, expense → danger tint |
| Cash-flow headers | operating → success, financing → info; in/out subtitle → `var(--theme-muted)` |
| Balance-sheet sections | `_bs_section` calls → info/warning/purple token tints; titles now carry the accent color |
| Balanced/imbalanced badge | success/danger token tints |
| Budget `Styler` rows | over → danger tint, on-track → success tint (CSS vars resolve inside inline cell styles) |
| Tests | `tests/test_phase16a_theme.py` — responsive, header, no-hardcoded-pastel guards (14 theme tests) |

**Remaining acceptable hex (decorative, legible both modes):** bright status dot (`#10b981`), white-on-color pills/avatars/banners, `#9ca3af` footnotes.

**16E follow-up — sidebar surface:** widget rules in `ui/widgets.css` are all scoped to `[data-testid="stMain"]`, so the sidebar kept Streamlit's fixed light `secondaryBackgroundColor` and stayed light in dark mode. Added a sidebar-surface block in `ui/theme.css` — background `var(--theme-card)`, right border `var(--theme-border)`, nav-button text `var(--theme-text)`, hover/active tints via `color-mix(var(--theme-info)…)`. Group-header labels keep `var(--theme-muted)` (more-specific `:has()` selector wins).

## 16C–16E checklist

- [x] **16B** — Widget + bordered container dark mode
- [x] **16C** — P0/P1 page sweep + `section_header_html` migration
- [x] **16D** — Header text, mobile drawer, responsive KPI grid
- [x] **16E** — Pastel-banner theming + contrast pass + tests + ROADMAP sign-off

---

## Acceptance criteria (phase 16 complete)

1. User light/dark persists; matches header toggle and My Account.
2. P0 pages: no large white patches in dark mode.
3. Mobile: one P0 flow usable at 390px width.
4. Tests green; Streamlit version pinned.
