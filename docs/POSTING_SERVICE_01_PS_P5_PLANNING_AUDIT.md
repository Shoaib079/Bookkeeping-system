# POSTING-SERVICE-01 — PS-P5 Planning Audit

**Phase:** PS-P5 planning (audit only — no code changes)
**Predecessors:** PS-P0…PS-P4 complete; suite green; working tree clean
**Purpose:** Classify all remaining posting-related logic in app.py and sequence PS-P5/PS-P6.
**Headline:** **GO** for PS-P5 = the self-contained, non-YEC-guarded set (receivables, inventory, simple equity, flag-only close voids). **Stop before** the BankTransaction-creating movements + YEC-guarded period-end cluster → PS-P6, gated on **TD-POSTING-05** YEC-guard centralization.

---

## 1. Remaining posting surface map

| Function | app.py | Area | GL? | Side effects beyond GL | Commit | Audit | Scoping | Return |
|----------|--------|------|-----|------------------------|--------|-------|---------|--------|
| `post_receivable_payment` | `:5096` | Receivables | yes (`ReceivablePayment` + FX Gain/Loss) | mutates `Sale.paid_amount/balance/status` | kernel + explicit `commit()` | **none** | `session.get` (no cq) | error `str`/None |
| `compute_sale_balance_status` | helper | Receivables | — | pure | — | — | — | tuple |
| `void_inventory_transaction` | `:2501` | Inventory | **no GL** | `Product.quantity -= change` | explicit | `log_audit` | `session.get` | `bool` |
| `void_reconciliation` | `:6321` | Recon/Close | reverses `CashReconciliation` | sets `reversed_je_id`, `voided_by_id` | explicit | `log_audit` | `cq(JournalEntry)` | error `str` |
| `void_eod_close` | `:6540` | Recon/Close | **no GL** | flag-only (`status="voided"`) | explicit | `log_audit` | `session.get` | error `str` |
| `calculate_expected_cash` / EOD snapshot | `:6072` / `:6438` | Recon/Close | read-only | none | — | — | heavy `cq` | dict/float |
| `post_capital_contribution` | `:6023` | Equity | yes (`CapitalContribution`) | none (GL-only) | kernel | none | `get_account_by_name` | None |
| `post_owner_drawing` | `:6037` | Equity | yes (`OwnerDrawing`) | none (GL-only) | kernel | none | `get_account_by_name` | None |
| `void_equity_movement` | `:6051` | Equity | reverses ref_type | `BankAccount.balance` inline ±; voids `BankTransaction` | explicit | `log_audit` | `session.get` | None |
| `post_salary` | `:5962` | Equity/payroll | yes (`Salary`) | none (GL-only) | kernel | none | `get_account_by_name` | None |
| `post_partner_movement` | `:6639` | Equity | yes (5-branch JE) | creates `BankTransaction` + `BankAccount.balance` ±; `PartnerMovement` record; **YEC Guard 4** | kernel + explicit | `log_audit` | `cq(YearEndClose)`, `session.get` | `(id, err)` |
| `void_partner_movement` | `:6745` | Equity | reverses JE | voids `BankTransaction` + balance; **YEC Guard 5** | explicit | `log_audit` | `cq(YearEndClose)` | error `str` |
| `post_worker_movement` | `:7576` | Equity | yes (multi-branch) | creates `BankTransaction` + balance; `WorkerMovement`; YEC guard | kernel + explicit | `log_audit` | `cq` | `(id, err)` |
| `void_worker_movement` | `:7747` | Equity | reverses JE | voids `BankTransaction` + balance; YEC guard | explicit | `log_audit` | `cq` | error `str` |
| `allocate_profit_to_partners` | `:7836` | Period-end | yes (`ProfitAllocation`, period-scoped) | `PartnerProfitAllocation` record | kernel + explicit | `log_audit` | `cq` | `(id, err)` |
| `void_profit_allocation` | `:7930` | Period-end | reverses JE | flag; **YEC Guard 3** | explicit | `log_audit` | `cq(YearEndClose)`, `session.get` | error `str` |
| `void_year_end_close` | `:8242` | Year-end | **no GL** | removes year lock (flag/status) | explicit | `log_audit` | `session.get` | error `str` |
| year-end / period close + retained-earnings posting | `:7836+`/`:8000+` | Year-end | yes (`PeriodClose`/`YearEndClose`) | closing JEs, RE roll-up | kernel + workflow | `log_audit` | `cq` | varies |

---

## 2. Per-area analysis

### 1. Receivables — `post_receivable_payment` (+ `compute_sale_balance_status`)
- **Deps:** `get_account_by_name`, `create_journal_entry`, `compute_sale_balance_status`. FX Gain/Loss line branches; `ReceivablePayment` ref.
- **Commit:** kernel JE commit + an extra explicit `session.commit()` for the sale-balance mutation. **Audit:** none. **Scoping:** `session.get` only.
- **Coverage:** **none dedicated** — not in PS-P0 char, no `post_receivable_payment` test file. The FX gain/loss paths are entirely unpinned.
- **Difficulty:** Medium (FX branches + sale-state mutation, but self-contained — no BankTransaction, no YEC guard). **Value:** **High** (core AR; FastAPI needs it).

### 2. Inventory — `void_inventory_transaction`
- **Deps:** `session.get(InventoryTransaction, Product)`. **No journal entry** — adjusts `Product.quantity` only.
- **Commit:** explicit. **Audit:** `log_audit`. **Scoping:** `session.get`.
- **Coverage:** thin/none dedicated. **Difficulty:** **Low** (stock-only, no GL). **Value:** Low–Medium (arguably a stock-ledger op, not GL posting).

### 3. Reconciliation / Close — `void_reconciliation`, `void_eod_close`, cash-recon compute
- **Deps:** `void_reconciliation` reverses `CashReconciliation` JE + `cq` reversal lookup; `void_eod_close` flag-only; `calculate_expected_cash`/EOD snapshot are read-only `cq`-heavy computes. Reconciliation *posting* helpers live in `reconciliation/match_post.py` (already a module, lazy `_app()`).
- **Commit:** explicit. **Audit:** `log_audit`. **Scoping:** `cq`. **Contract:** `owner_id` + error-`str` (unlike the bool voids).
- **Coverage:** `test_cash_reconciliation.py`, `test_end_of_day_close.py`. **Difficulty:** Medium (workflow state, `owner_id`/`str` contract; the voids themselves are flag/JE-reversal only). **Value:** Medium.

### 4. Equity / Ownership
- **Simple GL posters** (`post_capital_contribution`, `post_owner_drawing`, `post_salary`): GL-only pairs (like the bank posters) — balance handled by callers. `void_equity_movement` adds inline `BankAccount.balance` reversal + `BankTransaction` void. **No YEC guard.**
- **Movement families** (`post_partner_movement`/`void_partner_movement`, `post_worker_movement`/`void_worker_movement`): the heavy ones — **create** `BankTransaction`, mutate `BankAccount.balance`, write a movement record, post a **multi-branch JE** (5 partner branches), and carry **duplicate inline YEC guards** (Guards 4/5). `(id, err)`/`str` contracts; `created_by_id`/`voider_id` params.
- **Coverage:** `test_partner_statement_p1–p4`, `test_partner_ux_p1p2p3`, `test_workers.py` — substantial behavioral coverage.
- **Difficulty:** simple posters **Low–Medium**; movement families **High**. **Value:** **High** (partnerships).

### 5. Period-End / Year-End
- `allocate_profit_to_partners` (period-scoped `ProfitAllocation` JE), `void_profit_allocation` (**YEC Guard 3** + reversal), `void_year_end_close` (flag/lock removal, **no GL**), plus the forward year-end/period-close + retained-earnings posting chains.
- **Commit/Audit:** kernel + explicit + `log_audit`. **Scoping:** `cq(YearEndClose)`/`cq`. **Contract:** `voider_id`/`str`.
- **Coverage:** `test_year_end_close.py`. **Difficulty:** **High** (YEC guards everywhere, RE/period-close chains, lock management). **Value:** Medium–High.

---

## 3. Risk ranking (highest → lowest)

1. **Partner / worker movement families** — `BankTransaction` creation + balance mutation + multi-branch JE + duplicate YEC guards + `(id,err)`/user params. **Highest.**
2. **Period-end / year-end chains** (profit allocation, RE/period close) — YEC guards (TD-POSTING-05), lock management, retained-earnings roll-up.
3. **Reconciliation / close** (`void_reconciliation`, recon compute) — workflow state, `owner_id`/`str` contract; the voids themselves are easy.
4. **Receivables** (`post_receivable_payment`) — FX branches + sale-state mutation; self-contained but **uncharacterized** (highest *characterization* gap), High value.
5. **Simple equity posters** (`post_capital_contribution`, `post_owner_drawing`, `post_salary`, `void_equity_movement`) — GL pairs (+ one inline balance reversal). Low–Medium.
6. **Inventory** (`void_inventory_transaction`) — stock-qty only, no GL. **Lowest.**

---

## 4. Proposed PS-P5 waves (GO now — no YEC-guard / movement entanglement)

| Wave | Functions | Prereq |
|------|-----------|--------|
| **PS-P5-CHAR** | Characterize `post_receivable_payment` (incl. FX gain/loss), `void_inventory_transaction`, `void_equity_movement` balance reversal, simple-equity poster tuples | — |
| **PS-P5-1 — Receivables** | `post_receivable_payment` + `compute_sale_balance_status` | PS-P5-CHAR (FX) — **mandatory**, currently zero coverage |
| **PS-P5-2 — Inventory** | `void_inventory_transaction` | quick (stock-only) |
| **PS-P5-3 — Simple equity** | `post_capital_contribution`, `post_owner_drawing`, `post_salary`, `void_equity_movement` | poster-tuple + balance pins |
| **PS-P5-4 — Flag-only close voids** | `void_eod_close`, `void_year_end_close` (no GL); optionally `void_reconciliation` (JE reversal) | note `owner_id`/`str` contract |

All PS-P5 functions move **verbatim** with app shims supplying ambient `company_id`/user context; `log_audit` stays app-side; commit boundaries preserved (the PS-P3/P4 pattern).

---

## 5. Recommended stopping point before PS-P6

**Stop after PS-P5-4** — i.e., once everything **without** a duplicate inline YEC guard and **without** BankTransaction-creating movement logic is extracted. That draws a clean line:

- **PS-P5 = "remaining simple posting/voids"** (self-contained, verbatim-movable).
- **PS-P6 = "stateful workflow + YEC-guarded equity/period-end"** — the partner/worker movement families and the period-end/year-end/retained-earnings cluster, which share **TD-POSTING-05** (duplicate inline YEC Guards 3/4/5).

Do **not** begin PS-P6 extraction until TD-POSTING-05 is centralized — that refactor is a *behavioral change* (not a verbatim move) and must land with its own characterization first, or the duplicate guards will be frozen into the service layer.

---

## 6. Proposed PS-P6 waves (gated on TD-POSTING-05)

| Wave | Functions | Note |
|------|-----------|------|
| **PS-P6-0 — YEC-guard centralization (TD-POSTING-05)** | Replace inline Guards 3/4/5 with the shared `entry_date_posting_blocked` path | behavioral refactor; own CHAR + review |
| **PS-P6-1 — Partner movement family** | `post_partner_movement`, `void_partner_movement` | BankTransaction + balance + 5-branch JE |
| **PS-P6-2 — Worker movement family** | `post_worker_movement`, `void_worker_movement` | mirrors partner |
| **PS-P6-3 — Profit allocation** | `allocate_profit_to_partners`, `void_profit_allocation` | period-scoped JE |
| **PS-P6-4 — Year-end / period close + retained earnings** | close posting chains, `void_year_end_close` already done in P5 if taken | lock management, RE roll-up |
| **PS-P6-5 — Reconciliation posting** | `reconciliation/match_post.py` paths (lazy `_app()` → direct service) | finalize module boundary |

---

## 7. Updated migration-readiness estimate

| Milestone | Domain coverage | Boundary-ready (FastAPI) |
|-----------|-----------------|--------------------------|
| After PS-P4 (now) | ~70% | ~70% of extracted code (gated by TD-PS-01/-03) |
| After PS-P5 | **~82%** | unchanged ~70% (cleanups not yet done) |
| After PS-P6 | **~95%** | still gated until the TD-PS-01/-03/-06/-07 cleanup phase |

PS-P5 adds ~8 self-contained functions; PS-P6 clears the heavy cluster, leaving only the cross-cutting TD-PS cleanups and the reconciliation module boundary.

---

## 8. Migration blockers remaining

1. **TD-PS-01** — services commit internally (now incl. void services). Top blocker for boundary-owned transactions.
2. **TD-PS-03** — ORM return at the service boundary; needs a `PostingResult` DTO.
3. **TD-POSTING-05** — duplicate inline YEC guards (partner/worker/profit-allocation). **Blocks clean PS-P6.**
4. **TD-PS-06 / TD-PS-07** — `company_id` not unified (`gl_company_id`/`ambient_company_id` splits).
5. **`log_audit` ambient coupling** — every void relies on app-side `log_audit` (ambient `_current_user` + own commit). API needs explicit `user_id`. Note `owner_id`/`voider_id`/`created_by_id` already point the right way.
6. **Heterogeneous return contracts** — `bool` vs error-`str` vs `(id, err)` vs `None`. Normalize to a result/DTO for the API boundary.
7. **`post_receivable_payment` uncharacterized** — must close before PS-P5-1.
8. **`reconciliation/match_post.py`** still calls app shims via lazy `_app()` — finalize at PS-P6-5.

---

## Go / No-Go

| Decision | Verdict |
|----------|---------|
| PS-P5 = receivables + inventory + simple equity + flag-only close voids (verbatim, shims), CHAR first | **GO** |
| Include partner/worker movement families in PS-P5 | **NO-GO** — BankTransaction + balance + YEC guards → PS-P6 |
| Begin period-end/year-end extraction in PS-P5 | **NO-GO** — YEC-guarded; defer to PS-P6 |
| Extract `post_receivable_payment` before adding FX characterization | **NO-GO** — zero coverage today |
| Start PS-P6 before TD-POSTING-05 centralization | **NO-GO** — would freeze duplicate guards into the service |
| Fix TD-PS-01/-03/-06/-07 mid-extraction | **NO-GO** — dedicated cleanup phase before FastAPI Phase B |

---

*Audit only. No code modified. Update `POSTING_SERVICE_01_CASCADE_MAP.md`, `TECH_DEBT_AND_MIGRATION_CLEANUP.md`, and `AUDIT_HISTORY.md` as PS-P5 waves land.*
