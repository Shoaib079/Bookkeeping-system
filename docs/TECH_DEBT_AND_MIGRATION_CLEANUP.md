# Technical Debt & Migration Cleanup Register

**Purpose:** Living register of service-layer extraction, FastAPI/React prep, and cross-cutting migration debt.  
**Governance:** [MIGRATION-READINESS-01](../ROADMAP.md#migration-readiness-01--fastapireact-ready-service-checklist) · [FUTURE-MIGRATION-01](../ROADMAP.md#future-architecture--long-term-roadmap)

**When to update:** Whenever migration-prep debt is identified, scheduled, or resolved. Required by [MIGRATION-READINESS-01](../ROADMAP.md#migration-readiness-01--fastapireact-ready-service-checklist) item 8.

**Status key:** `Open` · `Scheduled` · `In progress` · `Resolved` · `Won't fix`

---

## Governance (TD-GOV)

| ID | Item | Priority | Status | Notes |
|----|------|----------|--------|-------|
| **TD-GOV-01** | Document **MIGRATION-READINESS-01** in `ROADMAP.md`, `ARCHITECTURE_HANDOFF.md`, `CLAUDE.md`, and Cursor rules; use DSC-P1 as reference implementation checklist | High | **Resolved** | Adopted 2026-06-05 |
| **TD-GOV-02** | Maintain this register (`TECH_DEBT_AND_MIGRATION_CLEANUP.md`) as the canonical tech-debt log for service extraction and API prep | High | **Resolved** | Created 2026-06-05 |
| **TD-GOV-03** | **Migration Cleanup report section** required at end of every implementation report (5-part template below); codified in MIGRATION-READINESS-01 | High | **Resolved** | Adopted 2026-06-05 |

---

## Implementation report — Migration Cleanup template

Copy this section into every implementation completion report:

```markdown
## Migration Cleanup

### 1. Code to keep during FastAPI/React migration
- …

### 2. Code likely to replace during FastAPI/React migration
- …

### 3. Dead code found
- …

### 4. Temporary Streamlit-only code
- …

### 5. Items added to TECH_DEBT_AND_MIGRATION_CLEANUP.md
- …
```

---

## DSC-P1 / External Sales Verification (TD-DSC)

| ID | Item | Priority | Status | When / trigger |
|----|------|----------|--------|----------------|
| **TD-DSC-01** | **Duplicate ERP sales aggregation** — `services/daily_sales_close.compute_erp_sales_totals` vs `app.calculate_eod_snapshot` inner `_sale_sum` logic; extract shared helper (e.g. `services/sales_daily_totals.py`) and point both callers at it | High | Open | Before DSC-P3 EOD warning hook |
| **TD-DSC-02** | **Service commits internally** — `save_draft`, `verify_external_sales`, and `void_verification` call `session.commit()` twice (data + audit); refactor to `flush()` + optional caller `commit` for FastAPI transaction control | Medium | Open | FastAPI Phase B |
| **TD-DSC-03** | **Error surface** — plain English `error` strings on `MutationResult`; add stable `error_code` (e.g. `ESV_SOURCE_REQUIRED`) for React/FastAPI clients | Medium | Open | Before FastAPI exposure |
| **TD-DSC-04** | **Module naming** — `services/daily_sales_close.py` vs entity `ExternalSalesVerification`; consider `external_sales_verification.py` with backward-compatible re-export | Low | Open | Optional clarity pass |
| **TD-DSC-05** | **Registry tolerance** — hardcoded `DEFAULT_TOLERANCE = 0.01`; wire `operations.sales_verify_tolerance` registry key per spec | Medium | Open | DSC-P2+ |
| **TD-DSC-06** | **Stale snapshot** — `sale_count_snapshot` only; amount edits without count change do not flag stale (same limitation as EOD); document or extend | Low | Open | DSC-P3+ |
| **TD-DSC-07** | **Roadmap / docs drift** — keep DSC phase status current in `ROADMAP.md` and spec §10 as P2–P4 land | Low | **Resolved** | 2026-06-05 — synced after DSC-P2: `ROADMAP.md`, `docs/DAILY_SALES_CLOSE_01_SPEC.md` §10, `docs/AUDIT_HISTORY.md`, `docs/TEST_COVERAGE_MAP.md`, `ARCHITECTURE_HANDOFF.md` |
| **TD-DSC-08** | **UI `_erp()` lazy import** — `ui/external_sales_verification.py` reaches into `app.py` for `_t`, `_can`, `amount_input`, `current_company_required`; replace with injected context or shared `ui/context.py` at API migration | Medium | Open | FastAPI Phase D |
| **TD-DSC-09** | **Widget session keys** — `esv_*` form keys and `esv_form_loaded_for` date-sync logic are Streamlit-only; React form state replaces entirely | Low | Open | React module for ESV |

---

## Global migration (TD-MIG)

Inherited cross-cutting debt — not introduced by DSC-P1 alone.

| ID | Item | Priority | Status | When / trigger |
|----|------|----------|--------|----------------|
| **TD-MIG-01** | Extract remaining `app.py` business logic into `services/` ([FUTURE-MIGRATION-01](../ROADMAP.md#future-architecture--long-term-roadmap) Phase A) | High | Open | Incremental per module |
| **TD-MIG-02** | Replace Streamlit `cq()` / `_current_company_id()` with explicit `company_id` in all new services; migrate legacy callers incrementally | High | Open | Per new service module |
| **TD-MIG-03** | SQLite → PostgreSQL: validate partial unique index `uq_esv_active` (`COALESCE(branch_location,'')`) and equivalent constraints on Postgres | Medium | Open | Pre-PostgreSQL cutover |
| **TD-MIG-04** | Float → `Decimal` for money fields across models and services | **High** | Open — [MONEY_DECIMAL_01_AUDIT.md](./MONEY_DECIMAL_01_AUDIT.md) (2026-06-16); blocker for PG **production** runtime |
| **TD-MIG-05** | SQLAlchemy 1.x `session.query()` → 2.0 `select()` style | Low | Open | Global migration prep |

---

## NAV-ARCH — Navigation single source of truth (TD-NAV-ARCH)

| ID | Item | Priority | Status | When / trigger |
|----|------|----------|--------|----------------|
| **TD-NAV-ARCH-01** | **Navigation registry** — dispatch, desktop, static roles, mobile, and `react_route` contract derive from `registry/navigation.py` | High | **Resolved** — S4 contract frozen | React migration |
| **TD-NAV-ARCH-02** | **Mobile presentation helpers** — `_MOBILE_HUB_CONFIG_ALIASES`, `_MOBILE_MORE_ACCORDION_EXCLUDE` still in `app.py` | Low | Open | Optional cleanup |
| **TD-NAV-ARCH-03** | **React route contract** — frozen in `docs/NAV_ARCH_REACT_ROUTE_CONTRACT.md` + `validate_react_route_contract()` | Medium | **Resolved** | NAV-ARCH-S4 |

**Audit:** [NAV_ARCH_AUDIT.md](./NAV_ARCH_AUDIT.md) · **Tests:** `tests/test_nav_arch_audit.py`

---

## UI-SYSTEM-02 — ERP-wide UI & theme (TD-UI-SYSTEM-02)

| ID | Item | Priority | Status | When / trigger |
|----|------|----------|--------|----------------|
| **TD-UI-SYSTEM-02-01** | **Mobile `--hdr-h` conflict** — `theme.css` sets `120px` at `max-width: 968px` while `mobile_header.css` owns `56px` / `86px` | High | **Resolved** — S2 removed stale override | UI-SYSTEM-02-S2 |
| **TD-UI-SYSTEM-02-02** | **Triple token source** — `theme.css :root`, `ui/theme.py` `LIGHT/DARK_ROOT_VARS`, and `@media (prefers-color-scheme: dark)` — no single registry file | Medium | **Resolved** — `ui/design_tokens.py` + parity tests | UI-SYSTEM-02-S2 |
| **TD-UI-SYSTEM-02-03** | **Sidebar render order hand-authored** — `_render_navigation_tree` does not consume `_NAV_DIRECT_PAGES`; Banking/section placement drifts from registry `sidebar_direct_order` | Medium | **Resolved** — `registry/sidebar_layout.py` owns frozen visual sequence | UI-SYSTEM-02-S3 |
| **TD-UI-SYSTEM-02-04** | **Dead CSS** — `.erp-mobile-report-filters { display: block }` duplicate at `theme.css:1106–1108` (live hide at `1353–1355`) | Low | **Resolved** — redundant mobile block rule removed | UI-SYSTEM-02-S4 |
| **TD-UI-SYSTEM-02-05** | **Expense bar width ladder** — 96× `[data-pct]` rules in `theme.css:1789–1884` | Low | **Resolved** — inline `width:%` in `app.py` | UI-SYSTEM-02-S4 |
| **TD-UI-SYSTEM-02-06** | **Stale role hue tokens** — `--role-*` in `:root` unused under mono avatar policy (`role_accent_css_var`) | Low | **Governed** — deprecated in token registry + S5 React contract | UI-SYSTEM-02-S5 |
| **TD-UI-SYSTEM-02-07** | **KPI grid split** — `.erp-mob-kpi-grid` / `.erp-mob-kpi-value` across `mobile_components.css`, `mobile_reports.css`, `mobile_txn.css` | Medium | **Resolved** — `mobile_components.css` owns grid; `--reports-cf` modifier | UI-SYSTEM-02-S4 |
| **TD-UI-SYSTEM-02-08** | **No `mobile_banking.css`** — banking mobile layout adaptation deferred (ROADMAP Banking UX) | Medium | Open | Banking UX epic |

### MONO-THEME-01 (TD-MONO)

| ID | Item | Priority | Status | When / trigger |
|----|------|----------|--------|----------------|
| **TD-MONO-THEME-01-01** | **Duplicated component grammar** — desktop (`theme.css`/`widgets.css`) and mobile (`mobile_*.css`) define card/nav-active/chip styling separately despite shared color tokens | High | **In progress** — S4 desktop cards migrated; S5–S6 mobile cards/tables | MONO-THEME-01-S5–S6 |
| **TD-MONO-THEME-01-02** | **Role hue references remain** — `DEPRECATED_ROLE_TOKEN_KEYS` still referenced in `auth.css` etc. | Low | Open | MONO-THEME-01-S7 cleanup |

**Audit:** [MONO_THEME_01_AUDIT.md](./MONO_THEME_01_AUDIT.md) · **Tests:** `tests/test_mono_theme_01_audit.py`, `tests/test_mono_theme_01_s2_shared_grammar_tokens.py`, `tests/test_mono_theme_01_s3_nav_active_grammar.py`, `tests/test_mono_theme_01_s4_desktop_card_grammar.py`

---

## POSTING-SERVICE-01 (TD-PS)

PS-P1 shipped 2026-06-13 — JE kernel verbatim in `services/posting.py`; app.py shims.  
PS-P2a shipped 2026-06-05 — `get_account_by_name`, sales `post_*` trio, `card_settlement_on`; app.py shims.  
PS-P2b shipped 2026-06-13 — `resolve_payment_credit_account`, `post_payable_creation`; app.py shims.  
PS-P2c shipped 2026-06-13 — `sync_company_cc_subledger` (P2c-1), `post_expense` + `post_payable_payment` (P2c-2), `post_purchase` + `resolve_purchase_debit_account` + `purchase_ref_type` (P2c-3); app.py shims.  
PS-P3 shipped 2026-06-13 — reversal primitives (P3-1), `void_expense` + `void_payable` (P3-2a), `void_sale` (P3-2b), purchase cascade helpers (P3-3a), `void_purchase` (P3-3b); app.py shims; `log_audit` remains app-side.  
PS-P4 shipped 2026-06-13 — `post_bank_transaction` + `post_bank_transfer` (P4-1), `void_bank_transaction` (P4-2); app.py shims; forward balance mutation callers remain in app.py; `void_reconciliation` deferred to PS-P5.  
PS-P5 shipped 2026-06-13 — `compute_sale_balance_status` + `post_receivable_payment` (P5-1), `void_inventory_transaction` (P5-2), `post_capital_contribution` + `post_owner_drawing` + `post_salary` + `void_equity_movement` (P5-3), `void_reconciliation` + `void_eod_close` + `void_year_end_close` (P5-4); app.py shims; movement/year-end family deferred to PS-P6 (**TD-POSTING-05**).

| ID | Item | Priority | Status | When / trigger |
|----|------|----------|--------|----------------|
| **TD-PS-01** | Kernel **commits internally** (`session.commit()` / `session.rollback()` moved verbatim) — includes reversal primitives and **void service post-flag commits** — convert to flush-only + boundary-owned transactions | High | Open | PS-P6+ per caller family; FastAPI Phase B hard requirement |
| **TD-PS-02** | app.py shims carry **ambient company resolution** (session state → explicit `company_id`) — remove per call site as callers migrate to the service | Medium | Open | Per wave; gone when last legacy caller migrates |
| **TD-PS-03** | Service returns **ORM `JournalEntry`** (legacy contract) — add `PostingResult` DTO for new consumers; deprecate ORM return | Medium | Open | First new consumer (SC approval, PS-P2); removal at FastAPI Phase B |
| **TD-PS-04** | Kernel `rollback()` on validation failure also discards the **caller's** uncommitted work (pre-existing behaviour, preserved verbatim) — fix lands with TD-PS-01 boundary conversion | Low | Open | PS-P2+ |
| **TD-PS-05** | **`get_account_by_name` partial extraction** — sales posting moved; ~50 app.py non-sales callers still use the shim; migrate incrementally or re-export from service at PS-P2b | Medium | Open | PS-P2b expense/purchase wave |
| **TD-PS-06** | **`resolve_payment_credit_account` partial `company_id`** — on Credit Card branch, `company_id` gates `company_card_enabled(session, cid)` but Credit Card Payable GL lookup uses `gl_company_id` only (ambient via shim); preserved verbatim in PS-P2b extraction — unify at intentional cleanup pass, not during extraction | Medium | Open | Post PS-P2b / before FastAPI Phase B |
| **TD-PS-07** | **`sync_company_cc_subledger` ambient fallback** — sink uses `company_id = company_id or ambient_company_id`; expense/purchase/payable-payment shims thread both `gl_company_id` and `ambient_company_id` from ambient session company; preserved verbatim in PS-P2c — unify with TD-PS-06 at intentional cleanup pass, not during extraction | Medium | Open | Post PS-P2c / before FastAPI Phase B |
| **TD-PS-08** | **Banking balance ownership asymmetry** — `post_bank_transaction` / `post_bank_transfer` are GL-only (no `BankAccount.balance` mutation); forward balance deltas applied by Streamlit banking UI callers in `app.py` via `apply_account_balance_delta`; `void_bank_transaction` owns balance reversal (`reverse_account_balance_delta` for deposit/withdrawal + direct transfer balance math). Intentionally preserved in PS-P4 — unify at BANKING-SERVICE-01 or deliberate balance-ownership pass | Medium | Open | BANKING-SERVICE-01 or post-PS-P6 cleanup |

### PS-P5 Migration Cleanup (2026-06-13)

#### 1. Code to keep during FastAPI/React migration
- `services/posting.py` — PS-P5 kernels: `compute_sale_balance_status`, `post_receivable_payment`, `void_inventory_transaction`, `post_capital_contribution`, `post_owner_drawing`, `post_salary`, `void_equity_movement`, `void_reconciliation`, `void_eod_close`, `void_year_end_close` (+ all PS-P1/P2/P3/P4 kernels)
- app.py shims for all moved names
- **`log_audit` stays in app.py** — bool void shims on `True`; close-family shims on `if not err:` (empty string = success)
- Tests: `p5_char.py` (23), `p5_4_char.py` (13) + `p5_1.py` through `p5_4.py` extraction proof

#### 2. Code likely to replace during FastAPI/React migration
- PS-P5 post/void shims — API layer supplies explicit `company_id` + `user_id`; audit write becomes boundary-owned
- `post_receivable_payment` service extra `session.commit()` for sale mutation — flush-only once TD-PS-01 lands
- Close void `str` return contract — may become structured result DTO at FastAPI boundary

#### 3. Remaining app.py real posting surfaces (not extracted — PS-P6 target)
- **Movement family:** `post_partner_movement`, `post_worker_movement`, `void_partner_movement`, `void_worker_movement` — **TD-POSTING-05** (duplicate inline YEC guards)
- **Profit allocation:** `allocate_profit_to_partners`, `void_profit_allocation` — **TD-POSTING-05**
- **Period/year-end posting chains:** `perform_year_end_close` workflow and related close posting paths
- **Reconciliation posting:** `reconciliation/match_post.py` lazy `_app()` paths — **TD-POSTING-06**
- **Balance (adjacent):** `calculate_account_balance`, `sync_account_balances`
- **Edit lifecycle (purchase):** `_create_purchase_payable`, `_update_purchase_payable`, `_sync_purchase_payable_lifecycle`
- **Balance mutation (banking UI):** `apply_account_balance_delta` callers in Streamlit banking flows (TD-PS-08)

#### 4. Dead code found
- None in PS-P5 scope

#### 5. Future cleanup items (registered above)
- **TD-POSTING-05** — primary remaining extraction blocker for PS-P6 movement/year-end family; duplicate inline YEC guards in movement paths must be centralized before service extraction
- TD-PS-01 through TD-PS-08 unchanged; **no TD cleanup performed in PS-P5**

### PS-P4 Migration Cleanup (2026-06-13)

#### 1. Code to keep during FastAPI/React migration
- `services/posting.py` — banking kernels: `post_bank_transaction`, `post_bank_transfer`, `void_bank_transaction` (+ all PS-P1/P2/P3 kernels)
- app.py shims for all moved names
- **Forward balance mutation callers in app.py** — Streamlit banking UI still calls `apply_account_balance_delta` when recording deposits/withdrawals/transfers (by design; see TD-PS-08)
- **`log_audit` stays in app.py** — `void_bank_transaction` shim calls it only on `True`
- Tests: `p4_char.py` (unchanged) + `p4_1.py`, `p4_2.py` extraction proof

#### 2. Code likely to replace during FastAPI/React migration
- Banking post/void shims — API layer supplies explicit `company_id` + `user_id`; audit write becomes boundary-owned
- Forward `apply_account_balance_delta` call sites — move into a banking service boundary once TD-PS-08 is resolved
- `void_bank_transaction` service post-flag `session.commit()` — flush-only once TD-PS-01 lands

#### 3. Remaining app.py real posting surfaces (not extracted)
- **PS-P5 equity/movement/close:** `post_partner_movement`, `post_worker_movement`, `post_salary`, `post_capital_contribution`, `post_owner_drawing`, `void_partner_movement`, `void_worker_movement`, `void_equity_movement`, `void_profit_allocation`, `void_year_end_close`, `void_eod_close`, `void_reconciliation`
- **Receivables mini-wave:** `post_receivable_payment` (FX gain/loss)
- **Inventory mini-wave:** `void_inventory_transaction`
- **Balance (adjacent):** `calculate_account_balance`, `sync_account_balances`
- **Edit lifecycle (purchase):** `_create_purchase_payable`, `_update_purchase_payable`, `_sync_purchase_payable_lifecycle`
- **Balance mutation (banking UI):** `apply_account_balance_delta` callers in Streamlit banking flows (TD-PS-08)

#### 4. Dead code found
- None in PS-P4 scope

#### 5. Future cleanup items (registered above)
- TD-PS-08 added: banking balance ownership asymmetry (forward posters GL-only; void owns reversal)
- TD-PS-01 through TD-PS-07 unchanged; **no TD-PS cleanup performed in PS-P4**

### PS-P3 Migration Cleanup (2026-06-13)

#### 1. Code to keep during FastAPI/React migration
- `services/posting.py` — reversal + void kernels: `create_reversing_journal_entry`, `reverse_journal_entries_for`, `void_expense`, `void_payable`, `void_sale`, `linked_purchase_payable`, `void_purchase_linked_payable`, `void_purchase` (+ all PS-P1/P2 kernels)
- app.py shims for all moved names; edit-lifecycle helpers `_create_purchase_payable`, `_update_purchase_payable`, `_sync_purchase_payable_lifecycle` (still in app.py, call `_linked_*` / `_void_purchase_linked_payable` shims)
- **`log_audit` stays in app.py`** — void shims call it only on `True`; stamps ambient `_current_user()`; owns the final audit commit
- Tests: `p3_char.py`, `p3_2a_char.py`, `p3_2b_char.py`, `p3_3a_char.py` (unchanged) + `p3_1.py` through `p3_3b.py` extraction proof

#### 2. Code likely to replace during FastAPI/React migration
- All void shims — API layer supplies explicit `company_id` + `user_id`; audit write becomes boundary-owned (not ambient `log_audit`)
- `_linked_purchase_payable` / `_void_purchase_linked_payable` shims — edit lifecycle callers migrate to direct service import
- Void service post-flag `session.commit()` — flush-only once TD-PS-01 lands

#### 3. Remaining app.py real posting surfaces (not extracted)
- **PS-P5 equity/movement/close:** `post_partner_movement`, `post_worker_movement`, `post_salary`, `post_capital_contribution`, `post_owner_drawing`, `void_partner_movement`, `void_worker_movement`, `void_equity_movement`, `void_profit_allocation`, `void_year_end_close`, `void_eod_close`, `void_reconciliation`
- **Receivables mini-wave:** `post_receivable_payment` (FX gain/loss)
- **Inventory mini-wave:** `void_inventory_transaction`
- **Balance (adjacent):** `calculate_account_balance`, `sync_account_balances`
- **Edit lifecycle (purchase):** `_create_purchase_payable`, `_update_purchase_payable`, `_sync_purchase_payable_lifecycle`

#### 4. Dead code found
- None in PS-P3 scope

#### 5. Future cleanup items (registered above)
- TD-PS-01 scope broadened: void services now own post-flag `session.commit()` in addition to kernel commits
- TD-PS-02 scope broadened: void/reversal shims add `current_company_required()`
- TD-PS-06/-07 unchanged; no new TD items in PS-P3

### PS-P2c Migration Cleanup (2026-06-13)

#### 1. Code to keep during FastAPI/React migration
- `services/posting.py` — `sync_company_cc_subledger`, `post_expense`, `post_payable_payment`, `post_purchase`, `resolve_purchase_debit_account`, `purchase_ref_type` (+ PS-P1/P2a/P2b kernels)
- app.py shims: `_sync_company_cc_subledger`, `post_expense`, `post_payable_payment`, `post_purchase`, `_resolve_purchase_debit_account`, `_purchase_ref_type`
- Tests: `tests/test_posting_service01_p2c_char.py` (unchanged), `tests/test_posting_service01_p2c1.py`, `tests/test_posting_service01_p2c2.py`, `tests/test_posting_service01_p2c3.py`

#### 2. Code likely to replace during FastAPI/React migration
- CC subledger + expense/purchase/payable-payment shims — direct service import at call sites
- `gl_company_id` + `ambient_company_id` split parameters — single explicit `company_id` once TD-PS-06/-07 fixed
- `_CC_NO_CARDS_MSG` and other pinned EN constants in service — i18n via API layer
- `reconciliation/company_card.py` still owns `post_cc_subledger_charge` leaves — sink in service calls them directly (acyclic)

#### 3. Dead code found
- None in PS-P2c scope

#### 4. Temporary Streamlit-only code
- `_sync_company_cc_subledger` underscore shim — internal callers (`_save_and_post_*`, edit paths) unchanged
- `_resolve_purchase_debit_account` / `_purchase_ref_type` shims — void/edit purchase paths still call underscore names
- `NAV_INVENTORY` default on `post_purchase` shim — service uses `_DEFAULT_PURCHASE_GL_DEBIT = "Inventory"`

#### 5. Future cleanup items (registered above)
- TD-PS-07 added PS-P2c session; TD-PS-06 scope broadened to cover sink ambient fallback; TD-PS-01–05 unchanged

### PS-P2b Migration Cleanup (2026-06-13)

#### 1. Code to keep during FastAPI/React migration
- `services/posting.py` — `resolve_payment_credit_account`, `post_payable_creation` (+ PS-P1/P2a kernels)
- app.py shims: `_resolve_payment_credit_account`, `post_payable_creation`
- Tests: `tests/test_posting_service01_p2b_char.py` (unchanged), `tests/test_posting_service01_p2b.py`

#### 2. Code likely to replace during FastAPI/React migration
- `_resolve_payment_credit_account` app shim — direct service import at expense/purchase/payable-payment call sites
- `gl_company_id` split parameter — single explicit `company_id` once TD-PS-06 fixed
- EN error string constants in service — i18n via API layer

#### 3. Dead code found
- None in PS-P2b scope

#### 4. Temporary Streamlit-only code
- `_resolve_payment_credit_account` underscore name retained for internal app callers
- `post_payable_creation` shim — transaction UI unchanged

#### 5. Future cleanup items (registered above)
- TD-PS-06 added PS-P2b session; TD-PS-01–05 unchanged

### PS-P2a Migration Cleanup (2026-06-05)

#### 1. Code to keep during FastAPI/React migration
- `services/posting.py` — `get_account_by_name`, `card_settlement_on`, `post_cash_sale`, `post_card_sale`, `post_credit_sale` (+ PS-P1 kernel)
- app.py shims for all five names (unchanged public signatures)
- Tests: `tests/test_posting_service01_p2a.py`; PS-P0 characterization unchanged through shims

#### 2. Code likely to replace during FastAPI/React migration
- app.py `get_account_by_name` shim — direct service import at remaining call sites (TD-PS-05)
- Internal `session.commit()` via `create_journal_entry` inside sales post_* (TD-PS-01)
- `registry.service.get_setting` inside `card_settlement_on` — settings service at API layer

#### 3. Dead code found
- None in PS-P2a scope

#### 4. Temporary Streamlit-only code
- `_card_settlement_on` app.py shim — UI/banking toggles still call the underscore name
- Sales post_* shims — Streamlit transaction pages unchanged

#### 5. Future cleanup items (registered above)
- TD-PS-05 added PS-P2a session; TD-PS-01–04 unchanged

---

## FUTURE-MIGRATION-AUDIT-01 (2026-06-13)

Independent architectural review (Claude) — baseline FastAPI/React readiness assessment. **Does not authorize migration implementation.**

**Migration readiness score:** **62 / 100** (historical baseline)

**Superseded for blocker/keystone/status truth by:** [DOCS_MIGRATION_CHECKPOINT_01.md](./DOCS_MIGRATION_CHECKPOINT_01.md) (DOCS-MIGRATION-CHECKPOINT-01, 2026-06).

| Finding | Detail (2026-06-13 baseline) | Updated (2026-06) |
|---------|------------------------------|-------------------|
| **Strength** | New `services/` modules FastAPI-ready — MIGRATION-READINESS-01 exemplars | Unchanged |
| **Main blocker (historical)** | `app.py` posting engine; PS-P2a sales only | **Resolved** — POSTING-SERVICE-01 complete |
| **Keystone (historical)** | POSTING-SERVICE-01 | **Complete** — see [POSTING_SERVICE_01_STATUS.md](./POSTING_SERVICE_01_STATUS.md) |

### Tracked migration tasks (FUTURE-MIGRATION-AUDIT-01)

| ID | Item | Priority | Status | When / trigger |
|----|------|----------|--------|----------------|
| **POSTING-SERVICE-01** | Extract GL posting engine from `app.py` (`create_journal_entry`, reversals, `post_*` wrappers) | **Critical** | **Complete** | PS-P0–P6-5 shipped; PS-P7 hardening deferred |
| **MONEY-DECIMAL-01** | `Float` → `Decimal` for money fields across models and services | High | **MD-04c+ ✅** · **MD-05-IMPL-1 ✅** · **IMPL-2 ✅** · **IMPL-3 ✅** · **IMPL-4 ✅** · **IMPL-5 ✅** — flag-gated cutover wired; PG **production** blocked | [MONEY_DECIMAL_04C_JE_FX_DECIMAL.md](./MONEY_DECIMAL_04C_JE_FX_DECIMAL.md); [MONEY_DECIMAL_05_NUMERIC_MIGRATION_PLAN.md](./MONEY_DECIMAL_05_NUMERIC_MIGRATION_PLAN.md) |
| **ALEMBIC-01** | Alembic revision chain replaces incremental `migrate_schema()` | Medium | **Complete** — P3.9-C no-op stub; Alembic-only | [P3_9_C_REMOVAL.md](./P3_9_C_REMOVAL.md) |
| **BANKING-SERVICE-01** | Extract banking subledger business logic to `services/` | High | **Partial** | `services/write_banking.py` manual API writes shipped; recon/import/balance ownership (TD-PS-08) open |
| **REPORTS-SERVICE-01** | Extract report queries/aggregations to read-only `services/` | Medium | **Partial** | Query layer in `services/read_*` (FASTAPI-P0); Streamlit presentation in `app.py` by design |
| **CONTEXT-AUDIT-01** | Audit `_erp()` / session-context coupling in `ui/`; plan injected context | Medium | Open | FastAPI Phase D; relates to TD-DSC-08, TD-UA-04, TD-SC-03/04 |

### Critical path (migration prep — DOCS-MIGRATION-CHECKPOINT-01)

1. ~~**AUTH-SESSION-02-IMPL-3**~~ ✅ — idle extension ([IMPL-3 doc](./AUTH_SESSION_02_IMPL_3.md); commit `ee57dc1`)
2. **BANKING-SERVICE-01** — extraction audit; balance ownership; `_app()` removal
3. ~~**P2-HARDEN-01**~~ ✅ — API `company_id` stamp audit closed ([closure doc](./P2_HARDEN_01_AUDIT_CLOSURE.md))
4. ~~**MONEY-DECIMAL-04c+**~~ ✅ — JE guard / FX Decimal boundary verified ([MD-04c doc](./MONEY_DECIMAL_04C_JE_FX_DECIMAL.md))
5. ~~**MONEY-DECIMAL-05-IMPL-5**~~ ✅ — flag-gated cutover (**IMPL-1 ✅** · **IMPL-2 ✅** · **IMPL-3 ✅** · **IMPL-4 ✅** · **IMPL-5 ✅**)
6. **P3.9** — phased `migrate_schema()` retirement (**✅ complete** — P3.9-A/B-CHAR/B/C)
7. ~~**PostgreSQL build + dual-run parity**~~ ✅ — Alembic PG test build + harness ([PG build doc](./POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md))
8. ~~**PostgreSQL runtime cutover prep**~~ ✅ — test-only SQLite→PG copy + gate parse-only ([prep doc](./POSTGRES_RUNTIME_CUTOVER_PREP.md))
9. ~~**Real SQLite→PG dry run**~~ ✅ — copy-only migration verified ([POSTGRES_REAL_DRY_RUN_20260616.md](./POSTGRES_REAL_DRY_RUN_20260616.md))
10. ~~**PostgreSQL production runtime cutover**~~ ✅ — flag-gated PG runtime wired; testing cutover verified ([cutover doc](./POSTGRES_PRODUCTION_CUTOVER.md)).
11. **React migration** — Phase D after API/service hardening.

**FastAPI foundation:** partial — P0–P2 exist; write routes feature-flagged; **not complete**. **PostgreSQL runtime:** production cutover ✅ (2026-06-16 testing); SQLite rollback preserved.

**Related roadmap:** [ROADMAP.md § FUTURE-MIGRATION-AUDIT-01](../ROADMAP.md#future-migration-audit-01--fastapi-readiness-audit) · [DOCS_MIGRATION_CHECKPOINT_01.md](./DOCS_MIGRATION_CHECKPOINT_01.md)

---

## P2-HARDEN-01 (2026-06-14)

Discovered during P2.9 closing write API — logged in [P2_AUDIT_01_LEDGER.md](./P2_AUDIT_01_LEDGER.md).

**Closed 2026-06-16:** H-01 matrix and H-02 fixture fidelity verified; H-03 silent auto-stamp **deferred/rejected**. No runtime changes. See [P2_HARDEN_01_AUDIT_CLOSURE.md](./P2_HARDEN_01_AUDIT_CLOSURE.md).

| ID | Item | Priority | Status | When / trigger |
|----|------|----------|--------|----------------|
| **P2-HARDEN-01** | **API `company_id` stamping audit** — explicit service-layer stamping verified for all P2 write paths; H-01 matrix + H-02 fixture fidelity green; H-03 silent auto-stamp **deferred/rejected** | High | **✅ Closed (2026-06-16)** | [P2_HARDEN_01_AUDIT_CLOSURE.md](./P2_HARDEN_01_AUDIT_CLOSURE.md) · tag `p2-harden-01-company-stamp-audit` |

**Related roadmap:** [ROADMAP.md § P2-HARDEN-01](../ROADMAP.md#p2-harden-01--company-stamp-audit)

---

## USER-ACCESS-01 (TD-UA)

| ID | Item | Priority | Status | When / trigger |
|----|------|----------|--------|----------------|
| **TD-UA-01** | **Service commits internally** — `set_override`, `clear_override`, `reset_to_template` call `session.commit()`; refactor to `flush()` + caller-owned transaction for FastAPI | Medium | Open | FastAPI Phase B |
| **TD-UA-02** | **Denied-attempt logging** — resolver returns `False` only; audit failed permission checks deferred | Low | Open | Security hardening |
| **TD-UA-03** | **Custom DB roles** — templates code-only in UA-P1; per-company role definitions deferred | Low | Open | Post UA-P1b |
| **TD-UA-04** | **Streamlit permission cache** — `_effective_perms_*` in `st.session_state`; replace with request-scoped context at API migration | Medium | Open | FastAPI Phase D |
| **TD-UA-05** | **`_PERMISSIONS` dict in app.py** — temporary re-export of `LEGACY_PERMISSION_MATRIX`; remove once all tests import registry/templates from service | Low | Open | After UA-P1b |

### UA-P1 Migration Cleanup (2026-06-13)

#### 1. Code to keep during FastAPI/React migration
- `models.UserPermissionOverride` — override schema; unique `(company_id, user_id, permission_key)`
- `services/user_access.py` — `PERMISSION_REGISTRY`, `PERMISSION_TEMPLATES`, `LEGACY_PERMISSION_MATRIX`, effective resolver, owner lockout guard, override CRUD
- Frozen DTOs: `PermissionRegistryEntry`, `PermissionOverrideView`, `EffectivePermissionsView`, `MutationResult`
- Tests: `tests/test_user_access01_permissions.py`, `tests/test_user_access01_models.py`
- `migrate_schema()` indexes for `user_permission_overrides`
- `_can(action)` signature unchanged — thin caller over `has_permission`

#### 2. Code likely to replace during FastAPI/React migration
- `_can()` Streamlit session cache (`_effective_perms_*`) — FastAPI dependency + JWT/session middleware
- `app._PERMISSIONS` re-export — API exposes `list_registry` / `template_definition` only
- Internal `session.commit()` in override mutations (TD-UA-01)
- `session.query()` ORM access — SQLAlchemy 2.0 `select()` (TD-MIG-05)

#### 3. Dead code found
- None in UA-P1 scope

#### 4. Temporary Streamlit-only code
- `_clear_permission_cache()` and `_effective_perms_{user}_{company}` keys in `app.py`
- `_PERMISSIONS` dict retained as backward-compat seed for tests reading `app._PERMISSIONS`
- No permission management UI (deferred to UA-P1b) — **shipped UA-P1b** `ui/permissions.py`

#### 5. Future cleanup items (registered above)
- TD-UA-01 through TD-UA-05 added this session

### UA-P1b Migration Cleanup (2026-06-13)

#### 1. Code to keep during FastAPI/React migration
- `ui/permissions.py` — `render_permissions_management`; calls `services.user_access` only
- Read APIs: `list_active_members`, `list_permission_audit`, `CompanyMemberView`, `PermissionAuditEntryView`
- `NAV_PERMISSIONS` nav key + Settings accordion wiring
- Tests: `tests/test_user_access01_ui_contract.py`
- Locale keys: `ua.*`, `nav.permissions` EN/TR

#### 2. Code likely to replace during FastAPI/React migration
- Streamlit selectbox/button mutation UX — React permission matrix UI
- `st.rerun()` after each mutation — API round-trip + client state refresh
- `erp._clear_permission_cache()` from UI — request-scoped cache invalidation at API layer
- Audit table rendered via `st.dataframe` — React data grid

#### 3. Dead code found
- None in UA-P1b scope

#### 4. Temporary Streamlit-only code
- `ui/permissions.py` — desktop-only; no mobile permission UI (by design)
- Provenance table built from `EffectivePermissionsView` frozensets in UI (presentation only)
- Permission labels fall back to title-cased key when `perm.*` locale missing

#### 5. Future cleanup items (registered above)
- TD-UA-01 through TD-UA-05 remain open; TD-UA-03 still deferred (no custom DB roles)

---

## STAFF-CAPTURE-01 (TD-SC)

| ID | Item | Priority | Status | When / trigger |
|----|------|----------|--------|----------------|
| **TD-SC-01** | **Injected posting seam** — `approve_expense_draft(..., post_fn=...)`; Streamlit wires `app.py` posting callables; replace with shared posting service | High | Open | FastAPI Phase B |
| **TD-SC-02** | **Posting function commit semantics** — injected `post_fn` may commit internally (legacy `app.py`); document transaction boundaries and test double-commit safety | Medium | Open | SC-P2 / FastAPI Phase B |
| **TD-SC-03** | **Streamlit attachment serving** — draft files on disk under `uploads/{company_id}/drafts/`; replace with FastAPI authenticated download endpoint | Medium | Open | SC-P1b UI / FastAPI Phase D |
| **TD-SC-04** | **Portal session routing** — capture-only allowlist dispatch in `main()` deferred to SC-P1 portal; replace with React route guards + API middleware | Medium | Open | SC-P1 portal / FastAPI Phase D |
| **TD-SC-05** | **Service commits internally** — draft mutations call `session.commit()`; refactor to `flush()` + caller-owned transaction for FastAPI | Medium | Open | FastAPI Phase B |

### SC-P1 Migration Cleanup (2026-06-13)

#### 1. Code to keep during FastAPI/React migration
- `models.ExpenseDraft`, `models.DraftAttachment` — spine + expense payload + posted-ref idempotency anchor
- `services/staff_capture.py` — lifecycle, attachment validation, permission checks, separation of duties, `approve_expense_draft` + `ExpensePostFn` injection
- Frozen DTOs: `ExpenseDraftInput`, `ExpenseDraftView`, `DraftAttachmentView`, `ExpensePostResult`, `MutationResult`
- SC permission keys in `services/user_access.py` (`STAFF_CAPTURE_PERMISSION_MATRIX` — SC-P1 subset)
- Tests: `test_staff_capture01_models.py`, `test_staff_capture01_drafts.py`, `test_staff_capture01_approval.py`
- `migrate_schema()` indexes for `expense_drafts`, `draft_attachments`

#### 2. Code likely to replace during FastAPI/React migration
- Injected `post_fn` from Streamlit — posting service extraction (TD-SC-01)
- Internal `session.commit()` in draft mutations (TD-SC-05)
- Disk path helper writing under `uploads_root` — object storage or signed URLs (TD-SC-03)
- `session.query()` ORM access — SQLAlchemy 2.0 `select()` (TD-MIG-05)

#### 3. Dead code found
- None in SC-P1 scope

#### 4. Temporary Streamlit-only code
- None in SC-P1 (service-only phase; no UI, portal, or inbox)
- Attachment warning on submit without receipt — policy only, not schema block
- `approve_expense_drafts` / `submit_expense_drafts` / `upload_receipts` registered in templates ahead of portal UI

#### 5. Future cleanup items (registered above)
- TD-SC-01 through TD-SC-05 added this session

### SC-P1b Migration Cleanup (2026-06-13)

#### 1. Code to keep during FastAPI/React migration
- `ui/staff_capture.py` — tab layout (submit · my submissions · inbox), permission gates, service-only mutations, `post_fn` injection at approve call site
- `app._staff_capture_post_expense_draft` — thin posting seam (TD-SC-01); maps `ExpenseDraftView` → `ExpenseRecord` + `_save_and_post_expense_record`
- Nav wiring: `NAV_STAFF_EXPENSE_CAPTURE`, `registry/nav_keys.py`, `nav_labels.py`, locales `sc.*` / `nav.staff_expenses`
- Tests: `tests/test_staff_capture01_ui_contract.py`

#### 2. Code likely to replace during FastAPI/React migration
- `_erp()` lazy `import app` in UI — injected context (CONTEXT-AUDIT-01)
- `st.session_state` form keys (`sc_*`) — React form state
- `st.file_uploader` / `st.download_button` attachment UX — authenticated API + signed URLs (TD-SC-03)
- Category/subcategory read via `erp.cq(TransactionCategory)` in UI — read API on service or shared catalog helper
- `_staff_capture_post_expense_draft` in `app.py` — POSTING-SERVICE-01 shared module

#### 3. Dead code found
- None in SC-P1b scope

#### 4. Temporary Streamlit-only code
- `app._staff_capture_post_expense_draft` — posting adapter only; no new GL rules
- Attachment download reads disk via `resolve_data_path` — no authenticated serving yet (TD-SC-03)
- Portal gate / capture-only session routing still deferred (TD-SC-04)

#### 5. Future cleanup items (registered above)
- TD-SC-01 through TD-SC-05 unchanged; TD-SC-03 partially exercised by SC-P1b download buttons

---

## RC-P1 / Recipe Costing (TD-RC)

| ID | Item | Priority | Status | When / trigger |
|----|------|----------|--------|----------------|
| **TD-RC-01** | **Service commits internally** — `create_ingredient`, `save_recipe`, `bulk_update_costs`, etc. call `session.commit()`; refactor to `flush()` + caller-owned transaction for FastAPI | Medium | Open | FastAPI Phase B |
| **TD-RC-02** | **Error surface** — plain English `error` on `MutationResult`; add stable `error_code` (e.g. `RC_CYCLE_DETECTED`) for React/FastAPI | Medium | Open | Before FastAPI exposure |
| **TD-RC-03** | **Float money** — ingredient `cost_per_base_unit` and computed breakdown use `float`; migrate to `Decimal` with TD-MIG-04 | Low | Open | Global migration prep |
| **TD-RC-04** | **Unit registry** — hardcoded `_UNIT_FACTORS` map; optional registry/settings for locale-specific units | Low | Open | RC-P2+ |
| **TD-RC-05** | **Dual `compute_recipe_cost` dispatch** — pure graph vs DB via `isinstance(Session)`; split into `rollup_recipe_cost` + `compute_recipe_cost` at API migration | Low | Open | FastAPI Phase B |
| **TD-RC-06** | **Roadmap / spec drift** — add `RECIPE_COSTING_01_SPEC.md` and ROADMAP phase table when RC-P2+ lands | Low | Open | RC-P1b UI shipped 2026-06-05; spec file still pending |
| **TD-RC-09** | **Widget session keys** — `rc_*` draft line state and recipe editor keys are Streamlit-only; React form state replaces at API migration | Low | Open | RC-P1b UI |
| **TD-RC-10** | **UI `_erp()` lazy import** — `ui/recipe_costing.py` reaches into `app.py` for `_t`, `_can`, `amount_input`, `current_company_required`; replace with injected context or `ui/context.py` | Medium | Open | FastAPI Phase D |
| **TD-RC-11** | **Menu price history** — append-only `MenuPriceHistory`; no soft-delete or price void; FastAPI may need explicit price correction workflow | Low | Open | RC-P2A |
| **TD-RC-12** | **Tax rate source** — `_get_company_tax_rate_pct` reads `CompanySetting.key == "tax_rate"`; align with registry `accounting.default_tax_rate` single source at API migration | Low | Open | RC-P2A |

### RC-P2A Migration Cleanup (2026-06-05)

#### 1. Code to keep during FastAPI/React migration
- `models.MenuItem`, `models.MenuPriceHistory` — menu schema; profitability computed on demand only
- RC-P2A service API in `services/recipe_costing.py`: menu CRUD, price history, pure profitability helpers, DTOs `MenuItemView`, `MenuPriceView`, `MenuProfitabilityView`
- `ui/recipe_costing.py` — `render_recipe_menu_items` thin renderer
- Registry: `NAV_RC_MENU_ITEMS`, locales `rc.menu.*`, `nav.rc_menu_items`
- Tests: `tests/test_recipe_costing_menu_models.py`, `tests/test_recipe_costing_menu_service.py`, UI contract extensions
- `migrate_schema()` indexes for `menu_items`, `menu_price_history`

#### 2. Code likely to replace during FastAPI/React migration
- `ui/recipe_costing.py` menu section → React menu profitability module
- `session.query(CompanySetting)` tax lookup — shared settings service
- Internal `session.commit()` in menu mutations (TD-RC-01)
- `st.number_input` for target food cost % — React form control bound to API query param

#### 3. Dead code found
- None

#### 4. Temporary Streamlit-only code
- `rc_menu_target_fc`, `rc_add_menu_*`, `rc_edit_menu_*`, `rc_menu_edit_pick` session keys
- Target food cost % widget (parameter only — math stays in service)

#### 5. Future cleanup items (registered above)
- TD-RC-11, TD-RC-12 added this session

### RC-P1b Migration Cleanup (2026-06-05)

#### 1. Code to keep during FastAPI/React migration
- All RC-P1 items (models, service, tests)
- `ui/recipe_costing.py` — three thin renderers; restaurant-friendly tree display
- Registry nav keys, permissions, EN/TR `rc.*` locales
- `tests/test_recipe_costing_ui_contract.py`

#### 2. Code likely to replace during FastAPI/React migration
- `ui/recipe_costing.py` → React recipe/ingredient modules
- `_erp()` lazy `app.py` import in UI — shared `ui/context.py` or API props
- `rc_*` Streamlit session keys for draft recipe lines
- Internal `session.commit()` in service (TD-RC-01)

#### 3. Dead code found
- None

#### 4. Temporary Streamlit-only code
- `ui/recipe_costing.py` entire module
- `rc_draft_lines`, `rc_loaded_recipe_id`, `rc_recipe_pick` session keys
- `_recipe_tree_markdown` presentation (reimplement in React)

#### 5. Future cleanup items (registered above)
- TD-RC-09, TD-RC-10 added this session

### RC-P1 Migration Cleanup (2026-06-05)

#### 1. Code to keep during FastAPI/React migration
- `models.Ingredient`, `models.Recipe`, `models.RecipeLine` — core schema; sub-recipe via `RecipeLine.sub_recipe_id` only (no SubRecipe table)
- `services/recipe_costing.py` — unit conversion, validation, cost rollup, `where_used`, CRUD mutations
- Frozen DTOs: `IngredientView`, `RecipeLineCost`, `RecipeCostBreakdown`, `WhereUsedEntry`, `ValidationResult`, `MutationResult`
- Tests: `tests/test_recipe_costing_service.py`, `tests/test_recipe_costing_models.py`
- `migrate_schema()` indexes for `ingredients`, `recipes`, `recipe_lines`

#### 2. Code likely to replace during FastAPI/React migration
- `compute_recipe_cost` Session dispatch — split into explicit API handler + pure `rollup` import
- `session.query()` style ORM access — SQLAlchemy 2.0 `select()` (TD-MIG-05)
- Internal `session.commit()` in service mutations — FastAPI dependency-injected unit of work
- `AuditLog` string `description` JSON blobs — structured audit event schema

#### 3. Dead code found
- None in RC-P1 scope (greenfield module)

#### 4. Temporary Streamlit-only code
- None — RC-P1 deliberately ships no UI, no `app.py` wiring, no Streamlit session keys

#### 5. Future cleanup items (registered above)
- TD-RC-01 through TD-RC-06 added this session

---

## POSTING-SERVICE-01 (TD-POSTING)

| ID | Item | Priority | Status | When / trigger |
|----|------|----------|--------|----------------|
| **TD-POSTING-01** | **`app.py` shims after extraction** — keep thin re-export wrappers (`post_cash_sale`, `void_sale`, `_staff_capture_post_expense_draft`, etc.) in `app.py` until Streamlit pages and `reconciliation/` callers migrate to `services/posting.py` | High | Open | PS-P1 extraction |
| **TD-POSTING-02** | **Internal commit behavior** — `create_journal_entry`, most `void_*`, `sync_account_balances`, `log_audit`, and several `post_*` paths call `session.commit()` internally; refactor to `flush()` + caller-owned transaction for FastAPI | **Critical** | Open | PS-P1 / FastAPI Phase B |
| **TD-POSTING-03** | **ORM return deprecation** — posting helpers return ORM objects (`JournalEntry`, movement rows) or bare IDs inconsistently; introduce frozen DTOs (`JournalEntryView`, `PostingResult`) at service boundary | Medium | Open | PS-P1 API surface |
| **TD-POSTING-04** | **Rollback semantics difference** — `create_journal_entry` rolls back on guard/balance failure; outer `post_*` / `void_*` callers may leave partial flushes; document and unify transaction boundaries during extraction | High | Open | PS-P1 extraction |
| **TD-POSTING-05** | **Year-end guard location** — YEC lock centralized in `_entry_date_posting_blocked` for JE posting but duplicated inline in `post_partner_movement`, `post_worker_movement`, and related void guards; consolidate in posting service before PS-P6 extraction | Medium | Open | PS-P6 planning / pre-extraction |
| **TD-POSTING-06** | **Reconciliation `_app` imports** — `reconciliation/company_card.py` and `reconciliation/match_post.py` lazy-import `app` for `create_journal_entry`; replace with `services/posting.py` import to break circular dependency | High | Open | PS-P1 / BANKING-SERVICE-01 |

### DRY UI Refactor — Shared Utilities (2026-06-16)

#### 1. Code to keep during FastAPI/React migration
- `ui/crud_helpers.py` — `void_confirmation_widget`, `attachment_section_selector`
- `ui/report_helpers.py` — `growth_comparison_kpi`
- These are **Streamlit-only** UI helpers and would be replaced by React components during migration, but serve as documentation of the interaction patterns needed.

#### 2. Code likely to replace during FastAPI/React migration
- `void_confirmation_widget` → React confirmation dialog + API endpoint
- `growth_comparison_kpi` → React dashboard card + API data endpoint
- `attachment_section_selector` → React file-upload component + API

#### 3. Dead code found
- None (all 10 refactored call sites now delegate to shared utilities)

#### 4. Temporary Streamlit-only code
- `ui/crud_helpers.py` and `ui/report_helpers.py` — Streamlit widget helpers; will be replaced by React equivalents during migration but pattern/API is transferable.

#### 5. Future cleanup items
- Additional void patterns in payables-payment panel could benefit from further extraction (lower priority — has extra pay-key conditional).

---

### PS-P0 Migration Cleanup (2026-06-05)

#### 1. Code to keep during FastAPI/React migration
- `app.py` posting engine (unchanged in PS-P0) — characterized baseline for extraction
- `docs/POSTING_SERVICE_01_CASCADE_MAP.md` — cascade / commit-behavior map
- Tests: `tests/test_posting_service01_characterization.py`
- Existing guards: `_entry_date_posting_blocked`, `create_reversing_journal_entry`, `reverse_journal_entries_for`

#### 2. Code likely to replace during FastAPI/React migration
- Entire posting/void block in `app.py` → `services/posting.py` (POSTING-SERVICE-01)
- `reconciliation/*` lazy `_app()` imports → direct posting service (TD-POSTING-06)
- Internal `session.commit()` in posting paths (TD-POSTING-02)
- `ChartOfAccounts.balance` cache maintenance — clarify read path vs write path in service API

#### 3. Dead code found
- None in PS-P0 scope (characterization only)

#### 4. Temporary Streamlit-only code
- `app._staff_capture_post_expense_draft` — posting adapter pending shared service (TD-SC-01 / TD-POSTING-01)
- All `post_*` / `void_*` remain monolith-hosted until PS-P1

#### 5. Future cleanup items (registered above)
- TD-POSTING-01 through TD-POSTING-06 added PS-P0 session

---

## Error Handling (TD-ERR)

| ID | Item | Priority | Status | Notes |
|----|------|----------|--------|-------|
| **TD-ERR-01** | ~55 remaining `except Exception:` blocks in `app.py` still use broad catches (idempotent migrations, UI rendering, and startup code) — narrow to specific types where feasible | Low | **Open** | Most are in migration ALTER TABLE blocks (intentionally idempotent) or deeply nested UI rendering; 25+ highest-impact blocks addressed 2026-06-16 |
| **TD-ERR-02** | Centralize structured logging config (level, format, handlers) so `_log.warning`/`_log.debug` calls added in error-handling audit are visible in production | Medium | **Open** | Currently relies on Python root logger defaults |

---

## Reference implementation

**DSC-P1** (`services/daily_sales_close.py`) is the first module built under:

- [ARCHITECTURE-PROTECTION-01](../ROADMAP.md#architecture-protection-01--service-first-development-rule)
- [VENDOR-NEUTRAL-01](../ROADMAP.md#vendor-neutral-01--vendor-neutral-architecture-rule)
- [MIGRATION-READINESS-01](../ROADMAP.md#migration-readiness-01--fastapireact-ready-service-checklist)

**RC-P1** (`services/recipe_costing.py`) follows the same pattern — second reference implementation under MIGRATION-READINESS-01.

**UA-P1** (`services/user_access.py`) and **SC-P1** (`services/staff_capture.py`) extend the pattern — permission resolver and staff capture with injected `post_fn` posting seam.

Audit source: DSC-P1 migration readiness review (2026-06-05); **FUTURE-MIGRATION-AUDIT-01** independent FastAPI readiness audit (2026-06-13) — score **62/100** (historical). **Register truth:** [DOCS_MIGRATION_CHECKPOINT_01.md](./DOCS_MIGRATION_CHECKPOINT_01.md) (2026-06) — POSTING-SERVICE-01 complete; REPORTS/BANKING partial.

---

*Update this file when debt items are added, scheduled, or resolved.*
