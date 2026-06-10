# Test Coverage Map — Banking, Reconciliation & Company CC

**Last updated:** 2026-06-05 (THEME-CONTRAST-01 closed · WCAG token contracts)  
**Full suite:** run `pytest tests/` — **943 passed, 2 xfailed** (16 ownership-contract tests: **14 pass, 2 xfail**).

This map covers the **minimum regression set** for banking/CC work. Run these before and after any change in those areas.

## Documentation maintenance (required)

When tests are added or modified, update **this file** (counts, gaps, risk levels) and follow the full checklist in [BANKING_RECON_CC_STATUS.md](./BANKING_RECON_CC_STATUS.md#documentation-maintenance-required).

---

## Quick command

```bash
pytest tests/test_phase18_mvp1.py tests/test_phase18_mvp2.py \
  tests/test_phase18_mvp3.py tests/test_phase18_mvp4.py tests/test_phase18_mvp5.py \
  tests/test_company_cc_safety.py tests/test_card_purchase_void_edit.py \
  tests/test_purchase_payable_lifecycle.py tests/test_cc_subledger_sync.py \
  tests/test_cc_recon_health.py tests/test_cc_bill_payment_void.py \
  tests/test_cc_expense_form.py tests/test_opening_balance_cc.py \
  tests/test_cash_reconciliation.py tests/test_end_of_day_close.py -q
```

**181 tests** in this bundle (as of 2026-06-09).

---

## Phase 18 MVP tests

### `tests/test_phase18_mvp1.py` (10 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `BankTransaction` schema (`is_reconciled`, `statement_ref`, `charge_subtype`) | Reconciliation provenance columns exist | **High** — match & post breaks |
| Banking toggles default OFF | Legacy behavior until opt-in | **High** |
| Phase 18 accounts 1150, 5800 seed | Clearing + Bank Charges exist | **High** |
| `post_card_sale` → Bank when settlement OFF | Default card sale path unchanged | **High** |
| `post_card_sale` → 1150 when settlement ON | Clearing architecture | **High** |
| Card sales reclassify backfill | One-time migration idempotent | **Medium** |
| Banking i18n EN/TR keys | Settings UI parity | **Low** |

---

### `tests/test_phase18_mvp2.py` (18 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `import_bank_statement_file` | Staging only — no GL on import | **High** |
| File hash / duplicate detection | Soft duplicate warning | **Medium** |
| Column mapping / parsing | CSV/Excel → `BankStatementRow` | **High** |
| Raw file storage + provenance | `raw_line_text`, upload path | **Medium** |
| Delete import | Cleanup staging data | **Medium** |
| Parse edge cases / i18n | Operator-facing errors | **Low** |

---

### `tests/test_phase18_mvp3.py` (4 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `post_deposit_clearing_match` | Card clearing deposit ties to sales | **High** |
| Amount mismatch raises | No unbalanced clearing match | **High** |
| `post_vendor_outflow` | Vendor payment / ad-hoc expense from stmt | **High** |
| `BankTransaction.statement_ref` | `bsr:{id}` provenance | **Medium** |

---

### `tests/test_phase18_mvp4.py` (14 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Inferred settlement fee → Bank Charges | Fee posting when confirmed | **High** |
| Fee requires `banking.bank_charges_enabled` | Toggle gating | **Medium** |
| Deposit label heuristics (gross/net) | Turkish bank description patterns | **Medium** |
| `looks_like_commission` / transfer fee / CC fee vs bill pay | Correct match kind routing | **High** |
| `post_bank_charge_outflow` | DR 5800 / CR Bank | **High** |
| Settlement CSV import | `SettlementStatementImport` staging | **High** |
| Settlement-linked clearing match | Gross/fee/net cross-check | **High** |

---

### `tests/test_phase18_mvp5.py` (7 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `apply_account_balance_delta` CC direction | Withdrawal increases CC liability cache | **Medium** |
| `post_expense` with CC → CR 2110 | Company CC expense GL | **High** |
| `post_payable_payment` with CC → CR 2110 | AP paid by card | **High** |
| `post_credit_card_bill_payment` | DR 2110 / CR Bank + sub-ledger | **High** |
| Bill pay requires company card toggle | Gating | **Medium** |
| Partner/owner statement matches | Extended match_post paths | **Medium** |

---

## Company credit card safety & purchases

### `tests/test_company_cc_safety.py` (10 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| CC hidden in pay method helpers when disabled | UI list = posting gate | **High** |
| CC visible when enabled | Feature toggle | **Medium** |
| Desktop/mobile share same AT helpers | Parity | **High** |
| `_resolve_payment_credit_account` blocks disabled CC | No silent post | **High** |
| Customer `"Card"` ≠ company CC in resolver | Card sale safety | **Critical** |
| `post_expense` blocks CC when disabled | Backend enforcement | **High** |
| `_coerce_at_payment_method` resets stale `at_pm` | Session hygiene | **Medium** |

---

### `tests/test_card_purchase_void_edit.py` (8 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| CC purchase void → GL net zero | `CardPurchase` reversal | **High** |
| CC purchase edit amount / type | Correct reverse + repost ref types | **High** |
| Cash purchase void unchanged | Regression | **Medium** |
| `CardSale` never uses `CardPurchase` | Customer vs company separation | **Critical** |

---

### `tests/test_purchase_payable_lifecycle.py` (11 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Credit edit amount → payable updated | AP sub-ledger sync | **High** |
| Credit → Cash/Bank/CC → payable voided | Open AP not orphaned | **High** |
| Cash/Bank/CC → Credit → payable created | AP created when owed | **High** |
| Void credit purchase → payable voided | AP cleanup | **High** |
| Paid payable blocks tier-2 edit | Data integrity | **Medium** |

---

## Core ERP (related operational closes)

### `tests/test_cash_reconciliation.py` (20 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Balanced cash count (no JE) | Physical = GL cash | **High** |
| Shortage / overage approval JEs | Cash Over/Short posting | **High** |
| Void creates reversal | Reversal pattern | **High** |
| Duplicate date/account prevention | One recon per day/account | **Medium** |
| Closed period block | Period lock | **High** |
| Role permissions (cashier/manager/owner) | Authorization | **Medium** |

*Not company CC — but part of daily banking/cash ops.*

---

### `tests/test_end_of_day_close.py` (33 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| EOD snapshot / warnings | Operational close record | **Medium** |
| Pending cash recon warning | Cross-module signal | **Medium** |
| Duplicate close prevention | One close per date | **Medium** |
| Void / reclose | Lifecycle | **Medium** |
| Stale detection after new JEs | Snapshot invalidation | **Medium** |
| **EOD posts no JEs** | GL integrity | **High** |
| Permissions | Role gates | **Low** |

---

### `tests/test_cc_subledger_sync.py` (11 tests) — AD-011

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| CC expense → 2110 + card balance + `BankTransaction` | Charge sync | **Critical** |
| CC purchase → 2110 + card balance | CardPurchase sub-ledger | **Critical** |
| CC payable payment → 2110 + card balance | AP paid by card sync | **Critical** |
| Bill pay after synced charge zeros GL + card | No negative card after pay | **High** |
| Multiple cards require explicit `credit_card_account_id` | No wrong-card attribution | **High** |
| No cards blocks posting | Clear error | **High** |
| Void CC expense / purchase reverses card | Void symmetry | **High** |
| Edit CC purchase amount re-syncs card | Edit symmetry | **High** |
| Customer `CardSale` regression | AD-003 separation | **Critical** |

---

### `tests/test_cc_recon_health.py` (7 tests) — AD-013

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `compute_cc_payable_recon_health` after synced expense/purchase/payable | No drift when AD-011 paths used | **High** |
| Bill pay after synced charge | GL + cards net zero | **High** |
| Manual CC withdrawal without GL | Drift warning surfaced | **High** |
| Multiple cards sum in health total | Multi-card aggregation | **Medium** |
| Customer `CardSale` regression | AD-003 isolation | **Critical** |

---

### `tests/test_cc_bill_payment_void.py` (8 tests) — AD-014

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `void_credit_card_bill_payment` full reversal | 2110, Bank GL, bank + card balances restored | **Critical** |
| Reversal JE for `BankStmtCCBillPay` | GL undo provenance | **High** |
| Both `bsr:{id}` and `bsr:{id}:cc` txns voided | No orphan sub-ledger | **Critical** |
| Double void blocked | `row.status=voided` guard | **High** |
| Wrong `match_type` rejected | Scope limited to cc bill pay | **Medium** |
| `void_bank_transaction` blocks `bsr:*` | No partial unsafe void | **Critical** |
| Wrong-card bill pay void | Restores selected card only | **High** |
| Partial bill payment void | Amount-accurate reversal | **High** |

---

### `tests/test_cc_expense_form.py` (13 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `_company_cc_charge_ready` visibility gating | CC hidden when toggle off or no card | **High** |
| `_resolve_submit_company_cc_card_id` one-card auto-pick | Save without manual picker | **High** |
| Multi-card requires explicit selection | Clear validation error | **Medium** |
| `_save_and_post_expense_record` GL 2110 + sub-ledger | AD-011 charge path | **Critical** |
| Failed save rolls back, no orphan row | No silent failure | **Critical** |
| `_at_save_succeeded` flag on success only | No silent form reset | **Critical** |
| Desktop `at_type_idx` preserved vs `mob_at_tab` | No silent reset to Sale | **Critical** |
| `_at_set_flash` survives rerun | Success/error visible after submit | **High** |

---

### `tests/test_opening_balance_cc.py` (6 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Bank OB DR Bank / CR OBE | Normal asset opening unchanged | **High** |
| CC OB DR OBE / CR 2110 | Liability opening (AD-015) | **Critical** |
| CC `withdrawal` txn + balance cache | Sub-ledger matches GL | **Critical** |
| Recon Health clean after CC OB | 2110 vs card total | **High** |
| Duplicate `OBBank` blocked | No double post | **High** |
| CC OB blocked when feature OFF | Gating | **Medium** |
| CardSale does not credit 2110 | AD-003 separation | **High** |

---

### `tests/test_quick_entry.py` (14 tests) — QUICK-ENTRY-01

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Top-5 alphabetical chips; selected category kept visible outside top 5 | Deterministic chip set; selection never hidden | **Medium** |
| `_mob_at_quick_chips` is a pure helper (no session writes) | Render must not mutate state | **Medium** |
| `_mob_at_apply_category_pick` resets subcategory | No stale subcategory on category change | **High** |
| Per-type last-category memory (`mob_at_last_cat_*`) | Sale/Expense/Purchase memories don't cross-contaminate | **Medium** |
| Seeding: last-used or sole active category | Correct visible preselection only — no auto-post | **Medium** |
| Last-cat keys in `_COMPANY_SCOPED_AT_KEYS` + cleared on switch | No category leakage across companies | **High** |
| Chips wired for Sale/Expense/Purchase only; other types unchanged | Vendor/customer/bank flows untouched | **Medium** |
| `More…` opens existing picker; `_mob_at_render_c_cat_row` still available | Picker fallback always reachable | **Medium** |
| CSS contract (`mob_at_quick_cat_chips` wrap + `--mob-at-chip-idle-*` tokens) | No horizontal scroll; CSS-02 ownership in `mobile_txn.css` | **Low** |

---

## MOBILE-14 M1–M6 — ownership contracts (implemented)

**Status:** ✅ **MOBILE-14 closed** — `tests/test_mobile14_ownership_contract.py` — **14 pass, 2 xfail** (16 total). All required steps done (M1+M2+M5+M6+TXH). Remaining xfails: M3 (optional), M4 (optional) only.

| Contract | M-step | Business rule protected | State |
|----------|--------|-------------------------|-------|
| `--hdr-h` ownership + within-file dedup (`theme.css`, `mobile_header.css`) | M1 | No fifth `--hdr-h` token; HDR-01 not regressed | ✅ Pass |
| `mobile_shell.css` has no `block-container padding-top` | M2 | Top inset owned by `mobile_header.css` only | ✅ Pass |
| Bottom-nav / FAB / hub styling owned by `mobile_shell.css` | Regression lock | Shell owns chrome styling | ✅ Pass |
| No bottom-chrome selectors in `widgets.css` | M3 optional | Suppression refs allowed; relocation optional | xfail |
| Profile / co-switch sheets owned by `mobile_shell.css` (E13) | Regression lock | Overlay sheet chrome in shell | ✅ Pass |
| No sheet selectors in `widgets.css` | M4 optional | Suppression refs allowed; relocation optional | xfail |
| No KPI / dashboard rules in `widgets.css` | M5 | `.erp-kpi-section`, `.kpi-grid` in `theme.css` only | ✅ Pass |
| Sidebar hide single-owner contract | M6 | `mobile_shell.css` sole owner (`theme: 0, shell: 2`) | ✅ Pass |
| No `mob_at_`/`mob_rpt_` layout grids in `widgets.css` | E4–E5 guard | AT/report layout ownership preserved | ✅ Pass |
| No `txh_` layout grids in `widgets.css` | TXH micro-step | `mobile_txn_history.css` canonical owner | ✅ Pass |
| Notification rule liveness pin (3 files) | M6 | Permanent two-owner contract — do not blind-delete | ✅ Pass |

**Rule:** Non-owner files may reference owned selectors for **state suppression** only. M3/M4 xfails are optional — not required for closure.

**Execution order:** M1 ✅ → M2 ✅ → M5 ✅ → M6 ✅ → TXH ✅ → optional M3/M4 (deferred).

---

## THEME-CONTRAST-01 — WCAG contrast tokens (implemented)

**Status:** ✅ **Closed** — `tests/test_theme_contrast.py` — **15 pass**.

| Contract | Business rule protected | State |
|----------|-------------------------|-------|
| White on `--erp-primary-fill` ≥ 4.5 (light + dark) | Primary CTA readable in both modes | ✅ Pass (5.17:1) |
| `--theme-text` / `--theme-muted` on card/bg ≥ 4.5 | Body copy readable on surfaces | ✅ Pass |
| `--theme-success-text` / `--theme-warning-text` on light card/bg ≥ 4.5 | Status/KPI foreground readable | ✅ Pass (~5.0:1) |
| Filled primary buttons use `--erp-primary-fill` | P0 scoped to solid buttons only | ✅ Pass |
| `--theme-info` unchanged in dark injection | Links/tints keep existing accent | ✅ Pass |

---

## LOGIN-01 — auth UI modernization (implemented)

**Status:** ✅ **Closed** — `tests/test_login01_auth_ui.py` — **10 pass**.

| Contract | Business rule protected | State |
|----------|-------------------------|-------|
| `auth.css` registered in `load_theme_css()` | Auth styles load on every page | ✅ Pass |
| `erp-auth-*` selectors only in `auth.css` | CSS-02 ownership; no drift in `mobile_header.css` | ✅ Pass |
| No inline `style=` in auth renderers | Token-driven styling only | ✅ Pass |
| Widget keys frozen | Streamlit state + test stability | ✅ Pass |
| `picker_start_setup01` → `_start_create_company_wizard(return_to="picker")` | Create-company entry unchanged | ✅ Pass |
| UX-01 restore before `render_login` | Session restore hook order | ✅ Pass |
| Login form + `_login` + error paths preserved | Auth behavior unchanged | ✅ Pass |
| Company picker membership revalidation | Security: never trust submitted ID alone | ✅ Pass |

---

### `tests/test_ux01_session_restore.py` (17 tests) — UX-01 v1

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Token mint/verify round trip | HMAC integrity + 8h expiry | **High** |
| Expired/tampered/password-changed tokens rejected | Restore cannot be forged or replayed | **High** |
| Inactive user rejected | Disabled accounts cannot restore | **High** |
| Revoked/deactivated company → picker | Token company not trusted without DB | **High** |
| Role re-derived from DB | Token carries no permissions | **High** |
| Restore never writes `at_*` / `mob_at_*` | Narrow scope — no draft leakage | **High** |
| Logout clears cookie + session | Explicit sign-out invalidates restore | **High** |
| No secret disables feature | Safe default when env unset | **High** |
| DEV_MODE skips restore/cookie | Dev bypass unchanged | **High** |
| Restore failure → login, no raise | Graceful degrade on bad cookie | **Medium** |

---

### `tests/test_date01_fast_mobile_date.py` (15 tests) — DATE-01

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `at_date_follows_today` on default/Today | Date rolls forward with calendar day | **High** |
| Flag cleared on Yesterday/Custom | Explicit backdate not overwritten overnight | **High** |
| Rollover guard (`_mob_at_apply_date_follow_today`) | Pinned Today stays current | **High** |
| Repeat sets today + follow flag | Repeat compatible with DATE-01 | **Medium** |
| Company switch clears flag | No cross-company date pin leakage | **High** |
| `_entry_date_posting_blocked` shared with JE | Courtesy check matches posting engine | **High** |
| Backdated Row 1 marker when date ≠ today | User sees non-today posting intent | **Medium** |
| Sheet weekday+date labels | Quick choices show full context | **Low** |
| Desktop `st.date_input` unchanged | Mobile-only scope | **High** |

---

### `tests/test_ux04_repeat_transaction.py` (20 tests) — Repeat Last Transaction v1

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Repeat visible for eligible Expense/Purchase only | No Repeat on Sale/Salary/Bank/Payable | **High** |
| Void + company-scope guards | Ineligible rows refused in UI and handler | **High** |
| Date → today; amount/notes copied | Fresh dated entry; user must Save | **High** |
| Active category/subcategory copied; inactive dropped | Stale taxonomy not prefilled | **High** |
| Purchase vendor active-only; PM coercion | Invalid vendor/PM fall back safely | **High** |
| Forbidden fields never copied (customer, worker, ids) | Explicit allowlist; no column iteration | **High** |
| No `_at_save` / posting during repeat | Prefill-only; no silent transaction | **High** |
| Navigate to Add Transaction | Opens AT panel after Repeat tap | **Medium** |

---

### `tests/test_ux04c_smart_defaults.py` (12 tests) — UX-04C

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Per-type PM memory isolation (Sale/Expense/Purchase) | Cash/Card/Credit remembered separately per type | **High** |
| Default chain: memory → static → first allowed | Chip tap preference honored on next open | **High** |
| Invalid remembered PM falls back when CC disabled | Company CC off does not leave stale PM | **High** |
| Type switch restores valid remembered PM | Sale Card → Expense → back to Sale restores Card | **Medium** |
| Company switch clears PM memory keys | No cross-company PM leakage | **High** |
| Single-bank auto-pick when PM requires Bank | One active account auto-selected | **High** |
| Two banks do not auto-pick | No wrong-bank inference | **High** |
| Bank trigger does not default first of many | Multi-bank requires explicit pick | **High** |
| PM chip tap calls `_mob_at_remember_last_pm` | Memory updated on user action only | **Medium** |
| No customer/vendor/worker inference added | Scope guard on UX-04C block | **Medium** |

---

### `tests/test_ux04b_payment_method_chips.py` (14 tests) — UX-04B

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Sale/Expense/Purchase PM lists from shared helpers | No duplicated method lists | **High** |
| Company CC chip gated by `_company_cc_charge_ready` | CC only when posting ready | **High** |
| Chip tap sets `at_pm` + clears stale account keys | Bank/card/CC picker state consistency | **High** |
| Type change coerces invalid PM | Sale Card → Expense resets to Cash | **Medium** |
| Bank Transaction has no PM chip row; `mob_at_pm2` preserved | Subtype row untouched | **High** |
| Row 1 exactly 3 buttons; payment picker retired | UX-04B layout contract | **Medium** |
| Post-save retains `at_pm` | PM chip stays selected after save | **Medium** |
| Desktop AT still uses `at_pm` selectbox | Mobile-only scope | **High** |
| `mob_at_pm_row` CSS + widgets selected-chip rule | Chip grammar parity with category chips | **Low** |

---

### `tests/test_ux04a_post_save_retention.py` (8 tests) — UX-04A

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `_at_clear_post_save_transient_fields` clears amount/notes | Fresh amount line after each save | **Medium** |
| `at_last_cat_id` not cleared post-save | Desktop subcategory retained across saves | **High** |
| `at_cust_sel` cleared post-save | Credit Sale customer dropdown not reused | **High** |
| Worker gross/deduction/advance keys cleared (desktop + mobile) | Salary values not copied to next worker | **High** |
| Type/payment/category/date/currency/vendor/bank/quick-entry memory retained | Workflow continuity after save | **Medium** |
| `_at_process_submit` uses helper; `at_last_cat_id` absent from inline clear | Regression guard on post-save block | **Medium** |

---

### `tests/test_ux03_inline_category.py` (11 tests) — UX-03

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `_cat_create_or_reactivate` creates company-scoped Expense category | New categories stamped to active company | **High** |
| Case-insensitive dedup returns `exists_active` | No duplicate active categories | **High** |
| Inactive duplicate reactivated (same id) | Reactivation path matches desktop dialog | **Medium** |
| Whitespace-only input blocked (`empty`) | No blank category rows | **Medium** |
| CTA only on `expense_cat` picker; Sale/Purchase excluded | Scope limited to Expense workflow | **High** |
| `_can("manage_categories")` gate on list-picker CTA | Permission model unchanged | **High** |
| CTA path auto-selects + updates `mob_at_last_cat_expense` | Last-used memory + chip promotion work | **Medium** |
| No always-visible add control on AT panel | UX placement stays inside picker sheet | **Medium** |
| `_cat_add_dialog` uses shared helper | Desktop/mobile parity on create logic | **Medium** |
| `txn.mob.add_category_cta` EN/TR locale keys | i18n contract | **Low** |

---

### `tests/test_mobile14_ownership_contract.py` (16 tests: 14 pass + 2 xfail) — MOBILE-14 closed

| Contract | State | Notes |
|---|---|---|
| `--hdr-h` defined only in theme.css + mobile_header.css | Pass | Regression lock |
| `--hdr-h` within-file dedup (theme ≤2, mobile_header ≤2) | Pass | M1 ✅ |
| `mobile_shell.css` no `block-container padding-top` | Pass | M2 ✅ |
| Bottom nav/FAB/hub styling owned by mobile_shell.css | Pass | Regression lock |
| No bottom-chrome selectors in widgets.css | xfail | M3 optional |
| Profile/co-switch sheets owned by mobile_shell.css (E13) | Pass | Regression lock |
| No sheet selectors in widgets.css | xfail | M4 optional |
| KPI/dashboard owned by theme.css | Pass | Regression lock |
| No KPI rules in widgets.css | Pass | M5 ✅ |
| Sidebar-hide post-M6 lock (`theme: 0, shell: 2`) | Pass | M6 ✅ |
| Sidebar-hide single owner (mobile_shell.css) | Pass | M6 ✅ |
| No `mob_at_`/`mob_rpt_` layout grids in widgets.css | Pass | E4/E5 lock |
| No `txh_` layout grids in widgets.css | Pass | TXH micro-step ✅ |
| Notification rule liveness pins (3 files) | Pass | Permanent two-owner contract |

Remaining xfails (M3/M4) are optional suppression relocations — not MOBILE-14 blockers.

---

## UI / theme regression (run after CSS or table helper changes)

```bash
pytest tests/test_phase16a_theme.py tests/test_ui1_design_language.py -q
```

**50 tests** (as of 2026-06-09) — includes financial table classes, `readable_dataframe_table_html`, `infer_column_kind`, `_render_readable_df`, no-`st.dataframe` policy grep, dark-mode widget rules, mono sweep 3 guards, dropdown + form widget visibility CSS contracts, New Transaction desktop/mobile host + popover click-through guards.

| Area | Protected |
|------|-----------|
| `.erp-fin-table` / code-name-amount | Financial + operational readable tables |
| `readable_dataframe_table_html` status rows | Budget over/on-track tint |
| No `st.dataframe` in app display path | Sweep 2 policy (grep audit in tests) |
| `stSelectboxVirtualDropdown` + `[role="option"]` CSS | Selectbox/multiselect option list readability |
| `stFormSubmitButton` + `stFileUploader` + `stNumberInput` CSS | Form submit, upload, number stepper readability |
| Popover `pointer-events` + desktop skips `erp_at_mobile_screen` | New Transaction selectbox post-pick click trap |
| `TestNewTransactionTypeState` bank/customer/sync | AT form state preserved across selector changes |

---

## Coverage gaps (known — tests NOT yet written)

| Gap | Risk | When to add |
|-----|------|-------------|
| Partial payable CC payments (multiple sub-ledger rows per payable) | **Low** | If partial CC payments become common |

---

## Risk level legend

| Level | Meaning |
|-------|---------|
| **Critical** | Wrong GL account or customer/company CC confusion |
| **High** | Material misstatement or broken posting path |
| **Medium** | Wrong sub-ledger, gating, or workflow inconsistency |
| **Low** | i18n, permissions edge, UI-only |
