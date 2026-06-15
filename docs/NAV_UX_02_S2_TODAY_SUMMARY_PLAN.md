# NAV-UX-02-S2 — Today's Summary Orphan Route: Decision Plan

**Status:** **Implemented** — see `docs/NAV_UX_02_S2_IMPLEMENTATION.md` (NAV-UX-02-S2-IMPL).

**Mode:** Planning only. **No UI change, no route deletion, no role change, no cleanup.** This decides what to do with the orphan `Today's Summary` route; implementation is a later, separately-approved slice.

## Key correction to the NAV-UX-02 audit

The **dispatch route** `NAV_TODAY_SUMMARY` is orphaned (in `_PAGE_DISPATCH` + `ALL_NAV_PAGE_KEYS` + a legacy alias, but in **no** accordion, direct list, mobile config, or role list — unreachable as a page). **However, the `render_today_summary` *function* is NOT dead** — it is reachable today via **Reports → Accounting Tools tab → "Today's Summary"** picker option (`app.py:22646-22655`, `rpt_exec_sel == "today_summary"`). So this is a **dead door to a live room**, not a dead feature.

## 1. `render_today_summary` — what it does

`app.py:22460-22546`. A strictly **today-only end-of-day snapshot**:
- Sales by type: Cash / Card / Credit / Total (`Sale.date == today`).
- Total expenses and total purchases for today.
- **Net cash position** metric = (cash + card collected) − today expenses.
- **Today's transactions table** (sales + expenses + purchases) with **Excel/PDF export** (`render_export_buttons(df, "Today_Summary")`).

## 2. How it differs from `render_dashboard`

`render_dashboard` (`app.py:10910+`) is a **broad multi-period operational hub**: today sales-by-type **and** yesterday comparison, this-month vs last-month, a **7-day trend**, **alerts** (overdue invoices, payables due soon, recurring pending), and **recon/EOD status badges**. It is KPI + trend + alert oriented.

`render_today_summary` is **single-day and report-shaped**: no comparisons, no trends, no alerts — but it **adds two things the dashboard does not have**: (a) today's **purchases** total and a dedicated **net-cash** metric, and (b) an **exportable line-item table** of every transaction booked today.

## 3. Unique daily-use value?

**Partial, but real.** The today KPIs (sales-by-type, today expenses) **duplicate** dashboard cards. The **exportable daily transaction table** and the **net-cash position** are **unique** — useful for a daily cash close / handover printout. So the page is not pure duplication; its export table is the distinguishing value.

## 4. Duplication assessment

- **Duplicates dashboard:** today sales-by-type, today expenses.
- **Does NOT duplicate:** the exportable today-transactions table; the explicit net-cash metric; today purchases.
- **Already linked:** reachable via Reports exec picker, so retiring the dead dispatch route loses **no** functionality.

## 5. Options A–D

| Option | Description | Assessment |
|--------|-------------|------------|
| **A. Surface as a direct page / accordion entry** | Add `Today's Summary` back into the sidebar/mobile nav and role lists | Adds a third today-view alongside Home + Reports exec; increases nav clutter; **not recommended** |
| **B. Link from a dashboard card/button only** | Keep the function reachable; add a Home button → the Reports exec "Today's Summary" view | Improves daily-use discoverability without a new top-level route; **recommended (optional enhancement)** |
| **C. Merge into Home dashboard** | Fold the export table + net-cash into `render_dashboard` | Bloats Home (KPI/trend/alert role) with a report table; mixes concerns; **not recommended** |
| **D. Retire the orphan route safely** | Remove the **dead dispatch route key + legacy alias**, keep `render_today_summary` reachable via Reports exec | De-dupes the dead door with zero feature loss; **recommended (primary)** |

## Recommendation

**D (primary) + B (optional).** Retire the **dead `NAV_TODAY_SUMMARY` dispatch route and its legacy alias** because the route is unreachable and the function stays available through Reports → Accounting Tools → "Today's Summary". Do **not** delete `render_today_summary` (it has a live caller and unique export value). Optionally (B) add a Home dashboard quick-link to the Reports exec Today's Summary view for daily discoverability. Reject A (nav clutter) and C (concern-mixing / Home bloat).

## 6. Legacy alias impact

- `LEGACY_NAV_ALIASES["📅 Today's Summary"] = NAV_TODAY_SUMMARY` and `"Today's Summary"` is itself a canonical key (`registry/nav_keys.py:101`, `:7`).
- A persisted `nav_selection == "Today's Summary"` (old bookmark) currently dispatches to the page. If the route is removed from `_allowed`, the existing guard (`app.py:26438-26440`) silently falls back to **Home** — safe (no crash) but lands the user away from the summary.
- **Graceful path:** repoint the alias so `normalize_nav_key("Today's Summary")` / the emoji form resolves to **`NAV_REPORTS`** and presets `rpt_exec_sel = "today_summary"` — mirroring the existing legacy-reroute pattern (`_LEGACY_RPT_EXEC_TO_STATEMENT`, `app.py:26456`). This preserves the user's intent (they reach the summary, now inside Reports) with no dead-end.

## 7. Risk level

**LOW.** The dispatch route is already unreachable, so removing it changes no working navigation. `render_today_summary` and its Reports-exec caller are untouched. The only back-compat surface is the persisted-`nav_selection`/bookmark alias, fully handled by the graceful reroute (item 6). No accounting, schema, role, or data change.

## Proposed implementation slice (NAV-UX-02-S2-IMPL — not implemented here)

1. Repoint `Today's Summary` legacy alias → `NAV_REPORTS` + preset `rpt_exec_sel="today_summary"` (add to the legacy-reroute handling in `main()`); keep `render_today_summary` and its Reports-exec option as-is.
2. Remove `NAV_TODAY_SUMMARY` from `_PAGE_DISPATCH` and from `ALL_NAV_PAGE_KEYS` (route retirement), keeping the constant only if still referenced by the reroute.
3. (Optional, B) Add a Home dashboard button → Reports exec Today's Summary.
4. Update `docs/NAV_UX_02_AUDIT.md` to reflect that the orphan is resolved.

## Contract tests (for the implementation slice)

- **No orphan dead-end:** `normalize_nav_key("Today's Summary")` and `normalize_nav_key("📅 Today's Summary")` resolve to a **reachable** target (`NAV_REPORTS`), not a removed key.
- **Route retired:** `NAV_TODAY_SUMMARY` (string `"Today's Summary"`) is **not** a `_PAGE_DISPATCH` key after the change (or is intentionally repurposed) — guard against silent re-introduction.
- **Function still reachable:** the Reports exec picker still offers the `("today_summary", "reports.exec.today_summary")` option (structural assertion over the option tuple at `app.py:22646-22655`).
- **Graceful fallback unchanged:** an unknown/removed `nav_selection` still falls back to `NAV_HOME` (existing guard) — no crash.
- **Dispatch ↔ keys parity:** every remaining `_PAGE_DISPATCH` key ∈ `ALL_NAV_PAGE_KEYS` and is reachable from sidebar/mobile/role config (the NAV-UX-02-S1 parity test, with `Today's Summary` no longer in `KNOWN_HIDDEN`).

## 8. Suite impact

**Full test suite should remain unchanged except navigation tests.** No accounting/posting/report/API test should change. Only nav-structure tests (the parity/alias assertions above) are added or updated in the implementation slice. This planning slice changes **no runtime code** and adds only this plan doc + its doc-contract test; the full suite stays green.

## No-change statement (NAV-UX-02-S2 planning)

- **No UI change, no route deleted, no role changed, no cleanup, no `app.py` edit.** Decision + evidence + risk + slice + tests only; execution is the separately-approved NAV-UX-02-S2-IMPL slice.

---

*Planning only. Correction: the Today's Summary route is orphaned but `render_today_summary` is still reachable via Reports → Accounting Tools → "Today's Summary" (`app.py:22646-22655`). It partly duplicates the dashboard's today KPIs but uniquely provides an exportable today-transactions table + net-cash metric. Recommendation: D (retire the dead dispatch route + legacy alias) + optional B (Home quick-link); keep the function and its Reports-exec caller; reject A (clutter) and C (Home bloat). Legacy alias repointed to NAV_REPORTS + rpt_exec_sel preset so old bookmarks reach the summary inside Reports instead of dead-ending. Risk LOW (route already unreachable; only the persisted-nav alias needs the graceful reroute). Contract tests: alias resolves to a reachable target, route retired from dispatch/keys, function still offered in Reports exec, fallback-to-Home preserved, dispatch↔keys parity. Suite unchanged except nav tests.*
