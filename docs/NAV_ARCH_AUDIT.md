# NAV-ARCH — Sidebar / Navigation Architecture Audit

**Mode:** Audit + guardrails (NAV-ARCH-S1). **No runtime navigation behavior change.** Exact paths + line numbers; consolidation deferred to S2–S4; migration-safe; ROADMAP kept current.

**Avoid-duplicate-fixes note:** this overlaps with the prior **NAV-UX-02** track (`docs/NAV_UX_02_AUDIT.md` + S1–S7 plans; S2/S4/S6 partially implemented). This audit **confirms current state with line numbers** and **does not re-propose** fixes already planned/implemented there; it adds one architectural recommendation (single nav registry) that NAV-UX-02-S7 anticipated.

**NAV-ARCH-S1 status:** ✅ **Complete** — `docs/NAV_ARCH_AUDIT.md` + strengthened `tests/test_nav_arch_audit.py` (doc contract + live parity guardrails). **No `registry/navigation.py` yet.**

## 1. Navigation inventory

| Concern | Mechanism | Location (app.py, 2026-06-17) |
|---|---|---|
| **Primary router** | `_PAGE_DISPATCH` dict → `render_*` per `nav_selection` | `26453`; dispatch call `26499` |
| **Desktop sidebar render** | `_render_navigation_tree(st.sidebar, …)` (custom button accordion) | def `3331`; call `26412` |
| **`st.sidebar` usage (only 2 sites)** | date-range filters; nav tree | `989-990`, `26412` |
| **`option_menu`** | **Not used** — no `streamlit-option-menu` dependency; nav is a custom button tree | (none) |
| **radio / selectbox page selection** | **Not the primary router.** Sub-page pickers only: banking section picker (`_banking_section_select`), reports exec picker / `st.tabs` | (banking/reports render fns) |
| **Accordion groups** | `_NAV_ACCORDION` (8 groups) | `3218` |
| **Direct (top-level) pages** | `_NAV_DIRECT_PAGES` | `3272` |
| **Role visibility** | `_NAV_ROLE_PAGES` (owner/manager/cashier/partner/viewer) | `3282` |
| **Mobile bottom nav** | `_MOBILE_BOTTOM_NAV` (5 slots) | `3156` |
| **Mobile hubs** | `_MOBILE_HUB_CONFIG` (money/reports/people/more) | `3175` |
| **Canonical route keys** | `NAV_*` constants + `ALL_NAV_PAGE_KEYS` + `LEGACY_NAV_ALIASES` + `normalize_nav_key` | `registry/nav_keys.py` |
| **Legacy reroutes** | `_LEGACY_NAV_TO_REPORTS_EXEC` (`3022`), `_LEGACY_RPT_EXEC_TO_STATEMENT/_TO_BOOKS`, Bank Statement Import reroute | `app.py` (per NAV-UX-02-S6) |

Full 43-route table with `render_fn`/`surface`/`role_gate`/`react_route` already exists in `docs/NAV_UX_02_AUDIT.md` §2 — not duplicated here.

## 2. Duplicate labels

- **None within `_PAGE_DISPATCH`.** Keys are unique; `tests/test_nav_arch_audit.py` asserts no duplicate `_nav_display()` labels across dispatch routes.
- **Cross-surface label reuse is intentional**, not a duplicate: financial statements appear under the desktop accordion **and** the mobile reports hub as *shortcuts* to one canonical route (documented in NAV-UX-02-S3). Not a defect.

## 3. Duplicate destinations / routes

- **Multi-door, single-room** (documented NAV-UX-02 §3): Banking, Financial Statements, Transaction Ledger, Receivables/Payables each have several entry points (sidebar + mobile hub + legacy reroute) that **converge on one canonical route** — these are entry-point shortcuts, **not** duplicated render paths.
- **Legacy reroutes** (`_LEGACY_*`) are compatibility shims, **telemetry-gated for retirement** (NAV-UX-02-S6); not duplicate destinations to fix now.
- **No two `_PAGE_DISPATCH` keys map to the same `render_*` unintentionally.**

## 4. Dead / orphan pages

- **Resolved:** `Today's Summary` orphan route (was dispatched but unreachable) — **retired (S2)**; `render_today_summary` remains reachable via Reports → Accounting Tools.
- **No remaining dispatch orphan:** NAV-UX-02-S1 + NAV-ARCH-S1 parity tests guard "every `_PAGE_DISPATCH` key is reachable from accordion/direct/mobile/role config" with an explicit `KNOWN_HIDDEN` allow-list (currently empty).
- **No dead `render_*`:** every `_PAGE_DISPATCH` value resolves to a live render function (42 routes); none are empty stubs.
- **"Settings inside Settings":** the Settings accordion group holds Company Settings / Members / Permissions / Audit Log / Backup & Restore — these are **distinct admin pages**, not a nested-settings recursion. No self-referential settings page found.

## 5. Risk areas

- **Seven parallel nav structures must stay in sync** — `registry/nav_keys.py` (keys), `_NAV_ACCORDION` (3218), `_NAV_DIRECT_PAGES` (3272), `_NAV_ROLE_PAGES` (3282), `_MOBILE_BOTTOM_NAV` (3156), `_MOBILE_HUB_CONFIG` (3175), `_PAGE_DISPATCH` (26453). **This is the core architectural risk: drift** (a page added to dispatch but missing from a role list, or a mobile hub key with no dispatch target). Today it is mitigated by NAV-UX-02-S1 + NAV-ARCH-S1 parity tests, **not** by a single source.
- **Legacy reroute surface** (`_LEGACY_*`) adds resolution-order complexity (NAV-UX-02-S6) — telemetry-gated, low risk.
- **Business-logic independence:** the nav structures are pure data + a render function; **no accounting/business logic lives in navigation** — good, and must stay that way for the FastAPI/React target.

## 6. Recommended single source of truth

- **One nav registry** (`registry/navigation.py` — **not yet created**) holding **per-page metadata**: `route_key`, `label`/i18n, `render_fn` reference, `surfaces` (sidebar/direct/mobile-hub), `accordion_group`, `roles`/permission, `react_route`, `hidden`, `legacy`, `order`, `icon`. **Derive** `_PAGE_DISPATCH`, `_NAV_ACCORDION`, `_NAV_DIRECT_PAGES`, `_NAV_ROLE_PAGES`, and the mobile config **from this one registry** instead of maintaining seven hand-synced lists.
- This is **UI-independent and FastAPI/React-ready** (the `react_route` column is the migration contract from NAV-UX-02-S7) and is the natural home for the parity invariants the S1 tests already assert.
- **Service-first:** the registry is data/metadata; render functions stay thin; no business logic moves into it.

## 7. Safe cleanup plan (suggested — NOT implemented in S1)

Respect migration safety; **do not duplicate** the NAV-UX-02 S1–S7 work. Net-new consolidation = safe slices:

| Slice | Scope | Status |
|-------|--------|--------|
| **NAV-ARCH-S0 — Guardrails** | No new parallel nav structures without registry plan | Active |
| **NAV-ARCH-S1 — Audit + parity guardrails** | `docs/NAV_ARCH_AUDIT.md` + `tests/test_nav_arch_audit.py`; `KNOWN_HIDDEN` allow-list; no runtime change | ✅ **Complete** |
| **NAV-ARCH-S2 — Introduce `registry/navigation.py`** | Per-page metadata registry; **derive `_PAGE_DISPATCH` only** first | 📋 Next |
| **NAV-ARCH-S3A — Desktop derived** | Derive `_NAV_ACCORDION` + `_NAV_DIRECT_PAGES` from registry | 📋 Planned |
| **NAV-ARCH-S3B — Role derived** | Derive `_NAV_ROLE_PAGES` from registry | 📋 Planned |
| **NAV-ARCH-S3C — Mobile derived** | Derive `_MOBILE_BOTTOM_NAV` + `_MOBILE_HUB_CONFIG` from registry | 📋 Planned |
| **NAV-ARCH-S4 — React route contract** | `docs/NAV_ARCH_REACT_ROUTE_CONTRACT.md`; freeze `react_route` map | 📋 Planned |

**Defer** legacy-reroute retirement to the existing NAV-UX-02-S6 telemetry gate; **do not** re-open NAV-UX-02 S2/S4/S6 (already implemented).

## ROADMAP suggestions (separate from implementation)

- Record **NAV-ARCH-S1 ✅** under the NAV track; next slice **NAV-ARCH-S2** (registry + derive dispatch only).
- State the architectural rule: **navigation must eventually derive from one registry; render functions stay thin; no business logic in nav** — aligns with the FastAPI/React target.
- Cross-link NAV-UX-02 (S1–S7) and note S2/S4/S6 are partially implemented so they are **not** re-scoped.

## S1 guardrails (tests)

| Guard | Test module |
|-------|-------------|
| Doc contract | `tests/test_nav_arch_audit.py` |
| Structural parity | `tests/test_nav_ux_02_s1_navigation_structural_contract.py` |
| Purpose / surfaces | `tests/test_nav_ux_02_s1_purpose_validation.py` |
| Shared helpers | `tests/nav_ux_02_contract.py` (`KNOWN_HIDDEN`, `page_dispatch_from_main`, …) |

## No-change statement (NAV-ARCH-S1)

- **No runtime navigation behavior change.** No route/label/role/mobile edits. No `registry/navigation.py`. Inventory + duplicate analysis + orphan analysis + risk areas + single-source recommendation + strengthened parity tests + ROADMAP update only. Consolidation is NAV-ARCH-S2 onward.

---

*Audit refreshed 2026-06-17. Navigation is a **custom button tree** (no `option_menu`); `st.sidebar` is confined to `app.py:989-990` (date filters) and `app.py:26412` (nav). The router is `_PAGE_DISPATCH` (`app.py:26453`), rendered by `_render_navigation_tree` (`app.py:3331`), fed by seven parallel structures. No duplicate dispatch labels; cross-surface shortcuts are intentional. No dead render_* and no "Settings inside Settings". **Core risk: seven hand-synced nav lists → drift**, mitigated by parity tests but not by a single source. Next: `registry/navigation.py` derive dispatch only (S2).*
