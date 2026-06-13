# POSTING-SERVICE-01 — Posting / Void Cascade Map

**Phase:** PS-P0 (characterization only — no extraction yet)  
**Source of truth:** `app.py` posting engine as of PS-P0  
**Purpose:** Freeze current behavior before moving GL posting into `services/posting.py`

---

## Core primitives (`app.py`)

| Function | Role | Commit behavior |
|----------|------|-----------------|
| `create_journal_entry` | Balanced JE writer; period/YEC guard via `_entry_date_posting_blocked` | **Commits internally** (`session.commit()` on success; `session.rollback()` + `ValueError` on guard/balance failure) |
| `create_reversing_journal_entry` | Swaps debit/credit from `original_entry.lines`; posts `reference_type="Reversal"`, `reference_id=original_entry.id` | **Commits internally** (delegates to `create_journal_entry`) |
| `reverse_journal_entries_for` | Finds all JEs for `(reference_type, reference_id)` and reverses each | **Commits internally** (per reversal via `create_journal_entry`) |
| `calculate_account_balance` | Derives all-time net balance from journal lines (company-scoped when `active_company_id` set) | Does not commit |
| `sync_account_balances` | Refreshes `ChartOfAccounts.balance` cache from `calculate_account_balance` for every account | **Commits internally** |
| `_entry_date_posting_blocked` | Shared fiscal-period + year-end-close guard | Does not commit |

**Balance cache rule (PS-P0):** `create_journal_entry` does **not** update `ChartOfAccounts.balance` in-place. Reads use `calculate_account_balance()`; startup calls `sync_account_balances()`.

---

## Posting family — `app.py` convenience wrappers

All wrappers below ultimately call `create_journal_entry` unless noted. Commit column reflects the **outermost** caller visible to Streamlit/UI code.

| Function | `reference_type` | Typical debit / credit | Commit behavior |
|----------|------------------|------------------------|-----------------|
| `post_cash_sale` | `CashSale` | Dr Cash · Cr Sales Revenue | Via `create_journal_entry` |
| `post_card_sale` | `CardSale` | Dr Bank (settlement OFF) or Dr Card Sales Clearing (settlement ON) · Cr Sales Revenue | Via `create_journal_entry` |
| `post_credit_sale` | `CreditSale` | Dr Accounts Receivable · Cr Sales Revenue | Via `create_journal_entry` |
| `post_receivable_payment` | `ReceivablePayment` | Dr Cash/Bank · Cr AR (+ optional FX Gain/Loss) | `create_journal_entry` + **additional `session.commit()`** for sale balance update |
| `post_purchase` | `Purchase` / `CashPurchase` / `BankPurchase` / `CardPurchase` | Dr expense/inventory · Cr AP/Cash/Bank/CC Payable | Via `create_journal_entry`; may call `_sync_company_cc_subledger` (subledger — see reconciliation) |
| `post_expense` | `Expense` | Dr expense category · Cr Cash/Bank/CC Payable | Via `create_journal_entry`; may call `_sync_company_cc_subledger` |
| `post_salary` | `Salary` | Dr Salary Expense · Cr Cash | Via `create_journal_entry` |
| `post_bank_transaction` | `BankDeposit` / `BankWithdrawal` | Dr/Cr Bank vs Cash | Via `create_journal_entry` |
| `post_payable_creation` | `PayableCreation` | Dr expense · Cr Accounts Payable | Via `create_journal_entry` |
| `post_payable_payment` | `PayablePayment` | Dr AP · Cr Cash/Bank/CC Payable | Via `create_journal_entry`; may call `_sync_company_cc_subledger` |
| `post_bank_transfer` | `BankTransfer` | Dr dest GL · Cr src GL (skipped when same GL) | Via `create_journal_entry` or no-op |
| `post_capital_contribution` | `CapitalContribution` | Dr Bank/Cash · Cr Owner Capital | Via `create_journal_entry` |
| `post_owner_drawing` | `OwnerDrawing` | Dr Owner Drawings · Cr Bank/Cash | Via `create_journal_entry` |
| `post_partner_movement` | Per `_PARTNER_REF_TYPES` | Movement-specific partner GL pairs | `create_journal_entry` + **`session.commit()`** + `log_audit` (audit commits again) |
| `post_worker_movement` | Per `_WORKER_REF_TYPES` | Salary/advance/repayment lines | `create_journal_entry` + **`session.commit()`** + `log_audit` |

### Period-close / allocation posting (also in `app.py`)

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

## Void family — `app.py`

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

## PS-P0 characterization coverage

**Characterized (tests in `tests/test_posting_service01_characterization.py`):**

- `create_journal_entry` balanced + unbalanced + period lock
- Balance cache vs `calculate_account_balance` vs `sync_account_balances`
- `post_cash_sale`, `post_card_sale`, `post_credit_sale`
- `post_expense`, `post_purchase` (Credit), `post_payable_creation`, `post_payable_payment`
- `create_reversing_journal_entry`, `void_sale`

**Partially characterized elsewhere:**

- YEC lock on `create_journal_entry` — `tests/test_year_end_close.py`
- Period lock company isolation — `tests/test_phase14c_isolation.py`
- Card purchase void/edit — `tests/test_card_purchase_void_edit.py`

**Uncharacterized (PS-P1+):**

- `post_receivable_payment` (incl. FX gain/loss lines)
- `post_salary`, `post_bank_transaction`, `post_bank_transfer`
- `post_capital_contribution`, `post_owner_drawing`
- `post_partner_movement`, `post_worker_movement`
- All `reconciliation/` posting paths
- `void_expense`, `void_purchase`, `void_payable`, `void_bank_transaction`, and remaining void workflows
- Period close / profit allocation / year-end close posting chains

---

*Update this map when posting code moves to `services/posting.py` (PS-P1+).*
