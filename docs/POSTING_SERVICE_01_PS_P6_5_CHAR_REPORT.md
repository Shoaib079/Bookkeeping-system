# POSTING-SERVICE-01 — PS-P6-5 Characterization Report

**Mode:** CHARACTERIZATION ONLY — no code change, no extraction, no refactor, no cleanup, no patch.
**Baseline:** `main`, clean tree, commit `c34db84 "Move fiscal close posting to service"`; tests 1881 passed, 2 xfailed.
**Scope:** reconciliation boundary (`reconciliation/match_post.py`), remaining posting refs outside `services/posting.py`, lazy `_app()` imports.
**Bottom line:** PS-P6-5 should be **DOCUMENTATION-ONLY** (with an *optional, separately-scoped* behavior-preserving cleanup). It is **NOT an extraction** — `match_post.py` already lives outside app.py and correctly delegates GL to the kernel. See §11.

---

## 1. Function inventory

**`reconciliation/match_post.py` — posting functions (real, orchestration; NOT shims):**

| Function | Role | JE ref_type(s) |
|----------|------|----------------|
| `post_deposit_clearing_match` | card deposit ↔ clearing + processor fee | `BankStmtSettlement` |
| `post_generic_deposit` | deposit → Bank / chosen credit GL | `BankStmtDeposit` |
| `post_partner_statement_match` | statement line → partner movement | `PartnerCapital/Drawing/Salary/Advance/Repayment` |
| `post_worker_statement_match` | statement line → worker salary/advance | `WorkerSalary` / `WorkerAdvance` |
| `post_equity_statement_match` | owner drawing/capital, loan pay/receipt | `BankStmtOwnerDrawing/OwnerCapital/LoanPayment/LoanReceipt` |
| `post_vendor_outflow` | payable payment or ad-hoc expense | `BankStmtPayable` (payable) / `Expense` (via `app.post_expense`) |
| `post_bank_charge_outflow` | bank fee → Bank Charges | `BankStmtBankCharge` |

**Helpers (pure / read-only, in match_post.py):** `_app`, `_row_context`, `_create_bank_txn`, `_finalize_row`, `_bank_charges_enabled`, `_resolve_settlement_fee`, `_partner_gl_accounts`, `get_same_day_deposit_rows`, `get_postable_rows`, and the heuristic family (`_fold_tr`, `looks_like_*`, `card_deposit_style`, `infer_bank_charge_subtype`, `bank_charge_fee_label`, `suggest_deposit_match_kind`, `suggest_withdrawal_match_kind`, `looks_like_worker_payroll`).

**Direct posting/GL calls made by match_post (all via lazy `_app()`):**
- `app.create_journal_entry` — every poster (the GL primitive)
- `app.get_account_by_name` — GL lookups
- `app.post_expense` — `post_vendor_outflow` ad-hoc-expense branch
- `app.get_worker_advance_balance` — `post_worker_statement_match` recovery check
- (also `reconciliation.company_card.apply_account_balance_delta` — direct import, not `_app()`; and `reconciliation.clearing.get_unsettled_card_sales`)

**Lazy `_app()` import:** single definition at `match_post.py:43` (`import app as app_module`). Reaches **4** app symbols: 3 are themselves app shims → `services.posting` (`create_journal_entry`, `get_account_by_name`, `post_expense`); **1 is a real app function** (`get_worker_advance_balance`, `app.py:7278`, `cq`-scoped).

**Posting-related functions still real outside `services/posting.py`:** the 7 `match_post` posters (legitimately reconciliation-specific) and `app.get_worker_advance_balance` (read helper). Everything generic-GL is already a shim (see §below).

**app.py shims that remain intentionally (consumed here):** `create_journal_entry` (`:1599`), `get_account_by_name` (`:2515`), `post_expense` (`:5883`) — all delegate to `posting_service`.

---

## 2. Call graph

```
UI (app.py import :243 + ui/banking.py) ──► match_post.post_* (7 posters)
                                          └► suggest_*/looks_like_* (heuristics, pure)

post_* (each)
  ├─ _row_context(row_id, company_id) ............ MatchPostError on bad state
  ├─ app.get_account_by_name(...) ................ lazy _app() → shim → service
  ├─ [validation: amount/direction/fee/shares]
  ├─ _create_bank_txn(...) ....................... creates BankTransaction(statement_ref="bsr:{id}")
  │        └─ apply_account_balance_delta(ba, type, amt)   ◄── BankAccount.balance mutation
  ├─ [optional] PartnerMovement / WorkerMovement / ExpenseRecord / Payable mutation
  ├─ app.create_journal_entry(row.date, desc, ref_type, ref_id, lines, currency)  [COMMIT in kernel]
  │        └─ (lazy _app() → shim → service; entry_date = row.date)
  ├─ _finalize_row(...) .......................... row.status="posted" + links
  ├─ [settlement_row / payable] further mutations
  └─ session.commit() ............................ [explicit COMMIT]
  → returns dict
```

**UI entry points:** `app.py:243` imports `post_worker_statement_match`, `suggest_deposit_match_kind`, `suggest_withdrawal_match_kind`, `looks_like_worker_payroll`; the other posters are wired through `ui/banking.py`. The CC-bill-payment path (`reconciliation/company_card.post_credit_card_bill_payment`) is a sibling, not in match_post.

**Rollback paths:** none explicit in match_post. `app.create_journal_entry` owns its own `rollback()` on guard/balance failure (TD-PS-04: discards the pending BankTransaction/balance/row mutations). `MatchPostError` is raised **before** any commit on validation failures.

**Audit calls:** **NONE.** No `log_audit` anywhere in `match_post.py` — reconciliation posting is **not audited** at this layer (characterize and preserve).

---

## 3. Posting behavior

- **JE ref_types:** `BankStmtSettlement`, `BankStmtDeposit`, partner `PartnerCapital/Drawing/Salary/Advance/Repayment`, `WorkerSalary`/`WorkerAdvance`, `BankStmtOwnerDrawing/OwnerCapital/LoanPayment/LoanReceipt`, `BankStmtPayable`, `Expense` (delegated), `BankStmtBankCharge`. `reference_id` is `row.id` for most; **`movement.id`** for partner/worker matches.
- **Debit/credit orientation (selected):** deposit clearing → Dr Bank (+ Dr Bank Charges if fee) / Cr Card Sales Clearing; generic deposit → Dr Bank / Cr chosen GL; partner Drawing/Salary → Dr current / Cr Bank; Advance → Dr advance / Cr Bank; CapitalContribution/Repayment → Dr Bank / Cr cap-or-advance; worker Salary → Dr Salary Expense, Cr advance (recovery), Cr Bank (net); vendor payable → Dr AP / Cr Bank; bank charge → Dr Bank Charges / Cr Bank.
- **Match/unmatch:** posting sets `row.status="posted"` + `match_type` + links. **No unmatch/unpost in this module** — bsr:-tagged BankTransactions are explicitly blocked by `void_bank_transaction` ("must be unposted from Bank Reconciliation"); unpost is handled outside match_post (UI / `company_card.void_credit_card_bill_payment` for the CC-bill case).
- **Reversal behavior:** none here (post-only module).
- **Bank/account effects:** every poster creates a `BankTransaction` (`statement_ref="bsr:{row.id}"`, `is_reconciled=True`) and mutates `BankAccount.balance` via `apply_account_balance_delta`.

---

## 4. Return contracts

| Function | Success | Failure |
|----------|---------|---------|
| 7 `post_*` | `dict[str, Any]` (`journal_entry_id`, `bank_transaction_id`, `amount`, `match_type`, + path-specific keys) | **raises `MatchPostError`** |
| `_resolve_settlement_fee` | `(fee_amt, fee_source, settlement_row|None)` | raises `MatchPostError` |
| `_row_context` | `(row, imp)` | raises `MatchPostError` |
| heuristics (`looks_like_*`, `card_deposit_style`, `suggest_*`) | `bool` / `str` / `None` | — (pure) |
| `get_postable_rows` / `get_same_day_deposit_rows` | `list[BankStatementRow]` | — |

No `None`-on-failure or error-string contracts — match_post uses **exceptions** (`MatchPostError`) for failure, **dicts** for success.

---

## 5. Error strings (exact, raised as `MatchPostError`)

Row/import: `"Statement row not found"`, `"Import not found for this company"`, `"This row is already posted"`, `"Cannot post a skipped or parse-error row"`, `"Row did not parse successfully"`, `"Bank account not found"`.
Direction: `"This row is a withdrawal, not a deposit"`, `"This row is a deposit, not a withdrawal"`, `"This row is a deposit, not a bank charge"`, `"Worker payroll requires a bank withdrawal line."`, `"This partner movement requires a bank withdrawal/deposit line."`
Settlement: `"Settlement batch not found or already used"`, `"Settlement batch belongs to another company"`, `"Settlement batch did not parse successfully"`, `"Settlement gross (…) must equal clearing total (…)"`, `"Settlement net (…) must equal bank deposit (…)"`, `"Settlement gross, fee, and net do not balance"`, `"Deposit (…) exceeds clearing total (…). Handle refunds or chargebacks manually."`, `"Deposit (…) is less than clearing (…). Enable **Bank charges**…"`, `"Processor fee of … will post to Bank Charges. Confirm the fee before posting."`
GL/missing: `"Bank or Card Sales Clearing GL account missing"`, `"Bank Charges GL account missing"`, `"GL accounts not found for deposit posting"`, `"Bank GL account not found"`, `"Partner GL accounts missing — check Partner Accounts setup."`, `"Accounts Payable GL missing"`, `"Owner Drawings/Owner Capital/Loans account missing"`, `"Salary Expense account missing"`, `"Employee Advances account missing"`.
Domain: `"Partner/Worker/Vendor not found …"`, `"Payable not found for this vendor"`, `"Payable is already paid"`, `"Amount must be positive."`, `"Select a payable or choose ad-hoc expense"`, `"Expense journal entry was not created"`, `"Enable **Bank charges** in Company Setup to post bank fee lines."`, worker net-pay mismatch + advance-recovery-exceeds strings.

---

## 6. Commit ownership

| Path | Commits | Count |
|------|---------|-------|
| Each poster (normal) | `app.create_journal_entry` kernel commit (1) + explicit `session.commit()` at end (1) | **2** |
| `post_vendor_outflow` ad-hoc-expense branch | `app.post_expense` → kernel commit (1) + final `session.commit()` (1) | **2** (expense JE committed inside `post_expense`, then the final commit persists `_finalize_row` + bank txn) |
| Failure (`MatchPostError`) before `create_journal_entry` | none | **0** |
| Closed-year `create_journal_entry` (kernel guard) | kernel `rollback()` then raises `ValueError` | **0** (pending work discarded — TD-PS-04) |

No audit commit (no `log_audit`).

---

## 7. Audit behavior

**None.** `match_post.py` contains **zero `log_audit` calls**. Reconciliation posting is not audited at this layer — neither success nor failure. (Contrast with app.py voids/close, which audit app-side.) This is current behavior and must be preserved unless an explicit decision adds auditing (out of PS-P6-5 scope).

---

## 8. Company scoping

- **Explicit `company_id` everywhere in match_post:** every poster takes `company_id`; `_row_context` validates `imp.company_id == company_id`; `_create_bank_txn` stamps `company_id` explicitly; `PartnerMovement`/`WorkerMovement`/`ExpenseRecord` records are stamped with the explicit `company_id`; settlement/partner/worker/vendor lookups validate `*.company_id == company_id`.
- **Unscoped `session.query` (intentional, but explicitly filtered):** `get_postable_rows` / `get_same_day_deposit_rows` use `session.query(BankStatementRow)` joined/filtered by `BankStatementImport.company_id == company_id` — scoped by explicit filter, not `cq`. `post_vendor_outflow` ad-hoc branch looks up the Expense JE via `session.query(JournalEntry).filter_by(reference_type="Expense", reference_id=…)` — **not company-filtered** (relies on the freshly-created `expense.id` being unique; preserve).
- **Cross-company risk to PRESERVE (latent inconsistency):** the **JE company stamp comes from the ambient shim**, not the explicit param. `app.create_journal_entry` (shim) stamps `company_id=_current_company_id()`; match_post passes its explicit `company_id` to the *records* (BankTransaction/movements) but **not** to the JE. In a normal session `_current_company_id() == company_id`, so they agree; if they ever diverged, the JE would be stamped with the ambient company while the records carry the explicit one. This is current behavior — preserve it, and note it as the key consideration for any boundary rewrite (§11).
- `app.get_worker_advance_balance` is `cq`-scoped (ambient).

---

## 9. YEC guard behavior

- **No `yec_block_message` call in match_post.** Reconciliation posting is guarded **only by the kernel** (`entry_date_posting_blocked` inside `create_journal_entry`), evaluated against `entry_date = row.date`.
- **Blocked behavior:** posting a statement row dated inside a closed `FiscalPeriod` (non-`PeriodClose` ref) or a non-void `YearEndClose` raises `ValueError` (the kernel message, **not** `MatchPostError`) and the kernel `rollback()` discards the pending `BankTransaction` + balance delta + row mutations (TD-PS-04). No partial commit.
- match_post is therefore **independent of the TD-POSTING-05 inline-guard cluster** — it inherits YEC protection transitively through the kernel.

---

## 10. Hidden side effects

- **`BankStatementRow` (`_finalize_row`):** `status="posted"`, `match_type`, `posted_journal_entry_id`, `bank_transaction_id`, `posted_at`, `posted_by_user_id`, `vendor_id`, `payable_id`, `expense_record_id`, `partner_movement_id`, `worker_movement_id`, `clearing_sale_ids_json`; plus `settlement_row_id` (clearing path).
- **`BankTransaction`:** created with `statement_ref="bsr:{row.id}"`, `is_reconciled=True`, `company_id`; `charge_subtype` set on fee/charge paths; description overwritten on partner/worker paths.
- **`BankAccount.balance`:** mutated by `apply_account_balance_delta` for every poster.
- **`SettlementStatementRow`:** `status="posted"`, `bank_statement_row_id`, `posted_journal_entry_id`, `posted_at`, `posted_by_user_id`.
- **`Payable` (vendor_outflow):** `paid_amount` += pay_amt, `balance` recomputed, `paid=True` + `balance=0.0` when `balance <= 0.01` (partial-payment-aware; `pay_amt = min(amt, balance|amount)`).
- **`PartnerMovement` / `WorkerMovement`:** created, `journal_entry_id` linked; worker movement stores gross/deductions/advance_recovery/net_paid.
- **`ExpenseRecord` (ad-hoc):** created, then `app.post_expense` posts its own JE (+ may sync CC subledger).
- **Timestamps:** `posted_at`, `created_at`, `posted_at` (settlement) = `datetime.datetime.now()`.

---

## 11. Extraction / cleanup proposal — and the PS-P6-5 verdict

**Verdict: PS-P6-5 is DOCUMENTATION-ONLY, not extraction.** Optionally a small, *separately-scoped*, behavior-preserving cleanup. Reasons:

1. **Nothing to extract.** `match_post.py` already lives outside `app.py`. Its posters are **reconciliation orchestration** (row finalize, settlement-fee resolution, bank-txn creation, statement-row mutations) — not generic GL posting. They correctly delegate the GL primitive to `create_journal_entry`. Moving them **into** `services/posting.py` would force the posting kernel to import reconciliation models (`BankStatementRow`, `SettlementStatementRow`, …) — an inverted, wrong-direction coupling. **Do not extract them.**
2. **The only debt is the lazy `_app()` indirection** (4 symbols; 3 are shims → services, 1 is the real `get_worker_advance_balance`). Routing `match_post` directly to `services.posting` for `create_journal_entry` / `get_account_by_name` / `post_expense` is cosmetic — **except** it collides with the §8 company-stamping subtlety:
   - `app.create_journal_entry` stamps `company_id = _current_company_id()` (ambient).
   - A direct `services.posting.create_journal_entry` call **requires** an explicit `company_id`; match_post *has* one — passing it would stamp the JE with the explicit company (arguably a latent-bug fix), which is a **behavior change**.
   - Therefore the import rewrite is **not** purely mechanical and must not be done as a "cleanup" that silently changes JE company stamping.

**Cleanly separated options (pick one; do NOT mix):**
- **Option A — documentation-only (recommended for PS-P6-5):** record that `match_post` is the correct boundary (reconciliation orchestration → kernel via app shims), document the ambient-vs-explicit JE company-stamp inconsistency (§8) and the absent audit (§7), and **defer** the `_app()`→direct-import rewrite + the company_id stamping decision to the **PS-P7 hardening** phase (alongside TD-PS-01/-03/-06/-07).
- **Option B — behavior-preserving cleanup (optional, separate commit):** replace `app.X` with `services.posting.X` for `get_account_by_name`/`create_journal_entry`/`post_expense`, **passing `company_id=_current_company_id()`** to `create_journal_entry` to reproduce the shim's ambient stamping **exactly** (zero behavior change). Keep `get_worker_advance_balance` via `_app()` (or extract it as a tiny read helper). This removes 3 lazy-`_app()` hops without touching behavior.

**What should move:** nothing in PS-P6-5 (Option A). Under Option B, only the *import target* changes, not function locations.
**What should stay:** all 7 posters + helpers in `reconciliation/match_post.py`; `get_worker_advance_balance` in app.py (or a minimal read-helper extraction, separately).
**Tests needed before any Option-B cleanup:** a contract test that each poster emits an **identical JE (ref_type, lines, currency, company stamp)** before and after the import switch; the closed-year `ValueError` path; the partial-payable `pay_amt = min(...)` math; the settlement-fee balance checks; the ambient-vs-explicit company-stamp behavior pinned explicitly.
**Risks:** (1) the JE company-stamp change if Option B forgets to pass ambient `company_id`; (2) `post_expense` re-entrancy (it commits + may sync CC subledger) — preserve ordering; (3) the unscoped Expense-JE lookup in `post_vendor_outflow`; (4) TD-PS-04 rollback discarding the pending bank-txn on closed-year posts.
**What must NOT change:** all `MatchPostError` strings; the dict return shapes + keys; `statement_ref="bsr:{row.id}"`; `is_reconciled=True`; the 2-commit count per poster; the absence of `log_audit`; the `_finalize_row` field set; `BankAccount.balance` mutation via `apply_account_balance_delta`; partial-payable `min()` math; and the ambient JE company stamp (unless Option B is explicitly chosen and characterized).

---

*PS-P6-5 CHAR report — characterization only. No code modified, no patch produced.*
