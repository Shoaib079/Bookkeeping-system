# POSTING-SERVICE-01 — PS-P3 Progress Audit

**Phase:** PS-P3 progress (audit only — no code changes)
**Done:** PS-P3-1 (reversal primitives), PS-P3-2a (`void_expense`, `void_payable`), PS-P3-3a (`linked_purchase_payable`, `void_purchase_linked_payable`), PS-P3-3b (`void_purchase`)
**State at audit:** suite green; working tree clean
**Verdict:** PS-P3 extraction is faithful. **Recommend: sweep `void_sale` (PS-P3-2b) to close PS-P3, then open PS-P4 as the banking family** — do *not* bolt `void_bank_transaction` onto PS-P3.

---

## 1–2. Remaining app.py posting/void surface (real, not shims), by domain

**Already extracted (app.py = shim only):** `create_journal_entry`, `create_reversing_journal_entry`, `reverse_journal_entries_for`, `get_account_by_name`, sales trio, `post_expense`, `post_purchase`, `post_payable_creation`, `post_payable_payment`, `resolve_payment_credit_account`, `sync_company_cc_subledger`, `void_expense`, `void_payable`, `void_purchase`, `_linked_purchase_payable`, `_void_purchase_linked_payable`.

**Remaining real functions:**

| Domain | Posting | Void |
|--------|---------|------|
| **Banking** | `post_bank_transaction` (`:6024`), `post_bank_transfer` (`:6077`) | `void_bank_transaction` (`:2488`), `void_reconciliation` (`:6396`) |
| **Receivables / sales** | `post_receivable_payment` (`:5144`, FX gain/loss) | `void_sale` (`:2355`) — **still real; PS-P3-2b not done** |
| **Partner / worker / owner equity** | `post_partner_movement` (`:6714`), `post_worker_movement` (`:7651`), `post_salary` (`:6010`), `post_capital_contribution` (`:6098`), `post_owner_drawing` (`:6112`) | `void_partner_movement` (`:6820`), `void_worker_movement` (`:7822`), `void_equity_movement` (`:6126`), `void_profit_allocation` (`:8005`) |
| **Year-end / close** | — | `void_year_end_close` (`:8317`), `void_eod_close` (`:6615`), (`void_profit_allocation` is close-adjacent) |
| **Inventory** | (inventory posting) | `void_inventory_transaction` (`:2549`) |
| **Balance (adjacent)** | `calculate_account_balance` (`:2601`), `calculate_account_balance_for_period` (`:2572`), `sync_account_balances` (`:2328`) | — |

**Intentionally kept in app.py:** edit-lifecycle helpers `_create_purchase_payable`, `_update_purchase_payable`, `_sync_purchase_payable_lifecycle` (reach the moved helpers via shims — per PS-P3-3 audit).

---

## 3. PS-P3 extraction preserved invariants

| Invariant | Status | Evidence |
|-----------|--------|----------|
| **Commit boundaries** | ✅ preserved | Service void kernels do `reverse_*` (kernel commits per JE) + entity flags + the post-flag `session.commit()`; app shim adds the `log_audit` commit. The 3-commit (unpaid) / 4-commit (paid purchase) counts are pinned by PS-P3-CHAR (`mock_commit.call_count`). |
| **Audit boundaries** | ✅ preserved | `log_audit` stays in the app shim, called **only on a `True` return**, after the service core — identical "commit then audit" ordering and ambient `_current_user` stamp. Verified in `void_expense`/`void_purchase`/`void_payable` shims. |
| **Company-scoping** | ✅ preserved | Every void shim passes `company_id=current_company_required()` (raises if absent — matches the old `cq()` semantics). Service functions take explicit `company_id`, no ambient reads (import-purity enforced). `linked_purchase_payable` reproduces the `purchase_id` + company filter. |

No commit, audit, or scoping behavior changed; suite green confirms.

---

## 4. TD-PS-01 … TD-PS-07 review

All seven present in `TECH_DEBT_AND_MIGRATION_CLEANUP.md`; **TD-PS-07 was added** and TD-PS-06 broadened (docs reconciled).

| ID | Accurate? | PS-P3 effect |
|----|-----------|--------------|
| TD-PS-01 (services commit internally) | ✅ Open — **scope broadened** | Void services now also own a `session.commit()` (post-flag). Still the top FastAPI blocker. |
| TD-PS-02 (shims carry ambient resolution) | ✅ Open — broader | Void shims add `current_company_required()`. |
| TD-PS-03 (ORM return) | ✅ Open | Voids return `bool` (no new ORM-return debt); posting still returns ORM JE. |
| TD-PS-04 (rollback discards caller work) | ✅ Open | Unchanged. |
| TD-PS-05 (`get_account_by_name` partial) | ✅ Open | Unchanged. |
| TD-PS-06 (resolver partial `company_id`) | ✅ Open | Unchanged. |
| TD-PS-07 (CC sink ambient fallback) | ✅ Open | Unchanged by PS-P3. |

---

## 5. Continue PS-P3 with `void_bank_transaction`, or close PS-P3 → PS-P4?

**Recommendation: close PS-P3 (after a `void_sale` sweep) and start PS-P4 as the banking family.** Do not attach `void_bank_transaction` to PS-P3.

Why `void_bank_transaction` is **not** a PS-P3 tail — it introduces side-effect surface absent from the document voids:
- **`BankAccount.balance` cache mutation** (`reverse_account_balance_delta` + inline transfer arithmetic) — new state not touched by expense/purchase/payable voids.
- **Paired-transfer cascade** — finds and voids the paired destination `BankTransaction` via `cq(...).filter(description.like("Transfer from …"))`, reversing its balance too.
- **Three guard branches** — `bsr:` raises `ValueError`; `Card Sale …` returns `False`; `Capital Contribution`/`Owner Drawing` returns `False`.

That surface is **banking-domain** and shares the balance-cache concern with `post_bank_transaction` / `post_bank_transfer`. It should be characterized and extracted **with** the banking posters, not as a one-off appended to the document-void wave.

`void_sale`, by contrast, is the **last flat document void** (reverse `CashSale`/`CardSale`/`CreditSale`/`ReceivablePayment` + flag + audit) and was the original PS-P3-2 partner to `void_expense`. Extracting it (PS-P3-2b) completes the simple-void pattern and gives PS-P3 a clean close. It's already characterized in PS-P0/PS-P3-CHAR.

**Suggested sequencing:**
- **PS-P3-2b (close PS-P3):** extract `void_sale` (flat pattern, shim adds `log_audit`).
- **PS-P4 — banking family:** `post_bank_transaction`, `post_bank_transfer`, then `void_bank_transaction`, then `void_reconciliation`. Add balance-cache + paired-transfer + guard characterization first.
- **PS-P5 — equity/movement/close voids** (`void_partner_movement`, `void_worker_movement`, `void_profit_allocation`, `void_equity_movement`, `void_year_end_close`, `void_eod_close`): blocked on centralizing the **duplicate inline YEC guards (TD-POSTING-05)** and parameterizing `voider_id`/`log_audit`.
- `post_receivable_payment` (FX) and `void_inventory_transaction` slot into a receivables / inventory mini-wave as convenient.

---

## 6. Updated migration-readiness estimate

| Slice | Readiness | Note |
|-------|-----------|------|
| JE kernel + reversal primitives | ~90% structural | commit ownership (TD-PS-01) still pending |
| Sales/expense/purchase/payable **posts + voids** (the transactional-document domain) | ~80% structural | extracted, pure, company-explicit; gated by TD-PS-01/-03 |
| Whole posting+void domain | **~65%** coverage | ~18 of ~40 functions still in app.py (banking, AR-payment+FX, equity/partner/worker, close, inventory, balance calc) |
| True FastAPI-readiness of *extracted* code | **~70%** | structurally clean but not boundary-owned (TD-PS-01) and still ORM-returning (TD-PS-03) |

Up from the PS-P2 completion estimate (write families ~75% / domain ~55–60%): PS-P3 added the reversal primitives and three document voids, lifting domain coverage to ~65%.

---

## 7. Remaining blockers to FastAPI migration

1. **TD-PS-01 — internal commits** (now incl. void services). Boundary-owned transactions are a hard FastAPI requirement. **Highest.**
2. **TD-PS-03 — ORM `JournalEntry` at the service boundary.** Needs a `PostingResult` DTO.
3. **TD-PS-06 / TD-PS-07 — `company_id` not unified** (`gl_company_id` / `ambient_company_id` splits). Cleanup pass before Phase B.
4. **`log_audit` ambient coupling** — every void shim relies on app-side `log_audit` (ambient `_current_user` + own commit). API path needs explicit `user_id` and a boundary-owned audit write.
5. **Unextracted surface (~18 functions)** — banking, AR-payment FX, partner/worker/equity, close, inventory, balance calc; several carry `cq()`, `voider_id`, and duplicate YEC guards (**TD-POSTING-05**).
6. **TD-PS-04** — kernel rollback discards caller work (lands with TD-PS-01).

---

## Risk ranking (remaining work)

| Work | Risk | Driver |
|------|------|--------|
| Partner/worker/profit-allocation/year-end/eod voids | **High** | duplicate inline YEC guards (TD-POSTING-05), `voider_id`, multi-step workflow commits, `log_audit` |
| `void_reconciliation` | **High** | reconciliation workspace state, multi-step |
| `void_bank_transaction` + banking posters | **Medium–High** | `BankAccount.balance` cache, paired-transfer cascade, statement-link/card/equity guards, `cq` paired lookup |
| `post_receivable_payment` | **Medium** | FX gain/loss lines, extra commit for sale-balance update |
| `void_inventory_transaction` | **Low–Medium** | inventory GL reversal + flags |
| `void_sale` (PS-P3-2b) | **Low** | flat reverse+flag+audit; already characterized |
| `post_salary`, `post_capital_contribution`, `post_owner_drawing` | **Low** | simple debit/credit pairs |

---

## Go / No-Go

| Decision | Verdict |
|----------|---------|
| Sweep `void_sale` as **PS-P3-2b** to close PS-P3 cleanly | **GO** |
| Attach `void_bank_transaction` to PS-P3 as a one-off | **NO-GO** — belongs to the PS-P4 banking family with the balance-cache surface |
| Open **PS-P4 = banking family** (`post_bank_transaction`, `post_bank_transfer`, `void_bank_transaction`, `void_reconciliation`), characterization first | **GO** |
| Start equity/movement/close voids next | **NO-GO** — defer to PS-P5 after TD-POSTING-05 YEC-guard centralization |
| Fix TD-PS-01/-03/-06/-07 mid-extraction | **NO-GO** — verbatim moves only; cleanup is a dedicated pass before FastAPI Phase B |

---

*Audit only. No code modified. Update `POSTING_SERVICE_01_CASCADE_MAP.md` and `AUDIT_HISTORY.md` as PS-P3 closes and PS-P4 opens.*
