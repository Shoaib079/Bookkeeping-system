# NAV-UX-02-A — Sidebar / Navigation Audit Plan

**Mode:** Documentation + lightweight contract test only. **No UI/runtime change in this slice.** `app.py` navigation is unchanged; no pages removed, no routes renamed, no role gates changed, no mobile nav changed; no schema/accounting/API change.
**Status:** **No navigation change yet.** This defines the **audit method and rules** to run **before** any sidebar/navigation cleanup.
**Goal:** produce a complete, repeatable audit plan so a later slice can clean navigation safely, without losing pages, breaking routes, or weakening role gates.

## 1. Audit method

- **Read-only inventory first.** Enumerate every navigation entry from the source of truth (`_render_navigation_tree()` and the `_PAGE_DISPATCH` map in `app.py`) and every `render_*` page function — **no edits**.
- **One row per entry.** Each desktop sidebar item, mobile nav item, and dispatched page gets a row in the inventory table (§2).
- **Cross-reference, don't assume.** For each entry, record its route key, the `render_*` function it dispatches to, the role/permission gate guarding it, and whether it also appears in mobile nav.
- **Classify, then recommend.** Every entry is classified (keep / merge / move / hide / rename-candidate) with a one-line rationale; **recommendations only** — no changes in this slice.
- **Evidence-based.** Every finding cites the `app.py` location (function/line) or the dispatch key; nothing is asserted without a source reference.

## 2. Inventory table format

The audit inventory uses a fixed column set so it is diffable and testable. **Every navigation surface and control is one row** — not just sidebar/menu entries (see §3 for the full control taxonomy).

| Column | Meaning |
|--------|---------|
| `label` | Display label/text shown on the control |
| `route_key` | `nav_selection` / dispatch key (or "—" for non-route controls) |
| `render_fn` | `render_*` function it dispatches to (`app.py`) |
| `surface` | desktop sidebar / mobile nav / both / hidden |
| `role_gate` | permission/role required (or "none") |
| `owner_area` | functional area (e.g. Sales, Banking, Reports, Settings, Admin) |
| `duplicate_of` | route_key it duplicates, if any (else "—") |
| `classification` | keep / merge / move / hide / rename-candidate |
| `react_route` | proposed future React route path |
| `notes` | one-line rationale / evidence reference |
| `control_type` | the control kind: sidebar-item / section-header / expander / dropdown-picker (selectbox) / radio / tab / button / inline-control (+ / ⚙) / quick-entry-shortcut / mobile-bottom-nav / mobile-hub-card / dialog-opener |
| `parent_surface` | where the control lives (e.g. sidebar, page header, transaction form, mobile hub, dialog) |
| `opens_dialog` | yes/no — does the control open a modal/dialog rather than navigate? |
| `navigates_to` | the destination route_key / view the control leads to (or "—") |
| `duplicate_workflow` | the workflow this is an alternate entry point to, if any (else "—") |
| `daily_use_impact` | high / medium / low — how often it is used in daily operation |

## 3. Scope to audit — every navigation surface

The audit covers **every control that navigates, switches view, or opens a workflow/dialog** — not only sidebar/menu entries. Each item below is inventoried (§2) with its `control_type`.

### 3a. Every navigation surface / control type

- **Sidebar items** — every clickable entry rendered by `_render_navigation_tree()`.
- **Sidebar section headers** — group headers/captions that organize the tree (navigational structure, even if non-clickable).
- **Sidebar expanders** — collapsible `st.expander` groups in the sidebar that reveal further entries.
- **Dropdown / selectbox page pickers** — any `st.selectbox`/dropdown used to choose a page, sub-view, or context.
- **Radio / tab navigation** — `st.radio` and `st.tabs` used to switch between views within a page.
- **Buttons that navigate or open dialogs** — `st.button` controls that change `nav_selection`, switch view, or open a modal.
- **Quick-entry shortcuts** — fast data-entry actions (new sale/expense/purchase/banking) wherever they appear.
- **Inline `+` and `⚙` controls** — inline add/create (`+`) and settings/config (`⚙`) icon controls embedded in pages/lists.
- **Settings shortcuts inside transaction forms** — config/settings links or icons surfaced within data-entry forms.
- **Mobile bottom nav** — every item in the mobile bottom navigation bar.
- **Mobile hubs / cards** — mobile hub screens and the cards/tiles that navigate from them.
- **Hidden / admin / dev pages** — entries not in the main nav (dev/admin/debug) and how they are reached.
- **Any duplicate entry point to the same workflow** — multiple controls (of any type) that lead to the same workflow (recorded via `duplicate_workflow`).

### 3b. The ten review areas (applied across all the above)

1. **Desktop sidebar entries** — every item rendered by `_render_navigation_tree()`; confirm each maps to a live `render_*`.
2. **Duplicate page names / routes** — labels or route_keys that collide or point at overlapping functionality.
3. **Settings placement** — where settings/config live (scattered vs. consolidated), **including `⚙` controls and settings shortcuts inside transaction forms**; candidates for a single Settings area.
4. **Transaction / data-entry shortcuts** — quick-entry actions (sales, expenses, purchases, banking) and inline `+` controls; whether they are discoverable/consistent.
5. **Mobile bottom nav / hubs** — every mobile nav item, hub, and card; map to desktop equivalents.
6. **Role gates and permissions** — the gate guarding each control (including buttons/dialogs/inline controls); flag ungated sensitive actions and inconsistent gates.
7. **Page ownership** — the functional area / owner for each page (`owner_area`); flag orphans with no clear area.
8. **Future React route mapping** — a proposed React route path per page/view for the FastAPI+React migration.
9. **Hidden / advanced / admin pages** — entries not in the main nav (dev/admin/debug) and how they are reached.
10. **Duplicate functionality across pages** — distinct routes/controls that do substantially the same thing (merge candidates), tracked via `duplicate_workflow`.

## 4. Duplicate detection rules

- **Route collision** — two entries sharing a `route_key` or dispatching to the same `render_fn` → duplicate.
- **Label collision** — identical or near-identical `label` on different routes → naming duplicate (rename-candidate, not auto-merge).
- **Functional overlap** — different routes whose pages perform substantially the same task (e.g. two ways to enter an expense) → merge-candidate, flagged with both route_keys in `duplicate_of`.
- **Duplicate workflow entry points** — multiple controls **of any type** (sidebar item, button, picker, tab, inline `+`, quick-entry shortcut, mobile card) that lead to the **same workflow** → recorded in `duplicate_workflow`; cross-control duplicates count even when `route_key` differs.
- **No auto-resolution** — duplicates are **recorded and classified only**; no merge/rename happens in this slice.

## 5. Role-gate review rules

- **Every entry must record its gate** — the permission/role checked before render (or explicitly "none").
- **Sensitive-page rule** — admin, settings, voids, period/year close, user management must be gated; an ungated sensitive page is a **flag** (not auto-fixed here).
- **Consistency rule** — pages in the same `owner_area` should use consistent gates; divergences are flagged.
- **No gate changes** — review and flag only; role gates are **not** modified in this slice.

## 6. Mobile / desktop consistency rules

- **Every mobile nav item maps to a desktop entry** (and vice-versa where intended); record gaps.
- **Same route_key across surfaces** — a page reachable on both surfaces should share the same `route_key` and gate.
- **Mobile-only / desktop-only entries are explicit** — anything intentionally single-surface is marked, not treated as a gap.
- **No mobile nav change** — consistency is documented; mobile nav is **not** modified in this slice.

## 7. Settings cleanup rules

- **Locate all settings surfaces** — every page/section that edits configuration (app, company, user, module).
- **Consolidation candidates** — settings scattered across unrelated pages are flagged for a future single Settings area.
- **Preserve registry behavior** — any cleanup must respect the Phase-14D-B settings/registry (`get_setting`, `get_effective_config`); no settings semantics change here.
- **Recommendations only** — no settings move/rename in this slice.

## 8. Future React route mapping rules

- **One canonical React path per page** — propose a stable, hierarchical route (e.g. `/sales/new`, `/banking/reconciliation`, `/settings/company`).
- **Mirror owner_area** — React paths should reflect `owner_area` grouping for a clean route tree.
- **Stable keys for migration** — the mapping is the contract a future React router will implement; route_key → react_route must be 1:1.
- **Mapping only** — no routing implemented; this is a planning artifact for the FastAPI+React migration.

## 9. No-change decision (this slice)

- **No `app.py` navigation change; no pages removed; no routes renamed; no role gates changed; no mobile nav changed.**
- **Audit and recommendations only** — every finding is record-and-classify; execution is a separate, later slice.
- **No schema/accounting/API change; full suite stays green.**

---

*Plan only — no UI/runtime change, `app.py` navigation untouched, no pages removed, no routes renamed, no role gates changed, no mobile nav changed. Audit method: read-only inventory from `_render_navigation_tree()` + `_PAGE_DISPATCH` + `render_*`, one row per control, evidence-cited, classify-then-recommend. Scope is every navigation surface — sidebar items, section headers, expanders, dropdown/selectbox page pickers, radio/tab navigation, buttons that navigate or open dialogs, quick-entry shortcuts, inline `+`/`⚙` controls, settings shortcuts inside transaction forms, mobile bottom nav, mobile hubs/cards, hidden/admin/dev pages, and any duplicate entry point to the same workflow — not just sidebar/menu entries. Fixed inventory columns (label, route_key, render_fn, surface, role_gate, owner_area, duplicate_of, classification, react_route, notes, control_type, parent_surface, opens_dialog, navigates_to, duplicate_workflow, daily_use_impact). Rules: duplicate detection (route/label/functional + cross-control duplicate_workflow, record-only), role-gate review (record gate, flag ungated sensitive actions, no changes), mobile/desktop consistency (map across surfaces, no mobile change), settings cleanup (locate ⚙ + in-form shortcuts + consolidation candidates, registry-safe), React route mapping (1:1 route_key→react_route). No-change this slice; recommendations executed later.*
