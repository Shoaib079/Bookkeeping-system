# FASTAPI-P2.0 — Write API Inventory & Contract Plan

**Mode:** Documentation + contract inventory only. No write endpoints, no accounting behavior changes, no service refactors, no Streamlit UI changes.
**Inputs:** `app.py` write/void/post surfaces, `services/posting.py`, `services/audit.py`, `services/commit_modes.py`, `services/staff_capture.py`, `services/daily_sales_close.py`, `services/user_access.py`, `reconciliation/*`, existing P0/P1 docs and tests.
**State:** P1.3e complete — read endpoints use `Authorization: Bearer` + `X-Company-Id`; `get_request_context` DB-resolves membership role and permissions. Streamlit remains primary UI.

---

## Scope

This document inventories **every current accounting write action** that will eventually become a FastAPI write endpoint, and defines the **contract plan** for exposing them without changing persisted behavior.

Covered:

- GL posting and reversal (sales, expenses, purchases, payables, receivable payments, bank, equity, partner/worker movements)
- Void cascades and entity flag mutations
- Reconciliation match/post and statement import side effects
- Period close, profit allocation, year-end close
- Supporting admin writes that touch accounting boundaries (staff capture approval → expense post, external sales verification, permission overrides)

Not covered here (later P2.x admin slices or out of accounting-write scope):

- Pure UI prefs (theme, locale, landing) unless they gate accounting
- Backup/restore file operations
- Chart-of-accounts seed migrations (startup-only)

---

## Non-goals

- **No write endpoints in P2.0** — inventory and contract only
- **No accounting logic moves** — services stay where they are until each P2 slice
- **No Streamlit removal** — UI keeps calling existing shims during migration
- **No PostgreSQL / React** — same SQLite + SQLAlchemy models
- **No licensing / payment / subscription gates** on API auth (local/self-hosted use remains unrestricted)
- **No request-body `company_id`** — company scope stays header + membership validated per request
- **No hard deletes** of posted accounting records — void + reversing JE only

---

## Core invariants

These apply to **every** future write endpoint:

| Invariant | Rule |
|-----------|------|
| **No GET commits** | Read routes remain flush-only; write routes commit at boundary only |
| **JWT RequestContext** | Identity from bearer token; `get_request_context` builds permissions from DB |
| **X-Company-Id** | Active company is explicit per request; re-validated membership every call |
| **Never trust company_id from request body** | Body may carry entity ids; tenant scope comes from headers + membership |
| **Never delete accounting records** | Void flags + reversing journal entries; no `DELETE` on financial rows |
| **Void → reverse → audit** | Reversal JE(s) first (where applicable), entity flags, cascade side effects, one audit row |
| **Preserve error strings** | `ValueError`, `PermissionDenied`, `MatchPostError`, guard messages unchanged at boundary |
| **Preserve return contracts** | Bool voids, `str` close-family returns, DTOs from `services/posting.py` helpers |
| **Preserve audit behavior** | `record_audit` / `log_audit` action + entity_type + description semantics |
| **Boundary commit ownership** | Flip per-family via `services/commit_modes.py`; dual-run parity before production |
| **Feature flags for risky rollout** | `COMMIT_MODE_<FAMILY>` env + per-slice API feature flags before default-on |
| **Streamlit remains functional** | Parallel paths: UI shims + API routes call same services until UI migrates |

---

## Write endpoint order

Recommended migration sequence (safest → riskiest). Each slice adds POST/PATCH routes only after read auth (P1.3e) and boundary commit parity for that family.

| Slice | Theme | Rationale |
|-------|-------|-----------|
| **P2.1** | Sales write API | Single-JE posts; characterized; `post_cash_sale` boundary scaffold exists |
| **P2.2** | Expense write API | Similar to sales; CC subledger split-commit documented |
| **P2.3** | Purchase / payable write API | Credit purchase → payable row; supplier payment |
| **P2.4** | Receivable payment write API | Extra sale-balance mutation + FX lines |
| **P2.5** | Void API | Unified void routes; highest cascade variance — after forward posts proven |
| **P2.6** | Partner / equity / worker write API | Multi-entity (movement + bank txn + JE); TD-POSTING-05 YEC guards |
| **P2.7** | Banking write API | Deposits/withdrawals/transfers; balance ownership asymmetry (TD-PS-08) |
| **P2.8** | Reconciliation write API | Per-row commits today; `match_post` lazy `app` imports |
| **P2.9** | Closing / allocation / YEC API | Multi-step workflows; period lock side effects |

---

## Write action inventory

Columns:

- **UI entry** — primary Streamlit surface today
- **Service** — target function (shim delegates here when extracted)
- **RequestContext** — permission keys / role expectations
- **company_id** — how tenant is supplied today vs API target
- **Commit mode** — `commit_modes` family + internal vs boundary today
- **Audit** — action / entity_type on success
- **Return** — caller-visible contract
- **Tests** — representative existing coverage
- **Proposed endpoint** — future HTTP shape (draft)
- **Risk** — Low / Medium / High

### P2.1 — Sales write API

| Action | UI entry | Service | RequestContext | company_id source | Commit mode | Audit | Return | Tests | Proposed endpoint | Risk |
|--------|----------|---------|----------------|-------------------|-------------|-------|--------|-------|-------------------|------|
| Create + post cash sale | `render_add_transaction` (Sale/Cash), `render_sales` | `post_cash_sale` | `create_transaction`; membership role from DB | `cq(session, …)` / shim `current_company_required()` | `post_cash_sale` family; kernel internal + audit | `Create` / `Sale` | `JournalEntry` / `PostingResult` DTO | `test_posting_service01_p2a.py`, `test_fastapi_p0_commit_ownership_cash_sale.py`, `test_posting_service01_characterization.py` | `POST /api/v1/sales` (create row) + `POST /api/v1/sales/{id}/post-cash` | Low |
| Create + post card sale | Same | `post_card_sale` | same | same | same (no dedicated family flag yet — maps to `sale`) | same | same | `test_posting_service01_p2a.py`, `test_phase18_mvp1.py` | `POST /api/v1/sales/{id}/post-card` | Low |
| Create + post credit sale | Same | `post_credit_sale` | same | same | same | same | same | `test_posting_service01_p2a.py` | `POST /api/v1/sales/{id}/post-credit` | Low |
| Sale entity persist (pre-post) | `render_add_transaction` save path | `app.py` direct `Sale` insert | `create_transaction` | ambient `cq` | UI/session `commit` | `Create` / `Sale` | sale id | UX tests, `test_ux04a_post_save_retention.py` | `POST /api/v1/sales` (draft/save) | Medium — split save vs post |

### P2.2 — Expense write API

| Action | UI entry | Service | RequestContext | company_id source | Commit mode | Audit | Return | Tests | Proposed endpoint | Risk |
|--------|----------|---------|----------------|-------------------|-------------|-------|--------|-------|-------------------|------|
| Save + post expense | `render_add_transaction` (Expense), `render_expenses`, `_save_and_post_expense_record` | `post_expense` | `create_transaction` | ambient / explicit in shim | `post_expense` family | `Create`/`Post` / `ExpenseRecord` | bool / expense id | `test_posting_service01_p2c2.py`, `test_fastapi_p0_commit_ownership_expense.py`, `test_cc_expense_form.py` | `POST /api/v1/expenses` + `POST /api/v1/expenses/{id}/post` | Medium — CC subledger split-commit |
| Staff draft create | `render_staff_expense_capture` | `staff_capture.create_expense_draft` | `submit_expense_drafts` | explicit `company_id` arg | service `commit` | draft audit | `MutationResult` | `test_staff_capture01_drafts.py` | `POST /api/v1/expense-drafts` | Medium |
| Staff draft submit/approve → post | Staff capture approval UI | `approve_expense_draft` → posting | `approve_expense_drafts` | explicit | service `commit` | `Approve` | `MutationResult` | `test_staff_capture01_approval.py` | `POST /api/v1/expense-drafts/{id}/approve` | High — multi-step workflow |

### P2.3 — Purchase / payable write API

| Action | UI entry | Service | RequestContext | company_id source | Commit mode | Audit | Return | Tests | Proposed endpoint | Risk |
|--------|----------|---------|----------------|-------------------|-------------|-------|--------|-------|-------------------|------|
| Save + post purchase | `render_add_transaction` (Purchase), `render_purchases` | `post_purchase` | `create_transaction` | ambient | `post_purchase` family | `Create` / `Purchase` | JE / bool | `test_posting_service01_p2c3.py`, `test_fastapi_p0_commit_ownership_purchase_payable.py` | `POST /api/v1/purchases` + `POST /api/v1/purchases/{id}/post` | Medium — credit → payable row |
| Create payable (credit purchase) | Purchase save path | `_create_purchase_payable` (`app.py`) | `create_transaction` | ambient | inline with purchase | `Create` / `Payable` | `Payable` | `test_posting_service01_p2c3.py` | internal to purchase post or `POST /api/v1/payables` | Medium |
| Post payable creation GL | Payables UI (legacy) | `post_payable_creation` | `create_transaction` | shim explicit | `purchase_payable` | `Post` / `Payable` | JE | `test_posting_service01_p2b.py` | `POST /api/v1/payables/{id}/post-creation` | Low |
| Supplier payment | `render_add_transaction` (Supplier Payment) | `post_payable_payment` | `create_transaction` | ambient | `post_payable_payment` family | `Payment` / `Payable` | JE | `test_posting_service01_p2c2.py`, `test_fastapi_p0_commit_ownership_purchase_payable.py` | `POST /api/v1/payables/{id}/payments` | Medium — CC sink `reference_id=je.id` |

### P2.4 — Receivable payment write API

| Action | UI entry | Service | RequestContext | company_id source | Commit mode | Audit | Return | Tests | Proposed endpoint | Risk |
|--------|----------|---------|----------------|-------------------|-------------|-------|--------|-------|-------------------|------|
| Customer payment / AR apply | `render_add_transaction` (Customer Payment) | `post_receivable_payment` | `create_transaction` | ambient | `post_receivable_payment` family (2 commits internal) | `Payment` / `Sale` | payment result DTO | `test_posting_service01_p5_1.py`, `test_fastapi_p0_commit_ownership_receivable_payment.py` | `POST /api/v1/sales/{id}/payments` | Medium — sale balance + FX |

### P2.5 — Void API

| Action | UI entry | Service | RequestContext | company_id source | Commit mode | Audit | Return | Tests | Proposed endpoint | Risk |
|--------|----------|---------|----------------|-------------------|-------------|-------|--------|-------|-------------------|------|
| Void sale | Transaction history void dialogs | `void_sale` | `void_transaction` | shim `current_company_required()` | `void_cascade` family | `Void` / `Sale` | `bool` | `test_posting_service01_p3_2b.py`, `test_posting_service01_p3_2b_char.py`, `test_fastapi_p0_commit_ownership_voids.py` | `POST /api/v1/sales/{id}/void` | High — multi ref_type reversal |
| Void expense | Expenses / history | `void_expense` | `void_transaction` | shim explicit | `void_cascade` | `Void` / `ExpenseRecord` | `bool` / void DTO | `test_posting_service01_p3_2a.py`, commit ownership voids | `POST /api/v1/expenses/{id}/void` | High — CC subledger |
| Void purchase | Purchases / history | `void_purchase` | `void_transaction` | shim explicit | `void_cascade` | `Void` / `Purchase` | `bool` | `test_posting_service01_p3_3b.py`, `test_card_purchase_void_edit.py` | `POST /api/v1/purchases/{id}/void` | High — linked payable cascade |
| Void payable | Payables UI | `void_payable` | `void_transaction` | shim explicit | `void_cascade` | `Void` / `Payable` | `bool` | `test_posting_service01_p3_2a_char.py` | `POST /api/v1/payables/{id}/void` | High |
| Void bank txn | Banking UI | `void_bank_transaction` | `void_transaction` + banking perm | shim explicit | `void_cascade` | `Void` / `BankTransaction` | `bool` | `test_posting_service01_p4_2.py`, `test_posting_service01_p4_char.py` | `POST /api/v1/bank-transactions/{id}/void` | High — paired transfer cascade |
| Void inventory txn | Inventory UI | `void_inventory_transaction` | `manage_inventory` | ambient | `void_cascade` | `Void` / `InventoryTransaction` | `bool` | `test_posting_service01_p5_2.py` | `POST /api/v1/inventory-transactions/{id}/void` | Medium — no GL |
| Void equity movement | Banking / equity flows | `void_equity_movement` | `post_equity_movement` / void perm | shim explicit | `void_cascade` | `Void` / `EquityMovement` | `bool` | `test_posting_service01_p5_3.py` | `POST /api/v1/equity-movements/{id}/void` | High |
| Void reconciliation | Cash recon UI | `void_reconciliation` | `void_reconciliation` | explicit `owner_id` param | `void_cascade` | `Void` / `DailyCashReconciliation` | `str` (empty=ok) | `test_posting_service01_p5_4.py`, `test_cash_reconciliation.py` | `POST /api/v1/reconciliations/{id}/void` | Medium |
| Void EOD close | EOD UI | `void_eod_close` | `void_eod` | explicit `owner_id` | `void_cascade` | `Void` / `EndOfDayClose` | `str` | `test_posting_service01_p5_4_char.py` | `POST /api/v1/eod-closes/{id}/void` | Medium |
| Void year-end close | YEC UI | `void_year_end_close` | `void_year_end_close` | explicit `voider_id` | `void_cascade` | `VoidYearEndClose` / `YearEndClose` | `str` | `test_year_end_close.py`, `test_posting_service01_p5_4_char.py` | `POST /api/v1/year-end-closes/{id}/void` | High |

### P2.6 — Partner / equity / worker write API

| Action | UI entry | Service | RequestContext | company_id source | Commit mode | Audit | Return | Tests | Proposed endpoint | Risk |
|--------|----------|---------|----------------|-------------------|-------------|-------|--------|-------|-------------------|------|
| Create partner | Partner accounts UI | `create_partner` (`app.py`) | `manage_partners` | ambient | app `commit` | `Create` / `Partner` | partner id | partner tests | `POST /api/v1/partners` | Low |
| Post partner movement | Partner UI | `post_partner_movement` | `post_partner_movement` | shim explicit | `post_partner_movement` family | `Post` / `PartnerMovement` | movement id | `test_posting_service01_p6_*.py`, `test_fastapi_p0_commit_ownership_movements.py` | `POST /api/v1/partners/{id}/movements` | High — bank txn + JE + YEC guard |
| Void partner movement | Partner UI | `void_partner_movement` | `void_partner_movement` | explicit `voider_id` | `void_cascade` | `Void` / `PartnerMovement` | `str` | `test_posting_service01_p6_2.py` | `POST /api/v1/partner-movements/{id}/void` | High |
| Create worker | Workers UI | `create_worker` | `manage_workers` | ambient | app `commit` | `Create` / `Worker` | worker id | `test_workers.py` | `POST /api/v1/workers` | Low |
| Post worker movement | Workers UI | `post_worker_movement` | `post_worker_movement` | shim explicit | `post_worker_movement` family | `Post` / `WorkerMovement` | movement id | `test_workers.py`, commit ownership movements | `POST /api/v1/workers/{id}/movements` | High |
| Void worker movement | Workers UI | `void_worker_movement` | `void_worker_movement` | explicit | `void_cascade` | `Void` / `WorkerMovement` | `str` | `test_workers.py` | `POST /api/v1/worker-movements/{id}/void` | High |
| Post capital contribution | Banking / equity UI | `post_capital_contribution` | `post_equity_movement` | shim explicit | `post_equity_movement` family | `Create` / `EquityMovement` | JE | `test_posting_service01_p5_3.py`, commit ownership movements | `POST /api/v1/equity/capital-contributions` | Medium |
| Post owner drawing | Same | `post_owner_drawing` | `post_equity_movement` | shim explicit | `post_equity_movement` family | same | JE | same | `POST /api/v1/equity/owner-drawings` | Medium |
| Post salary | Add transaction / payroll | `post_salary` | `create_transaction` | ambient | `sale`/`expense` adjacent | `Post` / `Salary` | JE | `test_posting_service01_p5_3.py` | `POST /api/v1/salaries` | Low |

### P2.7 — Banking write API

| Action | UI entry | Service | RequestContext | company_id source | Commit mode | Audit | Return | Tests | Proposed endpoint | Risk |
|--------|----------|---------|----------------|-------------------|-------------|-------|--------|-------|-------------------|------|
| Post bank deposit/withdrawal | `render_add_transaction` (Bank), Banking UI | `post_bank_transaction` | `manage_banking` | ambient + caller balance delta in UI | `bank_transaction` family | `Create` / `BankTransaction` | JE | `test_posting_service01_p4_1.py`, `test_phase18_mvp1.py` | `POST /api/v1/bank-transactions` + post | High — TD-PS-08 balance in UI |
| Post bank transfer | Banking UI | `post_bank_transfer` | `manage_banking` | ambient | `bank_transaction` | same | JE or no-op | `test_posting_service01_p4_char.py` | `POST /api/v1/bank-transfers` | High — paired legs |
| CC bill payment | Banking / CC UI | `post_credit_card_bill_payment` | `manage_banking` | explicit in recon | per-row internal commits | `Payment` | JE + bank txns | `test_cc_bill_payment_void.py`, `test_phase18_mvp5.py` | `POST /api/v1/credit-card/bill-payments` | High |
| Void CC bill payment | CC UI | `void_credit_card_bill_payment` | `void_transaction` | explicit | recon commits | `Void` | reversal | `test_cc_bill_payment_void.py` | `POST /api/v1/credit-card/bill-payments/{id}/void` | High |

### P2.8 — Reconciliation write API

| Action | UI entry | Service | RequestContext | company_id source | Commit mode | Audit | Return | Tests | Proposed endpoint | Risk |
|--------|----------|---------|----------------|-------------------|-------------|-------|--------|-------|-------------------|------|
| Import bank statement | Banking recon UI | `reconciliation.statement_import.import_bank_statement_file` | `import_bank_statement` | explicit `company_id` | per-import commits | `Upload` | import id | `test_phase18_mvp2.py` | `POST /api/v1/banking/statement-imports` | Medium |
| Import settlement file | Settlement UI | `settlement_import.import_settlement_statement_file` | `import_bank_statement` | explicit | per-import commits | `Upload` | import id | `test_phase18_mvp4.py` | `POST /api/v1/banking/settlement-imports` | Medium |
| Match post deposit clearing | Recon match UI | `match_post.post_deposit_clearing_match` | `manage_banking` | explicit row context | `reconciliation` family | `Post` / `BankStatementRow` | row state | `test_phase18_mvp3.py`, `test_fastapi_p0_commit_ownership_reconciliation.py` | `POST /api/v1/banking/statement-rows/{id}/match/deposit-clearing` | High — lazy `_app()` |
| Match post generic deposit | Same | `post_generic_deposit` | same | explicit | `reconciliation` | same | same | same | `POST .../match/generic-deposit` | High |
| Match post partner/worker/equity | Statement recon tabs | `post_partner_statement_match`, `post_worker_statement_match`, `post_equity_statement_match` | view/post perms | explicit | `reconciliation` | `Post` | JE + btxn | `test_phase18_mvp5.py` | `POST .../match/{kind}` | High |
| Match post vendor / bank charge | Same | `post_vendor_outflow`, `post_bank_charge_outflow` | same | explicit | `reconciliation` | same | same | `test_phase18_mvp4.py` | `POST .../match/vendor-outflow` | High |
| Submit / approve / reject cash recon | `NAV_CASH_RECONCILIATION` | `app.py` recon workflow | `submit/approve/reject_reconciliation` | ambient | app commits | `Submit`/`Approve`/`Reject` | status | `test_cash_reconciliation.py` | `POST /api/v1/cash-reconciliations/{id}/submit` etc. | Medium |
| CC subledger charge (sink) | Called from expense/purchase/payment posts | `company_card.post_cc_subledger_charge` | indirect | explicit | flush-only sink | — | subledger row | `test_cc_subledger_sync.py`, `test_posting_service01_p2c_char.py` | internal — not standalone API | Medium |

### P2.9 — Closing / allocation / YEC API

| Action | UI entry | Service | RequestContext | company_id source | Commit mode | Audit | Return | Tests | Proposed endpoint | Risk |
|--------|----------|---------|----------------|-------------------|-------------|-------|--------|-------|-------------------|------|
| Close fiscal period | Fiscal periods UI | `close_fiscal_period` | `close_fiscal_period` | explicit/shim | `period_close` family | `PeriodClose` / `FiscalPeriod` | period close DTO | period tests, `test_fastapi_p0_commit_ownership_close_allocation.py` | `POST /api/v1/fiscal-periods/{id}/close` | High — PeriodClose exempt from lock |
| Allocate profit | Partner allocation UI | `allocate_profit_to_partners` | `allocate_profit` | explicit | `profit_allocation` family | `ProfitAllocation` | allocation rows | `test_posting_service01_p6_*.py`, commit ownership close | `POST /api/v1/profit-allocations` | High |
| Void profit allocation | Partner UI | `void_profit_allocation` | `void_profit_allocation` | explicit | `void_cascade` | `Void` | `str` | `test_posting_service01_p6_2.py` | `POST /api/v1/profit-allocations/{id}/void` | High |
| Perform year-end close | YEC wizard | `perform_year_end_close` | `perform_year_end_close` | explicit | `year_end_close` family | `YearEndClose` | YEC DTO | `test_year_end_close.py` | `POST /api/v1/year-end-closes` | High — multi-step |
| External sales verify | External sales UI | `daily_sales_close.verify_external_sales` | `verify_external_sales` | explicit `company_id` | service commit | verification audit | record DTO | DSC tests | `POST /api/v1/external-sales/verify` | Medium |
| Void external verification | Same | `daily_sales_close.void_verification` | `void_external_sales_verification` | explicit | service commit | `Void` | DTO | DSC tests | `POST /api/v1/external-sales/{id}/void` | Medium |

### Admin / settings writes (post-P2.9 or parallel low-risk)

| Action | UI entry | Service | RequestContext | company_id source | Commit mode | Audit | Return | Tests | Proposed endpoint | Risk |
|--------|----------|---------|----------------|-------------------|-------------|-------|--------|-------|-------------------|------|
| Permission override set/clear | Permissions UI | `user_access.set_override` / `clear_override` | `manage_permissions` | explicit | service `commit` | permission audit | `MutationResult` | user access tests | `PUT /api/v1/members/{id}/permissions/{key}` | Medium — owner lockout guard |
| Company / global settings save | Settings UI | `save_settings`, `_save_company_settings` | `manage_settings` | explicit / global | app `commit` | varies | — | settings tests | `PUT /api/v1/settings` | Low |
| Attachment upload/delete | Attachment widgets | `app.py` upload helpers | `upload/delete_attachment` | ambient | app `commit` | `Upload`/`Delete` | attachment id | attachment tests | `POST /api/v1/attachments` | Low |

---

## Risk notes

### Cross-cutting

1. **TD-PS-01 commit ownership** — Services still commit internally in `internal` mode. API routes must use `unit_of_work` + per-family `COMMIT_MODE_*` before exposing writes; dual-run parity is mandatory (`docs/FASTAPI_P0_5D_COMMIT_OWNERSHIP_PLAN.md`).
2. **TD-PS-06/07 ambient company** — Shims pass `company_id=current_company_required()`. API must pass `context.company_id` from `X-Company-Id` only; never accept body `company_id`.
3. **TD-PS-08 bank balance asymmetry** — Forward bank posts are GL-only in service; Streamlit UI applies `BankAccount.balance` deltas. API P2.7 must either call the same companion logic or unify balance ownership first.
4. **TD-POSTING-05 duplicate YEC guards** — Partner/worker movement post/void paths duplicate inline guards; do not freeze into API until centralized.
5. **Reconciliation lazy `app` import** — `match_post._app()` reaches ambient JE stamping; fix explicit `company_id` on JE before API (`test_fastapi_p0_reconciliation_company_stamp.py`).
6. **Split-commit CC subledger** — `sync_company_cc_subledger` flushes; caller owns final commit. API must preserve ordering: JE post → subledger sink → boundary commit.
7. **Void cascade ordering** — Purchase void may cascade to linked payable and paid `PayablePayment` reversals; API must not partial-void.
8. **Error string stability** — Contract tests pin messages (`require_company_membership`, `Permission denied: {key}`, period/YEC `ValueError` text). HTTP mapping: 400 company missing, 401 bearer, 403 permission/membership, 422 validation, 409 business guard.

### Per-slice highlights

| Slice | Top risk |
|-------|----------|
| P2.1–P2.4 | Save-vs-post split in UI; idempotency on repost |
| P2.5 | Highest commit-count variance; audit must stay 1:1 with success |
| P2.6 | Bank txn + movement + JE atomicity |
| P2.7 | Balance cache vs GL (TD-PS-08) |
| P2.8 | Per-row recon commits; `MatchPostError` mapping |
| P2.9 | Period lock interaction; YEC empty-reason asymmetry on void returns |

---

## Testing strategy

### P2.0 (this doc)

- `tests/test_fastapi_p2_write_api_inventory.py` — doc exists + required sections/invariants
- Full suite must remain green (no runtime changes)

### Per future write slice (P2.1+)

| Layer | What to test |
|-------|----------------|
| **Auth** | Bearer + `X-Company-Id`; spoofed headers ignored; membership denied |
| **Permission** | 403 with stable `Permission denied: {key}` string |
| **Happy path** | Persisted state matches Streamlit/shim path (dual-run parity) |
| **GL parity** | JE lines, ref_types, amounts, dates unchanged |
| **Audit parity** | Exactly one audit row; action/entity_type/description match |
| **Guard parity** | Closed period, YEC lock, statement-linked bank txn guards |
| **Void cascade** | Linked entity flags + reversal JEs |
| **Commit mode** | `internal` count pins until family flips; `boundary` → 1 commit |
| **Company isolation** | No cross-tenant rows when switching `X-Company-Id` |
| **No GET commits** | Regression on all read routes |

Reuse existing families:

- Posting: `tests/test_posting_service01_*.py`
- Commit ownership: `tests/test_fastapi_p0_commit_ownership_*.py`
- FastAPI auth: `tests/test_fastapi_p1_auth_jwt_runtime.py`
- Recon stamp: `tests/test_fastapi_p0_reconciliation_company_stamp.py`

Add per-slice `tests/test_fastapi_p2_<slice>_write_api.py` with:

1. HTTP contract (status, error shape, DTO fields)
2. Service parity (API call vs direct service with same `RequestContext`)
3. No-new-commit on related GET endpoints

---

## Migration rules

1. **Inventory before implementation** — Every new write route must trace to a row in this doc (update doc in same PR).
2. **Read auth frozen** — P1.3e JWT + `X-Company-Id` is the only production auth path for API; `ERP_API_DEV_HEADERS=1` is test-only.
3. **Streamlit parallel** — Do not remove shims until API slice has parity tests + bake time.
4. **One family per PR** — Align with `services/commit_modes.py` families and P2.1–P2.9 order unless risk doc amended.
5. **Boundary before expose** — Flip `COMMIT_MODE_<FAMILY>=boundary` in staging before enabling write routes for that family.
6. **DTO at boundary** — Return `PostingResult` / void DTOs from `services/posting.py` helpers; do not serialize ORM at HTTP layer.
7. **company_id rule** — Request body lists entity fields only; tenant from `get_request_context().require_company_id()`.
8. **Feature flag per slice** — e.g. `ERP_API_WRITE_SALES=1` until slice proven; default off.
9. **No DELETE on financial entities** — Expose `POST .../void` only; never hard-delete posted rows.
10. **Preserve audit** — Route calls `record_audit` with explicit `performed_by`, `company_id`, `user_id` from context; same action strings as Streamlit.
11. **OpenAPI tag `writes`** — Add when first write route ships; keep separate from `auth` and read tags.
12. **Full suite green** — Every P2 slice PR runs `pytest`; no regressions on Streamlit auth or accounting tests.

---

## RequestContext mapping (API target)

All write routes use the same spine as P1.3e reads:

```
Authorization: Bearer <access_token>
X-Company-Id: <company_id>
        ↓
get_request_context(session) → RequestContext
        ↓
require_company_read_access / require_permission(context, key)
        ↓
service call(session, company_id=context.require_company_id(), user_id=context.user_id, …)
        ↓
unit_of_work boundary commit (when family in boundary mode)
        ↓
record_audit(…, company_id=context.company_id, performed_by=username)
```

Permissions resolve from **DB membership role + overrides**, never from JWT claims or `X-Role` (except `ERP_API_DEV_HEADERS` test fallback).

---

## References

| Doc | Relevance |
|-----|-----------|
| `docs/FASTAPI_MIGRATION_01_AUDIT.md` | API-readiness gaps |
| `docs/FASTAPI_P1_3_AUTH_STRATEGY.md` | JWT + company header split |
| `docs/FASTAPI_P0_5D_COMMIT_OWNERSHIP_PLAN.md` | Boundary commit sequencing |
| `docs/POSTING_SERVICE_01_CASCADE_MAP.md` | Post/void cascade source of truth |
| `services/commit_modes.py` | Per-family flip flags |
| `api/dependencies.py` | `get_request_context` (P1.3e) |
| `api/guards.py` | HTTP error mapping for reads (extend for writes) |

---

*P2.0 deliverable: migration-safe write inventory + contract plan. No endpoints implemented. Next step: P2.1 sales write API behind `COMMIT_MODE_POST_CASH_SALE=boundary` parity + `ERP_API_WRITE_SALES` feature flag.*
