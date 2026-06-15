# NAV-UX-02-S1 — Purpose Validation Report

**Mode:** Audit + S1/S2 validation. **S2 implemented:** Today's Summary dispatch route retired (see `docs/NAV_UX_02_S2_IMPLEMENTATION.md`).

**Source:** `docs/NAV_UX_02_AUDIT.md`, `tests/nav_ux_02_contract.py`, `tests/test_nav_ux_02_s1_navigation_structural_contract.py`, `tests/test_nav_ux_02_s1_purpose_validation.py`

## Validation summary

| Check | Result |
|-------|--------|
| Dispatch ↔ `ALL_NAV_PAGE_KEYS` parity | PASS |
| Role page keys valid | PASS |
| Accordion integrity (in dispatch, no double-group) | PASS |
| Mobile hub / bottom nav validity | PASS |
| Legacy alias targets valid | PASS |
| Every dispatch handler callable + non-stub body | PASS |
| Non-hidden routes reachable from ≥1 nav surface | PASS |
| Documented duplicate workflows have ≥2 entry kinds | PASS |
| Known hidden orphan explicit (`KNOWN_HIDDEN`) | PASS (empty after S2) |

## 1. Routes that are working

All **43** `_PAGE_DISPATCH` routes resolve to callable render handlers with meaningful bodies and are reachable from at least one intended navigation surface (sidebar direct, accordion, mobile hub/bottom, or documented programmatic shortcut).

| Area | Routes (working) |
|------|------------------|
| Dashboard | Home |
| Transactions | New Transaction, Transaction Ledger, Sales, Expenses, Purchases, Recurring Expenses |
| Closings | Cash Reconciliation, External Sales Verification, End-of-Day Close |
| Recipe Costing | Ingredients, Recipes, Cost Breakdown, Menu Items |
| People | Customers, Vendors, Receivables, Payables |
| Inventory | Inventory |
| Banking | Banking |
| Reports | Reports, Profit & Loss, Balance Sheet, Cash Flow |
| Books | General Ledger, Trial Balance, Journal Entries, Fiscal Periods, Year-End Close, Budget, Chart of Accounts, Recon Health, Opening Balances |
| Team | Partner Accounts, Workers |
| Settings | Company Settings, Members, Permissions, Audit Log, Backup & Restore |
| Account | My Account |

**Legacy reroutes working:** `Bank Statement Import` → Banking/import; `rpt_exec_sel` statement/Books mappings; all `LEGACY_NAV_ALIASES` resolve to valid dispatch keys.

**Mobile shortcuts working:** `report_sales` / `report_expenses` → Reports with tab preset; `banking_import` → Banking/import; hub `open_hub` / `accordion` entries resolve to valid hubs/groups.

**Dialogs working:** `_vendor_add_dialog`, `_vendor_manage_dialog`, `_cat_add_dialog`, `_cat_manage_dialog`, `_subcat_add_dialog`, `_subcat_manage_dialog` exist and are callable.

## 2. Suspicious / dead / orphan routes

| Route | Classification | Evidence | Fix class |
|-------|----------------|----------|-----------|
| **Today's Summary** | **Retired (S2)** | Dispatch route removed; `render_today_summary` via Reports exec + legacy reroute to `NAV_REPORTS` | **A** — implemented in NAV-UX-02-S2 |
| **Staff Expenses** | **Role/purpose mismatch** | Owner-only in `_NAV_ROLE_PAGES`; label implies staff/cashier capture workflow | **C** — role-gate behavior change (NAV-UX-02-S5) |

No dispatch route failed the dead-stub heuristic (empty render body).

## 3. Duplicates — intentional vs cleanup candidates

### Intentional (documented `duplicate_workflow`)

| Cluster | Entry points | Status |
|---------|--------------|--------|
| `banking` | Sidebar Banking, money hub, legacy BSI reroute | Intentional |
| `statements` | Accordion statements, Reports in-page tabs, mobile reports hub | Intentional (consolidation candidate) |
| `txn_ledger` | Sidebar direct, reports hub, dashboard quick link | Intentional |
| `ar` / `ap` | Accordion people, mobile people hub, dashboard notifications | Intentional |
| `new_txn` | Sidebar direct, mobile bottom ＋ | Intentional |
| `members` | Settings accordion (desktop), People hub (mobile) | Intentional (surface inconsistency) |
| `reports_shortcuts` | Mobile sales/expenses shortcuts → Reports tabs | Intentional |

### Cleanup candidates (multi-entry, not in audit duplicate set)

| Page | Entry kinds | Notes | Fix class |
|------|-------------|-------|-----------|
| Inventory | sidebar + mobile more + programmatic | Dashboard low-stock link adds 3rd kind | **D** — optional shortcut audit |
| Staff Expenses | accordion + mobile more (transactions) | Exposed on mobile More accordion without desktop cashier access | **C/D** |
| Purchases, Recurring Expenses | accordion + mobile more | Mobile mirrors desktop accordion | **D** — low priority |
| Books pages (GL, COA, JE, …) | accordion + mobile more | Expected mobile Books mirror | **D** — document only |
| My Account | programmatic + all roles | Header/profile entry | **A** — working as designed |

## 4. Classified findings (B–F — not implemented)

| ID | Finding | Class | Risk | Proposed fix | Tests needed |
|----|---------|-------|------|--------------|--------------|
| F-01 | Today's Summary unreachable except programmatically | **A** — **resolved S2** | Low | Retired dispatch; Reports exec + legacy reroute | `test_nav_ux_02_s2_today_summary_retirement.py` |
| F-02 | Staff Expenses owner-only vs staff workflow label | **C** | Medium | Expand manager/cashier visibility if intended | Role matrix tests |
| F-03 | Members under Settings desktop vs People mobile | **D** | Low | Align mobile/desktop grouping in S4 | Cross-surface parity test |
| F-04 | Statements triple-exposed (accordion + Reports + mobile) | **D** | Medium | Consolidate canonical home in S3 | Statement route contract |
| F-05 | Legacy `rpt_exec_sel` / BSI reroutes still active | **B** | Low | Document; retire in S6 after telemetry | Legacy alias regression |
| F-06 | Audit Log owner+manager vs other Settings owner-only | **C** | Low | Confirm intentional; document | Role gate tests |

**Class A implemented:** `KNOWN_HIDDEN`, shared contract helpers, structural + purpose tests, this report.

## 5. Recommended next slices

1. ~~**NAV-UX-02-S2** — Resolve Today's Summary orphan~~ **Done (S2-IMPL)**
2. **NAV-UX-02-S3** — Statements consolidation (canonical home for P&L/BS/CF).
3. **NAV-UX-02-S4** — Cross-surface consistency (Members, Audit Log placement).
4. **NAV-UX-02-S5** — Role/purpose review (Staff Expenses visibility).
5. **NAV-UX-02-S6** — Legacy reroute retirement (`Bank Statement Import`, `rpt_exec_sel`).
6. **NAV-UX-02-S7** — Freeze React route map from audit inventory.

## 6. Test commands

```bash
pytest tests/test_nav_ux_02_audit.py
pytest tests/test_nav_ux_02_s1_navigation_structural_contract.py
pytest tests/test_nav_ux_02_s1_purpose_validation.py
pytest
```

---

*Purpose validation only — no navigation redesign. 43 working routes; 1 documented orphan; 7 intentional duplicate clusters; 6 classified follow-ups (A–F). Only class A artifacts implemented in S1.*
