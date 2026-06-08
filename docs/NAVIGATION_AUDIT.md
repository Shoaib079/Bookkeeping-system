# Navigation Audit — AD-UI-001 Phase 1

**Decision ID:** AD-UI-001  
**Status:** **Phase D1 implemented** (Option D hybrid — financial statements discoverability)  
**Priority:** High  
**Gate:** D2+ (Executive rename, TB/GL dedup, Transaction History move) — **not started**

**Companion docs:** [UI_SHELL.md](../UI_SHELL.md) · [ROADMAP.md](../ROADMAP.md) · [AUDIT_HISTORY.md](./AUDIT_HISTORY.md)

**Audit date:** 2026-06-09  
**Context:** Post Banking Stabilization, UI Sweeps 1–3, Legacy UI Cleanup Phases 1–3.

---

## Approval record

| Field | Value |
|-------|-------|
| **ID** | AD-UI-001 |
| **Scope** | Sidebar structure, mobile hubs, Reports hub IA, role-visible pages, module catalog alignment |
| **Out of scope** | Posting logic, GL rules, registry accounting keys, navigation code changes (this pass) |
| **Prerequisite** | This document §1–§8 — **done** |
| **Implementation** | Separate task — blocked until IA option chosen |

---

## 1. Navigation sources (code map)

| Source | File | What it defines |
|--------|------|-----------------|
| Sidebar accordion | `app.py` → `_NAV_ACCORDION` | Direct pages + grouped Transactions / People / Closings / Books / Team / Settings |
| Role allow-lists | `app.py` → `_NAV_ROLE_PAGES` | owner / manager / cashier / partner / viewer page sets |
| Page dispatch | `app.py` → `_PAGE_DISPATCH` | `nav_selection` string → `render_*` function |
| Module registry | `registry/modules_catalog.py` | `ModuleDef.nav_page` — metadata; BS/P&L/CF not registered |
| Mobile bottom nav | `app.py` → `_MOBILE_BOTTOM_NAV`, `_MOBILE_HUB_CONFIG` | Home · Banking · New · Reports · More (+ People sub-hub) |
| Reports hub | `app.py` → `render_reports()` | 7 tabs desktop; mobile tab bar; Executive tab hosts financial statements |
| Permissions | `app.py` → `_PERMISSIONS`, `_can()` | In-page action gates (separate from nav visibility) |
| Module hide | `app.py` → `_module_hidden_nav_pages()` | Hides Inventory / Partner Accounts / Budget when company toggle off |
| Nav i18n | `registry/nav_labels.py`, `registry/locales/` | Display labels EN/TR |

---

## 2. Deliverable A — Complete navigation map

**Legend**

- **Sidebar depth:** clicks from collapsed sidebar (1 = direct button; 2 = open accordion + page).
- **Mobile depth:** taps from any page (1 = bottom bar; 2 = hub sheet + item; 3 = More → sub-hub/accordion + page).
- **Usage:** operator frequency estimate for a restaurant owner / cashier context.
- **Roles:** `O` owner · `M` manager · `C` cashier · `P` partner · `V` viewer · `(—)` hidden by role · `(mod)` hidden when company module off.

### 2.1 Top-level pages (`_PAGE_DISPATCH`)

| Page key | Render function | Sidebar location | Mobile location | Roles | Usage | Sidebar depth | Mobile depth |
|----------|-----------------|------------------|-----------------|-------|-------|---------------|--------------|
| 🏠 Home | `render_dashboard` | Direct (top) | Bottom **Home** | O M C P V | Daily | 1 | 1 |
| ➕ New Transaction | `render_add_transaction` | Direct | Bottom **New** (FAB) | O M C | Daily | 1 | 1 |
| 🏦 Banking | `render_banking` | Direct (Work section) | **Banking** hub → Banking | O M C | Daily | 1 | 2 |
| 📦 Inventory | `render_inventory` | Direct (Work section) | **More** → Inventory | O M `(mod)` | Weekly | 1 | 2 |
| 📊 Reports | `render_reports` | Direct (Reports section) | **Reports** hub / bottom **Reports** | O M C P V | Daily–Monthly | 1 | 2 |
| 💼 Sales | `render_sales` | **Transactions** accordion | **More** → Transactions → Sales | O M C | Daily | 2 | 3 |
| 💳 Expenses | `render_expenses` | Transactions | More → Transactions → Expenses | O M C | Daily | 2 | 3 |
| 🛒 Purchases | `render_purchases` | Transactions | More → Transactions → Purchases | O M C | Weekly | 2 | 3 |
| 🔁 Recurring Expenses | `render_recurring_expenses` | Transactions | More → Transactions → Recurring | O M C | Weekly | 2 | 3 |
| 👥 Customers | `render_customers` | **People** accordion | **People** hub / More → People hub | O M | Weekly | 2 | 2–3 |
| 🏢 Vendors | `render_vendors` | People | People hub | O M | Weekly | 2 | 2–3 |
| 📄 Receivables | `render_receivables` | People | People hub; Home AR shortcut (mobile) | O M C | Daily | 2 | 2–3 |
| 📌 Payables | `render_payables` | People | People hub; Home AP shortcut (mobile) | O M C | Daily | 2 | 2–3 |
| 💸 Cash Reconciliation | `render_cash_reconciliation` | **Closings** accordion | **Banking** hub | O M C | Daily | 2 | 2 |
| 🌙 End-of-Day Close | `render_end_of_day_close` | Closings | Banking hub | O M C | Daily | 2 | 2 |
| 🗂 General Ledger | `render_general_ledger` | **Books** accordion | More → Books (accordion) | O M | Monthly | 2 | 3 |
| 🔍 Chart of Accounts | `render_chart_of_accounts` | Books | More → Books | O M | Admin | 2 | 3 |
| 📓 Journal Entries | `render_journal_entries` | Books | More → Books | O M | Monthly | 2 | 3 |
| ⚖️ Trial Balance | `render_trial_balance` | Books | More → Books | O M | Monthly | 2 | 3 |
| 🗓 Fiscal Periods | `render_fiscal_periods` | Books | More → Books | O M | Monthly | 2 | 3 |
| 📆 Year-End Close | `render_year_end_close` | Books | More → Books | O M | Annual | 2 | 3 |
| 💰 Budget | `render_budget` | Books `(mod)` | More → Books | O M `(mod)` | Monthly | 2 | 3 |
| 🩺 Recon Health | `render_reconciliation_health` | Books | More → Books | O M | Weekly | 2 | 3 |
| ⚡ Opening Balances | `render_opening_balances` | Books | More → Books | O M | Admin (once) | 2 | 3 |
| 🏦 Partner Accounts | `render_partner_accounts` | **Team** accordion | People hub | O M P `(mod)` | Admin | 2 | 2–3 |
| 👷 Workers | `render_workers` | Team | People hub | O M | Admin | 2 | 2–3 |
| 🏢 Company Settings | `render_company_settings` | **Settings** accordion | More → Admin | O | Admin | 2 | 2 |
| 👤 Members | `render_user_management` | Settings | — (owner only; no mobile path) | O | Admin | 2 | — |
| 🕵️ Audit Log | `render_audit_log` | Settings | More → Admin | O M | Admin | 2 | 2 |
| 💾 Backup & Restore | `render_backup_restore` | Settings | More → Admin | O | Admin | 2 | 2 |
| 👤 My Account | `render_my_account` | Profile popover only | Profile popover | O M C P V | Occasional | 2 | 2 |
| 📅 Today's Summary | `render_today_summary` | **Not in sidebar** | Reports → Executive picker only | O M C P V | Daily | 3 | 3–4 |

### 2.2 Embedded / sub-route pages (no own `nav_selection`)

| Feature | Render function | How reached | Roles | Usage |
|---------|-----------------|-------------|-------|-------|
| Balance Sheet | `render_balance_sheet` | Reports → tab **Executive** → picker | All with Reports | Monthly |
| Profit & Loss | `render_profit_loss` | Reports → Executive (default picker) | All with Reports | Monthly |
| Cash Flow | `render_cash_flow` | Reports → Executive → picker | All with Reports | Monthly |
| Transaction History | `render_transaction_history` | Reports → Executive → **Transaction Ledger** | All with Reports | Daily |
| Today's Summary (dup path) | `render_today_summary` | Reports → Executive → Today's Summary | All with Reports | Daily |
| TB / GL / Budget (dup) | same as Books pages | Reports → Executive → picker | O M (+ cashier via Reports) | Monthly |
| Bank Statement Import | `render_bank_statement_import` | Banking → **Import** tab; mobile Banking hub import | O M (`import_bank_statement`) | Weekly |
| Category management | `render_manage_categories` | Company Settings (embedded) | O M C (`manage_categories`) | Admin |
| Setup wizard | `render_setup_wizard` | Company Settings (embedded) | O | Onboarding |
| Equity movements | `render_equity_movements` | Partner Accounts (embedded tab) | O M P | Admin |

### 2.3 Orphan render functions

| Function | Notes |
|----------|-------|
| *(none)* | Pre-D2 cleanup removed `render_advanced`, `render_customer_ledger`, `render_settings` |

### 2.4 Sidebar structure (desktop)

```
🏠 Home                          [direct]
➕ New Transaction                [direct]
── Work ──
  Record transactions ▸           [accordion: Sales, Expenses, Purchases, Recurring]
🏦 Banking                        [direct]
  Customers & suppliers ▸       [accordion: Customers, Vendors, Receivables, Payables]
📦 Inventory                    [direct]
── Reports ──
📊 Reports                        [direct]
  Closings ▸                    [accordion: Cash Recon, EOD]
── Advanced ──
  Books ▸                       [accordion: GL, COA, JE, TB, Fiscal, Year-End, Budget, Recon Health, OB]
  Team & partners ▸             [accordion: Partner Accounts, Workers]
  Settings ▸                    [accordion: Company Settings, Members, Audit, Backup]
```

Mobile bottom bar: **Home | Banking | New | Reports | More**  
Hub sheets: `banking`, `reports`, `more`, `people` (opened from More).

---

## 3. Deliverable B — Daily-use pages

| Page | Primary users | Best desktop path | Best mobile path |
|------|---------------|-------------------|------------------|
| 🏠 Home | All | Sidebar (1) | Bottom Home (1) |
| ➕ New Transaction | O M C | Sidebar (1) | Bottom New (1); Home quick-create chips |
| 💼 Sales (list/form) | O M C | Transactions (2) or New Transaction | More → Transactions (3) — **prefer New** |
| 💳 Expenses | O M C | Same | Same |
| 📄 Receivables | O M C | People (2) | Home AR button; People hub |
| 📌 Payables | O M C | People (2) | Home AP button; People hub |
| 🏦 Banking | O M C | Sidebar (1) | Banking hub (2) |
| 💸 Cash Reconciliation | O M C | Closings (2) | Banking hub (2) |
| 🌙 End-of-Day Close | O M C | Closings (2) | Banking hub (2) |
| 📊 Reports → P&L / Today | O M P V | Reports + Executive picker (2–3) | Reports hub deep-link (2–3) |
| Transaction History | O M C | Reports → Executive → Transaction Ledger (3) | Reports hub → Reports page → picker (3–4) |

---

## 4. Deliverable C — Weekly / monthly / admin pages

### Weekly

| Page | Desktop | Mobile |
|------|---------|--------|
| 🛒 Purchases | Transactions (2) | More → Transactions (3) |
| 🔁 Recurring Expenses | Transactions (2) | More → Transactions (3) |
| 👥 Customers / 🏢 Vendors | People (2) | People hub (2–3) |
| 📦 Inventory | Direct (1) | More (2) |
| 🩺 Recon Health | Books (2) | More → Books (3) |
| Bank Statement Import | Banking → Import tab (2) | Banking hub → Import (2) |

### Monthly

| Page | Desktop | Mobile |
|------|---------|--------|
| ⚖️ Trial Balance | Books (2) **or** Reports → Executive (3) | More → Books (3) **or** Reports hub (3) |
| 🗂 General Ledger | Books (2) **or** Reports → Executive (3) | Same |
| 🏛️ Balance Sheet | **Reports → Executive only (3)** | Reports hub → BS (2 + picker) |
| 💰 Profit & Loss | Reports → Executive (2–3; default) | Reports hub → P&L (2) |
| 💸 Cash Flow | Reports → Executive (3) | Reports hub → CF (2) |
| 💰 Budget | Books (2) **or** Reports → Executive (3) | More → Books (3) |
| 📓 Journal Entries | Books (2) | More → Books (3) |
| 🗓 Fiscal Periods | Books (2) | More → Books (3) |

### Admin / rare

| Page | Desktop | Mobile | Role gate |
|------|---------|--------|-----------|
| ⚡ Opening Balances | Books (2) | More → Books (3) | O M |
| 📆 Year-End Close | Books (2) | More → Books (3) | O (post); M view |
| 🏢 Company Settings + wizard | Settings (2) | More → Admin (2) | O |
| 👤 Members | Settings (2) | **No mobile nav entry** | O |
| 🕵️ Audit Log | Settings (2) | More → Admin (2) | O M |
| 💾 Backup & Restore | Settings (2) | More → Admin (2) | O |
| 🏦 Partner Accounts | Team (2) | People hub (2–3) | O M P |
| 👷 Workers | Team (2) | People hub (2–3) | O M |

---

## 5. Deliverable D — Hidden / hard-to-find pages

| Item | Why hidden / hard | Severity |
|------|-------------------|----------|
| Balance Sheet, P&L, Cash Flow | No sidebar entry; only Reports → **Executive** → 8-way picker | **High** |
| Transaction History (global) | Only Reports → Executive → Transaction Ledger; not under Transactions | **High** |
| 📅 Today's Summary | In `_PAGE_DISPATCH` but **no sidebar**; only Executive picker | Medium |
| Bank Statement Import | Banking sub-tab; not in sidebar accordion | Medium |
| Category management | Buried inside Company Settings | Medium |
| Setup wizard | Inside Company Settings; no first-run nav prompt | Medium |
| Members (mobile) | Owner-only page with **no mobile hub entry** | Medium |
| `render_advanced` | Dead launcher — historical | Low (code only) |
| `render_customer_ledger` | Dead function | Low (code only) |
| Recon Health | Inside Books accordion — non-obvious name | Medium |
| Opening Balances | Books accordion — one-time admin task | Low |

---

## 6. Deliverable E — Duplicate navigation paths

| Destination | Path 1 | Path 2 | Path 3 | Issue |
|-------------|--------|--------|--------|-------|
| Trial Balance | Books → Trial Balance | Reports → Executive → TB | — | Same page, two mental models |
| General Ledger | Books → GL | Reports → Executive → GL | — | Same |
| Budget | Books → Budget | Reports → Executive → Budget | — | Same |
| Record Sale | New Transaction (Sale type) | Sales page (inline form) | Home mobile QC Sale | Three entry points; confusing for new users |
| Record Expense | New Transaction | Expenses page | Home QC Expense | Same |
| Record Purchase | New Transaction | Purchases page | Home QC Purchase | Same |
| Cash Reconciliation | Closings accordion | Banking mobile hub | — | OK (complementary) |
| End-of-Day Close | Closings accordion | Banking mobile hub | — | OK |
| P&L / BS / CF | Reports Executive | Mobile Reports hub deep-links | — | Deep-link helps mobile; desktop still nested |
| Customers / Vendors | People accordion | People hub (via More) | — | Desktop vs mobile parity gap |
| Today's Summary | Dashboard KPIs (partial) | Reports → Executive → Today | — | Overlap without clear label |

---

## 7. Deliverable F — Workflow audit

### A. Record Sale

| Step | Desktop | Mobile |
|------|---------|--------|
| Nav clicks | 1 (New Transaction) | 1 (New FAB or Home QC Sale) |
| Depth | 1 | 1 |
| Friction | Sales accordion page duplicates simpler New Transaction flow | More → Transactions → Sales is 3 taps — easy to miss FAB |
| Suggested (not implemented) | Single canonical “record sale” entry; demote or link Sales list page | Promote FAB; hide Sales from More accordion for cashier role |

### B. Record Expense

| | Desktop | Mobile |
|-|--------|--------|
| Clicks | 1 (New Transaction → Expense) | 1 (New / QC Expense) |
| Friction | Expenses list page duplicates; CC expense requires payment-method pick on AT form | CC picker on mobile AT panel — extra scroll |
| Suggested | Link Expenses nav to New Transaction with `at_type_idx=1` preset | Same preset deep-link |

### C. Record Purchase

| | Desktop | Mobile |
|-|--------|--------|
| Clicks | 1 | 1 |
| Friction | Purchases page third duplicate entry | 3-tap path via More |
| Suggested | Same preset pattern as Expense | — |

### D. Supplier Payment

| | Desktop | Mobile |
|-|--------|--------|
| Clicks | 1 (New Transaction → Supplier Payment) **or** 2 (Payables → pay row) | 1 (New Transaction) **or** 2–3 (People hub → Payables) |
| Friction | Supplier Payment type not obvious in type list; Payables page separate | Payables not on bottom nav |
| Suggested | Dashboard “pay supplier” shortcut when AP due | Banking or People hub badge |

### E. Banking Transaction

| | Desktop | Mobile |
|-|--------|--------|
| Clicks | 1 (New Transaction → Bank) **or** 1 (Banking page) | 2 (Banking hub → Banking) |
| Friction | Banking page mixes account CRUD + ledger; bank txn on AT separate | — |
| Suggested | — | — |

### F. Credit Card Expense

| | Desktop | Mobile |
|-|--------|--------|
| Clicks | 1 (New Transaction → Expense + CC payment method) | 1 + panel picks |
| Friction | No nav item named “Credit Card”; depends on company CC toggle | Same |
| Suggested | Optional “Card expense” quick action when CC enabled | — |

### G. Reconciliation

| | Desktop | Mobile |
|-|--------|--------|
| Clicks | 2 (Closings → Cash Recon) | 2 (Banking hub) |
| Friction | Under “Advanced” sidebar section — feels back-office; dashboard shows status but **no link** | Reasonable via Banking hub |
| Suggested | Move Closings to Work section; dashboard recon badge → navigate | — |

### H. End of Day

| | Desktop | Mobile |
|-|--------|--------|
| Clicks | 2 (Closings → EOD) | 2 (Banking hub) |
| Friction | Same “Advanced” placement; dashboard EOD badge not clickable | — |
| Suggested | Pair with Cash Recon in a “Close the day” group at top level | — |

### I. Monthly Reporting (owner / accountant)

| Step | Desktop clicks | Friction |
|------|----------------|----------|
| Trial Balance | 2 (Books) or 3 (Reports → Executive → TB) | Duplicate paths |
| GL drill-down | 2 + in-page | OK once on GL |
| Balance Sheet | **3** (Reports → Executive → BS) | **Not in Books** — highest friction |
| P&L | 2–3 (Reports → Executive; default P&L) | Tab label “Executive” unclear |
| Cash Flow | 3 | Buried with BS |

**Suggested (not implemented):** Option B or D (§9) — statements in Books or dedicated Statements group.

---

## 8. Deliverable G — Financial reporting audit

| Report | Renderer | Current location | Expected (user mental model) | Discoverability (1–5) | Duplication | Naming issues |
|--------|----------|------------------|------------------------------|----------------------|-------------|---------------|
| Balance Sheet | `render_balance_sheet` | Reports → Executive → picker | Books or top-level Statements | **2** | None elsewhere | “Executive” tab |
| Profit & Loss | `render_profit_loss` | Reports → Executive (default) | Same | **3** | None | OK once found |
| Cash Flow | `render_cash_flow` | Reports → Executive → picker | Same | **2** | None | — |
| Trial Balance | `render_trial_balance` | Books **and** Reports → Executive | Books only | **4** | **Yes** | — |
| General Ledger | `render_general_ledger` | Books **and** Reports → Executive | Books only | **4** | **Yes** | — |
| Budget | `render_budget` | Books **and** Reports → Executive | Books or Reports | **3** | **Yes** | — |
| Transaction Ledger | `render_transaction_history` | Reports → Executive only | Transactions or top-level History | **2** | Overlaps per-module lists | “Transaction Ledger” vs “Transaction History” |
| Today's Summary | `render_today_summary` | Reports → Executive only | Home or Closings | **2** | Overlaps Home KPIs | Orphan nav key |

**Registry gap:** `modules_catalog.py` has no `balance_sheet`, `pnl`, `cash_flow`, or `transaction_history` modules.

**Permission gap:** Executive financial reports are **not** `view_management_reports`-gated; management tabs (Sales, Expenses, …) are. Cashier/viewer can open BS/TB/GL via Reports but cannot open Books sidebar.

---

## 9. Deliverable H — Mobile vs desktop audit

| Topic | Finding |
|-------|---------|
| **Consistency** | Desktop uses sidebar accordions; mobile uses bottom nav + hub sheets. Same canonical `nav_selection` keys — routing is consistent. |
| **Missing on mobile** | 👤 Members (owner); no dedicated “Books” bottom entry — buried in More |
| **Mobile-only affordances** | Home quick-create row; AR/AP split buttons; Reports tab bar (7 tabs); hub deep-links for P&L/BS/CF |
| **Desktop-only affordances** | Full Books accordion visible at once; sidebar date filters on Reports |
| **Duplicate paths** | Transactions accordion in More mirrors desktop Transactions — competes with New FAB |
| **Discoverability** | Financial statements easier on mobile (Reports hub lists P&L, BS, CF) than desktop (must know Executive tab) |
| **Friction** | More → open People hub → page = 3 taps for Customers; cashier cannot reach Customers at all |
| **Viewer** | Mobile Reports hub works; Banking/More hubs empty or sparse — OK |

**Tests enforcing nav contracts:** `tests/test_mobile_nav.py`, `tests/test_shell_stabilization.py` (toolbar, hubs, People wiring).

---

## 10. Top 10 navigation problems (ranked)

| # | Problem | Impact |
|---|---------|--------|
| 1 | Balance Sheet / P&L / Cash Flow not in sidebar; buried under Reports → **Executive** → 8-way picker | Owners cannot find core statements |
| 2 | **Executive** tab label does not mean “Financial Statements” | Cognitive load for non-accountants |
| 3 | TB / GL / Budget duplicated in Books and Reports → Executive | “Which path is correct?” |
| 4 | Transaction History only under Reports → Executive → Transaction Ledger | Daily ops history hard to find |
| 5 | Sales / Expenses / Purchases pages duplicate New Transaction | Three ways to do the same thing |
| 6 | Closings (Cash Recon, EOD) under sidebar **Advanced** — not Work | Daily restaurant close workflow feels “admin” |
| 7 | Cashier/viewer: no Books sidebar but full financial reports via Reports Executive | Role/nav asymmetry |
| 8 | Mobile: operational pages (Sales, Purchases, Books) require **More** (3+ taps) | Slower than desktop for same tasks |
| 9 | Members page has no mobile nav path | Owner cannot manage team on phone |
| 10 | Orphan routes (`Today's Summary` nav key, `render_advanced`, `render_customer_ledger`) | Maintenance debt; i18n/catalog drift |

---

## 11. IA options (from AD-UI-001 — evaluate, not implement)

| Option | Summary | Trade-off | Audit fit |
|--------|---------|-----------|-----------|
| **A — Restore top-level statements** | BS, P&L, CF as sidebar items | Clutter; highest discoverability | Fixes #1–2 quickly |
| **B — Books = Financial Statements** | Expand Books; move BS/P&L/CF; slim Reports to management | Clear model; Reports refactor | Fixes #1–3; best for accountants |
| **C — Rename Executive tab** | “Financial Statements”; reorder picker | Cheapest; still nested | Partial fix #2 only |
| **D — Hybrid** | Books = GL/TB/COA; new **Statements** group; Reports = operational | Most clarity; most churn | Best long-term; fixes #1–4 |

---

## 12. Preliminary recommendation — restaurant-owner workflow

**Persona:** Owner-operator, daily cash business, monthly review with accountant.

**Daily (optimize for 1–2 taps)**

- Keep: Home, New Transaction (FAB), Banking hub (recon + EOD), mobile AR/AP shortcuts.
- Fix: Move **Closings** out of “Advanced” into **Work** (or Banking group on desktop).
- Fix: Dashboard recon/EOD badges should navigate (not display-only).

**Weekly**

- Banking + Payables + Purchases — OK via People/Banking hubs; consider Payables on People hub only (already there).

**Monthly (critical gap)**

- Owner needs **P&L and Balance Sheet in ≤2 clicks** — current desktop path is 3+ and non-obvious.
- **Recommend Option B or D** for implementation: statements in Books or dedicated Statements accordion; rename Executive tab regardless.

**Roles**

- Cashier: keep New + Banking + Closings; hide Reports Executive financial picker OR show only Today’s Summary — policy decision for AD-UI-001 impl.
- Do not expand cashier write access via nav changes.

**Do not implement in this pass** — record for AD-UI-001 implementation task.

---

## 13. Audit checklist (§4 — completed)

| Item | Status |
|------|--------|
| Full page list (`_PAGE_DISPATCH`, sidebar, mobile) | ✅ §2 |
| Orphan routes | ✅ §2.3, §5 |
| Duplicate paths | ✅ §6 |
| Hidden-by-role pages | ✅ §2.1 role column |
| Day-one operator workflow | ✅ §7 A, G, H |
| Month-end accountant workflow | ✅ §7 I |
| Banking clerk workflow | ✅ §7 E, G |
| Owner management vs financial reports | ✅ §8 permission gap |
| Mobile parity | ✅ §9 |
| Reports hub vs deep-links | ✅ §9 |
| i18n / Executive label | ✅ §8, §10 #2 |
| `modules_catalog` gaps | ✅ §8 |
| Company toggles | ✅ §2.1 `(mod)` |
| `view_management_reports` vs Executive | ✅ §8 |
| Nav test contracts | ✅ §9 |

---

## 14. Redesign constraints (unchanged)

When AD-UI-001 implementation starts:

- Preserve `render_*` posting logic unless explicitly scoped
- Preserve `_NAV_ROLE_PAGES` semantics (reorganize OK; no silent cashier expansion)
- Preserve mobile shell contract ([UI_SHELL.md](../UI_SHELL.md))
- Preserve i18n key pattern
- Preserve AD-001–AD-015 accounting behavior

---

## 15. Audit log

| Date | Auditor | Summary |
|------|---------|---------|
| 2026-06-09 | — | AD-UI-001 approved; prerequisite doc created; pre-audit symptoms §2–3 (original) |
| 2026-06-09 | Cursor | **Phase 1 complete** — full inventory, workflows, financial/mobile audits, top 10 problems, IA evaluation, restaurant-owner recommendation |

---

## 16. D1 implementation (Option D — 2026-06-05)

**Scope delivered:** Routing and navigation only. No calculation, posting, or permission changes.

### Desktop

- New accordion **`statements`** (`nav.group.statements`) in **Reports & overview**, **before** `📊 Reports`.
- Pages: `💰 Profit & Loss`, `🏛️ Balance Sheet`, `💸 Cash Flow` — thin wrappers → existing `render_profit_loss` / `render_balance_sheet` / `render_cash_flow`.
- **Reports → Executive** picker trimmed to: Budget, Trial Balance, General Ledger, Transaction Ledger, Today's Summary.

### Mobile

- **Reports hub:** Financial Statements section + direct page links (replaces `report_exec` shortcuts for P&L/BS/CF).
- **More hub:** Financial Statements section + `statements` accordion mirror.

### Routing / redirects

- `_PAGE_DISPATCH` entries for three statement keys.
- Legacy `rpt_exec_sel` values `pnl` / `balance_sheet` / `cash_flow` redirect to new routes.
- Date filters: `_DATE_FILTER_PAGE_KEYS` = Reports + statement pages (sidebar desktop; `render_mobile_report_filters` on mobile).

### Roles

- Statement pages added to every role list that already had `📊 Reports` (owner via `_NAV_ACCORDION`; explicit for manager/cashier/partner/viewer).

### Tests

- `tests/test_nav_statements_d1.py` — routes, dispatch, Executive exclusion, mobile entries, date filters, role parity.
- `tests/test_mobile_nav.py` — viewer hub visibility updated.

### Deferred (D2+)

- Executive tab rename, TB/GL/Budget dedup, Transaction History sidebar move, Reports tab rework.

---

*Next step: D2 planning when approved — routing/presentation only.*
