# FASTAPI-P0 — Service Hardening Plan

**Mode:** Planning only. No API, no DB migration, no React, no implementation in this doc.
**Inputs:** `docs/FASTAPI_MIGRATION_01_AUDIT.md`, `docs/POSTING_SERVICE_01_STATUS.md`.
**Goal:** make the service layer genuinely API-ready **behind the existing Streamlit UI**, with accounting behavior preserved and **tests first** in every workstream.

**P0 invariants (apply to all workstreams):**
- Every change ships **behind Streamlit** — the UI keeps working identically; no endpoint exists yet.
- **Tests first:** characterize current behavior → add contract test → make the change → contract test stays green.
- **Preserve accounting behavior** exactly: GL lines, debits/credits, commit *counts* (pinned by prior CHARs), error strings, audit rows.
- **Additive before subtractive:** introduce new shapes (context, DTOs, services) alongside existing paths before removing the old ones.

---

## Recommended sequencing (safest order)

```
P0.1 RequestContext        (additive value object; zero behavior change)        ── foundation
P0.2 Read services         (read-only extraction; parallelizable; low risk)     ── independent of posting
P0.3 Audit service         (parameterize user_id; commit-ownership decision)    ── needs P0.1
P0.4 Permission boundary   (pure guard reusing user_access; converge _can)      ── needs P0.1
P0.5 Posting hardening     (DTO → company_id unify → recon stamp → commits)     ── heaviest, last; needs P0.1/P0.3
```

Rationale: P0.1 is a no-op-behavior foundation everything else consumes. P0.2 (reads) is the lowest-risk, highest-leverage work and is independent of the write-path hardening, so it can proceed in parallel and de-risks the eventual P1 read API. P0.5 (write-path hardening, incl. TD-PS-01) is the deepest, riskiest change and goes **last**, after context/audit/permission are stable.

---

## WS1 — RequestContext design

**Scope:** a frozen value object carrying `{user_id, company_id, role, effective_permissions}` — the explicit replacement for ambient `_current_user` / `_current_company_id` / `_current_company_role` / `_can`.
**P0 approach (additive):** define the type in a service-neutral module; add a **Streamlit builder** that constructs it from `st.session_state` (reusing `_current_*` + `user_access.resolve_effective_permissions`). Services and new read services accept a `RequestContext` (or its `company_id`/`user_id` fields) explicitly; Streamlit shims supply it. **Do not** remove ambient helpers yet — they back the builder.
**Tests first:** the builder yields the same `(user_id, company_id, role, permissions)` the ambient helpers resolve today, across roles + DEV mode.
**Risk:** Low (additive). **Must not change:** `current_company_required()` fail-loud behavior; permission resolution results.
**Depends on:** nothing. **Unblocks:** P0.3, P0.4, P0.5.

## WS2 — Audit service extraction

**Scope:** move `log_audit` into a service taking **explicit `user_id`** (from `RequestContext`) instead of ambient `_current_user`, with a deliberate **commit-ownership** decision (coordinate with TD-PS-01).
**P0 approach:** extract a `record_audit(session, *, user_id, action, entity_type, entity_id, description)` service; keep an `app.py` shim that supplies `user_id` from the context builder and preserves today's call sites. Decide: does audit commit (current behavior) or flush-and-let-caller-commit? In P0, **preserve current commit behavior** (audit commits) to avoid coupling to TD-PS-01; revisit commit ownership only inside P0.5.
**Tests first:** every existing audit row (action/entity/description/`performed_by`) is byte-identical after extraction; one audit per posted/voided row preserved (per PS-P3/P4 CHARs).
**Risk:** Low–Med (audit is cross-cutting; many call sites). **Must not change:** audit row content, the per-row audit cardinality, success-only audit placement.
**Depends on:** WS1.

## WS3 — Read service extraction (the de-risking core of P0)

**Scope:** lift read/compute logic out of `app.py` render functions into **DTO-returning read services**. Each is read-only (zero JEs), independently shippable behind Streamlit (render fn calls the service, renders its DTO).

| Read service | Source today | DTO |
|--------------|--------------|-----|
| **Reports** (P&L / BS / Cash Flow) | `app.py` render fns + `calculate_account_balance(_for_period)` | `FinancialStatement{lines[], totals}` |
| **Ledger** (transaction ledger) | `app.py` ledger render | `LedgerPage{rows[], page meta}` |
| **Reconciliation readiness** | P2.4 definitions; cockpit/health reads | `ReadinessStatus{level, tie_out, counts, blockers[]}` (enum + reasons) |
| **AR / AP** | `app.py` receivables/payables render | `ARRow[] / APRow[]` (+ aging) |
| **Partner statement** | Partner Statement P2 | `PartnerStatement{opening, movements[], closing}` |

**Shared prerequisite:** extract the **balance read helpers** (`calculate_account_balance`, `_for_period`) into a read service taking explicit `company_id` (they're `app.py` helpers reports depend on). Read-only; no commit.
**P0 approach:** per service — characterize current rendered values → extract compute returning a DTO → render fn consumes the DTO. Take **company_id explicitly** (from `RequestContext`), not ambient.
**Tests first:** DTO values equal the current rendered figures for seeded data; **zero JEs created**; company isolation (no cross-tenant rows).
**Risk:** Low (read-only). The trap is **definition drift** — reuse one balance source; do not re-derive (recall the cockpit-vs-health duplication risk from P2.1/P2.4).
**Depends on:** WS1 (for explicit company_id). Parallelizable across the five services.

## WS4 — Posting hardening dependencies (heaviest; last)

Sub-ordered for safety; each gated on characterization (the commit-count / line-tuple pins from the PS CHARs are the guardrails).

**WS4a — TD-PS-03 `PostingResult` DTO (additive first).**
Introduce a serializable `PostingResult` (je_id, ref_type, lines, company_id, …) returned **alongside** the ORM today; new read/consumers use the DTO; legacy callers keep the ORM until P2. *Tests:* DTO mirrors the ORM entry exactly.

**WS4b — TD-PS-06 / TD-PS-07 company-scoping unification (behavior-preserving).**
Collapse the `gl_company_id` / `ambient_company_id` split into a single explicit `company_id` sourced from `RequestContext`; remove the ambient fallback in `resolve_payment_credit_account` and `sync_company_cc_subledger`. *Tests:* identical GL/account resolution for single-company; **new** multi-company isolation tests prove no ambient leakage.

**WS4c — Reconciliation company-stamp fix (multi-tenant correctness).**
Fix the PS-P6-5 finding: statement JEs stamped from the ambient shim while records use explicit `company_id`. Route the JE company from the **explicit** `company_id` passed to `match_post`. *Tests:* JE and records share the same `company_id`; a cross-company scenario can't mis-stamp. (This is a real bug fix — characterize current behavior first, then assert the corrected, consistent stamping.)

**WS4d — TD-PS-01 commit ownership (the deepest change; do last).**
Convert kernel + void services to **flush-only**, with the caller (Streamlit shim now; API later) owning the commit via a unit-of-work boundary. *Tests:* the **pinned commit counts** (3-commit close, 2-commit YEC, 2-per-poster reconciliation, void counts) must be re-expressed against the new boundary **without changing observable persistence**; rollback-on-failure semantics preserved (TD-PS-04 also lands here). Highest risk — gate behind a full characterization pass and a feature-flagged rollout behind Streamlit.

**Also note TD-PS-08** (banking balance-ownership asymmetry) — forward posters don't own `BankAccount.balance` while voids do; document and decide during WS4, but do not expand scope mid-hardening.

**Risk:** WS4a Low, WS4b Med, WS4c Med (correctness), WS4d **High**. **Must not change:** GL line tuples, debit/credit orientation, error strings, the YEC-guard semantics (TD-POSTING-05 already centralized), and net persisted state.

## WS5 — Permission enforcement boundary

**Scope:** a **pure guard** — `check_permission(context, action) -> bool/raise` — reusing `user_access.resolve_effective_permissions` (policy is already service-ready).
**P0 approach:** build + test the guard; **converge `_can()`** to delegate to it (single source of truth) so Streamlit and the future API enforce identically. No endpoint enforcement yet.
**Tests first:** guard matches today's `_can()` decisions across roles + per-user overrides + DEV mode; locked/policy settings (P2.3) honored.
**Risk:** Low–Med (must not loosen any current denial). **Must not change:** any current allow/deny outcome.
**Depends on:** WS1.

## WS6 — First read-only endpoint candidates (identification only — no API)

Not endpoints in P0; this fixes the **DTO contracts** P1 will expose. Candidates (lowest risk, already explicit):
1. **Settings** — `registry.get_effective_config` (already a dict).
2. **Permissions & members** — `user_access` views (already `to_dict()`).
3. **One report** — P&L *or* reconciliation readiness via the WS3 read service.

P0 deliverable for WS6: confirm each candidate's read service returns a stable, serializable DTO with explicit `company_id`/`user_id`, ready to wrap in P1.

## WS7 — What must remain Streamlit-only for now

- All `render_*` UI, hub/bottom-nav, forms, the **column-mapping import wizard**, and the match-queue interaction state.
- **Session lifecycle / login** (`_login`, `auth_user`/`auth_expires`) — the token/auth spine is a **P1** concern; P0 only introduces `RequestContext` *built from* session state.
- `st.session_state` as the ambient store (kept; the builder reads it).
- The Streamlit shims over posting/void/reconciliation (kept; they now supply `RequestContext`/DTOs).
- No write-path enforcement swap, no commit-ownership change exposure beyond WS4d behind a flag.

---

## P0 exit criteria

- `RequestContext` exists and backs services; ambient helpers still work (additive).
- Read services for reports/ledger/readiness/AR-AP/partner-statement return DTOs with explicit company scope; zero-JE + isolation tests green.
- Audit is a service taking explicit `user_id`; audit rows unchanged.
- Permission guard is the single source of truth; `_can()` delegates; no decision changed.
- Posting hardening: `PostingResult` available; company scoping unified; reconciliation stamp fixed; commit ownership converted with pinned commit counts preserved.
- Full suite green; accounting behavior byte-identical; **no API, no DB change, no React.**

---

*Planning only. No API, no DB migration, no React, no implementation. Sequencing: RequestContext → read services (parallel, low-risk) → audit service → permission guard → posting hardening (DTO → company_id unify → recon stamp → commit ownership last). Tests-first throughout; every change preserves accounting behavior and ships behind the existing Streamlit UI.*
