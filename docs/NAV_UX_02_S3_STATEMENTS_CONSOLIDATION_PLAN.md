# NAV-UX-02-S3 — Financial Statements Consolidation: Decision Plan

**Mode:** Planning only. **No UI change, no route deletion, no role change, no cleanup.** This defines a single canonical navigation model for Profit & Loss, Balance Sheet, and Cash Flow; implementation is a later, separately-approved slice.

## Correction to the NAV-UX-02 audit

The audit said statements appear "as top-level accordion **+ inside the Reports page** + mobile hub." Reading the code, the **Reports page does NOT render the statements** — its tabs are `exec / sales / expenses / customers / vendors / banking / eod` (`app.py:22631-22639`, `_REPORTS_MOB_TAB_IDS` `22549-22557`). The statements are **separate canonical routes** with multiple *entry doors*, all converging on the **same** render path. So this is **multi-door, single-room**, not duplicated rendering — cleaner than the audit implied.

## 1. Current exposure map

Each statement is **one canonical route** → a thin page wrapper → the core renderer:

| Statement | route_key | page wrapper | core renderer | role_gate | date filter |
|---|---|---|---|---|---|
| Profit & Loss | `NAV_PROFIT_LOSS` | `render_profit_loss_page` (`app.py:25604`) | `render_profit_loss` (`25632`) | O M C P V | sidebar (`_DATE_FILTER_PAGE_KEYS`) |
| Balance Sheet | `NAV_BALANCE_SHEET` | `render_balance_sheet_page` (`25614`) | `render_balance_sheet` (`25733`) | O M C P V | sidebar |
| Cash Flow | `NAV_CASH_FLOW` | `render_cash_flow_page` (`25622`) | `render_cash_flow` (`25831`) | O M C P V | sidebar |

**Entry doors to those canonical routes (all set `nav_selection` to the same key):**
1. **Desktop sidebar — accordion group `statements` "Financial Statements"** (`app.py:3451-3455`): the three routes as top-level entries. ← *canonical desktop home*.
2. **Mobile reports hub** (`_MOBILE_HUB_CONFIG["reports"]`, `app.py:3394-3401`): `("page", NAV_PROFIT_LOSS…)` etc. — deep-links to the same routes.
3. **Legacy reroute** `_LEGACY_RPT_EXEC_TO_STATEMENT` (`app.py:3234-3238`, applied `26456`): old `rpt_exec_sel` ids `pnl/balance_sheet/cash_flow` → the same routes.

**No statement is rendered in a second place** — the Reports page, the mobile hub, and the legacy picker all route to the one canonical render. Role visibility is uniform (all five roles) on both the statements and the Reports page.

## 2. Proposed canonical ownership

- **Canonical home = the three statement routes** (`NAV_PROFIT_LOSS`, `NAV_BALANCE_SHEET`, `NAV_CASH_FLOW`), grouped under the existing desktop **"Financial Statements"** accordion. One route → one page wrapper → one core renderer per statement. **No change to that structure** — it is already the single source of truth.
- **`owner_area` = Reports (Financial Statements sub-area).** Statements belong to the reporting domain but remain their own group, distinct from the management-analytics **Reports** page (sales/expenses/customers/vendors/banking/eod). They are **peers under Reports**, not tabs of it.

## 3. Shortcut model

Every non-canonical surface is an explicit **shortcut** that navigates to the canonical route — it must **never** render a statement itself:

| Surface | Role | Behavior |
|---|---|---|
| Desktop accordion "Financial Statements" | canonical | the home; no change |
| Mobile reports hub statement entries | shortcut | deep-link → canonical route (no separate render) |
| Legacy `rpt_exec_sel` `pnl/balance_sheet/cash_flow` | shortcut (legacy) | reroute → canonical route; retirement candidate (S6/below), not now |
| Any future dashboard link | shortcut | navigate → canonical route |

Rule (mirrors S2): **shortcuts set `nav_selection`/preset only; the canonical route owns the render.**

## 4. Migration path (NAV-UX-02-S3-IMPL — not implemented here)

1. **Confirm & document** the three canonical routes as the single home (no code change; doc + audit update).
2. **Classify** the mobile-hub and legacy entries explicitly as *shortcuts* in the audit (no behavior change).
3. **Freeze the React route contract** (§React below) as the 1:1 migration map.
4. **(Later, telemetry-gated)** retire the legacy `_LEGACY_RPT_EXEC_TO_STATEMENT` reroute once no usage is observed — same pattern as NAV-UX-02-S6; **no deletion now**.

## React route contract

One canonical path per statement, nested under the reporting domain (1:1 `route_key → react_route`, consistent with the audit):

- `NAV_PROFIT_LOSS` → `/reports/profit-loss`
- `NAV_BALANCE_SHEET` → `/reports/balance-sheet`
- `NAV_CASH_FLOW` → `/reports/cash-flow`

The desktop "Financial Statements" group maps to the `/reports/*` statement sub-tree; mobile hub + legacy ids resolve to the same paths (shortcuts, not distinct routes). No statement gets a second React path.

## 5. Mobile behavior

Unchanged: the mobile **reports hub** keeps the three statement deep-links as shortcuts to the canonical routes. No statement becomes a mobile-only page; no new mobile route. The hub remains a launcher, not a renderer.

## 6. Role implications

**None.** P&L / BS / CF are visible to **all five roles** today, and so is the Reports page — so grouping statements under the Reports domain does **not** narrow or widen any gate. Consolidation must **preserve the all-roles visibility**; a contract test pins this so a future re-parenting can't silently change it.

## 7. Contract tests (for the implementation slice)

- **Canonical routes present:** `NAV_PROFIT_LOSS / BALANCE_SHEET / CASH_FLOW` ∈ `_PAGE_DISPATCH` and ∈ `ALL_NAV_PAGE_KEYS`.
- **All-roles visibility preserved:** each statement key ∈ every `_NAV_ROLE_PAGES` list (O/M/C/P/V) — guard against accidental gating on re-parent.
- **Single render path:** the page wrappers delegate to the core renderers (structural: `render_profit_loss_page`→`render_profit_loss`, etc.) — no second render site.
- **Statements are not a Reports tab:** `_REPORTS_MOB_TAB_IDS` / Reports `st.tabs` labels do **not** include P&L/BS/CF (regression guard against re-introducing a duplicate render inside Reports).
- **Shortcut targets valid:** every `_MOBILE_HUB_CONFIG["reports"]` statement entry and every `_LEGACY_RPT_EXEC_TO_STATEMENT` value ∈ `_PAGE_DISPATCH` (no shortcut dead-ends).
- **React map 1:1:** the three `react_route` paths are unique and map back to exactly one route_key each.

## 8. Implementation slices (for Cursor — DO NOT implement yet)

- **NAV-UX-02-S3-IMPL-1 — formalize canonical + shortcuts:** doc/audit update classifying doors as canonical vs shortcut; add the §7 contract tests. No runtime change.
- **NAV-UX-02-S3-IMPL-2 — React route contract:** freeze `/reports/profit-loss|balance-sheet|cash-flow` as the migration map (planning artifact for the React front end).
- **NAV-UX-02-S3-IMPL-3 — legacy reroute retirement (later):** remove `_LEGACY_RPT_EXEC_TO_STATEMENT` once telemetry shows no use; telemetry-gated, separate approval.

## 9. Risk assessment

**LOW.** The statements already converge on one canonical route each; there is **no duplicated render** to untangle. The consolidation is classification + a frozen React contract + guard tests — **no render change, no role change, no route deletion**. The only future-removal candidate (legacy `rpt_exec_sel` reroute) is deferred and telemetry-gated. No accounting, schema, or data impact.

## No-change statement (NAV-UX-02-S3 planning)

- **No UI change, no route deleted, no role changed, no cleanup, no `app.py` edit.** Exposure map + canonical ownership + shortcut model + migration path + contract tests + slices + risk only; execution is the separately-approved NAV-UX-02-S3-IMPL slices.

---

*Planning only. Correction: the Reports page does not render statements (tabs are exec/sales/expenses/customers/vendors/banking/eod); P&L/BS/CF are single canonical routes (thin page wrapper → core renderer) reached via three doors — the desktop "Financial Statements" accordion (canonical home), the mobile reports hub (shortcut), and the legacy rpt_exec_sel reroute (shortcut). Canonical ownership = the three routes under the Reports domain, all-roles visibility preserved. Shortcut model: non-canonical surfaces only navigate, never render. React contract: /reports/profit-loss, /reports/balance-sheet, /reports/cash-flow (1:1). Mobile unchanged (hub stays a launcher). No role change. Contract tests pin canonical presence, all-roles visibility, single render path, statements-not-a-Reports-tab, shortcut-target validity, and React 1:1. Risk LOW — no duplicated render, no deletion; legacy reroute retirement deferred + telemetry-gated.*
