# MOBILE-UX-01 — Full Mobile Navigation Audit

**Mode:** UX architecture audit — characterization only. No code, no implementation.
**Basis:** code-derived from `_MOBILE_BOTTOM_NAV`, `_MOBILE_HUB_CONFIG`, `_NAV_ACCORDION`, `_NAV_ROLE_PAGES`, and the mobile hub-sheet renderers (`app.py:3326–3492`).
**Lens:** configurable multi-industry ERP (restaurants, retail, trading, services, partnerships, bookkeeping firms) — **not** restaurant-optimized.

---

## 1. Current mobile navigation (exact structure)

**Bottom bar (5 fixed slots):**
`Home` · `Banking` (hub) · `New` (+ transaction) · `Reports` (hub) · `More` (hub).

**Hubs (bottom-sheet overlays, `mobile_hub_open` state):**
- **Banking hub:** Banking (accounts) · Cash Reconciliation · External Sales Verification · End-of-Day Close · Banking Import.
- **Reports hub:** Transaction Ledger · Sales (report) · Expenses (report).
- **People hub** (opened *from* More): Customers · Vendors/Suppliers · Receivables · Payables · Workers · Partner Accounts · Members.
- **More hub:** → People hub · **Statements** section (accordion: P&L, Balance Sheet, Cash Flow) · **Books** section (accordion: GL, Chart of Accounts, Journal Entries, Trial Balance, Fiscal Periods, Year-End Close, Budget, **Recon Health**, Opening Balances) · **History** section (Transaction Ledger *again* + transactions accordion: Sales, Expenses, Staff Capture, Purchases, Recurring) · Inventory · **Admin** section (Company Settings, Backup/Restore, Audit Log).

**Mobile-only nav:** the hub-sheet pattern; mobile profile sheet; company-switch sheet. **Hidden/not in mobile hubs:** Recipe Costing (desktop accordion only), Permissions (desktop Settings accordion), Today Summary, My Account (via profile sheet).

**Desktop vs mobile:** desktop uses `_NAV_ACCORDION` (8 groups) + direct pages in a sidebar tree; mobile collapses these into 4 hubs + bottom bar. Role gating (`_NAV_ROLE_PAGES`: owner/manager/cashier/partner/viewer) applies to both.

---

## 2. Navigation inventory (grouped, with mobile suitability)

| Group | Pages | Freq | Importance | Mobile fit |
|-------|-------|------|------------|-----------|
| **Daily work** | Home, New Transaction, Sales, Expenses, Staff Expense Capture, Purchases, Recurring Expenses, Today Summary | very high | high | **High** |
| **Closings** | Cash Reconciliation, External Sales Verification, End-of-Day Close | daily (some industries) | high | Med–High |
| **Banking** | Banking (accounts), Banking Import, Recon Health | weekly/monthly | high | **Mixed** — accounts/health fine; **import desktop-first** |
| **Reports** | Reports, P&L, Balance Sheet, Cash Flow, Transaction Ledger, Sales report, Expenses report | daily–weekly | high | **High (read)** |
| **Accounting/Books** | GL, Chart of Accounts, Journal Entries, Trial Balance, Fiscal Periods, Year-End Close, Budget, Opening Balances | monthly/rare | high (specialist) | **Low–Med — desktop-first** |
| **People** | Customers, Vendors, Receivables, Payables | daily–weekly | high | High |
| **Team/Partners** | Workers, Partner Accounts, Members | weekly/monthly | med | Med |
| **Inventory** | Inventory, Recipe Costing (industry) | varies | varies | Med (RC desktop-first) |
| **System/Admin** | Company Settings, Permissions, Backup/Restore, Audit Log, My Account | rare | med | **Low — desktop-first** |

---

## 3. Operator frequency analysis (challenging assumptions)

| Page class | Restaurant owner | Small-biz owner | Bookkeeper | Accountant | Partner |
|------------|------------------|-----------------|------------|------------|---------|
| Home / Today | multiple/day | daily | daily | weekly | weekly |
| New Transaction / capture | multiple/day | daily | daily | rarely | rarely |
| Closings (cash/EOD/ext-sales) | **daily** | weekly | weekly | monthly | rarely |
| Banking accounts/recon | weekly | weekly | **daily/weekly** | monthly | rarely |
| Reports (P&L/BS/CF) | weekly | weekly | weekly | **monthly (deep)** | **monthly** |
| Receivables/Payables | daily | daily | daily | monthly | weekly |
| Books (GL/JE/TB/YEC) | rarely | rarely | weekly | **monthly (core)** | rarely |
| Partners | n/a | rarely | monthly | monthly | **weekly** |
| Settings/Admin | rarely | rarely | rarely | rarely | never |

**Assumption challenges:**
- **Banking is not universally daily.** Restaurants close cash daily; a service business or partner banks rarely. Giving Banking a *fixed* bottom slot over-serves some industries and under-serves others — argues for a **role/industry-aware 4th slot**, not a hard-coded one.
- **"Reports" is everyone's monthly anchor — yet the bottom-nav Reports hub omits the financial statements** (they're buried under More). The most-wanted reports are the hardest to reach. (§6.)
- **Closings are not "Banking."** They're a distinct daily ritual mixed into the Banking hub today.

---

## 4. Bottom navigation audit

**Belongs permanently (universal):** `Home`, `New` (+), `More`. These are role/industry-neutral and high-frequency.

**Belongs, but conditionally:** `Reports` — yes, but only if it actually contains the statements (today it doesn't). `Banking` — yes for banking-heavy industries; questionable as a *fixed* slot for all.

**Does NOT belong / clutter:**
- Mixing **Closings** (Cash Recon, EOD, External Sales) into the **Banking** hub — conceptually wrong; closings are a daily ritual, not banking.
- **Banking Import** in a bottom hub — it's desktop-first (per BANKING-UX audits); promoting it on mobile invites a poor flow.

**Duplicate navigation:** **Transaction Ledger** appears in the Reports hub **and** the More→History section **and** as a direct page — three paths to one page. **Sales/Expenses** appear as *reports* (Reports hub) and as *record pages* (More→transactions) — the same label means two different things.

**Should never appear on the bottom bar:** Settings/Admin, Permissions, Backup/Restore, Journal Entries, Chart of Accounts, Year-End Close — specialist/rare, desktop-first.

---

## 5. More page audit

**Currently:** a nested **hub-sheet** (More → People hub; More → Books accordion of 9 pages; More → History; More → Admin). Depth: up to More → hub → accordion → page (3–4 taps).

- **Belongs there:** Books, Admin/Settings, Inventory, Team — low-frequency/specialist.
- **Missing / mis-placed:** **Recon Health** sits under *Books* (it's a banking/reconciliation page); **statements** are under More but should be in Reports.
- **Should move out:** the financial statements (→ Reports); Recon Health (→ Money/Banking).
- **Should be grouped:** People + Team are split awkwardly (People hub vs Team pages); collapse into clear "People & Team."

**Recommendation:** convert More from nested hub-sheets to a **full-screen, grouped, searchable page** (sections: People & Team · Books · Banking detail · Inventory · Admin/Settings). A full-screen More scales far better than stacked bottom-sheets as the page count grows (§9).

---

## 6. Reports audit

**Headline finding:** the **Reports bottom-nav hub does not contain the financial statements.** It holds Transaction Ledger + Sales/Expenses summaries; **P&L, Balance Sheet, Cash Flow live under More → Statements.** Every user persona (§3) reaches for these monthly, so the most-wanted reports are 3–4 taps deep while a transaction ledger sits on the front.

**Where reports should live:** a **dedicated Reports hub** that contains, in priority order: **P&L, Balance Sheet, Cash Flow**, then Transaction Ledger, then Sales/Expenses summaries. Not split across Reports + More. Reports are read-mostly and **genuinely mobile-friendly**, so they earn the bottom slot — *if filled correctly*.

---

## 7. Banking audit

- **Keep a primary bottom destination, but reframe it as "Money," not "Banking,"** and make its prominence **role/industry-aware** (C setting): for restaurants/retail it surfaces daily closings + banking; for a partner/viewer it could yield the slot to People or Reports.
- **Separate Reconciliation/Closings from Banking-accounts:** Cash Reconciliation, EOD, External Sales are a **daily ritual** — group them as "Close" within Money, distinct from account management.
- **Banking Import stays desktop-first** — expose only light review/approve on mobile (per BANKING-UX-02).
- **Move Recon Health into Money/Banking** (out of Books).
- Banking should **not** be demoted entirely to More — banking-heavy industries need it fast; the configurable-slot approach serves both.

---

## 8. Mobile-first vs desktop-first

**Genuinely useful on mobile (mobile-first):** Home/Today, New Transaction, Sales/Expense capture, Receivables/Payables lookup, Reports (read), Cash Reconciliation entry, EOD close, light Match-Queue *approve*, Recon Health (read).

**Desktop-oriented (mobile = read/approve only):** **Statement Import + column mapping**, full **Reconciliation Queue** work, **Journal Entries**, **Chart of Accounts**, **Year-End Close / Fiscal Periods**, **Budget**, **Opening Balances**, **Permissions / Members admin**, **Backup/Restore**. Inventory and Recipe Costing are mid (entry on mobile possible; bulk desktop).

Principle: mobile is for **capture, lookup, read, and approve**; desktop is for **bulk data entry, reconciliation work, and structural accounting**.

---

## 9. Scalability audit (3-year horizon)

- **Hub-sheet nesting won't scale.** More already nests a hub + multiple accordions; each new module deepens the stack. Bottom-sheets stacked 3–4 deep become unnavigable.
- **Menu growth risk:** Books already holds 9 pages; Admin and People will grow. Accordion-in-sheet hides them further.
- **Discoverability risk:** the Reports/Statements split shows the failure mode — important pages get buried as the tree grows.
- **Duplication risk:** Transaction Ledger (×3) and Sales/Expenses dual-meaning will multiply as more "view vs record" pairs appear.
- **Config risk:** a fixed 5-slot bar can't express per-industry priorities at scale — needs role/industry-aware slotting.

---

## 10. Recommended mobile information architecture (actual pages)

**Bottom nav (5, with a configurable 4th slot):**
1. **Home** (Home/Today)
2. **Money** (hub) — *Close*: Cash Reconciliation, External Sales Verification, End-of-Day Close · *Bank*: Banking accounts, Recon Health, (Import → "open on desktop" / light review)
3. **New (+)** — New Transaction
4. **Reports** (hub) — **P&L, Balance Sheet, Cash Flow**, Transaction Ledger, Sales summary, Expenses summary *(configurable: swap with People for finance-light roles)*
5. **More** (full-screen, grouped, searchable)

**More (full-screen) sections:**
- **People & Team:** Customers, Vendors, Receivables, Payables, Workers, Partner Accounts, Members
- **Books:** GL, Chart of Accounts, Journal Entries, Trial Balance, Fiscal Periods, Year-End Close, Budget, Opening Balances
- **Inventory:** Inventory (+ Recipe Costing *when industry enabled*)
- **Admin & Settings:** Company Settings, Permissions, Backup/Restore, Audit Log, My Account

**Reports location:** dedicated bottom hub (statements first). **Banking location:** "Money" bottom hub (with Close grouped in). **Settings location:** More → Admin & Settings (never bottom). **Recon Health:** Money (not Books). **De-duplicate** Transaction Ledger to one canonical home (Reports), and relabel Sales/Expenses *report* vs *record* distinctly.

---

## 11. FastAPI / React future

- Bottom slots become **stable top-level routes**: `/home`, `/money`, `/new`, `/reports`, `/more`; More sub-sections are nested routes (`/more/books`, `/more/people`). Reports/statements get real URLs (`/reports/profit-loss`) — fixing discoverability and deep-linking.
- **Drop the `mobile_hub_open` session-state coupling** — React uses the router; hubs become routes, not stateful sheets.
- **Role/industry config drives which routes render** (reuse the `_NAV_ROLE_PAGES` model + the registry company settings from P2.3) — the same config powers Streamlit now and React later.
- Keep nav **declarative** (a route table) so it survives migration unchanged.

---

## 12. Risks

- **Navigation debt:** Transaction Ledger reachable 3 ways; Sales/Expenses dual-meaning; Recon Health mis-grouped.
- **Hidden functionality:** financial statements buried under More instead of Reports — the single biggest discoverability bug.
- **Operator confusion:** Banking hub conflates banking with daily closings; "Sales" meaning record-vs-report.
- **Menu bloat:** nested hub-sheets + 9-item Books accordion; grows worse over 3 years.
- **One-size bottom bar:** fixed Banking slot mis-serves finance-light industries/roles.

---

## 13. Recommended MVP changes

**Small (safe, high-value):**
- Put **P&L / Balance Sheet / Cash Flow into the Reports hub** (fix the headline discoverability bug).
- Move **Recon Health** from Books → Money/Banking.
- **De-duplicate Transaction Ledger** to one canonical home; **relabel** Sales/Expenses *report* vs *record*.
- Rename Banking bottom hub → **"Money"** and group Closings as "Close" within it.

**Medium:**
- Convert **More to a full-screen, grouped, searchable page** (People & Team · Books · Inventory · Admin & Settings).
- Make the **4th bottom slot role/industry-aware** (Reports vs People) via the existing settings model.
- Mark Statement Import / Reconciliation Queue / Books pages **desktop-first** on mobile (read/approve only).

**Large (redesign):**
- **Configurable bottom navigation** per role + industry (C company / B user), reusing the P2.3 registry.
- **Route-based IA** for the React/FastAPI migration (declarative route table + role/industry filters).

---

*Characterization only. No code, no implementation. Core findings: the Reports bottom-nav omits the financial statements (biggest discoverability bug); Banking conflates banking with daily closings and is a fixed slot that mis-serves finance-light industries; More is a deeply-nested hub-sheet that won't scale; and duplicate paths (Transaction Ledger ×3, Sales/Expenses dual-meaning) are accruing navigation debt. Favor a configurable, route-ready IA over a restaurant-tuned fixed bar.*
