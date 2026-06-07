# Navigation Audit — Prerequisite for AD-UI-001

**Decision ID:** AD-UI-001  
**Status:** **Approved for future work** — **no implementation yet**  
**Priority:** High  
**Gate:** This audit must be completed and reviewed before any sidebar / navigation redesign ships.

**Companion docs:** [UI_SHELL.md](../UI_SHELL.md) · [ROADMAP.md](../ROADMAP.md) · [AUDIT_HISTORY.md](./AUDIT_HISTORY.md)

---

## Why this exists

Feature **discoverability** and **workflow efficiency** have become larger issues than accounting correctness. Phase 15 consolidated many financial reports under **Reports → Executive**, and Phase A mobile shell added hubs and deep-links — but users still cannot reliably find core statements (e.g. Balance Sheet) without knowing the hub structure.

AD-UI-001 approves a **sidebar and navigation redesign**. Implementation is blocked until this audit is done.

---

## Approval record (2026-06-09)

| Field | Value |
|-------|-------|
| **ID** | AD-UI-001 |
| **Scope** | Sidebar structure, mobile hubs, Reports hub IA, role-visible pages, module catalog alignment |
| **Out of scope (until redesign)** | Posting logic, GL rules, registry accounting keys |
| **Prerequisite** | Complete sections 1–6 below; stakeholder sign-off on IA proposal |
| **Implementation** | Separate task — do not start in the same pass as this audit |

---

## 1. Current navigation sources (code map)

| Source | File | What it defines |
|--------|------|-----------------|
| Sidebar accordion | `app.py` → `_NAV_ACCORDION` | Direct pages + grouped Books / People / Closings / Settings |
| Role allow-lists | `app.py` → `_NAV_ROLE_PAGES` | owner / manager / cashier / partner / viewer page sets |
| Page dispatch | `app.py` → `_PAGE_DISPATCH` | `selection` string → `render_*` function |
| Module registry | `registry/modules_catalog.py` | `ModuleDef.nav_page` — metadata; not all sub-reports registered |
| Mobile bottom nav | `app.py` → `_MOBILE_BOTTOM_NAV`, `_MOBILE_HUB_CONFIG` | Banking / Reports / People / More hubs |
| Reports hub | `app.py` → `render_reports()` | Seven tabs; Executive tab hosts financial statements |
| Nav i18n | `registry/nav_labels.py`, `registry/locales/transactional.py` | Display labels EN/TR |

---

## 2. Known discoverability issues (pre-audit findings)

These are **documented symptoms**, not the redesign spec. Confirm or extend during the full audit.

| Issue | Detail | Severity |
|-------|--------|----------|
| **Financial statements buried** | Balance Sheet, P&L, Cash Flow live only under `📊 Reports` → tab **Executive** → 8-way report picker (default: P&L) | High |
| **Asymmetric Books accordion** | Trial Balance + General Ledger are top-level under **Books**; Balance Sheet / P&L / CF are not | High |
| **Opaque tab label** | “Executive” does not read as “Financial Statements” to non-finance users | Medium |
| **Legacy regression** | `app.py.bak` had top-level `🏛️ Balance Sheet`, `💰 Profit & Loss`, `💸 Cash Flow` — removed in Phase 15 hub consolidation | Context |
| **Duplicate entry points** | TB and GL reachable from Books **and** Reports → Executive | Medium (confusing but not broken) |
| **Role asymmetry** | Cashier/viewer get Reports but not Books; can still reach TB/GL via Reports → Executive | Medium |
| **Management vs financial gating** | Executive financial reports are **not** `view_management_reports`-gated; Sales/Expenses/etc. tabs are | Low (document intent) |
| **Module catalog gap** | `modules_catalog.py` has no entries for balance_sheet / pnl / cash_flow | Low |

**Not a routing bug:** `render_balance_sheet()` and dispatch wiring are correct; the report is **hard to find**, not missing.

---

## 3. Financial reports inventory (baseline)

| Report | Exists | Primary UI path today | Renderer |
|--------|--------|----------------------|----------|
| Balance Sheet | Yes | Reports → Executive → Balance Sheet | `render_balance_sheet()` |
| Profit & Loss | Yes | Reports → Executive → P&L (default) | `render_profit_loss()` |
| Cash Flow | Yes | Reports → Executive → Cash Flow | `render_cash_flow()` |
| Trial Balance | Yes | Books → Trial Balance **or** Reports → Executive | `render_trial_balance()` |
| General Ledger | Yes | Books → General Ledger **or** Reports → Executive | `render_general_ledger()` |

Mobile: Reports hub deep-links P&L, Balance Sheet, Cash Flow; full tab bar on Reports page.

---

## 4. Audit checklist (required before redesign)

Complete each item; record findings in a new dated section at the bottom of this file.

### 4A. Inventory

- [ ] Full page list: every `_PAGE_DISPATCH` key, render function, and whether it appears in sidebar / mobile / both
- [ ] Orphan routes: render functions reachable only via deep-link or session preset
- [ ] Duplicate paths: same report from multiple nav entries (TB, GL, Budget, Today’s Summary)
- [ ] Hidden-by-role pages: per-role diff vs owner baseline

### 4B. User workflows

- [ ] Day-one operator: sale → EOD → cash recon — minimum clicks from Home
- [ ] Month-end accountant: TB → GL drill-down → Balance Sheet → Year-End Close
- [ ] Banking clerk: import → match → post — path from Banking hub
- [ ] Owner: Reports (management tabs) vs financial statements — permission clarity

### 4C. Mobile parity

- [ ] Every high-frequency desktop page has a mobile path (hub, bottom nav, or More accordion)
- [ ] Reports tab bar vs hub deep-links — redundant or complementary?
- [ ] Books accordion on mobile (inside More) — discoverability vs desktop

### 4D. i18n & labels

- [ ] EN/TR label consistency for nav vs in-page titles
- [ ] “Executive” / “Yönetici” usability review
- [ ] Icon + text pairs in sidebar vs mobile-only text

### 4E. Registry & feature gates

- [ ] `modules_catalog.py` vs actual nav — gaps and planned modules
- [ ] Company toggles (`inventory`, `banking.*`) — hidden vs disabled behavior
- [ ] `view_management_reports` and other `_can()` gates vs nav visibility

### 4F. Tests & regressions

- [ ] `tests/test_mobile_nav.py`, `tests/test_shell_stabilization.py` — what nav contracts are already enforced
- [ ] List tests that would break if menu keys or `_NAV_ACCORDION` structure changes

---

## 5. IA options (for audit conclusion — not approved yet)

Evaluate these in the audit; **do not implement** until one option is chosen.

| Option | Summary | Trade-off |
|--------|---------|-----------|
| **A — Restore top-level statements** | Balance Sheet, P&L, Cash Flow as sidebar items (legacy pattern) | More sidebar clutter; highest discoverability |
| **B — Books = Financial Statements** | Rename/expand Books accordion; move BS/P&L/CF there; slim Reports to management KPIs | Clear mental model; Reports hub refactor |
| **C — Rename Executive tab** | Keep structure; label tab “Financial Statements”; order BS/P&L/CF first | Cheapest change; still nested |
| **D — Hybrid** | Books for GL/TB/COA; new “Statements” group for BS/P&L/CF; Reports = operational | Best clarity; most nav churn |

---

## 6. Redesign constraints (frozen for AD-UI-001)

When implementation starts, it must preserve:

- Existing `render_*` functions and posting logic (presentation / routing only unless explicitly scoped)
- Role-based `_NAV_ROLE_PAGES` semantics (may reorganize, not silently expand cashier write access)
- Mobile shell contract in [UI_SHELL.md](../UI_SHELL.md) (header fixed, bottom nav ≤968px)
- i18n keys pattern (`registry/locales/transactional.py`, `nav_labels.py`)
- AD-001–AD-015 accounting behavior (no nav change that implies different GL rules)

---

## 7. Audit log (append findings here)

| Date | Auditor | Summary |
|------|---------|---------|
| 2026-06-09 | — | AD-UI-001 approved; this doc created; pre-audit symptoms from Balance Sheet discoverability investigation recorded in §2–3 |

---

*Update this file when the navigation audit completes. Link the chosen IA option and open questions before starting AD-UI-001 implementation.*
