# FASTAPI-P0.4 — Permission Boundary Plan

**Mode:** Planning only. No code, no implementation, no DB changes, no API endpoints, no React.
**Inputs:** `docs/FASTAPI_P0_SERVICE_HARDENING_PLAN.md`, `docs/FASTAPI_MIGRATION_01_AUDIT.md`, `services/context.py`, `services/user_access.py`.
**Goal:** one permission boundary used by Streamlit now and FastAPI later, **preserving every current allow/deny outcome.**

**Current state (already partly converged):** `services/context.py` defines `RequestContext{user_id, company_id, role, effective_permissions}` with `.can(action)` and `.require_company_id()` (fail-loud), plus `build_request_context` / `resolve_effective_permissions_for_context`. `app.py._can()` already builds context from ambient session and delegates to the **same** resolver (`user_access.effective_permissions` when company-scoped; `legacy_permissions_for_role` otherwise). So `_can` ↔ `RequestContext.can` already share resolution — P0.4 finishes the convergence and adds the company/membership guards.

---

## 1. Inventory of permission checks

| Check form | Where | Nature |
|------------|-------|--------|
| `_can(action)` (`app.py:3020`) | ~all gated actions + many UI show/hide | **Authorization** (canonical) — delegates to `user_access.effective_permissions` / legacy matrix |
| `_require_role(*roles)` (`app.py:2935`) | coarse role gates | **Authorization (raw role)** — `role in roles`, **bypasses** overrides + OWNER_LOCKED logic → drift risk |
| Direct role comparisons (`role == "owner"`, `_current_company_role() in (...)`) | scattered | **Authorization (raw role)** — same drift risk |
| `current_company_required()` / `cq()` | every business query | **Tenant scoping** — not authorization |
| `RequestContext.require_company_id()` | service layer | **Tenant scoping** (fail-loud) |
| `CompanyUser` membership queries (`:4578, :4794, :4957`) | login / company switch | **Membership gate** — validates the user belongs to the company; sets `membership_role` |
| `CompanyUser` enumeration (`:1006, :4538, :4686, :4913`) | company picker | **UI** (list the user's companies) |
| `_NAV_ROLE_PAGES` / `_can(...)` in `disabled=`/section gates (`:3707, :3923`) | nav + buttons | **UI visibility** |

## 2. Classification

- **Authorization** (may this actor perform this action?): `_can`, `_require_role`, raw `role ==`/`role in` comparisons. Canonical = `_can`; the raw-role forms are **drift risks** (they skip per-user overrides and OWNER_LOCKED stripping).
- **Tenant scoping** (whose data?): `current_company_required()`, `cq()`, `RequestContext.require_company_id()`. Answers *which company*, not *may you* — must not be conflated with authorization.
- **Membership** (does the actor belong to this company at all?): the `CompanyUser` checks at login/switch — both a gate and the source of `membership_role`. Today it runs when **binding** the active company, not per action.
- **UI visibility only**: `_NAV_ROLE_PAGES`, `_can(...)` used purely to show/hide/disable, the banking section gate. **Presentation, not security** — they may hide a control but must never be the *only* gate.

**Critical finding:** today `_can` doubles as both UI visibility *and* action gate. In Streamlit that's usually safe because the action runs right after the visible control. For an API, **UI visibility cannot be the boundary** — every write action needs a server-side `require_permission` independent of whether a control was shown. P0.4d catalogs which `_can` sites are true action gates vs visibility-only, so P2 endpoints know where `require_permission` is mandatory.

## 3. Boundary design (three functions, pure, reuse existing resolver)

- **`check_permission(context, action) -> bool`** — thin wrapper over `context.can(action)` (which is `action in context.effective_permissions`). Raising variant **`require_permission(context, action)`** for write paths. Single source of truth; subsumes `_can`, `_require_role`, and raw role comparisons.
- **`require_company(context) -> int`** — tenant scoping; mirrors `current_company_required()` / `context.require_company_id()` fail-loud. Write actions call this **before** `require_permission` so a no-company context can't authorize a tenant-scoped write via the legacy-role fallback.
- **`require_company_membership(session, context) -> str`** — verifies the user is an **active `CompanyUser`** of `context.company_id` and returns the membership role. Today implicit (active company is server-set from validated memberships at login/switch); the function makes it explicit so the API can run it **per request** (a client-supplied `company_id` must never be trusted).

These live in the service layer (extend `services/context.py` or a sibling `services/permissions.py`), import no Streamlit and no `app`.

## 4. How Streamlit uses it now vs FastAPI later

- **Streamlit (now):** the existing ambient builder constructs `RequestContext` from `st.session_state` (`_current_company_id`, `_current_company_role`, `User.role`). `_can` becomes a thin call to `check_permission(ctx, action)`; `_require_role`/raw comparisons converge onto `check_permission` with an equivalent action (or are reclassified as visibility). Company binding still validates membership at login/switch (unchanged); `require_company`/`require_company_membership` are available and used where a hard gate is wanted.
- **FastAPI (later):** the same three functions become **request dependencies** — the request resolves a `RequestContext` from the token (user_id + active company + role), then `require_company_membership` runs **every request** (re-validating the client-supplied company), and each write route declares `require_permission(ctx, <action>)`. Identical resolution code path as Streamlit → **one boundary, two callers.**

## 5. Multi-tenant risks (to neutralize, behavior-preserving)

- **Cross-company leak:** with API-supplied `company_id`, skipping membership re-validation lets a user act in another tenant. Today safe (server-set active company); the API **must** call `require_company_membership` per request. Build the function now so both paths converge.
- **Ambient company fallback:** when `company_id is None`, `resolve_effective_permissions_for_context` returns **legacy role-matrix** perms (no company scoping). For tenant-scoped writes this is a latent bypass — enforce `require_company` **before** `require_permission` on writes so the no-company path can't authorize them. (Reads/system events may legitimately use the no-company path.)
- **Admin bypass / drift:** `_require_role` and raw `role ==` skip per-user **deny overrides** and **OWNER_LOCKED** stripping that `resolve_effective_permissions` applies. They can grant what the permission model would deny. Converge them onto `check_permission`.
- **Role drift:** two role sources — `membership_role` (active company role) and `User.role` fallback. The single rule (`membership_role` preferred; fallback only when no company) is already encoded in `build_request_context`; the risk is call sites that read `User.role` directly. Route all role-derived decisions through the context.

## 6. Migration plan (additive first; `_can` converges; no behavior change)

| Step | Scope | Tests first |
|------|-------|-------------|
| **P0.4a — define boundary** | `check_permission` / `require_permission` / `require_company` / `require_company_membership` in the service layer, reusing the existing resolver. Additive; nothing calls them yet. | Unit: parity with `RequestContext.can`; membership/company fail-loud semantics |
| **P0.4b — characterize** | Golden matrix: for every (role × action) **and** per-user grant/deny override, `check_permission` == today's `_can`; reproduce `_require_role`/raw-role decisions; OWNER_LOCKED stripping; no-company legacy fallback | Full role×action×override snapshot |
| **P0.4c — converge `_can`** | `_can` delegates to `check_permission(ctx, action)`; reclassify/converge `_require_role` + raw role comparisons (authorization → `check_permission`; visibility → keep, documented) | Snapshot unchanged; no allow/deny flips |
| **P0.4d — catalog call sites** | Label every `_can`/`_require_role` site **action-gate** vs **visibility-only**; list the actions that P2 write endpoints must guard with `require_permission` | Inventory artifact (no behavior change) |
| **Deferred (P1/P2)** | Per-request `require_company_membership` enforcement on endpoints; decide removal of the no-company legacy fallback for writes | API-phase tests |

## 7. What must remain unchanged (P0.4)

- **Every current allow/deny outcome** (role × action × per-user override).
- **OWNER_LOCKED** stripping for non-owners; per-user **grant/deny** overrides.
- The **membership_role-preferred-then-`User.role`-fallback** rule.
- **Fail-loud** company requirement (`current_company_required` semantics).
- **Nav visibility** (`_NAV_ROLE_PAGES`) and UI show/hide behavior — a separate presentation layer, kept as-is.
- No DB change, no endpoint, no React.

**Exit criteria:** four boundary functions exist and are characterized; `_can` (and converged role checks) delegate to them with zero allow/deny changes; every call site classified authorization-vs-visibility; membership/company guards ready for per-request API use. One boundary, two future callers, identical decisions.

---

*Planning only. No code, no DB, no API, no React. The permission boundary is `check_permission` / `require_permission` (authorization), `require_company` (tenant scoping), and `require_company_membership` (per-request tenant validation) — all reusing the existing `user_access` resolver and `RequestContext`. P0.4 converges `_can` and the raw-role checks onto it, classifies every call site (authorization vs UI-visibility), and neutralizes the multi-tenant risks (ambient fallback, missing membership re-check, raw-role drift) — all behavior-preserving.*
