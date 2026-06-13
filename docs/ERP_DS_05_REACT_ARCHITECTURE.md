# ERP-DS-05 — React Architecture Mapping

**Phase:** DS-5  
**Mode:** Architecture specification — no implementation  
**Date:** 2026-06-05  
**Prerequisite:** [ERP_DS_04_MASTER_DESIGN_SYSTEM.md](./ERP_DS_04_MASTER_DESIGN_SYSTEM.md)

---

## 1. Architecture overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        React SPA (Vite/Next)                     │
├─────────────────────────────────────────────────────────────────┤
│  Layouts: DesktopShell │ MobileShell │ AuthLayout               │
├─────────────────────────────────────────────────────────────────┤
│  Router (TanStack Router or React Router v7)                     │
│    └─ route guards: role + module flags from registry mirror     │
├─────────────────────────────────────────────────────────────────┤
│  Data layer: TanStack Query + FastAPI client                     │
│    └─ optional Refine hooks for CRUD resources                   │
├─────────────────────────────────────────────────────────────────┤
│  Components: shadcn/ui + erp/* (DS-4)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ REST / JSON
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI (future)                             │
│  /api/v1/sales  /banking  /reports  /settings  /auth           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Route map (Streamlit → React)

**Source of truth:** `registry/nav_keys.py` — 42 page keys.

### URL convention

```
/{locale?}/{page-key-slug}
```

Examples:
- `/home`
- `/banking`
- `/banking/import`
- `/reports/profit-loss`
- `/settings/company`

### Full route table

| NAV constant | Streamlit handler | React path | Layout | Notes |
|--------------|-------------------|------------|--------|-------|
| `NAV_HOME` | `render_dashboard` | `/home` | Both | KPI + activity |
| `NAV_NEW_TRANSACTION` | `render_add_transaction` | `/transactions/new` | Both | Mobile: bottom panel |
| `NAV_TXN_LEDGER` | `render_transaction_history` | `/ledger` | Both | Card list mobile |
| `NAV_SALES` | `render_sales` | `/sales` | Desktop | CRUD list |
| `NAV_EXPENSES` | `render_expenses` | `/expenses` | Desktop | |
| `NAV_PURCHASES` | `render_purchases` | `/purchases` | Desktop | |
| `NAV_STAFF_EXPENSE_CAPTURE` | `render_staff_expense_capture` | `/expenses/staff` | Both | |
| `NAV_RECURRING_EXPENSES` | `render_recurring_expenses` | `/expenses/recurring` | Desktop | |
| `NAV_CASH_RECONCILIATION` | `render_cash_reconciliation` | `/close/cash-recon` | Both | |
| `NAV_EXTERNAL_SALES_VERIFICATION` | `render_external_sales_verification` | `/close/external-sales` | Both | |
| `NAV_END_OF_DAY_CLOSE` | `render_end_of_day_close` | `/close/eod` | Both | |
| `NAV_CUSTOMERS` | `render_customers` | `/people/customers` | Desktop | |
| `NAV_VENDORS` | `render_vendors` | `/people/vendors` | Desktop | |
| `NAV_RECEIVABLES` | `render_receivables` | `/people/receivables` | Both | |
| `NAV_PAYABLES` | `render_payables` | `/people/payables` | Desktop | |
| `NAV_INVENTORY` | `render_inventory` | `/inventory` | Desktop | Module gate |
| `NAV_BANKING` | `render_banking` | `/banking` | Both | Sub-routes below |
| — | `banking_section=cockpit` | `/banking/recon` | Both | Default |
| — | `banking_section=import` | `/banking/import` | Both | |
| — | `banking_section=accounts` | `/banking/accounts` | Desktop | |
| — | `banking_section=settings` | `/banking/settings` | Desktop | |
| `NAV_RECON_HEALTH` | `render_reconciliation_health` | `/banking/health` | Both | |
| `NAV_REPORTS` | `render_reports` | `/reports` | Desktop | Tab container |
| `NAV_PROFIT_LOSS` | `render_profit_loss` | `/reports/profit-loss` | Both | |
| `NAV_BALANCE_SHEET` | `render_balance_sheet` | `/reports/balance-sheet` | Both | |
| `NAV_CASH_FLOW` | `render_cash_flow` | `/reports/cash-flow` | Both | |
| `NAV_GENERAL_LEDGER` | `render_general_ledger` | `/books/gl` | Desktop | Virtualized |
| `NAV_TRIAL_BALANCE` | `render_trial_balance` | `/books/trial-balance` | Desktop | |
| `NAV_JOURNAL_ENTRIES` | `render_journal_entries` | `/books/journal` | Desktop | |
| `NAV_CHART_OF_ACCOUNTS` | `render_chart_of_accounts` | `/books/coa` | Desktop | |
| `NAV_FISCAL_PERIODS` | `render_fiscal_periods` | `/books/periods` | Desktop | |
| `NAV_YEAR_END_CLOSE` | `render_year_end_close` | `/books/year-end` | Desktop | |
| `NAV_BUDGET` | `render_budget` | `/books/budget` | Desktop | Module gate |
| `NAV_OPENING_BALANCES` | `render_opening_balances` | `/books/opening` | Desktop | |
| `NAV_PARTNER_ACCOUNTS` | `render_partner_accounts` | `/people/partners` | Desktop | Module gate |
| `NAV_WORKERS` | `render_workers` | `/people/workers` | Desktop | |
| `NAV_COMPANY_SETTINGS` | `render_company_settings` | `/settings/company` | Both | |
| `NAV_MEMBERS` | `render_user_management` | `/settings/members` | Desktop | |
| `NAV_PERMISSIONS` | `render_permissions_management` | `/settings/permissions` | Desktop | |
| `NAV_AUDIT_LOG` | `render_audit_log` | `/settings/audit` | Desktop | |
| `NAV_BACKUP_RESTORE` | `render_backup_restore` | `/settings/backup` | Desktop | |
| `NAV_MY_ACCOUNT` | `render_my_account` | `/account` | Both | |
| Recipe costing (4) | `render_recipe_*` | `/recipe/*` | Desktop | Module gate |

---

## 3. Layout shells

### DesktopShell

```
┌────────────────────────────────────────────┐
│ AppHeader (company, search/Cmd+K, user)    │
├──────────┬─────────────────────────────────┤
│ Sidebar  │ <Outlet /> page content         │
│ 240px    │                                 │
│ accordion│                                 │
└──────────┴─────────────────────────────────┘
```

**Maps from:** `_render_navigation_tree()` + `_NAV_ACCORDION`

**Sidebar groups → routes:**

| Accordion key | Routes |
|---------------|--------|
| `transactions` | sales, expenses, purchases, recurring, staff |
| `people` | customers, vendors, receivables, payables |
| `close_day` | cash-recon, external-sales, eod |
| `recipe_costing` | recipe/* |
| `statements` | reports/profit-loss, balance-sheet, cash-flow |
| `accounting` | books/* |
| `team` | partners, workers |
| `settings` | settings/* |

### MobileShell

```
┌─────────────────────────┐
│ MobileHeader            │
├─────────────────────────┤
│ <Outlet />              │
├─────────────────────────┤
│ BottomNav (5 slots)     │
└─────────────────────────┘
     + HubSheet overlay
     + FAB → /transactions/new
```

**Maps from:** `_MOBILE_BOTTOM_NAV` + `_MOBILE_HUB_CONFIG`

### Hub sheet routes (mobile)

| Hub key | Sheet content | Deep links |
|---------|---------------|------------|
| `money` | Close + Bank sections | `/close/*`, `/banking/*` |
| `reports` | Statements + Ledger + Summaries | `/reports/*`, `/ledger` |
| `more` | People shortcut + Books + Admin | `/people/*`, `/books/*`, `/settings/*` |
| `people` | CRM routes | `/people/*` |

**State today:** `st.session_state["mobile_hub_open"]`  
**React:** URL query `?hub=money` or dedicated `/hub/money` overlay route.

---

## 4. Navigation state migration

| Streamlit session key | React equivalent |
|-----------------------|------------------|
| `nav_selection` | `route.pathname` + route params |
| `sidebar_group` | Sidebar UI state (local) |
| `mobile_hub_open` | Overlay route or query param |
| `_erp_mobile_ui` | `useMediaQuery('(max-width: 968px)')` + user preference |
| `banking_section` | `/banking/:section` |
| `mob_reports_tab` | `/reports?tab=sales` |
| `date_from`, `date_to` | URL search params or Zustand filter store |
| `txh_active_view` | `/ledger/:id` |
| `mob_at_picker` | Nested route or sheet state |

**Page transition cleanup (Streamlit):** clears `confirm_*`, `void_*`, hub sheets.  
**React:** `useEffect` on route change + React Query cache invalidation rules.

---

## 5. Command palette

**Streamlit today:** None (global search on Transaction History + Reports only).

**React target:** shadcn `Command` dialog.

| Group | Items |
|-------|-------|
| Pages | All `NAV_*` routes with i18n labels |
| Actions | New Transaction, Import Statement, EOD Close |
| Recent | Last 5 visited routes (localStorage) |
| Search | Ledger fuzzy search (debounced API) |

**Keyboard:** `Cmd+K` / `Ctrl+K`  
**Mobile:** Header search icon → full-screen command sheet.

---

## 6. Tables

| Surface | Streamlit | React |
|---------|-----------|-------|
| Transaction Ledger desktop | `desktop_txn_history.css` grid | TanStack Table, fixed columns |
| Transaction Ledger mobile | Card + action bar | `<ListRow>` + `<ActionBar>` |
| General Ledger | HTML table / dataframe | **Virtualized** TanStack Table |
| Financial statements | `financial_statement_table_html` | `<FinTable>` static HTML or table |
| Banking statement | `ui/banking.py` panels | Queue list + detail split |
| Reports export | `render_export_buttons` | API `/export?format=xlsx` |

### Column patterns (ledger desktop)

Weights from `_TXH_DESKTOP_COL_WEIGHTS`:
`date 0.68 · type 0.88 · party 1.05 · description 3.4 · amount 1.2 · status 0.92 · actions 0.72`

---

## 7. Mobile behavior map

| Pattern | Streamlit CSS/JS | React component |
|---------|------------------|-----------------|
| Bottom nav | `mobile_shell.css` | `<BottomNav>` |
| Hub sheet | `_render_mobile_hub_sheet` | Radix `<Sheet side="bottom">` |
| AT keypad panel | `mobile_txn.css` fixed panel | `<TransactionEntryPanel>` |
| Picker sheet | `erp-at-picker-open-host` | `<PickerSheet>` |
| Profile sheet | `mob_profile_open` | `<ProfileSheet>` |
| Company switch | `mob_co_switch_open` | `<CompanySwitcher>` |
| KPI grid | `mobile_components.css` | `<KpiGrid>` |
| List card | `mobile_list_row_html` | `<ListRow>` |
| TXH action bar | 4-col grid 44px | `<ActionBar>` |
| Date filters | `erp_mob_rpt_filters` | `<DateRangeBar>` |

**Breakpoint:** 968px — matches `MOBILE_VIEWPORT_NARROW_MAX_PX` in `ui/theme.py`.

---

## 8. Data layer (FastAPI)

### API shape (proposed)

```
GET  /api/v1/me
GET  /api/v1/company/settings
GET  /api/v1/modules                    # registry mirror
GET  /api/v1/transactions?from&to&q
POST /api/v1/transactions
GET  /api/v1/transactions/:id
POST /api/v1/transactions/:id/void
GET  /api/v1/banking/accounts
GET  /api/v1/banking/statements/:id/lines
POST /api/v1/banking/match
GET  /api/v1/reports/profit-loss?from&to
GET  /api/v1/reports/balance-sheet?as_of
GET  /api/v1/reports/cash-flow?from&to
GET  /api/v1/ledger?account&from&to
```

### TanStack Query keys

```typescript
['transactions', { from, to, q }]
['transaction', id]
['banking', 'queue', accountId]
['reports', 'pnl', { from, to }]
['settings', 'company']
['modules']
```

### Refine option

```typescript
// CRUD resources — good fit
resources: ['customers', 'vendors', 'coa', 'members']

// Custom pages — no resource wrapper
['banking/recon', 'reports/pnl', 'close/eod']
```

---

## 9. Auth & access control

| Streamlit | React |
|-----------|-------|
| `_current_user()` | JWT/session cookie via FastAPI |
| `_can("edit_transaction")` | `usePermission('edit_transaction')` |
| `_NAV_ROLE_PAGES` | Route guard middleware |
| `_MODULE_NAV_PAGES` | `useModule('inventory')` hook |
| `registry/service.py` `get_effective_config()` | `GET /api/v1/config/effective` |

---

## 10. i18n

| Streamlit | React |
|-----------|-------|
| `registry/locales/` + `_t()` | `react-i18next` + same JSON/message keys |
| `registry/nav_labels.py` | `nav.*` namespace |
| `registry/locales/transactional.py` | `txn.*` namespace |

**Rule:** Reuse existing message keys — do not rename during migration.

---

## 11. Component import map

| Streamlit helper | React component | DS-4 § |
|------------------|-----------------|--------|
| `section_header_html` | `<SectionHeader>` | §1 |
| `page_report_banner_html` | `<PageBanner>` | §1 |
| `financial_section_header_html` | `<FinSectionHeader>` | §1 |
| `financial_statement_table_html` | `<FinTable>` | §5.2 |
| `mobile_kpi_chip_html` | `<KpiChip>` | §5.1 |
| `mobile_kpi_grid_html` | `<KpiGrid>` | §5.1 |
| `mobile_list_row_html` | `<ListRow>` | §5.8 |
| `mobile_status_pill_html` | `<StatusPill>` | §5.7 |
| `mobile_empty_state_html` | `<EmptyState>` | §5.9 |
| `mobile_highlight_banner_html` | `<SummaryBanner>` | §5.12 |
| `mono_role_pill_html` | `<RolePill>` | §7 |
| `aging_buckets_html` | `<AgingBuckets>` | §7 |
| `render_export_buttons` | `<ExportMenu>` | §7 |

---

## 12. Migration phases (DS-6 sub-phases)

| Sub-phase | Scope | Streamlit status |
|-----------|-------|----------------|
| 6a | Auth + shell + home | Streamlit remains parallel |
| 6b | New Transaction + Ledger | Mobile-first |
| 6c | Banking + reconciliation | Highest complexity |
| 6d | Reports (P&L, BS, CF) | FinTable parity |
| 6e | Books (GL, COA, JE) | Virtualized tables |
| 6f | Settings + admin | CRUD resources |
| 6g | Deprecate Streamlit UI | Feature flag per company |

**Rule:** No visual guessing — every component cites DS-04 §.

---

## 13. What stays server-side

| Concern | Stay in FastAPI/Python |
|---------|------------------------|
| Double-entry posting | `create_journal_entry` |
| Schema migrations | SQLAlchemy |
| PDF/Excel export generation | `exports.py` |
| Report calculations | P&L, BS, CF logic |
| Banking matching algorithms | `ui/banking.py` logic → service layer |
| Period close enforcement | Business rules |

React is **presentation + orchestration** only.

---

## 14. Testing strategy

| Layer | Tool |
|-------|------|
| Component unit | Vitest + Testing Library |
| Design contract | Storybook + DS-04 props |
| Visual regression | Playwright per DS-03 frames |
| Route guards | Integration tests per role |
| API contract | OpenAPI schema tests |
| Parity with Streamlit | Shared golden files for report HTML |

---

## 15. File structure (proposed)

```
frontend/
  src/
    routes/
      home.tsx
      banking/
        index.tsx
        import.tsx
        recon.tsx
      reports/
        profit-loss.tsx
        ...
    layouts/
      DesktopShell.tsx
      MobileShell.tsx
      HubSheet.tsx
    components/
      ui/              # shadcn
      erp/             # KpiChip, ListRow, FinTable, ...
    lib/
      api/client.ts    # FastAPI fetch wrapper
      auth.ts
      permissions.ts
      modules.ts
    hooks/
      useMobile.ts
      useDateRange.ts
    i18n/
      en.json          # synced from registry/locales
  styles/
    tokens.css         # DS-04 tokens
```

---

## References

- `registry/nav_keys.py` — route constants
- `registry/modules_catalog.py` — feature flags
- `app.py` `_PAGE_DISPATCH` — handler map
- `docs/MOBILE_UI_SYSTEM.md` — mobile behavior
- `ui/mobile_components.css` — interim token implementation

**Next:** DS-6 implementation (gated on FastAPI + approval)
