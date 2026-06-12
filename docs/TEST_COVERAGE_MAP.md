# Test Coverage Map — Banking, Reconciliation & Company CC

**Last updated:** 2026-06-13 (USER-ACCESS-01 UA-P1)  
**Full suite:** run `pytest tests/` — **1502 passed, 2 xfailed** (see latest `pytest tests/ -q` tail).

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

### `tests/test_recipe_costing_service.py` (32 tests) — RC-P1 / RC-P1b / RC-P2A

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `to_base_units` / `from_base_units` | Canonical g/ml/each; same-dimension only | **High** |
| `validate_ingredient` / `validate_recipe_lines` | Base-unit costs; ingredient/sub-recipe XOR | **High** |
| `compute_recipe_cost` (pure + DB) | On-demand rollup; never stored; waste %; sub-recipe scale | **High** |
| Cycle + recursion depth (max 3) | Sub-recipe graph safety | **Critical** |
| `where_used` transitive | Ingredient/sub-recipe parent chain | **Medium** |
| `bulk_update_costs` atomicity | All-or-nothing cost batch | **High** |
| Deactivated ingredient warning | Breakdown continues with warning | **Medium** |
| Explicit `company_id` API | No Streamlit in service | **High** |
| `list_ingredients` / `get_recipe` / `update_ingredient` | Read APIs for RC-P1b UI | **High** |
| Menu service APIs on migration contract | `create_menu_item` … `list_menu_profitability` take `company_id` | **High** |
| Posting/inventory guard contract scan | No JE/inventory imports in `services/` | **Critical** |

---

### `tests/test_recipe_costing_menu_service.py` (15 tests) — RC-P2A

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `gross_to_net_price` / `net_to_gross_price` | Tax-inclusive gross → net revenue | **High** |
| `compute_food_cost_pct` / `compute_markup_pct` | Food cost % and markup from cost + net price | **High** |
| `compute_suggested_gross_price` | Target food cost % → suggested list price | **High** |
| `get_current_menu_price` / `as_of` | Latest effective price; historical lookup | **High** |
| Company `tax_rate` setting | Net price from `CompanySetting` | **High** |
| Company isolation | Menu items scoped per company | **Critical** |
| Inactive menu item warning | Profitability still computed with warning | **Medium** |
| `list_menu_profitability` `active_only` | Inactive items excluded by default | **Medium** |

---

### `tests/test_recipe_costing_ui_contract.py` (9 tests) — RC-P1b / RC-P2A

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Renderer calls `services.recipe_costing` only | No business logic in UI | **High** |
| No costing math in UI source | No duplicate rollup or profitability math in Streamlit | **Critical** |
| Restaurant-friendly tree (`_recipe_tree_markdown`) | Names not raw IDs in forms | **Medium** |
| Recipe Costing nav + permissions wired | Owner/manager access; Menu Items page | **Medium** |
| No inventory/posting imports in UI | Scope guard | **High** |

---

### `tests/test_recipe_costing_models.py` (3 tests) — RC-P1

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Company-scoped ingredient name uniqueness | Multi-tenant isolation | **High** |
| Recipe line XOR via service validation | No dual ingredient + sub-recipe | **High** |
| Recipe row has no stored computed cost | Cost always computed on demand | **High** |

---

### `tests/test_recipe_costing_menu_models.py` (3 tests) — RC-P2A

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Company-scoped menu item name uniqueness | Multi-tenant isolation | **High** |
| Menu item has no stored profitability columns | Profitability always computed on demand | **High** |
| `MenuPriceHistory` append-only | Price changes add rows; no overwrite | **High** |

---

### `tests/test_daily_sales_close_service.py` (~36 tests) — DSC-P1

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `compute_erp_sales_totals` / `compute_variance` | Read-only ERP compare; pure variance math | **High** |
| `save_draft` / `verify_external_sales` / `void_verification` | Draft nullability; material-variance ack; branch uniqueness | **High** |
| Explicit `company_id` API | No Streamlit `cq()` in service | **High** |
| Posting-guard + vendor-neutrality contract scan | No JE/posting/vendor branches in `services/` | **Critical** |
| `is_verification_stale` | Snapshot invalidation | **Medium** |

---

### `tests/test_daily_sales_close_models.py` (5 tests) — DSC-P1

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Draft ERP/variance NULL | Distinguish draft vs verified | **High** |
| Branch normalization uniqueness | Default-site collision | **Medium** |

---

### `tests/test_daily_sales_close_ui_contract.py` (9 tests) — DSC-P2

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Renderer calls `services.daily_sales_close` only | No business logic in UI | **High** |
| No `Sale` sum/query in UI source | No duplicate ERP math in Streamlit | **High** |
| `source_name` text input (not vendor dropdown) | VENDOR-NEUTRAL-01 | **High** |
| Closings nav + permissions wired | Owner/manager access | **Medium** |

*Orthogonal to EOD — `test_end_of_day_close.py` unchanged until DSC-P3 EOD hook.*

---

### `tests/test_user_access01_permissions.py` (23 tests) — UA-P1

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Template-only resolution | `template ∪ grants − denies` baseline | **Critical** |
| Grant / deny / clear / reset lifecycle | Override CRUD + audit rows | **High** |
| Deny beats grant | Explicit deny wins over grant | **High** |
| Owner lockout guard | Last active owner cannot lose `manage_permissions` | **Critical** |
| Legacy matrix backward compatibility | Owner/manager/cashier/partner parity with `_PERMISSIONS` seed | **Critical** |
| Company isolation | Overrides scoped per company | **Critical** |
| Unknown permission key → false | Registry is authoritative | **High** |
| Service migration contract | No Streamlit/app imports; explicit `company_id`/`user_id`; DTO `to_dict()` JSON-safe | **High** |

---

### `tests/test_user_access01_models.py` (1 test) — UA-P1

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Unique `(company_id, user_id, permission_key)` | One override row per key; flip updates in place | **High** |

**UA-P1 smoke audit (2026-06-13):**
- Owner compatibility passed
- Manager compatibility passed
- Viewer compatibility passed
- 0 permission regressions
- 0 hidden page regressions
- 0 access regressions
- `manage_permissions` is an intentional owner-only addition (not a regression)

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

## TXH-DETAIL-01 — expanded transaction detail polish (implemented)

**Status:** ✅ **Closed** — `tests/test_txh_detail01.py` — **6 pass**.

| Contract | Business rule protected | State |
|----------|-------------------------|-------|
| No inline `style=` in JE/Edit render helpers | Token-driven detail styling | ✅ Pass |
| Semantic `erp-txh-je-*` / `erp-txh-edit-*` in app + CSS | CSS-02 ownership in `desktop_txn_history.css` | ✅ Pass |
| Edit diff uses `--theme-danger-text` / `--theme-success-text` | THEME-CONTRAST-01 readable diffs | ✅ Pass |
| JE grid: account + right-aligned Dr/Cr | Scannable ledger detail | ✅ Pass |
| `_txh_render_row_panels` action/edit/void logic unchanged | Accounting behavior frozen | ✅ Pass |

---

## VIEWPORT-SYNC-01 — JS/CSS mobile threshold sync (implemented)

**Status:** ✅ **Closed** — `tests/test_viewport_sync01.py` — **5 pass**.

| Contract | Business rule protected | State |
|----------|-------------------------|-------|
| JS detector thresholds match `MOBILE_VIEWPORT_*` constants | 968 / 1366 / 520 boundaries pinned | ✅ Pass |
| CSS coarse arm uses 1366px not 1024px | Touch tablets get layout CSS | ✅ Pass |
| Identical `@media` header across 6 mobile CSS owners | No partial mobile chrome | ✅ Pass |
| `erp_mobile_ui` cookie in detector + sync | UA/cookie hint stable | ✅ Pass |

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

### `tests/test_partner_statement_p4.py` (27 tests) — PARTNER-STATEMENT-01 P4

| Contract | Protects |
|---|---|
| One row per partner; values match `build_partner_statement` | P1 projection rollup |
| Multiple partners with different activity | Multi-partner rollup |
| Voided movements excluded | Statement integrity |
| Profit allocation by fiscal period end-date | Period attribution |
| AdvanceOffset shown but zero net effect | Settlement accounting |
| Position = capital + current − advances | Core formula |
| company_owes / partner_owes / settled status | Status labels |
| Footer totals match row sums | Rollup math |
| Reconciliation / outstanding advance / closed-period warnings | P1 warning alignment |
| Inactive partner included by default; hide inactive filter | Partner filters |
| Month preset + invalid range + empty period | Period controls |
| Excel/CSV export rows + footer totals | Export parity |
| PDF payload primary columns + bytes generated | PDF export |
| P4 above single-partner statement; shared period keys | UI placement |
| View statement sets selected partner session key | Row action |
| EN/TR `partner.stmt.all_*` locale keys resolve | i18n |
| `post_partner_movement` / `allocate_profit_to_partners` unchanged | No posting drift |

---

### `tests/test_partner_statement_p3.py` (9 tests) — PARTNER-STATEMENT-01 P3

| Contract | Protects |
|---|---|
| PDF payload summary totals match statement | Export parity |
| PDF payload includes detail lines | P2 detail in PDF |
| AdvanceOffset zero net effect in PDF detail | Settlement accounting |
| Allocation detail date = fiscal period end | Period attribution |
| Empty period PDF generates | Edge case |
| Warnings included in PDF payload | Status export |
| Excel export DataFrame unchanged from P2 | Regression |
| Print UI uses banner/financial helpers | No fragile inline styles |
| `post_partner_movement` unchanged | No posting drift |

---

### `tests/test_partner_statement_p2.py` (8 tests) — PARTNER-STATEMENT-01 P2

| Contract | Protects |
|---|---|
| Detail running position reaches closing | Running balance math |
| AdvanceOffset detail net effect zero | Settlement accounting |
| Profit allocation detail uses period end-date | Period attribution |
| Inactive partner detail lines | Partner filter |
| Empty period opening = closing | Zero-activity reconcile |
| Export summary totals match screen | Excel export parity |
| Detail expander + export in UI | P2 wiring |
| `post_partner_movement` unchanged | No posting drift |

---

### `tests/test_partner_statement_p1.py` (20 tests) — PARTNER-STATEMENT-01 P1

| Contract | Protects |
|---|---|
| Position = capital + current − advances | Core formula |
| Status phrasing (company owes / partner owes / settled) | Direction labels |
| All six movement types bucketed correctly | Activity sections |
| AdvanceOffset zero net position effect | Settlement accounting |
| Profit allocation by fiscal period end-date (not JE date) | Period attribution |
| Stored `PartnerProfitAllocationLine.amount` used | No % recompute |
| Voided movements excluded | Statement integrity |
| Outstanding advance warning | Status section |
| Closed period without allocation warning | Compliance hint |
| Reconciliation identity check | opening + activity = closing |
| Inactive partner with balance renders | Partner filter |
| `post_partner_movement` / `allocate_profit_to_partners` unchanged | No posting drift |
| Statement tab on Partner Accounts page | UI placement |

---

### `tests/test_partner_ux_p1p2p3.py` (9 tests) — PARTNER-UX-01 P1–P3 + i18n fix

| Contract | Protects |
|---|---|
| Movement explain + P2/P3 locale keys EN/TR | i18n parity |
| Movement form renders type explanation | P1 captions |
| `get_partner_advance_balance` uses 15XX GL | P2 advance source |
| No-advance warning for Repayment/AdvanceOffset | P2 guardrail |
| Exceeds-outstanding warning before submit | P2 guardrail |
| Summary tab plain-language labels | P3 UX |
| Summary labels translate (not raw `partner.summary_*` keys) | i18n regression |
| Summary labels in MESSAGES + TRANSACTIONAL catalogs | Reliable lookup |
| `post_partner_movement` unchanged | No posting drift |

---

## BANK-03 — Banking Wording Verification

**Status:** Verified (2026-06-05)  
**Coverage:** `tests/test_bank03_wording.py` (13 contract tests) + stale-wording guards in `tests/test_banking_desktop_b1b2.py`

| Contract | Protects |
|---|---|
| Canonical EN/TR labels (POS / Card Settlement, Settlement preview, Match check, Card sales deposit) | Wording consistency |
| No BSI / card clearing / clearing sales / deposit clearing in banking locales | Retired jargon |
| All `bank.*` / `banking.*` keys resolve via `t()` EN/TR | No raw locale keys |
| MESSAGES duplicates match TRANSACTIONAL for banking keys | Reliable lookup |
| `render_banking` uses `_st_page_title(NAV_BANKING)` | Localized page header |
| Banking chips use locale keys (`bank.section.*`, `banking.pos_entry.title`) | Navigation labels |

**Quick command:**

```bash
pytest tests/test_bank03_wording.py tests/test_banking_desktop_b1b2.py -q
```

---

## UI-STAB-02 — Banking Presentation Separation

**Status:** Complete  
**Coverage:** `tests/test_ui_stab02_banking.py` (17 contract tests)

| Contract | Protects |
|---|---|
| `ui/banking.py` owns extracted renderers | Presentation layer isolated from `app.py` |
| `app.py` re-exports `_render_*` / `_banking_*` aliases | Existing wiring + test entry points unchanged |
| POS settlement route keys unchanged | P1B navigation (`pos_settlement`, `bsi_match_kind`) |
| P1–P4 panels present in UI module | Preview · clearing visibility · unsettled list · match failure |
| `_render_bsi_deposit_clearing` stays in `app.py` with posting | No accounting drift into UI layer |
| No `post_*` / `create_journal_entry` in `ui/banking.py` | UI module is presentation-only |
| Lazy `import app` in `ui/banking.py` | Avoids circular import at module load |

**Quick command:**

```bash
pytest tests/test_ui_stab02_banking.py -q
```

---

## UI-STAB-01 — Shared Avatar Renderer

**Status:** Complete  
**Coverage:** `tests/test_ui_stab01_avatar.py`

| Contract | Protects |
|---|---|
| `user_initials` / `render_user_avatar` in `ui/avatar.py` | Single initials renderer |
| Header, login, My Account use shared helper | No duplicate avatar markup in `app.py` |
| `.erp-user-avatar--sm/md/lg` in `theme.css` | Size tokens |

---

## BANKING-UX-02 — POS Settlement Transparency

**Status:** Complete  
**Coverage:** P1 · P1B · P2 · P3 · P4 (79 tests total)

| Test file | Tests | Phase |
|---|---|---|
| `tests/test_banking_ux02_p1.py` | 13 | P1 — Settlement preview |
| `tests/test_banking_ux02_p1b.py` | 19 | P1B — Focused POS / Card Settlement entry |
| `tests/test_banking_ux02_p2.py` | 11 | P2 — Card Sales Clearing visibility |
| `tests/test_banking_ux02_p3.py` | 14 | P3 — Unsettled card sales list |
| `tests/test_banking_ux02_p4.py` | 22 | P4 — Match failure explanation |

**Quick command:**

```bash
pytest tests/test_banking_ux02_p1.py tests/test_banking_ux02_p1b.py \
  tests/test_banking_ux02_p2.py tests/test_banking_ux02_p3.py \
  tests/test_banking_ux02_p4.py -q
```

**Protected invariants (all phases):** No changes to revenue recognition · `post_deposit_clearing_match` JE · Card Sales Clearing account **1150** · Sales Revenue advanced-only guardrails.

### `tests/test_banking_ux02_p1.py` (13 tests) — P1

| Contract | Protects |
|---|---|
| Expected deposit = settlement − fee | Preview math |
| Remaining clearing after settlement | Preview math |
| Explicit settlement-batch fee | Fee source |
| Warnings: exceeds clearing, fee > settlement, negative deposit, zero balance | Guardrails |
| Preview renders before post button | UI placement |
| Revenue note in preview | P1 explainer |
| Sales Revenue still advanced-only | P1 regression |
| Settlement JE lines unchanged | No posting drift |
| EN/TR locale keys | i18n parity |

---

### `tests/test_banking_pos_workflow_p1p2.py` (7 tests) — BANKING-POS-WORKFLOW-01 P1+P2

| Contract | Protects |
|---|---|
| Sales Revenue not in main Other Income options | P1 demotion to advanced expander |
| Sales Revenue selection shows double-count warning | P1 guardrail |
| `card_deposit_style` + Sales Revenue shows POS warning | P1 escalated guardrail |
| POS Settlement explainer in Card Sale Deposit panel | P2 workflow explanation |
| Banking Settings caption includes POS Settlement line | P2 settings explanation |
| EN/TR locale keys for P1+P2 | i18n parity |
| `post_generic_deposit` / `post_deposit_clearing_match` unchanged | No posting drift |

---

### `tests/test_banking_desktop_b1b2.py` (11 tests) — BANKING-DESKTOP-01 B1+B2

| Contract | Protects |
|---|---|
| `banking.css` registered in `load_theme_css()` | Banking chip CSS bundled |
| Chip grid layout in `banking.css` | `bank_sec_sel_*` 2-column grid |
| `banking.css` not in `MOBILE_VIEWPORT_CSS_OWNER_FILES` | Desktop banking CSS excluded from mobile list |
| `_banking_section_select` chips-only (no `st.radio`) | Canonical Banking chip helper |
| `render_banking` uses chips + `banking_section` key | Banking top-level nav |
| `render_bank_statement_import` uses chips + `bsi_section` key | BSI wizard nav |
| BSI staged upload keys not cleared on section switch | Upload → Review/Match/History survives |
| No stale Card settlement workflow wording (EN/TR) | BANK-03 closure |
| POS Settlement wording present (EN/TR) | BANK-03 positive contract |

---

### `tests/test_desktop_reports_r1.py` (6 tests) — REPORTS-DESKTOP-01 R1 + REPORTS-DESKTOP-02

| Contract | Protects |
|---|---|
| `desktop_reports.css` registered in `load_theme_css()` | Desktop Reports CSS bundled |
| `_mgmt_report_select` chips-only (no `st.selectbox`) | Canonical chip selector |
| No `erp_rpt_sel_desktop_*` in app or mobile CSS | Desktop selectbox retired |
| Chip grid layout in `desktop_reports.css` | Desktop + mobile chip rows |
| `desktop_reports.css` not in `MOBILE_VIEWPORT_CSS_OWNER_FILES` | Desktop file excluded from mobile list |

---

### `tests/test_dashboard01_d1.py` (7 tests) — DASHBOARD-01 D1 + D2

| Contract | Protects |
|---|---|
| No `banner banner-primary` in `render_dashboard` | Legacy gradient welcome retired |
| `erp-dash-welcome-card` in app + theme.css | Flat dashboard welcome owner |
| No inline `style=` in `render_dashboard` | D2 class-system ownership |
| `erp-dash-alert-card` — no inline border-left | Named overdue alert surface |
| `erp-dash-*` classes in `theme.css` | Dashboard CSS sole owner |
| `render_kpi_grid` variant-only (no `color=` escape) | KPI grammar standardized |
| Theme contrast module importable | Existing contrast suite unaffected |

---

### `tests/test_icon_svg_contract.py` (8 tests) — ICON-MODERNIZE-01

| Contract | Protects |
|---|---|
| Scoped nav keys are text-only (no emoji) | No fragile Unicode in routing keys |
| Critical nav pages have SVG icon mapping | Inline SVG via `PAGE_ICON` / `nav_page_icon_html` |
| TXH actions use ASCII labels | `st.button` safe compact labels (V/E/R/D/X) |
| `modules_catalog` aligned with `nav_keys` | Registry ↔ dispatch integrity |
| App wires `_nav_page_button` + `normalize_nav_key` | Runtime nav render path uses icon system |
| `icons.css` injected in theme | Icon sizing / currentColor tokens |
| Partner tab labels have no emoji | Owner Equity / partner tabs text-only |
| `icon_svg` uses `currentColor` | Theme-aware SVG strokes |

---

### `tests/test_mobile_nav_icons.py` (5 tests) — MOBILE-NAV-ICON-01

| Contract | Protects |
|---|---|
| No emoji in `_MOBILE_BOTTOM_NAV` | Bottom nav stays on the SVG system |
| Icon names exist in `icon_svg` registry + render with currentColor | home/landmark/plus/bar-chart/menu wiring |
| Render fn uses SVG overlay + ZWSP first line | Touch target geometry unchanged |
| Shell CSS owns overlay + `:has(primary)` active state | Active tab icon turns theme-info |
| FAB unchanged ("+" label, circle styling) | Blue floating Add button preserved |

---

### `tests/test_portal_theme_contract.py` (7 tests) — PORTAL-THEME-01

| Contract | Protects |
|---|---|
| Popover-body text/caption rules present, tokenised | Notification + profile popover readability |
| Dialog text + input rules (incl. placeholder/caret) | st.dialog forms readable in OS/app theme splits |
| Primary/secondary button grammar in portals | `--erp-primary-fill` + `--erp-on-primary` usage |
| Calendar popup rules | st.date_input popup readability |
| **No stMain prefix on portal rules** | The regression that caused the bug |
| No literal hex in portal section | Token-only policy |
| Selectbox dropdown fix untouched | Original portal fix preserved |

`test_theme_contrast.py` +2: portal text/caption-on-card and on-primary-on-fill pairs, both modes.

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
