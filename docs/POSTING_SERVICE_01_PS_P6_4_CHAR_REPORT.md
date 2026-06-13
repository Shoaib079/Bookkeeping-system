# POSTING-SERVICE-01 — PS-P6-4 Characterization Report

**Mode:** CHARACTERIZATION ONLY — no extraction, no cleanup, no refactor, no patch.
**Baseline:** `main`, clean tree, commit `52f1dd8 "Move profit allocation posting to service"`; tests 1852 passed, 2 xfailed.
**Scope:** period close / fiscal close / retained-earnings / year-end-close posting chains + related helpers.
**Goal:** freeze current behavior (incl. bugs, commit counts, return contracts, error strings, audit, company scoping, YEC-guard behavior) before any PS-P6-4 extraction.

---

## 1. Function inventory

**In scope — still real in `app.py` (extraction targets):**

| Function | app.py | Role | GL? |
|----------|--------|------|-----|
| `close_fiscal_period` | `:8107` | Posts the period closing JE; locks the period | **yes** (`PeriodClose`) |
| `perform_year_end_close` | `:7531` | Validates the year, creates the `YearEndClose` lock record | **no JE** |
| `_check_period_continuity` | `:7484` | Helper: gap/coverage check over the year | read-only `cq` |
| `_get_year_bounds` | `:7478` | Helper: `(Jan 1, Dec 31)` for a fiscal year string | pure |

**Already in `services/posting.py` (app.py keeps shims) — consumed by the chain:**
`create_journal_entry` (shim `:1590`), `get_account_by_name` (shim `:2517`), `_validate_partner_shares` (shim `:7407`), `_get_period_net_income_from_je` (shim `:7414`), `allocate_profit_to_partners` / `void_profit_allocation` / `_allocate_all_pending` (shims `:7421/:7447/:7469`, PS-P6-3), `void_year_end_close` (shim `:7731`, PS-P5-4).

**App-only helpers used (NOT extracted — read-only / cross-cutting):**
`calculate_account_balance` (`:2549`), `calculate_account_balance_for_period` (`:2520`, supports `exclude_refs`), `log_audit` (`:1557`, ambient `_current_user` + commits), `cq` (company-scoped query).

**Remaining posting functions outside `services/posting.py`:** `close_fiscal_period` and `perform_year_end_close` are the **last GL-adjacent close functions** still in app.py. (Reconciliation `match_post.py` posters remain on the lazy-`_app()` boundary — out of PS-P6-4 scope.)

---

## 2. Call graph

```
UI: render_year_end_close (:8175) ──► perform_year_end_close(session, fiscal_year, closed_by_id, notes, acknowledged_warnings)   [call site :8433]
UI: fiscal-period page (:8747+) ────► close_fiscal_period(session, period_id)                                                  [call site :8755]

close_fiscal_period
  ├─ session.get(FiscalPeriod)                       guard → raise ValueError
  ├─ get_account_by_name("Retained Earnings")        guard → raise ValueError       [shim → service, ambient company]
  ├─ cq(ChartOfAccounts).filter_by(is_active=True)   [company-scoped]
  ├─ calculate_account_balance_for_period(acct, start, end, exclude_refs=["PeriodClose"])   per Income/Expense acct
  ├─ create_journal_entry(end_date, "Period Close: {name}", "PeriodClose", period_id, lines) [shim → service; COMMIT #1 in kernel]
  ├─ period.is_closed=True; closed_at=today; closing_je_id=je.id
  ├─ session.commit()                                 [COMMIT #2]
  └─ log_audit("PeriodClose","FiscalPeriod",period_id,…)   [COMMIT #3, success only]

perform_year_end_close
  ├─ _get_year_bounds(fiscal_year)
  ├─ _check_period_continuity(...)                    Hard Block 1 → return (None, [], err)
  ├─ cq(YearEndClose) dup check                       Hard Block 2 → (None, [], err)
  ├─ cq(FiscalPeriod) open-period check               Hard Block 3 → (None, [], err)
  ├─ cq(PartnerProfitAllocation) per period           Hard Block 4 → (None, [], err)
  ├─ _validate_partner_shares()                       Hard Block 5 → (None, [], err)   [shim → service]
  ├─ cq(JournalEntryLine) TB sum                      Hard Block 6 → (None, [], err)
  ├─ soft warnings: get_account_by_name + calculate_account_balance (RE, OBE, partner advances, legacy 3000/3200),
  │                 cq(DailyCashReconciliation), cq(EndOfDayClose)
  ├─ unacked warnings → return (None, warnings, "")   [NO commit]
  ├─ net_income_snapshot = Σ _get_period_net_income_from_je(p)   [shim → service]
  ├─ session.add(YearEndClose(...)); session.commit() [COMMIT #1]   (NO create_journal_entry)
  └─ log_audit("YearEndClose","YearEndClose",yec.id,…)            [COMMIT #2, success only]
```

**Rollback paths:** none explicit in either function. `close_fiscal_period` raises **before** any commit on its three guards; `create_journal_entry` owns its own rollback internally (TD-PS-01). `PeriodClose` is exempt from the kernel **FiscalPeriod** lock; the kernel **YEC** guard still applies (not reached in normal close).

---

## 3. Posting behavior

**`close_fiscal_period`:**
- `reference_type = "PeriodClose"`, `reference_id = period_id`, `entry_date = period.end_date`.
- Lines: for each active Income account with `bal > 0.005` → `(acct, Dr=bal, 0)` (zeroes the credit balance); for each Expense account with `bal > 0.005` → `(acct, 0, Cr=bal)`.
- `net_income = total_income − total_expense`; **profit** (`> 0.005`) → `Cr Retained Earnings`; **loss** (`< −0.005`) → `Dr Retained Earnings`; exactly-zero → no RE line.
- Balances derived via `calculate_account_balance_for_period(..., exclude_refs=["PeriodClose"])` — **excludes prior PeriodClose JEs** (preserve this).

**`perform_year_end_close`:**
- **Posts NO journal entry.** RE roll-up happens at *period* close, not year-end. Year-end only validates + creates the `YearEndClose` lock record. RE residual is a **soft warning**, never auto-posted.

**Retained-earnings logic:** RE is credited/debited only inside `close_fiscal_period`'s net-income line. Year-end snapshots `re_balance_at_close = calculate_account_balance(RE)` but does not post to it.

---

## 4. Commit ownership

| Path | `session.commit()` locations | Count |
|------|------------------------------|-------|
| `close_fiscal_period` success | kernel commit in `create_journal_entry` (#1) + explicit `:8165` (#2) + `log_audit` (#3) | **3** |
| `close_fiscal_period` failure (any of 3 guards) | none — raises `ValueError` before any commit | **0** |
| `perform_year_end_close` success | explicit `:7721` (#1) + `log_audit` (#2); **no kernel commit (no JE)** | **2** |
| `perform_year_end_close` hard block / unacked-warnings | none — returns before commit | **0** |

These counts are part of the contract — pin them before extraction.

---

## 5. Return contracts

| Function | Success | Failure |
|----------|---------|---------|
| `close_fiscal_period` | returns the `JournalEntry` ORM object (`je`) | **raises `ValueError`** (no tuple/None) |
| `perform_year_end_close` | `(yec_id: int, warnings: list[(key,msg)], "")` | hard block → `(None, [], err)`; unacked warnings → `(None, warnings, "")` |
| `_check_period_continuity` | `""` (ok) | descriptive error `str` |
| `_get_year_bounds` | `(date, date)` | — |

Note the asymmetry: `close_fiscal_period` **raises**; `perform_year_end_close` **returns a 3-tuple**. The unacked-warnings case returns an **empty error string with a non-empty warnings list and `yec_id=None`** — caller must re-submit with `acknowledged_warnings`.

---

## 6. Error strings (exact)

**`close_fiscal_period` (raised `ValueError`):**
- `"Period not found or already closed."`
- `"Retained Earnings account not found in Chart of Accounts."`
- `"No income or expense activity in this period. Nothing to close."`

**`perform_year_end_close` (returned in tuple):**
- continuity (`_check_period_continuity`): `"No fiscal periods exist for this year ({start} – {end})."`, `"Gap at start of year: {a} to {b} is not covered by any fiscal period."`, `"Gap detected: {a} to {b} is not covered by any fiscal period."`, `"Gap at end of year: {a} to {b} is not covered by any fiscal period."`
- `"Year {fiscal_year} is already closed (Year-End Close #{id})."`
- `"Not all periods are closed. Open: {names}{suffix}."`
- `"Periods missing profit allocation: {names}{suffix}."`
- `"Partner shares invalid: {share_err}"`
- `"Trial Balance is not balanced for year {fiscal_year}: Debit {d:,.2f} vs Credit {c:,.2f}."`

**Soft-warning keys + messages:** `re_residual`, `obe_balance`, `advance_{partner_id}`, `legacy_capital`, `legacy_drawings`, `unresolved_recons`, `stale_eod` (messages as written at `:7629–7691`).

---

## 7. Audit behavior

| Function | `log_audit(action, entity_type, entity_id, desc)` | When |
|----------|---------------------------------------------------|------|
| `close_fiscal_period` | `("PeriodClose", "FiscalPeriod", period_id, "Closed period '{name}' ({s}–{e}). Net income: ${ni:,.2f}. Closing JE #{je.id}.")` | **success only**, after commit |
| `perform_year_end_close` | `("YearEndClose", "YearEndClose", yec.id, "Year {fy} closed. {n} periods, net income {ni:,.2f}, RE at close {re:,.2f}.")` | **success only**, after commit |

Both audits fire **after** the function's own `session.commit()`, so `log_audit`'s internal commit is the trailing commit. No audit on failure/hard-block/unacked paths. `log_audit.performed_by` is the **ambient `_current_user`** — distinct from `closed_by_id` (stored on the YEC record).

---

## 8. Company scoping

- **All scoping is ambient**, via `cq()` (→ `current_company_required()`) and the ambient shims (`get_account_by_name`, `create_journal_entry`, `calculate_account_balance*` use `_current_company_id()`). Neither function takes an explicit `company_id`.
- `close_fiscal_period`: `cq(ChartOfAccounts)` + `calculate_account_balance_for_period` (ambient) + `create_journal_entry` (ambient).
- `perform_year_end_close`: every query is `cq`-scoped (`YearEndClose`, `FiscalPeriod`, `PartnerProfitAllocation`, `JournalEntryLine` TB, `Partner`, `DailyCashReconciliation`, `EndOfDayClose`); `YearEndClose` record gets `company_id` via the `before_flush` stamp hook (not set explicitly).
- **Cross-company risks to preserve on extraction:** the Trial-Balance hard block (`cq(JournalEntryLine)`), the period-continuity scan, and the per-period allocation check are all company-scoped. An extraction that replaces `cq` with `session.query` **without** an explicit `company_id` filter would leak across companies. The `before_flush` company-stamp on the new `YearEndClose` must continue to apply.

---

## 9. YEC guard behavior

- **Neither `close_fiscal_period` nor `perform_year_end_close` calls `yec_block_message`.** They are **not** part of the TD-POSTING-05 inline-guard cluster.
- `perform_year_end_close` *creates* the YEC lock; its own Hard Block 2 (`cq(YearEndClose)` dup check) prevents a second close. `close_fiscal_period` posts `PeriodClose`, which is **exempt from the kernel FiscalPeriod lock** but still subject to the kernel **YEC** guard (not reached in a normal forward close).
- **Implication:** PS-P6-4 introduces no new `yec_block_message` call sites and is independent of the TD-POSTING-05 centralization.

---

## 10. Hidden side effects

**`close_fiscal_period`:** mutates `period.is_closed=True`, `period.closed_at=datetime.date.today()`, `period.closing_je_id=je.id`; creates one `PeriodClose` JE (+ lines). No record reversal.

**`perform_year_end_close`:** creates a `YearEndClose` record with `status="closed"`, `closed_by_id`, `closed_at=now`, `notes` (stripped), `period_count=len(periods)`, `allocation_count=len(periods)` (note: set equal to period count, *not* counted from allocations), `net_income_snapshot=Σ _get_period_net_income_from_je`, `re_balance_at_close`, `warnings_acknowledged_json` (JSON of acknowledged keys or `None`), `is_void=False`. No JE, no mutation of other records. Company stamp via `before_flush`.

**`void_year_end_close` (shim, PS-P5-4):** sets `is_void`, `status="voided"`, `voided_by_id`, `voided_at`, `void_reason` (in service) — reopens the year lock; no GL reversal.

Quirk to preserve: `allocation_count` is derived from `len(periods_in_year)`, not from a count of allocation rows.

---

## 11. Extraction proposal (for the eventual PS-P6-4 — NOT this task)

**Safest boundary:** move `close_fiscal_period`, `perform_year_end_close`, `_check_period_continuity`, `_get_year_bounds` into `services/posting.py` with an explicit `company_id` parameter; app.py keeps shims supplying `current_company_required()` and the trailing `log_audit` (ambient user) on success. **Prerequisite:** the read helpers `calculate_account_balance` / `calculate_account_balance_for_period` must be reachable service-side with explicit `company_id` (extract or parameterize first) — they are the one un-extracted dependency.

**Target service functions:**
- `posting_service.close_fiscal_period(session, period_id, *, company_id) -> JournalEntry` (raises `ValueError`).
- `posting_service.perform_year_end_close(session, fiscal_year, closed_by_id, notes, acknowledged_warnings, *, company_id) -> (yec_id|None, warnings, err)`.

**Files likely touched:** `app.py` (shims), `services/posting.py` (kernels + the two helpers), `tests/` (new char + extraction-proof).

**Tests required before extraction (current gaps):**
- `close_fiscal_period`: exact `PeriodClose` line tuples (Income Dr / Expense Cr / RE net), **profit vs loss** RE orientation, the three raise paths + exact strings, **3-commit count**, period flag mutations, `exclude_refs=["PeriodClose"]` effect, exactly-zero-net (no RE line).
- `perform_year_end_close`: **2-commit count + no-JE assertion**, each soft-warning key/message, the unacked-warnings `(None, warnings, "")` path + re-submit, `net_income_snapshot` derivation, all snapshot fields incl. the `allocation_count = period_count` quirk.
- **Company-scoping isolation** for both (periods/accounts/TB from another company must not leak).
- Existing `tests/test_year_end_close.py` already covers: close success, acknowledged warnings, dup-close block, void/double-void/requires-reason, reclose-after-void, JE/movement/allocation blocked-or-allowed in/out of closed year, gap/missing-start/no-periods/open-period/unallocated/shares-not-100 blocks, `gl_balanced_after_close`, `gl_debit_credit_symmetric_after_close`, permissions.

**Risks:**
1. Ambient company scoping (`cq` + balance calculators) → must parameterize without cross-company leakage.
2. `close_fiscal_period` **raises** (does not return an error) — shim must propagate, not swallow.
3. `calculate_account_balance_for_period(..., exclude_refs=["PeriodClose"])` semantics must be reproduced exactly.
4. `perform_year_end_close`'s read-heavy soft-warning block touches many models — preserve each query + threshold (`0.01`/`0.005`).
5. `before_flush` company-stamp on the new `YearEndClose` record.

**What must NOT change:** `PeriodClose` ref_type and `entry_date=period.end_date`; RE Dr/Cr orientation; the `0.005`/`0.01` thresholds; all exact error strings + soft-warning keys; commit counts (3 close / 2 YEC); the raise-vs-tuple return contracts; `log_audit` action/entity strings; the no-JE nature of year-end close; and the `allocation_count = period_count` quirk.

---

*PS-P6-4 CHAR report — characterization only. No code modified, no patch produced.*
