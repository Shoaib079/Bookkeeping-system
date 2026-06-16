# P2-HARDEN-01-H03 — Systemic API company-stamp hook: Audit

**Mode:** Audit only. **No production code, no hook implementation, no schema change, no route change, no feature-flag change.** Decides whether a systemic API `before_flush` company-stamp hook (driven by a `RequestContext.company_id` contextvar) is still needed after H01/H02 proved explicit service-layer stamping works.

## Recommendation

**DEFER — and reject the "silent auto-stamp" form outright.** Do **not** add an auto-stamping `before_flush` hook now. **Keep explicit service-layer `company_id` stamping as the standard.** If any systemic net is ever added, it must be a **fail-loud guard** (raise on a NULL tenant `company_id` at flush), **not** a silent auto-fill, and it should be introduced **at the FastAPI runtime cutover** — when sessions are API-owned — not now.

## 1. Evidence

- **`RequestContext` is explicit — there is no contextvar.** `services/context.py:47-63` defines a frozen dataclass passed explicitly into services; H03's premise ("before_flush from `RequestContext.company_id` contextvar") would require **introducing a new `ContextVar`** — net-new ambient machinery, not the wiring of something that exists.
- **The API session is clean — no listener registered.** `api/dependencies.py:26-32` `get_db()` yields a bare `SessionLocal()` and closes without committing; **no `before_flush` is attached to the API session.** The Streamlit `before_flush` (`app.py` `_stamp_company_id_on_new_objects`) reads the Streamlit ambient company and is a **no-op on API requests** (confirmed in P2-HARDEN-01).
- **Write services already stamp explicitly and pervasively.** `company_id=company_id` is passed at construction throughout `services/write_banking.py`, `write_expenses.py`, `write_closing.py`, `write_partner_worker.py`, etc. (dozens of sites).
- **The only NULL-risk rows are already covered by the H01a tactical stamps.** `write_partner_worker._stamp_company_on_movement` (stamps the kernel-created `PartnerMovement` + its linked `BankTransaction`, `:134-150`) and `write_closing.allocate` (`if allocation.company_id is None: allocation.company_id = company_id`, `:153-154`). No remaining family creates a tenant row without a company_id.
- **The matrix already passes without a hook.** H01 (`test_p2_harden_01_company_stamp_matrix`) is green with explicit stamping; H02 removed the misleading P2 fixture hooks. There is **no failing case** for H03 to fix.

## 2. Risk analysis

| Concern | A silent auto-stamp hook | Explicit stamping (status quo) |
|---|---|---|
| **Hides missing-stamp bugs (Q3)** | **Yes — the core danger.** A hook that auto-fills NULL `company_id` makes a service that *forgot* to stamp pass silently; the matrix tests would stay green even if explicit stamping were deleted. A loud, test-catchable tenant-isolation defect becomes invisible. | Bugs surface loudly: a missing stamp leaves NULL and the matrix/isolation tests fail at the call site. |
| **Conflicts with explicit-context design (Q6)** | Reintroduces **ambient state** via a `ContextVar` — the exact pattern FastAPI-P0 removed in favor of explicit `RequestContext`. Two sources of truth (explicit arg vs ambient var) can diverge. | Single source of truth: the `company_id` passed to the service. |
| **Concurrency / leakage** | A request-scoped `ContextVar` must be set/reset perfectly per request; a missed reset on a reused worker can **leak one tenant's company_id into another request** — a cross-tenant hazard. | None — no shared ambient state. |
| **Clobber/ordering** | Must never override an explicitly-set `company_id`; ordering vs. the kernel's own writes adds surface. | None. |
| **Benefit** | Marginal defense-in-depth for a class of bug the tests already catch. | — |

**Net:** for an auto-stamp hook, **cost > benefit now**. It would mask the very bugs the H01 matrix exists to catch and re-introduce ambient state the architecture deliberately removed.

## 3. Answers to the questions

1. **Is H03 needed now?** **No.** Explicit stamping covers every P2 write family; the matrix is green without it; there is no failing case.
2. **Should the API use a before_flush safety net anyway?** **Not as an auto-stamp.** At most, a **fail-loud guard** (raise on NULL tenant company_id) could be considered later — and only at the FastAPI runtime cutover.
3. **Would a hook hide missing explicit company_id bugs?** **Yes** — a silent auto-stamp converts a test-catchable defect into an invisible one and erodes the matrix guarantee. This is the decisive reason to reject the auto-stamp form.
4. **Should the standard remain explicit company_id stamping?** **Yes** — it is migration-safe, FastAPI/React-ready, auditable, single-source-of-truth, and test-enforced (aligns with ARCHITECTURE-PROTECTION-01 / MIGRATION-READINESS-01).
5. **What tests if H03 is implemented?** See §4 — but only for a **fail-loud** guard.

## 4. Contract tests *if* H03 is ever implemented (as a fail-loud guard, later)

- **Fail-loud, never silent:** a service that omits the stamp **still fails** a "no NULL tenant company_id" assertion — the guard **raises** at flush, it does not auto-fill. (Proves the guard surfaces bugs rather than hiding them.)
- **No clobber:** the guard never overrides an explicitly-set `company_id`.
- **ContextVar isolation:** concurrent/sequential requests do not leak `company_id`; the var is set and **reset per request** (no cross-request bleed on a reused worker).
- **Parity:** with the guard active, the H01 stamp matrix and all `test_fastapi_p2_*` suites still pass; no behavior change for already-correct services.
- **API-session scope:** the guard applies only to API-owned sessions and does not double-act with the Streamlit ambient hook.

## 5. Roadmap update recommendation

- Record **P2-HARDEN-01-H03 = DEFERRED** (auto-stamp form **rejected**) under the P2-HARDEN track.
- State the standing rule explicitly: **explicit service-layer `company_id` stamping is the standard**; the H01 matrix is the guarantee; the H01a tactical stamps cover kernel-created rows.
- Revisit **only at the FastAPI runtime cutover**, and **only** as a **fail-loud guard** (raise on NULL tenant company_id), never as a silent auto-stamp — with the §4 tests as the acceptance gate.

## Test run note

The task lists `pytest tests/test_p2_harden_01_company_stamp_matrix.py`, `pytest tests/test_fastapi_p2_*`, and `pytest`. These are **already green in the repo** (H01/H02) and this audit changes **no code**, so they remain green. pytest cannot execute in this sandbox (no `sqlalchemy`), so run them locally to confirm; this audit adds only a doc + a pure-stdlib doc-contract test.

## No-change statement (P2-HARDEN-01-H03 audit)

- **No production code, no hook, no schema change, no route change, no feature-flag change, no `app.py`/`api`/`services` edit.** Recommendation + evidence + risk analysis + conditional contract tests + roadmap recommendation only.

---

*Audit only. H03 is **not needed now**: `RequestContext` is explicit (no contextvar), `get_db()` yields a clean session with no before_flush, and the write services stamp `company_id` explicitly everywhere (with the H01a tactical stamps covering the only kernel-created NULL-risk rows). The H01 matrix is green without a hook and H02 removed the misleading fixtures. Recommendation: **DEFER**, and **reject the silent auto-stamp form** — it would hide missing-stamp bugs (making the matrix pass even if explicit stamping were deleted) and reintroduce ambient state (contextvar) that the explicit-RequestContext design removed, plus cross-request leakage risk. Keep explicit stamping as the standard. If any net is ever added, make it a **fail-loud guard** (raise on NULL tenant company_id) at the FastAPI runtime cutover, with no-clobber + contextvar-isolation + parity tests. Risk of acting now > benefit.*
