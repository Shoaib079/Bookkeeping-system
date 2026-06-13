# POSTING-SERVICE-01 — Posting / Void Cascade Map

**Phase:** PS-P2 complete (PS-P0 characterization → PS-P1 kernel → PS-P2a sales → PS-P2b payable resolver → PS-P2c expense/purchase/payable + CC sink)  
**Source of truth:** `services/posting.py` for extracted write paths; `app.py` shims + remaining surfaces below  
**Purpose:** Track posting/void cascade as extraction proceeds toward PS-P3 (void/reversal)

---

## Core primitives

| Function | Location | Role | Commit behavior |
|----------|----------|------|-----------------|
| `create_journal_entry` | `services/posting.py` (shim `app.py`) | Balanced JE writer; period/YEC guard via `entry_date_posting_blocked` | **Commits internally** (`session.commit()` on success; `session.rollback()` + `ValueError` on guard/balance failure) |
| `entry_date_posting_blocked` | `services/posting.py` (shim `_entry_date_posting_blocked`) | Shared fiscal-period + year-end-close guard | Does not commit |
| `create_reversing_journal_entry` | **`app.py` only** | Swaps debit/credit from `original_entry.lines`; posts `reference_type="Reversal"`, `reference_id=original_entry.id` | **Commits internally** (delegates to `create_journal_entry` shim → kernel) |
| `reverse_journal_entries_for` | **`app.py` only** | Finds all JEs for `(reference_type, reference_id)` and reverses each | **Commits internally** (per reversal via `create_journal_entry`) |
| `calculate_account_balance` | **`app.py` only** | Derives all-time net balance from journal lines (company-scoped when `active_company_id` set) | Does not commit |
| `sync_account_balances` | **`app.py` only** | Refreshes `ChartOfAccounts.balance` cache from `calculate_account_balance` for every account | **Commits internally** |
| `get_account_by_name` | `services/posting.py` (shim `app.py`) | GL account lookup by name/currency/company | Does not commit |

**Balance cache rule (PS-P0, unchanged):** `create_journal_entry` does **not** update `ChartOfAccounts.balance` in-place. Reads use `calculate_account_balance()`; startup calls `sync_account_balances()`.

---

## `services/posting.py` — shipped write paths (PS-P1 through PS-P2c)

| Service function | Wave | `reference_type` / role | CC subledger | Commit behavior |
|------------------|------|----------------------|--------------|-----------------|
| `post_cash_sale` | PS-P2a | `CashSale` | — | Via `create_journal_entry` |
| `post_card_sale` | PS-P2a | `CardSale` | — | Via `create_journal_entry` |
| `post_credit_sale` | PS-P2a | `CreditSale` | — | Via `create_journal_entry` |
| `resolve_payment_credit_account` | PS-P2b | resolver (Cash/Bank/CC Payable) | — | Does not commit |
| `post_payable_creation` | PS-P2b | `PayableCreation` | — | Via `create_journal_entry` |
| `sync_company_cc_subledger` | PS-P2c-1 | CC sink (no extra JE) | `post_cc_subledger_charge` | **No commit** — `flush()` only; split-commit with caller |
| `post_expense` | PS-P2c-2 | `Expense` | calls `sync_company_cc_subledger` on Credit Card | Via `create_journal_entry` + optional sink |
| `post_payable_payment` | PS-P2c-2 | `PayablePayment` | calls sink; subledger `reference_id` = **`je.id`** | Via `create_journal_entry` + optional sink |
| `resolve_purchase_debit_account` | PS-P2c-3 | debit GL mapper | — | Does not commit |
| `purchase_ref_type` | PS-P2c-3 | pure ref_type mapper | — | Does not commit |
| `post_purchase` | PS-P2c-3 | `Purchase` / `CashPurchase` / `BankPurchase` / `CardPurchase` | calls sink on Credit Card; `ccc:CardPurchase:{purchase_id}` | Via `create_journal_entry` + optional sink |

All above have **app.py compatibility shims** with identical public signatures. Ambient company threading: `company_id` / `gl_company_id` / `ambient_company_id` supplied by shims (TD-PS-02, TD-PS-06, TD-PS-07).

---

## Posting family — remaining in `app.py` (not yet extracted)

All wrappers below ultimately call `create_journal_entry` (via shim) unless noted. Commit column reflects the **outermost** caller visible to Streamlit/UI code.

| Function | `reference_type` | Typical debit / credit | Commit behavior |
|----------|------------------|------------------------|-----------------|
| `post_receivable_payment` | `ReceivablePayment` | Dr Cash/Bank · Cr AR (+ optional FX Gain/Loss) | `create_journal_entry` + **additional `session.commit()`** for sale balance update |
| `post_salary` | `Salary` | Dr Salary Expense · Cr Cash | Via `create_journal_entry` |
| `post_bank_transaction` | `BankDeposit` / `BankWithdrawal` | Dr/Cr Bank vs Cash | Via `create_journal_entry` |
| `post_bank_transfer` | `BankTransfer` | Dr dest GL · Cr src GL (skipped when same GL) | Via `create_journal_entry` or no-op |
| `post_capital_contribution` | `CapitalContribution` | Dr Bank/Cash · Cr Owner Capital | Via `create_journal_entry` |
| `post_owner_drawing` | `OwnerDrawing` | Dr Owner Drawings · Cr Bank/Cash | Via `create_journal_entry` |
| `post_partner_movement` | Per `_PARTNER_REF_TYPES` | Movement-specific partner GL pairs | `create_journal_entry` + **`session.commit()`** + `log_audit` (audit commits again) |
| `post_worker_movement` | Per `_WORKER_REF_TYPES` | Salary/advance/repayment lines | `create_journal_entry` + **`session.commit()`** + `log_audit` |

**PS-P2 moved to service (shims only in app.py):** `post_cash_sale`, `post_card_sale`, `post_credit_sale`, `post_payable_creation`, `post_expense`, `post_payable_payment`, `post_purchase` — see table above.

### Period-close / allocation posting (still in `app.py`)

| Function | `reference_type` | Commit behavior |
|----------|------------------|-----------------|
| Period close helpers | `PeriodClose` | Via `create_journal_entry` (PeriodClose exempt from period lock) |
| Profit allocation | `ProfitAllocation` | Via `create_journal_entry` |
| Year-end close | `YearEndClose` | Via `create_journal_entry` + surrounding close workflow commits |

---

## Posting family — `reconciliation/` (lazy `_app()` import)

These modules lazy-import `app` via `_app()` and call `create_journal_entry` or related helpers. **Not extracted in PS-P0.**

| Module | Function | Notes | Commit behavior |
|--------|----------|-------|-----------------|
| `reconciliation/company_card.py` | `post_cc_subledger_charge` | CC subledger charge row + GL | Via `app.create_journal_entry` (TD-POSTING-06) |
| `reconciliation/company_card.py` | `post_credit_card_bill_payment` | Bill payment GL | Via `app.create_journal_entry` |
| `reconciliation/company_card.py` | `void_credit_card_bill_payment` | Reversal + subledger | Via reversal helpers + local commits |
| `reconciliation/match_post.py` | `post_deposit_clearing_match` | Card settlement clearing | Via `app.create_journal_entry` |
| `reconciliation/match_post.py` | `post_generic_deposit` | Generic bank deposit match | Via `app.create_journal_entry` |
| `reconciliation/match_post.py` | `post_partner_statement_match` | Partner statement reconciliation | Via `app.create_journal_entry` |
| `reconciliation/match_post.py` | `post_worker_statement_match` | Worker statement reconciliation | Via `app.create_journal_entry` |
| `reconciliation/match_post.py` | `post_equity_statement_match` | Equity statement reconciliation | Via `app.create_journal_entry` |
| `reconciliation/match_post.py` | `post_vendor_outflow` | Vendor payment from reconciliation | Via `app.create_journal_entry` |
| `reconciliation/match_post.py` | `post_bank_charge_outflow` | Bank charge fee posting | Via `app.create_journal_entry` |

---

## Void family — `app.py` (PS-P3 scope — not extracted)

| Function | GL reversal | Cascade / side effects | Commit behavior |
|----------|-------------|------------------------|-----------------|
| `void_sale` | `reverse_journal_entries_for` for `CashSale`, `CardSale`, `CreditSale`, `ReceivablePayment` | Sets `Sale.is_void`, `status="Void"` | **`session.commit()`** + `log_audit` (commits again) |
| `void_expense` | `reverse_cc_subledgers_for_gl_reference` + `reverse_journal_entries_for("Expense")` | Sets `ExpenseRecord.is_void` | **`session.commit()`** + `log_audit` |
| `void_purchase` | CC subledger reverse + `reverse_journal_entries_for` by purchase ref type | Sets `Purchase.is_void`; cascades `_void_purchase_linked_payable` (reverses `PayablePayment` GL if paid) | **`session.commit()`** + `log_audit` |
| `void_payable` | CC subledger + `PayableCreation` + `PayablePayment` reversals | Sets `Payable.is_void` | **`session.commit()`** + `log_audit` |
| `void_bank_transaction` | `BankDeposit` / `BankWithdrawal` / `BankTransfer` reversals | Reverses `BankAccount.balance`; blocks statement-linked / card-sale / equity rows | **`session.commit()`** + `log_audit` |
| `void_inventory_transaction` | Inventory GL reversal | Sets inventory txn void flags | **`session.commit()`** + `log_audit` |
| `void_equity_movement` | `reverse_journal_entries_for(ref_type)` | Voids `BankTransaction`; adjusts bank balance | **`session.commit()`** + `log_audit` |
| `void_partner_movement` | `create_reversing_journal_entry` on linked JE | Voids bank txn + balance; YEC guard (Guard 5) | **`session.commit()`** + `log_audit` |
| `void_worker_movement` | Reversal on linked JE | Voids bank txn + balance; YEC guard | **`session.commit()`** + `log_audit` |
| `void_profit_allocation` | Reversal on allocation JE | Sets allocation void; YEC guard | **`session.commit()`** + `log_audit` |
| `void_reconciliation` | Match-specific unpost | Reconciliation workspace state | **Commits internally** (workflow-dependent) |
| `void_eod_close` | EOD verification void | Daily sales close linkage | **Commits internally** |
| `void_year_end_close` | YEC reversal workflow | Reopens closed year | **Commits internally** |

### Known cascade patterns

1. **Credit purchase → payable:** `post_purchase(Credit)` posts AP via `Purchase` ref; `_create_purchase_payable` creates tracking row without duplicate `PayableCreation` GL. `void_purchase` reverses purchase GL then voids linked payable; if payable was paid, also reverses `PayablePayment` GL.
2. **Bank transfer void:** Reverses both legs when posted as `BankTransfer`; paired destination txn may cascade.
3. **Card sale deposit:** Bank deposit rows tagged `Card Sale …` cannot be voided via Banking — must void originating `Sale`.
4. **Statement-linked bank txns:** `statement_ref` starting with `bsr:` must be unposted from Bank Reconciliation, not `void_bank_transaction`.

---

## Year-end / period guards

| Location | Guard |
|----------|-------|
| `_entry_date_posting_blocked` inside `create_journal_entry` | Closed `FiscalPeriod` (except `reference_type="PeriodClose"`) + non-void `YearEndClose` spanning `entry_date`; company-scoped |
| `post_partner_movement` | Duplicate YEC query (Guard 4) before posting |
| `post_worker_movement` | Duplicate YEC query before posting |
| `void_partner_movement` | YEC guard (Guard 5) before void |
| `void_profit_allocation` | YEC guard before void |

**TD-POSTING-05:** YEC guard is centralized in `_entry_date_posting_blocked` for JE posting but duplicated inline in partner/worker movement post/void paths.

---

## Commit behavior summary

| Category | Functions | Notes |
|----------|-----------|-------|
| **Commits internally** | `create_journal_entry`, `create_reversing_journal_entry`, `sync_account_balances`, most `void_*`, `post_partner_movement`, `post_worker_movement`, `log_audit` | Primary extraction risk (TD-POSTING-02) |
| **Does not commit internally** | `calculate_account_balance`, `_entry_date_posting_blocked`, `post_bank_transfer` (no-op path only), `payable_payment_already_posted` | Read-only or early-return helpers |
| **Unknown / needs confirmation** | `reconciliation/*` match posting error paths; `void_reconciliation`; `void_eod_close`; `void_year_end_close` full multi-step commit boundaries | Confirm during PS-P1 extraction with integration tests |

---

## PS-P0 / PS-P2 characterization coverage

**Characterized (tests in `tests/test_posting_service01_characterization.py`):**

- `create_journal_entry` balanced + unbalanced + period lock
- Balance cache vs `calculate_account_balance` vs `sync_account_balances`
- `post_cash_sale`, `post_card_sale`, `post_credit_sale`
- `post_expense`, `post_purchase` (Credit), `post_payable_creation`, `post_payable_payment`
- `create_reversing_journal_entry`, `void_sale`

**PS-P2c characterization (`tests/test_posting_service01_p2c_char.py`, 19 tests — unchanged through PS-P2c-3):**

- CC `statement_ref` exact strings: `ccc:Expense:{id}`, `ccc:CardPurchase:{id}`, `ccc:PayablePayment:{je.id}`
- `sync_company_cc_subledger` `company_id=None` path + ambient fallback
- Split-commit (JE committed, subledger pending until caller commits)
- `post_purchase` Cash/Bank JE tuples + ref_types
- `post_expense` category debit mapping (Rent/Salary/Utility/Advertising/Fuel/fallback) + Bank path
- Entry-point dedup + amount≤0 errors (`CompanyCardError` propagation from `post_cc_subledger_charge`)

**Extraction proof tests:** `test_posting_service01_p2b.py`, `p2c1.py`, `p2c2.py`, `p2c3.py` (shim delegation + import purity).

**Partially characterized elsewhere:**

- YEC lock on `create_journal_entry` — `tests/test_year_end_close.py`
- Period lock company isolation — `tests/test_phase14c_isolation.py`
- Card purchase void/edit — `tests/test_card_purchase_void_edit.py`
- CC subledger GL+card+record triangle — `tests/test_cc_subledger_sync.py`

**Uncharacterized (PS-P3-CHAR target):**

- `post_receivable_payment` (incl. FX gain/loss lines)
- `post_salary`, `post_bank_transaction`, `post_bank_transfer`
- `post_capital_contribution`, `post_owner_drawing`
- `post_partner_movement`, `post_worker_movement`
- All `reconciliation/` posting paths
- `void_expense`, `void_purchase`, `void_payable`, `void_bank_transaction`, and remaining void workflows
- `reverse_journal_entries_for` multi-JE behavior
- Period close / profit allocation / year-end close posting chains

---

*Last updated PS-P2 completion (2026-06-13). Next update at PS-P3 extraction.*
