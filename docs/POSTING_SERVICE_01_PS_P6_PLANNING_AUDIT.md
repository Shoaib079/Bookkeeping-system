# POSTING-SERVICE-01 — PS-P6 Planning Audit (final extraction cluster)

**Phase:** PS-P6 planning (audit only — no code changes)
**Predecessors:** PS-P0…PS-P5 complete; baseline 1767 passed, 2 xfailed; working tree clean; all audit docs committed
**Purpose:** Plan the last extraction cluster — partner/worker movements, profit allocation, year-end/period close, the reconciliation posting boundary — and resolve TD-POSTING-05.
**Headline:** **GO**, but **centralize TD-POSTING-05 first (PS-P6-0)** as a behavior-preserving refactor. Extract movement families → profit allocation → close chains last. Then **stop before TD-PS-01** and do the cross-cutting transaction/DTO/company_id cleanup as a single dedicated phase.

---

## 1. Remaining posting surface table

| Function | app.py | JE ref types | BankTransaction | BankAccount.balance | Partner/Worker balance | cq | user param | Commit | Audit |
|----------|--------|--------------|-----------------|---------------------|------------------------|----|-----------|--------|-------|
| `post_partner_movement` | `:6507` | `PartnerCapital/Drawing/Salary/Advance/AdvanceOffset` (5-branch) | **creates** | **± mutates** | via current/advance accts (JE) | yes (YEC, `session.get`) | `created_by_id` | kernel + explicit | `log_audit` |
| `void_partner_movement` | `:6613` | reverses above | **voids** | **± reverses** | — | yes (YEC) | `voider_id` | explicit | `log_audit` |
| `post_worker_movement` | `:7444` | `WorkerSalary/Advance/Repayment` (multi-line: salary/deduction/advance-recovery) | **creates** (if cash_out>0) | **± mutates** | `get_worker_advance_balance` check | yes (YEC) | `created_by_id` | kernel + explicit | `log_audit` |
| `void_worker_movement` | `:7615` | reverses above | **voids** | **± reverses** | — | yes (YEC) | `voider_id` | explicit | `log_audit` |
| `allocate_profit_to_partners` | `:7704` | `ProfitAllocation` (Dr/Cr RE ↔ partner current; dated **today**) | none | none | partner current accts (JE) + `PartnerProfitAllocationLine` | yes | `allocated_by_id` | kernel + explicit | `log_audit` |
| `void_profit_allocation` | `:7798` | reverses `ProfitAllocation` (today-dated reversal) | none | none | — | yes (YEC Guard 3) | `voider_id` | explicit | `log_audit` |
| `_allocate_all_pending` | `:7836` | (orchestrates `allocate_profit_to_partners`) | none | none | — | yes | `allocated_by_id` | per-allocation | — |
| `close_fiscal_period` | `:8486` | `PeriodClose` (closing JE → RE) | none | none | RE roll-up | yes | — | workflow | `log_audit` |
| year-end close creation/posting | `:8500+` (UI-driven) | `YearEndClose`/`PeriodClose` + RE | none | none | RE roll-up; creates `YearEndClose` lock | yes | owner | multi-step workflow | `log_audit` |
| `void_year_end_close` | done in PS-P5-4? (`:8150`) | none (flag/lock) | none | none | — | `session.get` | `voider_id` | explicit | `log_audit` |
| `reconciliation/match_post.py` posters (×8) | module | `DepositClearing`/`GenericDeposit`/`PartnerStmt`/`WorkerStmt`/`EquityStmt`/`VendorOutflow`/`BankCharge` | varies | varies | varies | via `app` | varies | via `app.create_journal_entry` (lazy `_app()`) | per-match |

(`void_year_end_close`, `void_reconciliation`, `void_eod_close` were the PS-P5-4 flag-only wave — listed here only for the close-chain context.)

---

## 2. TD-POSTING-05 guard map

The shared/centralized guard lives in `services.posting.entry_date_posting_blocked` (and app shim `_entry_date_posting_blocked`): blocks a closed `FiscalPeriod` **and** a non-void `YearEndClose` spanning `entry_date`. It runs **inside `create_journal_entry`**.

**Duplicate inline YEC guards (the TD-POSTING-05 instances):**

| # | Location | app.py | Message | Side |
|---|----------|--------|---------|------|
| 1 | `post_partner_movement` (Guard 4) | `:6521` | "Year {y} is closed. Cannot post movements dated in that year." | post |
| 2 | `void_partner_movement` (Guard 5) | `:6622` | "Year {y} is closed. Void the year-end close before voiding movements inside it." | void |
| 3 | `post_worker_movement` | `:7467` | "…Cannot post movements dated in that year." | post |
| 4 | `void_worker_movement` | `:7623` | "…Void the year-end close before voiding…" | void |
| 5 | `void_profit_allocation` (Guard 3) | `:7809` | "…Void the year-end close before voiding allocations inside it." | void |
| — | UI period-reopen block (`_yec_guard`) | `:9093` | locale `fiscal.year_closed_reopen_block` | UI gate (not a posting fn) |

**Critical behavioral distinction — the inline guards are NOT all redundant:**

- **Post-side guards (#1, #3):** *semi-redundant.* The kernel guard would also block (the movement JE uses the movement `date`), but only **after** the `BankTransaction` + movement record + balance mutation are already created — leaving churn that `create_journal_entry`'s `rollback()` then discards, and returning the wrong shape. The inline guard gives a clean early `(None, err)` with a friendlier message **before** any side effect.
- **Void-side guards (#2, #4, #5):** **NOT redundant — must be preserved.** Reversals are posted via `create_reversing_journal_entry`, which dates the reversal **`datetime.date.today()`**, not the original movement/period date. So the kernel guard checks **today** against closed years and will **not** catch a movement/allocation whose *original* date lies in a closed prior year. The inline void guards check the **original date's** year. Removing them would silently allow voiding inside a closed year.

This is the trap: any "dedup" that routes voids through the kernel guard alone **changes behavior**.

**Safest centralization strategy (behavior-preserving):**
1. Add a shared, pure helper in `services.posting`, e.g. `yec_block_message(session, date, *, mode, company_id)` returning the **post** vs **void** message variant (preserve both exact strings), querying non-void `YearEndClose` spanning `date`.
2. Replace the 5 inline guards with calls to it — keeping **all 5 call sites** and the **original-date** argument for the void sites (never the reversal's today-date).
3. Do **not** remove any guard; this is dedup of the query, not removal of the check.

---

## 3. Recommended PS-P6 sequence

| Wave | Content | Notes |
|------|---------|-------|
| **PS-P6-0a** | Add `yec_block_message` (pure) to `services.posting` — **additive, no call-site change** | zero behavioral risk; characterize both message variants |
| **PS-P6-0b** | Refactor the 5 inline guards (#1–#5) to call it — **behavior-preserving** | needs §2 characterization (esp. void original-date semantics) |
| **PS-P6-1** | Partner movement family: `post_partner_movement` + `void_partner_movement` | BankTransaction + balance + 5-branch JE; verbatim move incl. now-centralized guard call |
| **PS-P6-2** | Worker movement family: `post_worker_movement` + `void_worker_movement` | mirrors partner; multi-line salary/deduction/advance JE |
| **PS-P6-3** | Profit allocation: `allocate_profit_to_partners` + `void_profit_allocation` (+ `_allocate_all_pending`) | RE ↔ partner-current JE; period-net-income derivation; no BankTransaction |
| **PS-P6-4** | Close chains: `close_fiscal_period`, year-end-close creation/posting, RE roll-up | **highest complexity**; multi-step workflow; move LAST |
| **PS-P6-5** | Reconciliation boundary: rewrite `reconciliation/match_post.py` `_app()` calls → direct `services.posting` imports | low-risk import rewrite; no behavior change |

---

## 4. What must be characterized before each wave

- **Before PS-P6-0b:** the 5 guard messages (post vs void wording) **and** the void original-date-vs-reversal-today-date distinction — a test that voids a movement dated in a closed prior year and asserts the inline guard (not the kernel) blocks it.
- **Before PS-P6-1/-2 (movements):** post — BankTransaction creation + `BankAccount.balance` delta + each JE branch's line tuples + `(id, err)` returns + partial-state-avoidance on guard; void — BankTransaction void + balance reversal + commit count + `log_audit`. (Partner: `test_partner_statement_p1–p4`, `test_partner_ux_*`; Worker: `test_workers.py` — confirm branch + balance coverage; add commit-count pins.)
- **Before PS-P6-3 (allocation):** profit vs loss line orientation, last-partner rounding remainder, period-net-income-from-JE derivation, "already allocated"/"period not closed"/"no closing JE" guards, today-dated JE. (`void_profit_allocation`: YEC Guard 3 original-date.)
- **Before PS-P6-4 (close):** closing-JE → RE roll-up, period-close lock, YEC creation snapshot fields (`net_income_snapshot`, `re_balance_at_close`, `period_count`, `allocation_count`), reopen behavior. Highest characterization need.
- **Before PS-P6-5 (recon):** the 8 match_post posters already have reconciliation tests; add a contract test that they post identical JEs after the import switch.

---

## 5. What must NOT be moved yet

- **The forward year-end-close creation/posting + `close_fiscal_period` + RE roll-up (PS-P6-4)** until movements + allocation + guard centralization are done — it sits atop all of them.
- **Any void-side YEC-guarded function before PS-P6-0** — extracting verbatim first would freeze duplicate guard queries into the service, then require a second dedup pass.
- **`reconciliation/match_post.py`** rewrite before the kernel is otherwise stable (it's last, PS-P6-5).
- **No TD-PS-01 / TD-PS-03 / TD-PS-06 / TD-PS-07 changes** interleaved with any wave — verbatim moves only.

---

## 6. Must TD-POSTING-05 centralization happen before extraction?

**Yes — PS-P6-0 must precede PS-P6-1.** Rationale:
- Extracting the families verbatim first would copy **5 inline guard queries** into `services.posting`, then force a dedup pass across already-moved code (more churn, more risk).
- Centralizing first means each family extraction moves a function that already calls one shared, characterized guard helper.
- The centralization is **decomposed for safety**: PS-P6-0a is purely additive (no behavior change); PS-P6-0b is behavior-preserving and gated on the §2 characterization (the void original-date semantics is the one place a careless dedup breaks behavior).

It is the single highest-leverage, must-do-first item of PS-P6.

---

## 7. Recommended stopping point before TD-PS-01 transaction cleanup

**Stop when 100% of posting/void logic lives in `services.posting` (commits still internal, verbatim), i.e. at the end of PS-P6-5.** Do **not** interleave TD-PS-01.

TD-PS-01 (boundary-owned transactions / flush-only) is a cross-cutting rewrite that touches every extracted function's commit semantics. It is far safer to perform **once** against the fully assembled service layer than to convert functions piecemeal as they move. The same applies to TD-PS-03 (DTO return) and TD-PS-06/-07 (`company_id` unification). Bundle these into a dedicated **PS-P7 "service hardening"** phase after PS-P6 completes.

So the line is: **PS-P6 = finish moving everything (verbatim); PS-P7 = commit ownership + DTO + company_id unification + YEC-guard semantics finalization.**

---

## 8. Updated migration-readiness estimate

| Milestone | Domain coverage | Boundary-ready (FastAPI) |
|-----------|-----------------|--------------------------|
| After PS-P5 (now) | ~82% | ~70% of extracted code |
| After PS-P6-0…3 (movements + allocation) | ~90% | ~70% (cleanups deferred) |
| After PS-P6-4/-5 (close chains + recon) | **~98%** | ~70% |
| After PS-P7 (TD-PS-01/-03/-06/-07) | ~100% | **~95%** |

PS-P6 brings the *structural* extraction to near-complete; **boundary-readiness stays flat (~70%) until PS-P7**, because internal commits (TD-PS-01) and ORM returns (TD-PS-03) are the true FastAPI gates and are intentionally untouched during extraction.

---

## 9. Go / No-Go

| Decision | Verdict |
|----------|---------|
| PS-P6-0a (add pure `yec_block_message`) then PS-P6-0b (refactor 5 guards), after §2/§4 characterization | **GO** |
| PS-P6-1/-2/-3 (movements, allocation) verbatim after PS-P6-0 + per-wave CHAR | **GO** |
| PS-P6-4 (year-end/period close + RE roll-up) — last, after heavy CHAR | **GO (with care)** |
| PS-P6-5 (recon `_app()` → direct import) | **GO** (low risk; last) |
| Extract any void-side YEC-guarded function before PS-P6-0 | **NO-GO** — freezes duplicate guards |
| Route void guards through the kernel (today-date) guard alone | **NO-GO** — changes behavior (misses original-date closed-year voids) |
| Start TD-PS-01 / TD-PS-03 / TD-PS-06 / TD-PS-07 during PS-P6 | **NO-GO** — defer to PS-P7 against the assembled service layer |

---

*Audit only. No code modified. Recommend a docs-only reconciliation of the still-missing PS-P2c/PS-P3 entries in `CASCADE_MAP`/`AUDIT_HISTORY`, and registering the PS-P7 hardening phase (TD-PS-01/-03/-06/-07 + TD-POSTING-05 finalization) in `TECH_DEBT_AND_MIGRATION_CLEANUP.md`.*
