# UX-STABILIZE-01 — Data-Entry State Cleanup

**Status:** Closed (2026-06-05)  
**Tag:** `ux-stabilize-01-data-entry-state`  
**Scope:** Add Transaction UX state only — no posting/accounting/migration changes.

## Problems

1. **Worker Salary showed stale expense categories** — desktop worker radio and mobile Salary type could retain `at_cat` / `mob_at_cat_id` from a prior general expense, affecting validation labels and gather context even when category widgets were hidden.
2. **Post-save category bleed** — category keys were listed in `_AT_POST_SAVE_CLEAR_KEYS` but not consolidated through `_at_clear_category_session_state()`, risking drift if one list lagged the other.
3. **Navigation scroll position** — sidebar / bottom-nav page changes did not scroll the main pane to top; users landed mid-page on long screens.

## Root causes

| Issue | Cause |
|-------|--------|
| Worker vs category | Worker/salary detection duplicated; category session keys not cleared when entering worker mode |
| Post-save reset | Category pop list duplicated instead of reusing `_at_clear_category_session_state()` |
| Scroll | Page-change handler cleared overlays but had no scroll helper |

## Fixes (reuse existing helpers)

| Helper | Role |
|--------|------|
| `_at_is_worker_expense_entry()` | Single gate for mobile Salary + desktop `at_expense_mode == "worker"` |
| `_at_clear_category_session_state()` | Clears category/subcategory keys (existing ADD-TXN-FIX-01 helper) |
| `_at_clear_worker_entry_session_state()` | Clears worker widget keys when leaving Salary type |
| `_at_clear_post_save_transient_fields()` | Now calls `_at_clear_category_session_state()` after key pops |
| `_scroll_main_to_top()` | Zero-height `components.html` scroll (same pattern as session-restore cookie JS) |
| `_mob_at_c_apply_type()` | Salary → worker mode + category clear; other types → worker clear |
| `_at_gather_submit_fields()` | Skips category resolution in worker expense mode |
| `main()` page-change block | Calls `_scroll_main_to_top()` alongside existing overlay clears |

## Retention policy (unchanged)

After save: **keep** transaction section (`at_type_idx` / mobile tab sync) + date; **reset** everything else per RETENTION-01 / UX-04A.

## Tests

`tests/test_ux_stabilize_01_data_entry_state.py` — worker isolation, type picker state, post-save category cleanup, scroll contract, submit type resolution.

## Out of scope

- Salary posting / `post_worker_movement` / GL logic
- NAV_ARCH audit files (left untracked)
- PostgreSQL runtime / migration

## Regression fix (2026-06-05)

**Symptom:** Worker Salary / Advance showed category/subcategory; worker picker missing.

**Cause:** UI branched on `expense_mode == "worker"` (radio return value) while `_at_is_worker_expense_entry()` could be true via mobile Salary tab sync (`mob_at_tab` + `mob_at_more_idx`) before `at_expense_mode` was synced; empty-worker gating hid the worker radio entirely on desktop.

**Fix:** `_at_presync_salary_expense_mode()`, `_at_apply_worker_expense_mode_transitions()`, shared `_at_render_worker_expense_panel()`; branch on `_at_is_worker_expense_entry()`; always offer worker/general radio; no-workers prompt restored.
