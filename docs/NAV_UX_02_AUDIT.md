# NAV-UX-02 — Sidebar & Navigation Audit

**Mode:** Audit + S1/S2/S3/S4/S5/S6 validation. **S6 implemented (2026-06):** `nav.legacy` telemetry for legacy reroutes; see `docs/NAV_UX_02_S6_LEGACY_REROUTE_PLAN.md` + `docs/NAV_UX_02_S6_IMPLEMENTATION.md` + `tests/test_nav_ux_02_s6_legacy_reroute_structural_contract.py`.
**Source of truth:** `_PAGE_DISPATCH` (`app.py:26520`), `_NAV_ACCORDION` (`app.py:3426`), `_NAV_DIRECT_PAGES` (`app.py:3480`), `_NAV_ROLE_PAGES` (`app.py:3490`), `_MOBILE_BOTTOM_NAV` (`app.py:3364`), `_MOBILE_HUB_CONFIG` (`app.py:3383`), `registry/nav_keys.py` (route keys + legacy aliases).

## 1. Audit plan

- **Method:** read-only extraction from the dispatch map, accordion, role tables, and mobile config; every row cites an `app.py` location or registry key. No edits.
- **Surfaces covered:** desktop sidebar (direct pages + 8 accordion groups), mobile bottom nav (5 slots) + hubs (money/reports/people/more), in-page sub-navigation (banking section picker, reports tabs, partner/workers tabs, members tabs, year-end tabs), header controls (company switch, theme toggle, search, profile/My Account), dialogs (`@st.dialog`), and hidden/programmatic routes.
- **Captured per entry:** `label`, `route_key`, `render_fn`, `surface`, `role_gate`, `owner_area`, `control_type`, `parent_surface`, `opens_dialog`, `navigates_to`, `duplicate_workflow`, `daily_use_impact`, `react_route`.
- **Role gate basis:** page visibility is role-driven via `_NAV_ROLE_PAGES` (owner / manager / cashier / partner / viewer). `O/M/C/P/V` flags below are derived directly from those lists; "owner-only" = present only in the owner list.
- **Scope boundary:** low-level action buttons inside forms (save / void / pay / export) are **not** navigation and are listed only where they *navigate* or *open a dialog*. This keeps the inventory to navigation-significant controls.

## 2. Navigation inventory

### 2a. Dispatch routes (43) — `_PAGE_DISPATCH`

> **S2 update:** `Today's Summary` removed from dispatch (2026-06). `render_today_summary` remains via Reports → Accounting Tools exec picker; legacy nav keys reroute to `NAV_REPORTS` + `rpt_exec_sel="today_summary"`.

Role gate legend: **O**=owner, **M**=manager, **C**=cashier, **P**=partner, **V**=viewer.

| label (route_key) | render_fn | surface | role_gate | owner_area | control_type | react_route |
|---|---|---|---|---|---|---|
| Home | render_dashboard | sidebar-direct + mobile-bottom | O M C P V | Dashboard | sidebar-item / bottom-nav | `/` |
| Today's Summary | render_today_summary | **retired dispatch (S2)** — Reports exec only | none in any role list | Dashboard | reports-exec | `/today` |
| New Transaction | render_add_transaction | sidebar-direct + mobile-bottom (＋) | O M C | Transactions | sidebar-item / quick-entry | `/transactions/new` |
| Transaction Ledger | render_transaction_ledger_page | sidebar-direct + reports hub | O M C P V | Transactions | sidebar-item | `/transactions/ledger` |
| Sales | render_sales | sidebar-accordion `transactions` | O M C P | Sales | sidebar-item | `/sales` |
| Expenses | render_expenses | sidebar-accordion `transactions` | O M C | Expenses | sidebar-item | `/expenses` |
| Staff Expenses | render_staff_expense_capture | sidebar-accordion `transactions` | **permission** (`submit_expense_drafts` ∨ `approve_expense_drafts`) | Expenses | sidebar-item | `/expenses/staff-capture` |
| Recurring Expenses | render_recurring_expenses | sidebar-accordion `transactions` | O M C | Expenses | sidebar-item | `/expenses/recurring` |
| Purchases | render_purchases | sidebar-accordion `transactions` | O M C | Purchases | sidebar-item | `/purchases` |
| Cash Reconciliation | render_cash_reconciliation | accordion `close_day` + money hub | O M C | Closings | sidebar-item | `/closings/cash-recon` |
| External Sales Verification | render_external_sales_verification | accordion `close_day` + money hub | O M C | Closings | sidebar-item | `/closings/external-sales` |
| End-of-Day Close | render_end_of_day_close | accordion `close_day` + money hub | O M C | Closings | sidebar-item | `/closings/eod` |
| Ingredients | render_recipe_ingredients | accordion `recipe_costing` | O M | Recipe Costing | sidebar-item | `/recipes/ingredients` |
| Recipes | render_recipe_recipes | accordion `recipe_costing` | O M | Recipe Costing | sidebar-item | `/recipes` |
| Cost Breakdown | render_recipe_cost_breakdown | accordion `recipe_costing` | O M | Recipe Costing | sidebar-item | `/recipes/cost-breakdown` |
| Menu Items | render_recipe_menu_items | accordion `recipe_costing` | O M | Recipe Costing | sidebar-item | `/recipes/menu-items` |
| Customers | render_customers | accordion `people` + people hub | O M C | People | sidebar-item | `/customers` |
| Vendors | render_vendors | accordion `people` + people hub | O M C | People | sidebar-item | `/vendors` |
| Receivables | render_receivables | accordion `people` + people hub | O M C P | People | sidebar-item | `/receivables` |
| Payables | render_payables | accordion `people` + people hub | O M C | People | sidebar-item | `/payables` |
| Inventory | render_inventory | sidebar-direct + more hub | O M | Inventory | sidebar-item | `/inventory` |
| Banking | render_banking | sidebar-direct + money hub | O M C | Banking | sidebar-item (has sub-picker) | `/banking` |
| Reports | render_reports | sidebar-direct + reports hub | O M C P V | Reports | sidebar-item (has tabs) | `/reports` |
| Profit & Loss | render_profit_loss_page | accordion `statements` (canonical) + reports hub (shortcut) | O M C P V | Reports | sidebar-item | `/reports/profit-loss` |
| Balance Sheet | render_balance_sheet_page | accordion `statements` (canonical) + reports hub (shortcut) | O M C P V | Reports | sidebar-item | `/reports/balance-sheet` |
| Cash Flow | render_cash_flow_page | accordion `statements` (canonical) + reports hub (shortcut) | O M C P V | Reports | sidebar-item | `/reports/cash-flow` |
| General Ledger | render_general_ledger | accordion `accounting` | O M | Books | sidebar-item | `/books/general-ledger` |
| Trial Balance | render_trial_balance | accordion `accounting` | O M | Books | sidebar-item | `/books/trial-balance` |
| Journal Entries | render_journal_entries | accordion `accounting` | O M | Books | sidebar-item | `/books/journal-entries` |
| Fiscal Periods | render_fiscal_periods | accordion `accounting` | O M | Books | sidebar-item | `/books/fiscal-periods` |
| Year-End Close | render_year_end_close | accordion `accounting` | O M | Books | sidebar-item (has tabs) | `/books/year-end-close` |
| Budget | render_budget | accordion `accounting` | O M | Books | sidebar-item | `/books/budget` |
| Chart of Accounts | render_chart_of_accounts | accordion `accounting` | O M | Books | sidebar-item | `/books/chart-of-accounts` |
| Recon Health | render_reconciliation_health | accordion `accounting` (excl. mobile more) | O M | Books | sidebar-item | `/books/recon-health` |
| Opening Balances | render_opening_balances | accordion `accounting` | O M | Books | sidebar-item | `/books/opening-balances` |
| Partner Accounts | render_partner_accounts | accordion `team` + people hub | O M P | Team & Partners | sidebar-item (has tabs) | `/partners` |
| Workers | render_workers | accordion `team` + people hub | O M | Team & Partners | sidebar-item (has tabs) | `/workers` |
| Company Settings | render_company_settings | accordion `settings` + more hub | **O only** | Settings | sidebar-item | `/settings/company` |
| Members | render_user_management | accordion `settings` + more/admin (mobile) | **O only** | Settings | sidebar-item (has tabs) | `/settings/members` |
| Permissions | render_permissions_management | accordion `settings` | **O only** | Settings | sidebar-item | `/settings/permissions` |
| Audit Log | render_audit_log | accordion `settings` + more/admin (mobile) | O M | Settings | sidebar-item | `/settings/audit-log` |
| Backup & Restore | render_backup_restore (lambda) | accordion `settings` + more hub | **O only** | Settings | sidebar-item | `/settings/backup-restore` |
| My Account | render_my_account | header profile menu | O M C P V | Account | header-control | `/account` |

### 2b. Mobile bottom nav (5 slots) — `_MOBILE_BOTTOM_NAV`

| slot | kind | label key | target | control_type |
|---|---|---|---|---|
| home | page | nav.bottom.home | Home | bottom-nav |
| money | hub | nav.bottom.money | Money hub | mobile-hub-opener |
| new | page | nav.bottom.new | New Transaction (＋) | quick-entry / bottom-nav |
| reports | hub | nav.bottom.reports | Reports hub | mobile-hub-opener |
| more | hub | nav.bottom.more | More hub | mobile-hub-opener |

### 2c. Mobile hubs — `_MOBILE_HUB_CONFIG`

- **money** → close section (Cash Reconciliation, External Sales Verification, End-of-Day Close), bank section (Banking, Recon Health, Statement import).
- **reports** → Profit & Loss, Balance Sheet, Cash Flow (**shortcuts** to canonical statement routes), Transaction Ledger, Sales report, Expenses report.
- **people** → Customers, Vendors, Receivables, Payables, Workers, Partner Accounts (**operational records only**; Members removed S4).
- **more** → opens People hub, Books accordion (accounting), History accordion (transactions), Inventory, Admin section (Company Settings, **Members**, Backup & Restore, Audit Log).

### 2d. In-page sub-navigation & dialogs

| control | parent_surface | control_type | opens_dialog | evidence |
|---|---|---|---|---|
| Banking section picker (cockpit/accounts/pos_settlement/import/settings) | Banking page | dropdown-picker (radio-like) | no | `app.py:21345`, opts `21336-21344` |
| Reports tabs | Reports page | tabs | no | `app.py:22631-22639`, `_REPORTS_MOB_TAB_IDS` `22555-22562` — **exec/sales/expenses/customers/vendors/banking/eod only; no P&L/BS/CF** |
| Year-End Close tabs (Close Year / History) | Year-End Close | tabs | no | `app.py:8213` |
| Partner Accounts tabs (contrib/drawings + per-partner) | Partner Accounts | tabs | no | `app.py:9135`, `10015` |
| Workers tabs (workers/movements/summary) | Workers | tabs | no | `app.py:9568` |
| Members tabs (roster/manage; add-existing/create-new) | Members | tabs | no | `app.py:24328`, `24372` |
| Add/Manage Supplier | Vendors / forms | dialog | **yes** | `app.py:23643`, `23674` |
| Add/Manage Category, Add/Manage Subcategory | transaction/category forms | dialog | **yes** | `app.py:23894-23965` |
| Company switch confirm | header | dialog-opener | yes | `_render_company_switch_confirm` |
| Theme toggle ☀️/🌙 | header | button (state toggle) | no | `_flip_header_theme` `app.py:3211` |
| Profile / My Account | header | header-control → route | no | `app.py:1103`, `1321` |
| Receivables / Payables / Inventory quick links | dashboard cards | button → navigates | no | `app.py:1293-1321`, `11162-11170` |

## 3. Duplicate workflow report

Multiple entry points reaching the **same workflow** (record-only; not defects, but cleanup candidates):

1. **Banking** — `duplicate_workflow=banking`: sidebar-direct **Banking**, money-hub Banking entry, **and** legacy `"Bank Statement Import"` key rerouted to Banking + `banking_section="import"` (`app.py:26449`, `24864`, `3930`). Three entry points; statement import reachable as both a legacy route and a banking sub-section.
2. **Financial statements (S3 reclassified)** — **canonical routes** `NAV_PROFIT_LOSS` / `NAV_BALANCE_SHEET` / `NAV_CASH_FLOW` with desktop accordion `statements` as **canonical home** (one route → thin page wrapper → core renderer). **Shortcut doors only** (navigate, never render): mobile reports hub deep-links and legacy `rpt_exec_sel` reroute (`_LEGACY_RPT_EXEC_TO_STATEMENT`, `app.py:3235-3238`, `26467`). The **Reports page does not render statements** — its tabs are exec/sales/expenses/customers/vendors/banking/eod.
3. **Transaction Ledger** — `duplicate_workflow=txn_ledger`: sidebar-direct, reports hub, and dashboard quick link (`app.py:11406`). Also legacy "Accounting Tools" picker → Books (`_LEGACY_RPT_EXEC_TO_BOOKS`).
4. **Receivables / Payables** — `duplicate_workflow=ar` / `ap`: accordion `people`, mobile people hub, **and** dashboard quick-link buttons (`app.py:1293-1303`, `11162-11170`).
5. **New Transaction** — `duplicate_workflow=new_txn`: sidebar-direct + mobile bottom ＋ button (`app.py:3642`, `15661`, `15932`). Expected redundancy (primary CTA) — keep, but note dual source.
6. **Reports (Sales/Expenses)** — mobile reports hub exposes `report_sales`/`report_expenses` shortcuts that re-enter the Reports page with a preset tab — duplicate of in-page Reports tabs.

**Resolved (S4):** Members cross-surface inconsistency — was Settings desktop / People hub mobile; **now** Settings desktop / More→Admin mobile (owner-only unchanged).

## 4. Proposed ownership map

| owner_area | pages | notes |
|---|---|---|
| **Dashboard** | Home, Today's Summary | Today's Summary is orphaned (see §5) |
| **Transactions** | New Transaction, Transaction Ledger | entry + lookup |
| **Sales** | Sales | |
| **Expenses** | Expenses, Staff Expenses, Recurring Expenses | Staff Expenses nav is permission-derived (submit/approve); page enforces same gate |
| **Purchases** | Purchases | |
| **Closings** | Cash Reconciliation, External Sales Verification, End-of-Day Close | |
| **Recipe Costing** | Ingredients, Recipes, Cost Breakdown, Menu Items | industry-optional module |
| **People** | Customers, Vendors, Receivables, Payables | |
| **Inventory** | Inventory | |
| **Banking** | Banking (+ cockpit/accounts/pos/import/settings sub-sections) | sub-nav via picker |
| **Reports** | Reports, Profit & Loss, Balance Sheet, Cash Flow | statements are canonical routes under Reports domain; Reports page tabs are management analytics only |
| **Books** | General Ledger, Trial Balance, Journal Entries, Fiscal Periods, Year-End Close, Budget, Chart of Accounts, Recon Health, Opening Balances | |
| **Team & Partners** | Partner Accounts, Workers | |
| **Settings** | Company Settings, Members, Permissions, Audit Log, Backup & Restore | admin domain; config pages owner-only; Audit Log manager-visible oversight exception |
| **Account** | My Account | header-only |

## 5. Notable findings (record-only)

- **Orphan route (resolved S2):** `Today's Summary` dispatch route **retired**; `render_today_summary` reachable via Reports exec + legacy reroute to `NAV_REPORTS`.
- **Role/purpose mismatch (resolved S5):** Staff Expenses nav visibility now matches the page gate — shown iff `submit_expense_drafts` or `approve_expense_drafts` (default: owner, manager, cashier). Approval remains the GL-posting boundary behind `approve_expense_drafts`.
- **Cross-surface inconsistency (resolved S4):** `Members` now lives under **Settings** on desktop **and** **More→Admin** on mobile (removed from People hub). `Audit Log` remains owner+manager while other Settings config pages are owner-only — documented oversight exception.
- **Legacy reroutes still active (S6 telemetry added):** `"Bank Statement Import"` key, `rpt_exec_sel` → statement/Books mappings — kept for back-compat; `nav.legacy` logs hits for telemetry-gated retirement review.
- **Statements multi-door (S3 resolved):** P&L/BS/CF are **single canonical routes** with desktop accordion as home; mobile hub + legacy `rpt_exec_sel` are **shortcut doors** — not duplicate renders. Reports page tabs exclude statements.

## 6. Contract-test recommendations (safe, additive only)

These are **assertions over existing structures** — no runtime change, no behavior coupling:

1. **Dispatch ↔ keys parity:** every `_PAGE_DISPATCH` key ∈ `ALL_NAV_PAGE_KEYS`, and every key is reachable from `_NAV_DIRECT_PAGES` ∪ accordion ∪ mobile config (S2: `KNOWN_HIDDEN` empty).
2. **Role-page validity:** every key in `_NAV_ROLE_PAGES[*]` ∈ `ALL_NAV_PAGE_KEYS` (catch typos/renames).
3. **Accordion integrity:** every accordion page key ∈ dispatch; every group has ≥1 page; no key appears in two groups.
4. **Mobile hub validity:** every `_MOBILE_HUB_CONFIG` page key ∈ dispatch; every `_MOBILE_BOTTOM_NAV` hub payload ∈ `_MOBILE_HUB_KEYS`.
5. **Legacy alias targets:** every `LEGACY_NAV_ALIASES` value ∈ `ALL_NAV_PAGE_KEYS`.
6. **No duplicate route_key labels** except the documented `duplicate_workflow` set (regression guard for accidental new duplicates).

A doc-contract test for this audit (existence + sections + inventory coverage) ships with this slice; the structural tests above are **recommended** for the cleanup slice, not added now (they assert against live structures and belong with any change that touches them).

## 7. Implementation slices (for Cursor — DO NOT implement yet)

- **NAV-UX-02-S1 — structural contract tests** (safe now): add the §6 parity tests with an explicit `KNOWN_HIDDEN` allow-list. Pure assertions over existing dicts; no UI change.
- **NAV-UX-02-S2 — resolve the orphan:** **Implemented (S2-IMPL)** — retired dispatch route; Reports exec + legacy reroute preserved.
- **NAV-UX-02-S3 — statements consolidation:** **Implemented (S3-IMPL-1)** — canonical routes + shortcut doors formalized; contract tests in `tests/test_nav_ux_02_s3_statements_structural_contract.py`; React paths `/reports/profit-loss`, `/reports/balance-sheet`, `/reports/cash-flow`.
- **NAV-UX-02-S4 — cross-surface consistency:** **Implemented (S4-IMPL-1)** — Members relocated on mobile from People hub → More/Admin; People hub operational records only; contract tests in `tests/test_nav_ux_02_s4_members_audit_structural_contract.py`; React `/settings/members` preserved.
- **NAV-UX-02-S5 — role/purpose review:** **Implemented (S5-IMPL-1)** — Staff Expenses nav permission-derived; default mapping verified (`submit`: owner/manager/cashier; `approve`: owner/manager); contract tests in `tests/test_nav_ux_02_s5_staff_expenses_structural_contract.py`.
- **NAV-UX-02-S6 — legacy reroute retirement:** **S6-IMPL-1 implemented (2026-06)** — `nav.legacy` telemetry only; alias/reroute retirement deferred to S6-IMPL-3 after zero-hit bake-in (S6-IMPL-2).
- **NAV-UX-02-S7 — React route map adoption:** freeze the §2 `react_route` column as the migration contract (1:1 route_key→path) for the FastAPI+React front end.

## No-change statement (NAV-UX-02 audit)

- **Audit only — S6-IMPL-1 added `nav.legacy` telemetry only; no alias deleted; no route deleted; no page deleted; no route renamed; no role gate changed; no render change; no cleanup performed.**
- Inventory, duplicate report, ownership map, test recommendations, and slices are **planning artifacts only**; execution is gated to the S1–S7 slices above.

---

*Audit + S1–S6 validation. S6: `nav.legacy` telemetry on legacy reroute hits; retirement deferred. Key open findings: Audit Log manager-visible oversight exception.*
