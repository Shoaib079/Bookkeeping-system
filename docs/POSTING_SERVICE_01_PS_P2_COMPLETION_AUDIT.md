# POSTING-SERVICE-01 — PS-P2 Completion Audit

**Phase:** PS-P2 completion (audit only — no code changes)
**Predecessors:** PS-P0, PS-P1, PS-P2a, PS-P2b, PS-P2c-1/-2/-3 — all reported complete
**State at audit:** suite green (1652 passed, 2 xfailed); working tree clean after PS-P2c-3 commit
**Verdict:** **GO** — PS-P2 write-path extraction is complete and faithful. One **documentation-gate gap** (non-code) to close. PS-P3 (void/reversal) is clear to plan.

---

## 1. PS-P2 posting functions now in `services/posting.py`

| Service function | Wave | app.py shim |
|------------------|------|-------------|
| `create_journal_entry` | PS-P1 | `app.py:1590` ✓ |
| `entry_date_posting_blocked` | PS-P1 | (internal) |
| `get_account_by_name` | PS-P2a | `app.py:174` ✓ |
| `card_settlement_on` | PS-P2a | `_card_settlement_on` `:5244` ✓ |
| `post_cash_sale` / `post_card_sale` / `post_credit_sale` | PS-P2a | `:5235` / `:5980` / `:5989` ✓ |
| `resolve_payment_credit_account` | PS-P2b | `_resolve_payment_credit_account` ✓ |
| `post_payable_creation` | PS-P2b | `:6073` ✓ |
| `sync_company_cc_subledger` | PS-P2c-1 | `_sync_company_cc_subledger` `:5758` ✓ |
| `post_expense` | PS-P2c-2 | `:6024` ✓ |
| `post_payable_payment` | PS-P2c-2 | `:6082` ✓ |
| `resolve_purchase_debit_account` | PS-P2c-3 | `_resolve_purchase_debit_account` `:5998` ✓ |
| `purchase_ref_type` | PS-P2c-3 | `_purchase_ref_type` `:6005` ✓ |
| `post_purchase` | PS-P2c-3 | `:6010` ✓ |

**Confirmed:** every function in the planned PS-P2 scope (sales trio, expense, purchase + 2 helpers, both payable functions, the resolver, the CC sink, plus the PS-P1 kernel and PS-P2a account/setting helpers) now lives in `services/posting.py`.

## 2. app.py keeps compatibility shims only (for moved functions)

Every moved function's app.py body is now a one-call delegation to `posting_service.*`, adding only ambient resolution. De-underscored service names; shims keep the legacy underscore names where internal callers used them. The shims pass the ambient session company explicitly:

- `create_journal_entry`, `post_*_sale`, `post_payable_creation` → `company_id=_current_company_id()`
- `resolve_payment_credit_account`, `post_purchase`, `post_expense`, `post_payable_payment` → `gl_company_id=_current_company_id()` (and `ambient_company_id=_current_company_id()` where the CC sink is reachable)
- `sync_company_cc_subledger` shim → `ambient_company_id=_current_company_id()`

No business logic remains in the shims — verified by reading each body and by `tests/test_posting_service01_p2b.py` import-purity + shim-delegation assertions.

## 3. Remaining `post_*` functions still in app.py (real, not shims)

| Function | app.py | Notes |
|----------|--------|-------|
| `post_receivable_payment` | `:5170` | AR settlement + **FX gain/loss** lines; extra `session.commit()` for sale balance |
| `post_salary` | `:6036` | Dr Salary Exp / Cr Cash |
| `post_bank_transaction` | `:6050` | deposit/withdrawal Cash↔Bank |
| `post_bank_transfer` | `:6103` | no-op when same GL |
| `post_capital_contribution` | `:6124` | equity |
| `post_owner_drawing` | `:6138` | equity |
| `post_partner_movement` | `:6740` | commit + `log_audit`; duplicate YEC guard |
| `post_worker_movement` | `:7677` | commit + `log_audit`; duplicate YEC guard |

These were **out of PS-P2 scope** (PS-P2 covered the expense/purchase/payable/sales families). They remain candidates for a later write-path wave.

## 4. Posting-adjacent functions not yet migrated

| Function | app.py | Role |
|----------|--------|------|
| `create_reversing_journal_entry` | `:2339` | reversal primitive (swaps debits/credits → `create_journal_entry`) |
| `reverse_journal_entries_for` | `:2357` | bulk reversal by `(ref_type, ref_id)` |
| `calculate_account_balance` | `:2627` | derived balance from lines |
| `calculate_account_balance_for_period` | `:2598` | period-scoped balance |
| `sync_account_balances` | `:2328` | refresh `ChartOfAccounts.balance` cache |
| `reconciliation/*` posting | match_post / company_card | call `app.create_journal_entry` via lazy `_app()` (now the PS-P1 shim → kernel) |

The two reversal primitives are the **keystones for PS-P3** and currently still route through the (extracted) kernel via the app shim.

## 5. Void / reversal behavior unchanged

All `void_*` functions remain in app.py and were not in PS-P2 scope: `void_sale`, `void_expense`, `void_purchase`, `void_payable`, `void_bank_transaction`, `void_inventory_transaction`, `void_equity_movement`, `void_reconciliation`, `void_eod_close`, `void_partner_movement`, `void_worker_movement`, `void_profit_allocation`, `void_year_end_close`. `create_reversing_journal_entry`/`reverse_journal_entries_for` bodies are unchanged (verified verbatim). Because reversals call `create_journal_entry`, reversal posting now flows through the extracted kernel — but that path moved verbatim in PS-P1, so **GL reversal semantics are identical**. Green suite (incl. `test_cc_subledger_sync` void cases and `void_sale` characterization) confirms no behavioral drift.

## 6. Transaction boundaries / commit behavior unchanged

- Kernel still **commits internally** on success and `rollback()`s before raising — moved verbatim, still owns the transaction (TD-PS-01 deliberately unaddressed).
- `sync_company_cc_subledger` still performs **no commit** — adds the `BankTransaction` + flushes, riding the caller's next commit (split-commit preserved).
- Shims add only ambient `company_id`/`gl_company_id`/`ambient_company_id` resolution; no new commit/rollback points.
- `post_receivable_payment` and the movement posters keep their extra `session.commit()` + `log_audit` (also commits) — untouched.

No transaction-boundary change introduced by PS-P2.

## 7. TD-PS-01 … TD-PS-06 accuracy

| ID | Still accurate? | Note |
|----|-----------------|------|
| TD-PS-01 (kernel commits internally) | ✅ accurate, Open | unchanged by PS-P2; still the top FastAPI blocker |
| TD-PS-02 (shims carry ambient resolution) | ✅ accurate, Open — **now broader** | PS-P2c added `ambient_company_id` (sink) + `gl_company_id` on expense/purchase/payable-payment shims; list of ambient-carrying shims grew |
| TD-PS-03 (ORM `JournalEntry` return) | ✅ accurate, Open | no DTO added in PS-P2 |
| TD-PS-04 (rollback discards caller work) | ✅ accurate, Open | unchanged |
| TD-PS-05 (`get_account_by_name` partial) | ✅ accurate, Open | still a shim with many non-posting app callers; posting families now call the service copy |
| TD-PS-06 (resolver partial `company_id`) | ✅ accurate, Open — **understated** | PS-P2c-1 introduced a **second instance**: `sync_company_cc_subledger` ambient fallback + dual `gl_company_id`/`ambient_company_id` threading on three posters. Should be registered (suggest **TD-PS-07**) so the cleanup pass unifies resolver + sink together |

**Documentation-gate gap (non-code finding):** the TD-PS section header lists only "PS-P1 / PS-P2a / PS-P2b shipped" and has no **PS-P2c Migration Cleanup** entry; `TECH_DEBT_AND_MIGRATION_CLEANUP.md`, `POSTING_SERVICE_01_CASCADE_MAP.md`, and `AUDIT_HISTORY.md` contain **no `PS-P2c` reference** at all. Per the project documentation gate, PS-P2c-1/-2/-3 completion should append: the shipped-lines, a PS-P2c cleanup section, and the new TD-PS-07 (sink ambient fallback). This does not affect code correctness but the TD ledger is currently stale relative to the working tree.

## 8. Migration-readiness score after PS-P2

Against MIGRATION-READINESS-01:

| Criterion | Write path (PS-P2 families) | Posting domain overall |
|-----------|------------------------------|------------------------|
| Explicit inputs (no `cq`/Streamlit/`_t`/ambient in service) | ✅ enforced by purity test | partial |
| Serializable output (DTO, no ORM at boundary) | ❌ TD-PS-03 | ❌ |
| Validation separate from UI | ◑ pure helpers exist (`resolve_*`, `entry_date_posting_blocked`, `purchase_ref_type`); no formal `validate_*`/DTO | ◑ |
| Tests without Streamlit | ✅ char + p2b/p2c suites | ◑ (voids partially) |
| Boundary-owned transactions | ❌ TD-PS-01 (commits internally) | ❌ |

**Estimate:**
- **PS-P2 write families: ~75% migration-ready** — structure, purity, and explicit company inputs are done; the remaining 25% is commit-ownership (TD-PS-01), ORM→DTO (TD-PS-03), and `company_id` unification (TD-PS-06/-07).
- **Whole posting domain: ~55–60%** — writes mostly extracted, but void/reversal family (13 functions), the reversal primitives, and balance calculators are still 100% in app.py.

## 9. Recommended PS-P3 scope & sequencing (void migration)

Mirror the proven "shared keystone first, then leaves, defer the workflow-heavy tail" pattern:

- **PS-P3-CHAR (first):** add characterization for the void paths below (see §10) before any move.
- **PS-P3-1 — reversal primitives:** extract `create_reversing_journal_entry` + `reverse_journal_entries_for` → `services/posting.py` (de-underscored), with app shims. They depend only on `create_journal_entry` (already in service) and `cq` (replace with explicit `company_id` param, shim supplies ambient). Lowest risk; unblocks all voids.
- **PS-P3-2 — simple voids:** `void_sale`, `void_expense` (also calls `reverse_cc_subledgers_for_gl_reference`, already a clean module). Pattern: GL reversal + entity flag set + `log_audit`. Decide the `log_audit` boundary — recommend extracting a pure *reverse-and-validate* core to the service and keeping the audit-logging orchestration in the app shim (`log_audit` is cross-cutting and commits again).
- **PS-P3-3 — cascade voids:** `void_purchase` (→ linked payable + `PayablePayment` reversal), `void_payable`, `void_bank_transaction` (`BankAccount.balance` reversal + `bsr:`/card-sale guards). Higher complexity; needs the §10 cascade characterization landed.
- **PS-P3-DEFER (PS-P4):** movement/equity/close voids — `void_partner_movement`, `void_worker_movement`, `void_profit_allocation`, `void_equity_movement`, `void_year_end_close`, `void_reconciliation`, `void_eod_close`. These carry **duplicate inline YEC guards (TD-POSTING-05)**, bank-balance side effects, and multi-step workflow commits. Treat as a separate wave after the YEC guard is centralized.

## 10. Characterization gaps before PS-P3

From the cascade map's "Uncharacterized" list, only `void_sale` and `create_reversing_journal_entry` are pinned. Add before extraction:

1. `reverse_journal_entries_for` over a **multi-JE** reference (asserts one reversal per original).
2. `void_expense` — GL reversal + `is_void` flag + **CC subledger reversal** (`reverse_cc_subledgers_for_gl_reference`).
3. `void_purchase` — purchase GL reversal **+ cascade** to linked payable, including `PayablePayment` reversal when paid.
4. `void_payable` — `PayableCreation` + `PayablePayment` reversals + flag.
5. `void_bank_transaction` — `BankAccount.balance` reversal; **guards** for `bsr:` statement-linked and `Card Sale …` deposit rows (must-not-void).
6. **Void commit/audit boundary** — pin that each void commits then `log_audit` commits again (locks current behaviour before any TD-PS-01 boundary change).
7. (For the deferred wave) YEC guard on movement/allocation voids.

---

## Summary

| Question | Answer |
|----------|--------|
| **PS-P2 completion verdict** | **Complete & faithful.** All planned write-path functions extracted; app.py holds shims only; commit/void/reversal semantics unchanged; suite green. |
| **Remaining app.py posting surface** | 8 real `post_*` (receivable payment, salary, bank txn/transfer, capital, drawing, partner/worker movement); reversal primitives ×2; balance calculators ×3; 13 `void_*`. |
| **Risks before PS-P3** | (a) stale TD ledger / missing PS-P2c doc entry + unregistered TD-PS-07; (b) void family largely uncharacterized; (c) `log_audit` + double-commit boundary in voids; (d) deferred-wave duplicate YEC guards (TD-POSTING-05). |
| **Recommended PS-P3 plan** | CHAR → reversal primitives → simple voids → cascade voids → defer movement/equity/close voids to PS-P4. |
| **Go / No-Go** | **GO** for PS-P3 planning. **NO-GO** to start void extraction before PS-P3-CHAR lands and the TD ledger / PS-P2c docs are reconciled. **NO-GO** to fix TD-PS-01/-06/-07 inside PS-P3 (verbatim moves only). |

---

*Audit only. No code modified. Recommend a docs-only follow-up to append the PS-P2c shipped lines, a PS-P2c Migration Cleanup section, TD-PS-07, and PS-P2c entries in `CASCADE_MAP` and `AUDIT_HISTORY`.*
