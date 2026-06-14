# FASTAPI-P0.5 — Posting Hardening Characterization (TD-PS-01/03/06/07)

**Mode:** Characterization only. No code, no implementation. Preserve accounting behavior exactly.
**Inputs:** `docs/FASTAPI_P0_SERVICE_HARDENING_PLAN.md`, `docs/FASTAPI_MIGRATION_01_AUDIT.md`, `services/posting.py`, `services/audit.py`, `services/context.py`.
**Scope:** commit ownership (TD-PS-01), DTO return (TD-PS-03), company-scoping split (TD-PS-06/07), reconciliation company-stamp.

---

## 1. Commit ownership inventory

Every transaction boundary currently in the posting path (`services/posting.py` + `services/audit.py` + the reconciliation orchestrators):

| Function | flush | rollback | commit | returns |
|----------|-------|----------|--------|---------|
| `create_journal_entry` (`:246`) | `:287` (after add lines) | `:275` (period/YEC guard), `:308` (imbalance) | **`:315`** (per JE) | ORM `entry` |
| `post_*_sale` / `post_expense` / `post_purchase` / `post_payable_*` | — | — | via `create_journal_entry` | None |
| `post_receivable_payment` (`:447`) | — | — | `create_journal_entry` (1) + **extra `:513`** (sale balance) | error `str`/None |
| `sync_company_cc_subledger` | flush only | — | **none** (rides caller's next commit) | None |
| `void_*` (expense/payable/purchase/bank_txn/inventory/equity/partner/worker/profit-alloc/yec) | — | — | reverse-JE commits (in kernel, per reversed JE) + **explicit flag commit** | `bool` / error `str` |
| `allocate_profit_to_partners` | flush | — | `create_journal_entry` (1) + **explicit commit** | `(id, err)` |
| `close_fiscal_period` (`:2073`) | — | — | `create_journal_entry` (1) + **`:2143`** | ORM `je` |
| `perform_year_end_close` (`:2147`) | — | — | **`:2360`** (no JE) | `(yec_id, warnings, err)` |
| `record_audit` (`audit.py:49`) | — | — | **`:70`** (per audit row) | ORM `AuditLog` |

**Pinned commit counts (from prior CHARs — the contract):**
- post sale/expense/purchase/payable: kernel JE commit + **audit commit** = **2**.
- reconciliation posters (`match_post`): kernel JE commit + final commit per row = **2/row**.
- `post_receivable_payment`: kernel JE commit + extra sale-balance commit (+ audit if shim audits) .
- `close_fiscal_period`: JE commit + explicit + audit = **3**.
- `perform_year_end_close`: explicit + audit = **2** (no JE).
- `void_expense` (unpaid): reversal + flag + audit = **3**; `void_purchase` (paid cascade): **4**.

**Audit interaction:** `record_audit` **commits** (P0.3 deliberately kept legacy ownership) — it is the *trailing* commit in every count above. Any TD-PS-01 conversion **must convert audit's commit too**, or atomicity is lost (audit would commit independently of the entity).

**Reconciliation interaction:** `match_post` posters call the **app shim** `create_journal_entry` (→ kernel commit) then their own `session.commit()` per row; they create the `BankTransaction` + mutate `BankAccount.balance` in the same row scope. The JE is stamped with the **ambient** company (shim) while the row/txn records use the **explicit** `company_id` (PS-P6-5) — see §3/§4.

## 2. DTO opportunities (TD-PS-03)

Replace ORM / tuple / bare-bool returns at the service boundary with frozen, `to_dict()`-able results (precedent: `user_access.MutationResult`, `CompanyMemberView`).

| Result DTO | Replaces | Fields (characterized from current behavior) |
|------------|----------|----------------------------------------------|
| **`PostingResult`** | ORM `entry`/`je` from `create_journal_entry` / `close_fiscal_period` | `je_id, reference_type, reference_id, entry_date, company_id, lines[], currency` |
| **`VoidResult`** | `bool` from `void_*` | `voided: bool, reversal_je_ids[], cascade[] (e.g. linked payable), reason` |
| **`PaymentResult`** | error `str`/None from `post_receivable_payment` | `je_id, applied_amount, fx_gain_loss, sale_balance_after, error` |
| **`AllocationResult`** | `(id, err)` from `allocate_profit_to_partners` | `allocation_id, je_id, per_partner[], net_income, error` |
| **`YearEndCloseResult`** | `(yec_id, warnings, err)` from `perform_year_end_close` | `yec_id, warnings[(key,msg)], error` (already structured — formalize) |
| **`PeriodCloseResult`** | ORM `je` from `close_fiscal_period` | `je_id, period_id, net_income, closing_je_id` |
| **`MatchPostResult`** | dicts from `match_post` posters | already dict-shaped → formalize the keys |

**Approach:** **additive** — return the DTO *alongside* the legacy ORM/tuple first; new consumers use the DTO; legacy callers keep the old shape until they migrate. No behavior change.

## 3. Ambient company usage

| Location | Form | Real ambient leak? |
|----------|------|--------------------|
| `services` — `resolve_payment_credit_account` (`:516`) | **`company_id` vs `gl_company_id` split** (TD-PS-06): CC-enabled gate uses `company_id or gl_company_id`; GL lookup uses `gl_company_id` only | **Yes (vestigial)** — exists only so the app shim can inject `_current_company_id()` as `gl_company_id` |
| `services` — `sync_company_cc_subledger` | **`ambient_company_id` param** (TD-PS-07) | **Yes (vestigial)** — same: shim injects ambient |
| `app.py` shims | pass `gl_company_id=_current_company_id()`, `ambient_company_id=_current_company_id()` | **Yes** — the actual ambient *read* |
| `app.py` | `_current_company_id()`, `cq()` (`current_company_required`) | tenant scoping; ambient by design |
| `reconciliation/match_post` | JE stamped via shim `create_journal_entry` (ambient company) while records use explicit `company_id` | **Yes (correctness bug)** — PS-P6-5 |

**Key read:** the *service kernel* is already explicit (`company_id` params); the ambient surface is (a) the **split params** that exist only to carry ambient from the shims, and (b) the **reconciliation JE stamp**. Collapsing the split to a single explicit `company_id` and fixing the recon stamp removes ambient from the write path entirely.

## 4. Multi-tenant risks

1. **`gl_company_id` ≠ `company_id` divergence (TD-PS-06):** the CC-enabled gate is checked against one company while the "Credit Card Payable" GL is resolved under another (the ambient). In a multi-tenant API with a wrong/missing ambient, the gate and the GL could reference different tenants. Today masked because both equal the active company.
2. **Reconciliation JE ambient stamp (PS-P6-5):** statement JE company comes from the shim's ambient `_current_company_id()` while the `BankTransaction`/movement records carry the explicit `company_id`. If they diverge, the JE is mis-stamped to the wrong tenant. **A real correctness bug to fix before API writes.**
3. **`sync_company_cc_subledger` ambient fallback (TD-PS-07):** `company_id or ambient_company_id` — same class.
4. **Batch / partial-commit across tenants:** because each row commits independently (reconciliation batch, void cascades), a wrong context mid-iteration would persist rows under the wrong tenant with no rollback (TD-PS-04 interaction).

## 5. Safe migration sequence (additive → behavior-preserving → deepest last)

1. **TD-PS-03 `PostingResult`/`VoidResult`/… (additive).** Return DTOs alongside ORM/tuples. Zero behavior change.
2. **TD-PS-06/07 company-scoping unification.** Collapse `gl_company_id`/`ambient_company_id` into a single explicit `company_id` sourced from `RequestContext`; remove the ambient fallback. Behavior-preserving for single-company; add multi-tenant isolation tests.
3. **Reconciliation company-stamp fix.** Route the statement JE company from the **explicit** `company_id` `match_post` already holds (not the shim ambient). Characterize current, then assert consistent stamping.
4. **TD-PS-01 commit ownership (deepest; last).** Convert kernel + `void_*` + close/allocation **and `record_audit`** to **flush-only**, with a unit-of-work boundary (Streamlit shim now, API request later) owning the single commit. TD-PS-04 (rollback discards caller work) resolves here.

Rationale: DTOs and company unification de-risk the call sites; the commit-ownership change — which alters *observable commit counts* — goes last, once everything it touches is otherwise stable.

## 6. Feature-flag opportunities

- **Commit-ownership flag** (`internal-commit` vs `flush-only + boundary commit`) — per-call-family toggle so TD-PS-01 rolls out **reversibly** behind Streamlit (e.g., enable for the sales family first, then expense/purchase/payable, then voids, then close/allocation).
- **DTO-return flag** is unnecessary (additive — both shapes coexist).
- **Reconciliation-stamp fix** can ship behind a flag that asserts JE/record company equality and falls back to log-and-warn during bake-in.

## 7. Tests required before TD-PS-01

1. **Commit-point characterization** — assert, per family, the current commit/flush/rollback sequence and counts (the pins in §1) *before* any change.
2. **Re-pin as persisted-state + boundary commit** — TD-PS-01 *changes the commit count* (batched at the boundary), so the count tests must be **re-expressed** to assert: identical net persisted rows/balances + exactly **one** boundary commit + audit row present. (You cannot keep both internal-per-JE and boundary commit — the contract shape changes; net persistence must not.)
3. **Audit atomicity** — audit row commits **with** the entity under the new boundary (no independent audit commit); one audit per posted/voided row preserved.
4. **Rollback / partial-failure (TD-PS-04)** — a guard failure (closed period/YEC) rolls back the *whole* unit of work, not just the JE; reconciliation batch partial-failure semantics characterized under the boundary.
5. **DTO parity** — each `*Result` mirrors the ORM/tuple it replaces, field-for-field.
6. **Company unification isolation** — `resolve_payment_credit_account` + `sync_company_cc_subledger` resolve gate and GL under the **same** explicit company; cross-tenant data cannot leak; reconciliation JE and records share `company_id`.
7. **GL invariants unchanged** — line tuples, debit/credit orientation, error strings, YEC-guard semantics, float accumulation order — byte-identical across all four TDs.

---

## What must not change

- GL line tuples, debit/credit orientation, reference types, dates, float accumulation order.
- Error strings (`MatchPostError`, kernel `ValueError`), YEC-guard semantics.
- **Net persisted state** of every flow (the commit *mechanism* changes under TD-PS-01; the *result* must not).
- One-audit-per-row cardinality; audit row content.
- Single-company behavior throughout (company unification is invisible to single-tenant use).

---

*Characterization only. No code, no implementation, accounting behavior preserved. The service kernel is already explicit-`company_id`; the remaining hardening is: DTOs (additive), collapse the `gl_company_id`/`ambient_company_id` split + fix the reconciliation ambient JE stamp (behavior-preserving, multi-tenant correctness), and — last, behind a per-family flag — convert internal commits (incl. `record_audit`) to a single boundary-owned commit, re-expressing the pinned commit counts as persisted-state assertions.*
