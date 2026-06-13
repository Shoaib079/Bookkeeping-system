# FASTAPI-MIGRATION-01 — Audit

**Mode:** Audit only. No code, no implementation, no React, no DB migration. Preserve accounting behavior; no redesign.
**Basis:** code-derived from `services/`, `registry/service.py`, `db.py`, the auth/scoping helpers in `app.py`, and the POSTING-SERVICE-01 status.
**Target:** FastAPI + SQLAlchemy (retained) + PostgreSQL, React later.

**Central thesis (challenges the obvious assumption):** "service-extracted" is **not** the same as "API-ready." The posting kernel is fully extracted yet still **commits internally** (TD-PS-01), **returns ORM** (TD-PS-03), and carries **ambient company fallback** (TD-PS-06/07). So the safe first move is **read-only endpoints over already-explicit services + a request-context/auth spine** — *not* exposing posting. Writes wait for PS-P7 hardening.

---

## 1. What is already service-ready?

| Module | State | API-readiness |
|--------|-------|---------------|
| `services/posting.py` | GL kernel fully extracted; explicit `company_id`; raises `ValueError`/returns ORM/bool | **Structurally ready, not boundary-ready** — internal commits + ORM return (TD-PS-01/03) |
| `services/user_access.py` | Permissions: `LEGACY_PERMISSION_MATRIX`, `resolve_effective_permissions(session, company_id, user_id)`, registry/member views with `to_dict()` | **Strong** — explicit inputs, DTO-shaped outputs, no Streamlit |
| `registry/service.py` | `get_setting/set_setting/get_effective_config(session, company_id, user_id)` + scopes + locks | **Strong** — explicit, serializable, scope-aware |
| `services/daily_sales_close.py` | DSC-P1 exemplar (MIGRATION-READINESS-01 reference) | **Strong** (read/compute); writes share TD-PS-01 |
| `services/recipe_costing.py`, `services/staff_capture.py` | Service-first, explicit context | **Good**; verify commit ownership |

These follow MIGRATION-READINESS-01 (explicit `company_id`/`user_id`, `to_dict()` outputs, no Streamlit, tests without Streamlit). `user_access` and `registry` are the **cleanest first candidates** because they're read-mostly and already DTO-shaped.

## 2. What still depends on Streamlit / app.py?

- **Ambient request context:** `_current_user()`, `_current_company_id()`, `_current_company_role()`, `current_company_required()`, `cq()`, `_can()` all read `st.session_state`. This is the deepest coupling — every business query flows through `cq()`'s ambient company.
- **Auth:** `_login()`, `auth_user` dict + `auth_expires` datetime in session_state (no token/JWT).
- **Posting/void shims:** the `app.py` shims add audit (`log_audit`) + ambient company on top of the services.
- **Reconciliation orchestration:** `reconciliation/match_post.py` reaches `app` via lazy `_app()`; JE company stamped from the ambient shim (PS-P6-5 finding).
- **Read/compute logic in UI:** reports (P&L/BS/CF), AR/AP lists, transaction ledger, reconciliation readiness, balance calculators (`calculate_account_balance`, `sync_account_balances`, `get_worker/partner_advance_balance`) live in `app.py` render functions / helpers — **not** in services.
- **Audit:** `log_audit()` is in `app.py`, stamps ambient `_current_user`, commits internally.
- **Schema evolution:** `migrate_schema()` (SQLite `ALTER TABLE ADD COLUMN`) + `MigrationFlag`.

## 3. What modules should become FastAPI endpoints first?

**Read-only, already-explicit, zero accounting-write risk:**
1. **Settings** — `registry.get_effective_config` (company/user/policy).
2. **Permissions & members** — `user_access` (`resolve_effective_permissions`, `list_active_members`, registry) — already `to_dict()`.
3. **One report** — P&L *or* reconciliation readiness — via a newly-extracted **read service** (the compute currently lives in `app.py`).

These prove auth + scoping + DTO + error patterns end-to-end without touching the GL.

## 4. What must stay untouched until later?

- **Posting/void writes** — until PS-P7 (commit ownership + `PostingResult` DTO + `company_id` unification).
- **Reconciliation posting** — until the ambient-vs-explicit company-stamp bug is fixed (PS-P6-5 / PS-P7).
- **Year-end / period close, profit allocation** — multi-step workflow commits; highest write complexity.
- **The Streamlit UI** — keep it running as primary; FastAPI runs alongside, same models/DB.
- **DB engine** — stay on SQLite until a dedicated PostgreSQL phase.

## 5. Missing service boundaries

| Missing boundary | Why needed |
|------------------|------------|
| **RequestContext** (`user_id`, `company_id`, `role`, `effective_permissions`) | Replace ambient `_current_*`/`cq`/`_can`; the spine of every endpoint |
| **Read/query services** (reports, ledger, AR/AP, recon readiness, partner statement) | Compute lives in `app.py` render fns; API needs DTO-returning read services |
| **Unit-of-work / transaction boundary** (TD-PS-01) | Services must flush-only; caller owns commit per request |
| **Permission enforcement** (dependency/guard) | Policy is in `user_access`; enforcement (`_can`) is ambient |
| **Audit service** | `log_audit` must take explicit `user_id` and be boundary-owned |
| **Balance read service** | `calculate_account_balance*` are `app.py` helpers reports depend on |

## 6. Schemas / DTOs needed

- **`RequestContext`** — `{user_id, company_id, role, permissions[]}`.
- **`PostingResult`** (TD-PS-03) — replace ORM `JournalEntry` at the boundary.
- **Read DTOs** — `StatementLine`/`FinancialStatement` (P&L/BS/CF), `LedgerRow`, `ReconciliationSummary` + `ReadinessStatus` (enum + reasons[], per P2.4), `MatchCandidate` (+ suggested kind/confidence), `ARRow`/`APRow`, `PartnerStatement`. `MemberView`/`PermissionRegistryEntry`/settings already have `to_dict()`.
- **Error model** — map `MatchPostError` / `ValueError` (closed-period) / permission failures → structured HTTP problem responses with stable codes.

## 7. Company / user scoping risks

- **Ambient company everywhere** (`cq`, `_current_company_id`): for an API, `company_id` must come from the **request/token**, not session_state. Every `cq()` call site and every shim calling `_current_company_id()` is a migration touch-point; a single miss = **cross-tenant data leak**. (`current_company_required()` raising is good fail-loud behavior — but it reads session_state.)
- **TD-PS-06 / TD-PS-07** — posting ambient company fallback; **reconciliation JE stamped from ambient shim while records use explicit `company_id`** (PS-P6-5) — a real multi-tenant correctness bug that must be fixed before API writes.
- **Settings locks/policy** (P2.3) — must be enforced server-side per permission, not just UI-gated.

## 8. Auth / permissions assumptions

- **Session-state auth:** `auth_user` dict + `auth_expires` datetime; **no token/JWT**; single Streamlit session = one user = one active company. `_login()` does the password check; `DEV_MODE` bypass exists (`_DEV_USER`).
- **Roles:** per-company `active_company_role` with `User.role` fallback; **permission policy is service-ready** (`user_access.resolve_effective_permissions` + per-user `UserPermissionOverride`), but **enforcement** (`_can`) is ambient.
- **FastAPI implication:** need **stateless token auth** carrying (or resolving) `user_id` + active `company_id` + role, with **per-request permission resolution** (the `user_access` service already supports this) and a **company-membership check** on every request.

## 9. Database changes needed before PostgreSQL

(Defer to the DB phase — listed for planning, not now.)
- **Alembic migrations** to replace `migrate_schema()` `ALTER TABLE ADD COLUMN` idioms + `MigrationFlag`.
- **Drop SQLite-only `check_same_thread`**; add PG connection pooling; request-scoped sessions.
- **Money columns `Float` → `Numeric/Decimal`** — *the single most accounting-sensitive change.* Must be deliberate and **characterized for rounding parity** (the posting kernel's float accumulation order is pinned by tests) — never a casual type swap.
- Verify `Boolean == True/False` literal filters, autoincrement → sequences, date/datetime handling, FK enforcement (PG enforces by default; SQLite needed the connect pragma).
- These are PostgreSQL-phase items; SQLite stays until then.

## 10. First FastAPI milestone

**Milestone 1 — Read-only API spine (no accounting writes, SQLite retained, Streamlit still primary):**
1. **Auth + `RequestContext`** — token-based; resolves `user_id`, active `company_id`, role, and `effective_permissions` per request (replacing ambient `_current_*`).
2. **Thin FastAPI app** sharing the same SQLAlchemy models + a request-scoped session.
3. **3–5 read endpoints** over explicit services: settings (`registry`), members/permissions (`user_access`), and one report/readiness via a freshly-extracted read service.
4. **Error + permission patterns** established (problem responses, per-endpoint permission dependency).

Outcome: proves auth, scoping, DTOs, and error handling end-to-end with **zero accounting risk** — the template every later endpoint follows.

## 11. What should NOT be migrated yet

- Posting/void **writes** (need PS-P7: commit ownership + DTO + `company_id` unification).
- **Reconciliation posting** (ambient company-stamp bug).
- **Close/allocation/year-end** workflows (multi-step commits).
- **PostgreSQL** swap (separate phase; money-type change needs characterization).
- **React** (after the API stabilizes).
- Any **rewrite of accounting logic** — preserve behavior; only relocate/parameterize.

## 12. Recommended phased migration roadmap

| Phase | Scope | DB / UI |
|-------|-------|---------|
| **P0 — Service hardening (no API yet)** | PS-P7: commit boundaries (TD-PS-01), `PostingResult` DTO (TD-PS-03), `company_id` unification (TD-PS-06/07), reconciliation stamp fix, audit-as-service. Extract **read services** (reports, ledger, recon readiness, AR/AP, partner statement) returning DTOs. | SQLite; Streamlit primary; behavior pinned by tests |
| **P1 — Read-only API spine** | Auth + `RequestContext`; thin FastAPI sharing models; read endpoints (settings, permissions/members, one report). | SQLite; Streamlit primary |
| **P2 — Write API (hardened families only)** | Posting/reconciliation **after P0**, with request-context company/user, transaction boundaries, audit. Permission enforcement on writes. | SQLite; Streamlit + API coexist |
| **P3 — PostgreSQL** | Alembic, `Numeric` money (characterized), pooling, request-scoped sessions. | Postgres; both UIs on PG |
| **P4 — React frontend** | React (per Mobile-UX design system) consuming the API; Streamlit retired incrementally. | Postgres; API-first |

**Sequencing rule:** P0 (hardening + read-service extraction) is the gate — it makes the services genuinely API-ready and is the highest-leverage, lowest-risk work, all behind the existing Streamlit UI with tests preserving accounting behavior. Do not start P1 endpoints that touch writes, and do not start P3/P4 early.

---

*Audit only. No code, no implementation, no React, no DB migration. Core findings: services are extracted but not yet boundary-ready (TD-PS-01/03/06/07); the migration spine is a request-context/auth layer replacing ambient session-state scoping; the safe first endpoints are read-only over `registry`/`user_access` + a freshly-extracted read service; writes and PostgreSQL wait for PS-P7 hardening; and the `Float→Numeric` money-type change is the most accounting-sensitive DB step and must be characterized, not casual.*
