# NAV-ARCH-S4 — React Route Contract

**Status:** ✅ **Frozen (NAV-ARCH-S4)**  
**Source of truth:** `registry/navigation.py` → `NAV_PAGES[].react_route`  
**Consumers:** Future FastAPI + React SPA router (not implemented in this slice)  
**Tests:** `tests/test_nav_arch_s4_react_route_contract.py`

## Purpose

This document freezes the **1:1 `route_key → react_route` migration contract** for the ERP navigation registry. Streamlit continues to route by `route_key` (`nav_selection`); React will route by `react_route` path.

## Contract rules

1. **One canonical path per `route_key`** — no duplicate `react_route` values across dispatch routes.
2. **Safe path naming** — lowercase ASCII segments; hyphen separators; absolute paths; pattern `^/(?:[a-z0-9]+(?:/[a-z0-9-]+)*)?$` (root `/` allowed once for Home).
3. **No legacy alias paths** — `LEGACY_NAV_ALIASES` in `registry/nav_keys.py` resolve to canonical `route_key` values; aliases do **not** receive separate React paths.
4. **Retired routes stay retired** — `Today's Summary` reroutes to `Reports` (`/reports`); no `/today` path.
5. **Change policy** — any `react_route` edit requires updating `registry/navigation.py`, this doc, and `tests/test_nav_arch_s4_react_route_contract.py`.

## Domain map (43 routes)

| Domain | `react_route` prefix | Notes |
|--------|----------------------|-------|
| Dashboard | `/` | Home only |
| Transactions | `/transactions/*` | New Transaction, Transaction Ledger |
| Operations | `/sales`, `/expenses/*`, `/purchases`, `/closings/*` | Includes staff capture under `/expenses/` |
| Recipes | `/recipes/*` | Recipe costing module |
| CRM | `/customers`, `/vendors`, `/receivables`, `/payables` | People operational records |
| Inventory / Banking | `/inventory`, `/banking`, `/banking/accounts` | Direct sidebar + hidden React-only bank accounts list |
| Reports | `/reports`, `/reports/*` | Hub + statement shortcuts share reporting domain |
| Books | `/books/*` | GL, COA, fiscal, budget, recon health, opening balances |
| Team | `/partners`, `/workers` | Partner accounts + workers |
| Settings / Admin | `/settings/*` | Company, members, permissions, audit, backup |
| Account | `/account` | My Account (header profile; not sidebar) |

## Frozen mapping (`route_key` → `react_route`)

| route_key | react_route |
|-----------|-------------|
| Home | `/` |
| New Transaction | `/transactions/new` |
| Transaction Ledger | `/transactions/ledger` |
| Sales | `/sales` |
| Expenses | `/expenses` |
| Staff Expenses | `/expenses/staff-capture` |
| Recurring Expenses | `/expenses/recurring` |
| Purchases | `/purchases` |
| Cash Reconciliation | `/closings/cash-recon` |
| External Sales Verification | `/closings/external-sales` |
| Ingredients | `/recipes/ingredients` |
| Recipes | `/recipes` |
| Cost Breakdown | `/recipes/cost-breakdown` |
| Menu Items | `/recipes/menu-items` |
| End-of-Day Close | `/closings/eod` |
| Customers | `/customers` |
| Vendors | `/vendors` |
| Receivables | `/receivables` |
| Payables | `/payables` |
| Inventory | `/inventory` |
| Banking | `/banking` |
| Bank Accounts | `/banking/accounts` |
| Reports | `/reports` |
| Profit & Loss | `/reports/profit-loss` |
| Balance Sheet | `/reports/balance-sheet` |
| Cash Flow | `/reports/cash-flow` |
| General Ledger | `/books/general-ledger` |
| Trial Balance | `/books/trial-balance` |
| Journal Entries | `/books/journal-entries` |
| Fiscal Periods | `/books/fiscal-periods` |
| Year-End Close | `/books/year-end-close` |
| Budget | `/books/budget` |
| Chart of Accounts | `/books/chart-of-accounts` |
| Recon Health | `/books/recon-health` |
| Partner Accounts | `/partners` |
| Workers | `/workers` |
| Company Settings | `/settings/company` |
| Members | `/settings/members` |
| Permissions | `/settings/permissions` |
| Audit Log | `/settings/audit-log` |
| Backup & Restore | `/settings/backup-restore` |
| Opening Balances | `/books/opening-balances` |
| My Account | `/account` |

## NAV-UX-02 subdomain contracts (aligned)

These NAV-UX-02 guardrails remain valid and are subsets of the frozen map above:

| Contract | Paths |
|----------|-------|
| **Financial statements** | `/reports/profit-loss`, `/reports/balance-sheet`, `/reports/cash-flow` |
| **Settings / admin** | `/settings/company`, `/settings/members`, `/settings/permissions`, `/settings/audit-log`, `/settings/backup-restore` |
| **Staff expenses** | `/expenses/staff-capture` (not under `/people/` or `/workers`) |

## Legacy aliases (canonical resolution only)

`LEGACY_NAV_ALIASES` (`registry/nav_keys.py`) maps persisted emoji/legacy `nav_selection` strings to canonical `route_key` values. Examples:

| Legacy alias | Canonical `route_key` | `react_route` |
|--------------|----------------------|---------------|
| `Today's Summary` | Reports | `/reports` |
| `Bank Statement Import` | Banking | `/banking` |
| `🏠 Home` | Home | `/` |

**No alias receives its own React path.** Resolution order: legacy reroute telemetry (`app.py`) → `normalize_nav_key()` → dispatch.

## Validation API

```python
from registry.navigation import react_routes, validate_react_route_contract

validate_react_route_contract()  # raises ValueError on contract violation
routes = react_routes()          # dict[route_key, react_route]
```

## No-change statement (NAV-ARCH-S4)

- **No React implementation.** No FastAPI route exposure. Documentation + validation tests only.
- **No Streamlit navigation behavior change.**

---

*Frozen 2026-06-17. Registry: `registry/navigation.py`. Parity guard: `tests/test_nav_arch_s4_react_route_contract.py`.*
