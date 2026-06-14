# FASTAPI-P0.3 — Audit Service Plan

**Mode:** Planning only. No code, no implementation, no DB migration, no React.
**Inputs:** `docs/FASTAPI_P0_SERVICE_HARDENING_PLAN.md`, `docs/FASTAPI_MIGRATION_01_AUDIT.md`.
**Goal:** remove audit ownership from `app.py` ambient state and prepare it for FastAPI, **without changing any persisted audit row or commit count** in P0.

**P0.3 stance:** extract `log_audit` into a service that takes the actor + company **explicitly** (from `RequestContext`, WS1), centralize the action/entity taxonomy, and **keep audit's own commit** (the commit-ownership change waits for TD-PS-01). The only behavior fix in P0.3 is making the **ambient tenant/actor stamping explicit** — a multi-tenant correctness prep — while keeping rows byte-identical.

---

## 1. Current `log_audit` call sites

`log_audit(session, action, entity_type, entity_id, description)` — defined `app.py:1569`. ~60+ call sites in `app.py` plus one in `reconciliation/company_card.py` (via lazy `app.log_audit`). All are **success-only, post-commit**, and use ambient actor + company.

| Action | Representative entities |
|--------|------------------------|
| `Create` | Sale, ExpenseRecord, Purchase, Payable, Partner, Worker, EquityMovement, InventoryTransaction, ChartOfAccounts |
| `Edit` | Purchase, ExpenseRecord |
| `Void` | ExpenseRecord, Purchase, Payable, Sale, BankTransaction, InventoryTransaction, EquityMovement, DailyCashReconciliation, EndOfDayClose, PartnerProfitAllocation |
| `Post` | BankStatementRow (reconciliation match/post — one per posted row) |
| `Submit` / `Approve` / `Reject` | DailyCashReconciliation |
| `PeriodClose` / `YearEndClose` / `VoidYearEndClose` | FiscalPeriod, YearEndClose |
| `ProfitAllocation` | PartnerProfitAllocation |
| `Upload` / `Delete` | Attachment |

Key call-site properties to preserve: **one audit per posted/voided row** (reconciliation/posting, per PS-P3/P4/P1.3 CHARs); audit fires **after** the entity's own commit; description is sometimes **free-text JSON** (e.g. `Edit` before/after diffs).

## 2. Audit data model (`AuditLog`, `models.py:465`)

| Column | Type | Note |
|--------|------|------|
| `id` | Integer PK | |
| `timestamp` | DateTime | naive (no tz) |
| `action` | String(100) | free string today |
| `entity_type` | String(100), nullable | free string |
| `entity_id` | Integer, nullable | |
| `description` | Text, nullable | free text; sometimes JSON |
| `performed_by` | String(100), nullable | **username string, not a user_id FK** |
| `company_id` | Integer, nullable | NULL = system event; set = company event |

**API/multi-tenant gaps (do NOT fix the schema in P0):**
- `performed_by` is a **display username**, not a stable `user_id` — fine for display, weak for API joins/integrity.
- `company_id` is **not passed by `log_audit`**; it is stamped by the ambient `before_flush` hook (`_stamp_company_id_on_new_objects`) — an ambient dependency.
- `timestamp` is naive — a tz-aware column matters under PostgreSQL/multi-region.
- No structured payload / event-type enum / correlation id.

These are **DB-phase** items (later). P0.3 addresses them only at the **service boundary** (explicit params), not the schema.

## 3. Explicit RequestContext integration

Replace the ambient `_current_user()` read with an explicit actor from `RequestContext` (WS1):

- New service signature (conceptual): `record_audit(session, *, action, entity_type, entity_id, description, performed_by, company_id)` — actor + company passed in, never read from `st.session_state`.
- `app.py` shim `log_audit(...)` builds `performed_by` (username) and `company_id` from the **context builder** and delegates — preserving today's call sites and row content.
- For the future API, the request handler supplies the same fields from the request-resolved context. The service itself imports no Streamlit and no `app`.

## 4. Write ownership

- The **service owns** constructing + `session.add()`-ing the `AuditLog` row (timestamp, action, entity, description, performed_by, company_id).
- **Company stamping becomes explicit in the service** (set `company_id` from context) rather than relying on the ambient `before_flush` hook — this is the multi-tenant prep. In P0 the explicit value equals what the hook would set, so rows are unchanged; the service no longer *depends* on the hook for correctness.
- **System events** (login, cross-company admin) remain possible with `company_id = None` (context may carry no active company).

## 5. Commit ownership interaction with TD-PS-01

- **Today `log_audit` commits** — it is the trailing commit in the pinned counts (3-commit period close, 2-commit YEC, 2-per-poster reconciliation, the void counts).
- If P0.3 converted audit to flush-only **now**, those pinned counts would break and audit rows could fail to persist when a caller doesn't commit.
- **Decision:** P0.3 **keeps audit's internal commit** (unchanged). The flush-only / boundary-owned-commit conversion for audit lands **with TD-PS-01 (P0.5 / WS4d)**, where the commit-count characterization is re-expressed against the new unit-of-work boundary.
- Net: P0.3 changes *who supplies actor/company* (explicit), not *who commits* (still audit). Pinned commit counts stay green.

## 6. API readiness

- Service is **import-pure** (no Streamlit, no `app`), takes explicit actor + company, returns the created id (or nothing).
- **Converge the reconciliation call site** (`reconciliation/company_card.py` lazy `app.log_audit`) onto the service — removes one `_app()` hop and gives reconciliation a real audit path (relevant to the PS-P7 reconciliation-audit gap).
- **Forward-looking (DB phase, not P0):** add a nullable `user_id` FK alongside `performed_by` so API consumers can join on identity; tz-aware timestamp; optional structured payload. Plan now, migrate later.

## 7. Multi-tenant safety

Two ambient leaks exist today and both must become request-derived:
1. **Actor** — `performed_by` from ambient `_current_user()` → from explicit context.
2. **Company** — from the ambient `before_flush` hook → set **explicitly** in the service from context.

For a concurrent multi-tenant API, an ambiently-stamped audit row could attach to the wrong tenant/user. P0.3's explicit stamping removes that class of bug **before** any endpoint exists. Preserve the **`company_id = None` system-event** path. Tests must assert no cross-tenant attribution under an explicit context.

## 8. Event taxonomy

Formalize the **implicit `action × entity_type` matrix** (Section 1) into a documented canonical set, centralized as **service constants** so call sites stop using magic strings:

- **Actions:** `Create, Edit, Void, Post, Submit, Approve, Reject, PeriodClose, YearEndClose, VoidYearEndClose, ProfitAllocation, Upload, Delete`.
- **Entities:** `Sale, ExpenseRecord, Purchase, Payable, BankTransaction, BankStatementRow, DailyCashReconciliation, EndOfDayClose, FiscalPeriod, YearEndClose, Partner, Worker, PartnerMovement, WorkerMovement, EquityMovement, InventoryTransaction, ChartOfAccounts, Attachment, PartnerProfitAllocation`.

P0 keeps `action`/`entity_type` as **strings** (no enum DB migration); the constants are a typing/consistency layer and the basis for a future enum + structured payload.

## 9. What must remain unchanged (P0)

- Every `AuditLog` row's content — `action`, `entity_type`, `entity_id`, `description` (incl. free-text JSON diffs), `performed_by` (username string), `company_id`, `timestamp` semantics — **byte-identical**.
- **Audit's own commit** (preserves all pinned commit counts).
- **Success-only** placement and **one-audit-per-row** cardinality.
- The **`AuditLog` schema** (no DB migration in P0).
- The `company_id = None` system-event capability.

## 10. Migration plan (tests-first, phased)

| Step | Scope | Tests |
|------|-------|-------|
| **P0.3a — characterize** | Snapshot every audit row produced by representative flows (create/edit/void/post/close/allocation/upload) | Golden snapshot of `(action, entity_type, entity_id, description, performed_by, company_id)` |
| **P0.3b — extract service** | `record_audit(...)` with explicit `performed_by` + `company_id`; centralize action/entity constants; set company_id explicitly (drop hook reliance for audit). `app.py log_audit` becomes a context-building shim that delegates; **keep internal commit** | Snapshot rows byte-identical; pinned commit counts unchanged; system-event (`company_id=None`) preserved |
| **P0.3c — converge reconciliation** | Route `reconciliation/company_card.py` audit through the service (remove `_app()` hop) | CC bill-payment void audit row unchanged |
| **P0.3d — multi-tenant assertions** | Add explicit-context tests proving no cross-tenant/actor mis-attribution | Audit attributed to the context's company/actor, not ambient |
| **Deferred (with TD-PS-01 / WS4d)** | Convert audit to flush-only / boundary-owned commit | Re-pin commit counts against the unit-of-work boundary |
| **Deferred (DB phase)** | Nullable `user_id` FK + tz timestamp + optional payload; backfill | Migration + parity tests |

**Exit criteria (P0.3):** audit is a Streamlit-free service taking explicit actor + company; all audit rows byte-identical; commit counts unchanged; reconciliation audit converged; multi-tenant stamping explicit; taxonomy centralized. No DB migration, no commit-ownership change, no API.

---

*Planning only. No code, no implementation, no DB migration, no React. P0.3 makes audit actor + company **explicit** (multi-tenant prep) and Streamlit-free, centralizes the event taxonomy, and **keeps audit's internal commit** — deferring the flush-only conversion to TD-PS-01 and the `user_id`/tz schema additions to the DB phase. Accounting behavior and every audit row preserved exactly.*
