# GLOBAL-STABILITY-AUDIT-01 — Fix Regression / SSOT Stop Report

**Mode:** Stop report only. **No code changes, no commits, no pushes, no patches.** Determines, per major fix, whether it is a **global rule with a single source of truth (SSOT)** or a **path-specific patch** that can silently reappear elsewhere. Anchored to the real tests/docs in the repo (cited per row).

## Why fixes "reappear"

Across the families below, the recurrent pattern is **the same rule implemented per-screen instead of behind one helper**, plus **two render surfaces (desktop `app.py` / mobile `ui/*`, and Python / React)** that each re-state the rule. When a fix lands on one surface's call site rather than the shared helper, a *different* screen that never routed through the helper keeps the old behavior — so the bug looks "un-fixed." The **date family** and **cross-surface error/format rules** are the highest-risk because they have many call sites.

## Matrix (compact)

| Fix | Intended global rule | Canonical owner | Tests | Bypasses (risk surface) | Duplicate paths | Global? | Risk |
|---|---|---|---|---|---|---|---|
| **DATE-01** | One date parse/format/ownership pipeline; user date-format is display-only | `registry/date_utils.py` + `ui/date_input.py` (`parse_bound_date`, `render_preferred_date_input`) + `_active_user_date_format` (app.py) | `test_date_utils`, `test_date_format01`, `test_date_input_contract`, `test_date_mask02a`, `test_date01_fast_mobile_date` | Any form that builds a date without `parse_bound_date` (per-type Add-Txn wiring) | desktop date text vs mobile native picker | **Mostly** | **High** |
| **OBS-001** at_date submit crash | Submitting with a typed/empty date never crashes | `parse_bound_date` (ui/date_input) | `test_obs_001_at_date_submit_crash`, `test_at_sale_past_date` | a non-routed date widget | desktop/mobile date entry | Partial | High |
| **OBS-002** at_date selected posting | The **selected** date is the **posted** date (not today) | Add-Transaction date binding → posting wrappers | `test_obs_002_at_date_selected_posting`, `test_at_cash_sale_date_regression` | per-transaction-type paths (sale/expense/purchase) | each type wires date separately | Partial | High |
| **OBS-004** at_date ownership (all types) | Every Add-Txn **type** owns its date identically | `test_at_date_ownership_all_types` (the guard) | `test_obs_004_at_date_ownership`, `test_at_date_ownership_all_types` | a new type added without the shared binding | Sale/Expense/Purchase branches | Partial | High |
| **OBS-003** txh edit decimal amount | Editing a txn preserves decimal amount | `amount_input`/`_parse_amount_str` (app.py) | `test_obs_003_txh_edit_decimal_amount` | a screen using raw `st.number_input` | desktop edit vs mobile edit | Partial | Med |
| **OBS-005/006/007/009/010** | Post-launch stability regressions (legacy expenses CC, etc.) | per-OBS helpers | `test_post_launch_stability_02_obs` (one suite) | screen-local | — | Partial | Med |
| **OBS-011** banking import route | POS-settlement → statement-import upload route resolves | banking route reroute (`banking_section="import"`) | `test_obs_011_banking_statement_import_route` | the recon-off quick-CSV branch (see BANKING-PATHMAP) | recon-on staging vs recon-off CSV | Partial | Med |
| **REACT-LOCAL-OBS-01/02** | API errors never render `[object Object]`; route shell gating | React `apiError.ts` (`errorMessageFromCatch`) + route shell | `test_react_local_obs_01_home` | any React page using `String(detail)` directly | **Python error formatting vs TS `apiError.ts`** (same rule, two languages) | One-surface (React) | Med |
| **BANKING-UX-02** | Banking design/landing rules | `ui/banking.py` + `_banking_*` getters | `test_banking_ux02_p1/p1b/p2/p3/p4` | mobile banking surface | desktop vs mobile banking | Partial | Med |
| **BANKING-UX-03** | Reconciliation cockpit / match-post UX | `reconciliation/*` + `ui/banking.py` | `test_banking_ux03_p1_1..p2_4` | — | — | Mostly | Low-Med |
| **NAV-UX-02 / NAV-ARCH** | One nav registry → dispatch/accordion/role/mobile | `registry/navigation.py` (+ `nav_keys.py`) | `test_nav_ux_02_s1..s6_*structural_contract`, `test_nav_arch_audit` | none (parity tests guard) | resolved (registry-derived) | **Yes** | Low |
| **POST-LAUNCH-STABILITY-02** | Bundle of OBS regressions | per-OBS | `test_post_launch_stability_02_obs` | screen-local | — | Partial | Med |

## Per-fix detail (the 14 fields) — highest-risk families

### DATE-01 (+ OBS-001/002/004) — date pipeline
1. **Rule:** one parse/format/ownership pipeline; the user's date *format* is display-only; the *selected* date is the *posted* date for **every** transaction type, desktop and mobile.
2. **Commit/tag:** see tests (`test_date_*`, `test_obs_00[124]_*`, `test_at_*_date_*`); no single tag — multiple slices.
3. **Tests:** `test_date_utils`, `test_date_input_contract`, `test_date_format01`, `test_date_mask02a`, `test_date01_fast_mobile_date`, `test_obs_001/002/004`, `test_at_date_ownership_all_types`, `test_at_cash_sale_date_regression`, `test_at_sale_past_date`, `test_txh_created_by_backdate`.
4. **Canonical owner:** `registry/date_utils.py` + `ui/date_input.py` (`parse_bound_date`, `render_preferred_date_input`) + `_active_user_date_format` (app.py).
5. **Screens using it:** Add Transaction (Sale/Expense/Purchase), txn edit, staff capture, banking date fields.
6. **Bypasses:** any widget that reads a date string without `parse_bound_date`; a newly added transaction type that re-wires its own date.
7. **Desktop coverage:** yes (date-text + mask).
8. **Mobile coverage:** yes but **separate** widget (native picker, `test_date01_fast_mobile_date`) — the duplication surface.
9. **Company-specific:** no.
10. **Feature flags:** none.
11. **Session-state keys:** `at_date`, `at_date_text`, `sc_form_date`, `mob_at_date_custom_str`, the `at_*_sync_*` deferral keys.
12. **Duplicate implementations:** desktop date-text vs mobile native picker (two widgets, one rule).
13. **Dead/stale:** none confirmed.
14. **Risk:** **High** — many call sites; "fixed on one type/screen, not the helper" is exactly how it reappears. The guard `test_at_date_ownership_all_types` is the closest thing to an SSOT enforcer.

### REACT-LOCAL-OBS-01/02 — cross-language rule duplication
- **Rule:** API error → human message, never `[object Object]`; route shell stays on placeholder when `VITE_ERP_REACT_PAGES` off. **Owner:** React `apiError.ts` (`errorMessageFromCatch`). **Flag:** `VITE_ERP_REACT_PAGES`. **Duplicate:** the *same* "format an error for the user" rule also exists in Python — **two implementations in two languages**; they can drift. **Risk:** Med (React-only surface today, but the rule has no single cross-stack contract).

## Stop-report answers

**A. Which fixes are truly global (one SSOT, parity-tested)?**
- **NAV-UX-02 / NAV-ARCH** — `registry/navigation.py` derives dispatch/accordion/role/mobile; structural contract tests enforce parity. **Genuinely global.**
- **THEME / tokens** (context) — `ui/design_tokens.py` via THEME-AUTHORITY-01, contract-tested. Global.
- **match_post duplicate-post safeguard** — single dedup authority. Global (and locked).

**B. Which fixes only apply on one path?**
- **OBS-001/002/004 / DATE-01** — protected at the *helper* but applied per *transaction-type call site*; a type or screen that doesn't route through `parse_bound_date` is unprotected.
- **OBS-003** decimal edit — depends on each screen using `amount_input` (not raw `number_input`).
- **OBS-011** banking route — the recon-off quick-CSV branch is a separate path.
- **REACT-LOCAL-OBS-01/02** — React surface only; the Python equivalent is a separate implementation.
- **BANKING-UX-02** — desktop banking covered more than mobile.

**C. Which bugs can reappear because there is no SSOT?**
- **Date ownership / posted-date** — highest. New transaction type or a mobile-only widget can resurrect "posted today instead of selected date."
- **Decimal-amount editing** — any new edit screen using `st.number_input` directly.
- **Cross-surface error formatting** — Python vs React `apiError.ts` drift.
- **Banking import behavior** — recon-on staging vs recon-off CSV diverging.

**D. Which modules need centralization (make the rule live behind one enforced helper + a "no bypass" test)?**
1. **Date entry/ownership** → force all transaction types + mobile picker through `ui/date_input` + a *grep-style* contract test that **fails if any date widget bypasses `parse_bound_date`** (extend `test_at_date_ownership_all_types` to scan call sites).
2. **Money input** → one `amount_input`; a test that no posting/edit screen uses raw `st.number_input` for money.
3. **Error formatting** → a single cross-stack contract: Python error-message helper + TS `apiError.ts` assert the same shape (shared fixture).
4. **Banking import** → fold the recon-off quick-CSV path under the same import entry (telemetry-gate then retire) so there is one import owner.
5. **Desktop/mobile component grammar** (theme) → the MONO-THEME-01 shared-token layer (already recommended).

**E. Settings incorrectly behaving company-/user-specific when they should be global (or vice-versa)?**
- **Correct as-is:** date **format** (user-specific display), `banking.workflow_mode` / `banking.reconciliation` / `pos_settlement` (legitimately company-specific), theme mode (user pref over a global token base).
- **Watch / should stay global, not per-screen:** the date **ownership/posted-date rule** must be **global behavior**, not a per-screen choice — today it is *implemented* per call site, which makes it *behave* path-specific even though it is conceptually global. **This is the core mismatch.** Same for **money parsing** and **error formatting** — global rules currently realized per-surface.
- **No evidence** of a setting that is global-by-storage but leaking across companies (NAV/theme/match_post are correctly scoped).

## Recommended next step (no code here)

Add **"no-bypass" contract tests** (static call-site scans) for the centralization targets in D — these are the cheapest insurance against recurrence: they fail the build the moment a new screen re-implements a rule instead of calling the helper. Sequence: D1 date → D2 money → D3 error formatting → D4 banking import → D5 theme grammar.

## No-change statement

- **No code changes, no commits, no pushes, no patches.** Matrix + SSOT classification + A–E answers + centralization targets only.

## GLOBAL-STABILITY-HARDENING-01 implementation note (contract tests only)

Following this stop report, **GLOBAL-STABILITY-HARDENING-01** added no-bypass contract tests (`tests/test_global_stability_hardening_01.py`, `tests/global_stability_hardening_contract.py`) — **tests only, no runtime patches** in that slice:

| Slice | What the contract enforces |
|-------|---------------------------|
| S1 | Date fields on AT / TXH / Staff Capture / Banking must route through canonical helpers (`parse_bound_date`, `render_preferred_date_input`, `at_date_ownership`); native-calendar exceptions explicitly classified |
| S2 | Posting/edit money fields must use `amount_input` / `_parse_amount_str`; `st.number_input` exceptions classified |
| S3 | React pages must not grow legacy `String(detail)` bypasses; `HomePage` uses `errorMessageFromCatch`; Python BSI post errors use `_bsi_statement_post_error_message` |
| S4 | Banking import routes to canonical upload owner; recon-on staging vs recon-off legacy CSV branch classified |
| S5 | This document + `tests/test_global_stability_audit_01_stop_report.py` remain the audit contract |

**Known classified debt (not fixed here):** 40 React read pages on frozen legacy error pattern; TXH edit native calendar; recon-off quick-CSV branch.

---

*Stop report. Truly global (SSOT + parity tests): NAV-ARCH (`registry/navigation.py`), theme tokens (`ui/design_tokens.py`/THEME-AUTHORITY-01), match_post dedup. Path-specific (reappear-risk): DATE-01/OBS-001/002/004 (date rule protected at the helper but applied per transaction-type call site; mobile picker is a separate widget), OBS-003 decimal edit (per-screen `amount_input`), OBS-011 banking route (recon-off quick-CSV is a separate path), REACT-LOCAL-OBS-01/02 (React `apiError.ts` vs a separate Python error formatter — same rule, two languages). Bugs reappear because the rule lives at call sites, not behind one enforced helper. Centralize: date entry/ownership, money input, error formatting, banking import, desktop/mobile theme grammar — each with a "no-bypass" static contract test. Settings mismatch: the date posted-date/ownership rule (and money/error formatting) are conceptually global but realized per-screen, so they behave path-specific; date format / banking modes / theme mode are correctly user-/company-scoped. No code changes.*
