# NAV-UX-02-S6 — Legacy Navigation Reroutes & Aliases: Decision Plan

**Mode:** Planning + **S6-IMPL-1 implemented (2026-06).** Behavior-neutral `nav.legacy` telemetry added; no alias/route deletion.

## 1. Legacy alias inventory

Five legacy mechanisms exist today (all targets verified valid):

| # | Mechanism | Location | Source → Target | Protects |
|---|---|---|---|---|
| 1 | **`LEGACY_NAV_ALIASES`** (emoji bulk) | `registry/nav_keys.py:98-147` | ~40 emoji-prefixed keys (e.g. `"🏠 Home"`) → canonical text keys (`NAV_HOME`, …) | persisted `nav_selection` / bookmarks from the pre-ICON-MODERNIZE emoji era |
| 2 | **`LEGACY_NAV_ALIASES`** (Today's Summary) | `nav_keys.py:100-101` | `"📅 Today's Summary"`, `"Today's Summary"` → `NAV_REPORTS` | old Today's Summary bookmarks (repointed in S2) |
| 3 | **`LEGACY_NAV_ALIASES`** (Bank Statement Import) | `nav_keys.py:145-146` | `"📥 Bank Statement Import"`, `"Bank Statement Import"` → `NAV_BANKING` | bookmarks to the old standalone import page |
| 4 | **`_LEGACY_NAV_TO_REPORTS_EXEC`** (S2) | `app.py:3270-3272` | `NAV_TODAY_SUMMARY`, `"📅 Today's Summary"` → preset `rpt_exec_sel="today_summary"` + `NAV_REPORTS` | Today's Summary intent → Reports exec view (S2 contract) |
| 5 | **`_LEGACY_RPT_EXEC_TO_STATEMENT`** / **`_LEGACY_RPT_EXEC_TO_BOOKS`** | `app.py:3258-3268` | `pnl/balance_sheet/cash_flow` → statement routes; `budget/trial_balance/general_ledger` → Books routes | persisted `rpt_exec_sel` from the old Accounting Tools picker |
| 6 | **Bank Statement Import reroute** (section-preserving) | `app.py:26486-26489` | `nav_selection=="Bank Statement Import"` → `NAV_BANKING` + `banking_section="import"` | old import route, **preserving the import sub-section** (alias #3 alone would not set the section) |

**Target validity:** every alias/reroute target is a current dispatch route (`NAV_*`) or a valid sub-state (`rpt_exec_sel="today_summary"`, `banking_section="import"`). **No dead-ends.** The ultimate safety net is `normalize_nav_key` → unknown keys pass through, then the `_allowed` guard (`app.py:26475-26477`) falls back to `NAV_HOME`.

## 2. Reroute behavior map

Order of resolution in `main()`:

1. **`_LEGACY_NAV_TO_REPORTS_EXEC`** (`app.py:26467-26470`): if the raw nav key is a Today's-Summary legacy key → set `nav_selection=NAV_REPORTS` + `rpt_exec_sel="today_summary"`.
2. else **`normalize_nav_key`** (`26472-26474`): emoji/legacy key → canonical via `LEGACY_NAV_ALIASES`.
3. **`_allowed` guard** (`26475-26477`): anything not permitted → `NAV_HOME` (safety net).
4. **Bank Statement Import reroute** (`26486-26489`): `"Bank Statement Import"` → `NAV_BANKING` + `banking_section="import"`.
5. **`_LEGACY_RPT_EXEC_TO_STATEMENT` / `_TO_BOOKS`** (`26492-26502`): a lingering `rpt_exec_sel` → the corresponding statement/Books route, then pops the key.

All five converge on **valid** routes/sub-states; the chain is idempotent (re-running normalizes once and pops the transient key).

## 3. Risk classification (per item — A/B/C/D/E)

| # | Mechanism | Class | Rationale |
|---|---|---|---|
| 1 | Emoji `LEGACY_NAV_ALIASES` (bulk) | **B — keep until React migration** | Protects durable persisted bookmarks; cost is one dict lookup; persisted emoji keys may linger until the React front end replaces the persistence model |
| 2 | Today's Summary alias → `NAV_REPORTS` | **B — keep until React migration** | Recently set by S2; still serving the agreed S2 contract; trivial cost |
| 3 | Bank Statement Import alias → `NAV_BANKING` | **B — keep until React migration** | Durable-bookmark protection; pairs with #6 |
| 4 | `_LEGACY_NAV_TO_REPORTS_EXEC` (S2) | **B — keep until React migration** | Recently added; the live S2 mechanism; do not retire prematurely |
| 5 | `_LEGACY_RPT_EXEC_TO_STATEMENT` / `_TO_BOOKS` | **C — telemetry-gated retirement** | Protects a **transient session key** (`rpt_exec_sel`), not a durable bookmark; lower retention value; retire after a window of zero hits |
| 6 | Bank Statement Import section-preserving reroute | **C — telemetry-gated retirement** | Page-merge reroute for an old standalone route; preserves the import section; retire after telemetry shows no use |

- **No item is class D (safe to retire now)** — none is provably unused without telemetry.
- **No item needs class E (new compatibility shim)** — each already *is* a shim, and the `normalize_nav_key` → `NAV_HOME` fallback covers any unmapped key.
- **Class A (keep permanently):** the **`normalize_nav_key` fallback-to-HOME safety net** itself (not an alias) — keep permanently as the ultimate guard regardless of alias retirement.

## 4. Retirement recommendation

- **Keep all aliases/reroutes now** — nothing is deleted in S6 or its first implementation slice.
- **B-class (1–4):** retain **through the React migration**; re-evaluate when the persistence/bookmark model is replaced. The emoji-alias dict is the cheapest possible compatibility layer.
- **C-class (5–6):** **telemetry-gated** — add logging (§5), bake in for a defined window, and retire **only** after observing **zero** hits. Retirement = remove the specific reroute dict/branch; the `normalize_nav_key` → `NAV_HOME` safety net remains.
- **Order of eventual retirement (later):** C-class first (transient-session reroutes), then re-assess B-class at React migration. Never retire an alias whose telemetry shows live hits.

## 5. Telemetry / logging recommendation

Add **lightweight, behavior-neutral logging** at each legacy resolution point (no functional change):

- Log when `_LEGACY_NAV_TO_REPORTS_EXEC` fires (raw key → reports exec).
- Log when `normalize_nav_key` actually **substitutes** a key (i.e. `result != raw`), recording the source alias — measures emoji-bookmark usage.
- Log when `_LEGACY_RPT_EXEC_TO_STATEMENT` / `_TO_BOOKS` fires (which `rpt_exec_sel` → which route).
- Log when the **Bank Statement Import** reroute fires.
- Use a single dedicated logger (e.g. `nav.legacy`) at `INFO`/`DEBUG`; optionally a counter for a bake-in dashboard. **No `st.*`, no user-visible change, no behavior change** — observation only. C-class retirement is gated on a window of zero logged hits.

## 6. Contract tests (for the implementation slice)

- **No alias dead-ends:** every `LEGACY_NAV_ALIASES` value ∈ `ALL_NAV_PAGE_KEYS`.
- **Reroute targets valid:** every `_LEGACY_RPT_EXEC_TO_STATEMENT` / `_TO_BOOKS` value ∈ `_PAGE_DISPATCH`; `_LEGACY_NAV_TO_REPORTS_EXEC` values are valid `rpt_exec_sel` options; Bank Statement Import target == `NAV_BANKING` and `"import"` is a valid `banking_section`.
- **Today's Summary repoint:** `normalize_nav_key("Today's Summary")` and the emoji form resolve to `NAV_REPORTS` (S2 invariant preserved).
- **Fallback safety net:** an unknown nav key passes through `normalize_nav_key` and is then guarded to `NAV_HOME` (existing behavior, class-A invariant).
- **Idempotency:** applying normalization twice yields the same canonical key; the `rpt_exec_sel` reroute pops the key so it does not re-fire.
- **Telemetry fires (after impl):** a `nav.legacy` log line is emitted on each legacy hit (structural assertion).

## 7. Implementation slices (for Cursor — DO NOT implement yet)

- **NAV-UX-02-S6-IMPL-1 — telemetry only:** **Implemented (2026-06)** — `nav.legacy` logging at five resolution points + validity/idempotency tests in `tests/test_nav_ux_02_s6_legacy_reroute_structural_contract.py`; see `docs/NAV_UX_02_S6_IMPLEMENTATION.md`. **No alias/route removed.**
- **NAV-UX-02-S6-IMPL-2 — bake-in review:** after a defined window, review `nav.legacy` counts; produce a usage report.
- **NAV-UX-02-S6-IMPL-3 — C-class retirement (telemetry-gated):** if and only if zero hits, remove `_LEGACY_RPT_EXEC_TO_STATEMENT`/`_TO_BOOKS` and/or the Bank Statement Import reroute; keep the `NAV_HOME` safety net.
- **NAV-UX-02-S6-IMPL-4 — B-class re-evaluation (React migration):** revisit the emoji aliases + S2 reroute when the persistence/bookmark model changes.

## 8. Risk assessment

**LOW.** All targets are valid today; this slice changes nothing. The only future risk is retiring a reroute that still has live bookmarks — fully mitigated by (a) telemetry-gating C-class retirement on zero observed hits, (b) keeping B-class through the React migration, and (c) the permanent `normalize_nav_key → NAV_HOME` safety net that prevents any dead-end even if an alias is ever removed. No accounting, schema, role, or render impact.

## No-change statement (NAV-UX-02-S6 planning)

- **No route deleted, no alias deleted, no UI change, no role change, no cleanup, no `app.py`/registry edit.** Inventory + behavior map + classification + retirement recommendation + telemetry recommendation + contract tests + slices + risk only; execution is the separately-approved NAV-UX-02-S6-IMPL slices.

---

*Planning only. Five legacy mechanisms: (1) bulk emoji `LEGACY_NAV_ALIASES`, (2) Today's Summary→Reports alias, (3) Bank Statement Import→Banking alias, (4) `_LEGACY_NAV_TO_REPORTS_EXEC` (S2 exec preset), (5) `_LEGACY_RPT_EXEC_TO_STATEMENT`/`_TO_BOOKS`, plus (6) the section-preserving Bank Statement Import reroute. All targets valid; ultimate safety net is normalize_nav_key→NAV_HOME. Classification: 1–4 = B (keep until React migration, durable-bookmark protection, trivial cost); 5–6 = C (telemetry-gated retirement, they protect transient session keys); none are D (safe now) or E (need new shim); the NAV_HOME fallback is A (keep permanently). Recommendation: keep everything now; add behavior-neutral `nav.legacy` logging; retire C-class only after a zero-hit window; re-evaluate B-class at React migration. Contract tests pin no-alias-dead-ends, valid reroute targets, Today's Summary repoint, NAV_HOME fallback, and idempotency. Risk LOW — nothing deleted; retirement deferred + telemetry-gated; permanent fallback prevents dead-ends.*
