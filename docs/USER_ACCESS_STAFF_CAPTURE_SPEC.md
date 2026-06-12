# USER-ACCESS-01 + STAFF-CAPTURE-01 — Design Specification

**Status:** Design approved for review — NOT yet scheduled for implementation.
**Scope guard:** No accounting logic changes. Approval posts through existing posting
functions only. Staff actions never create journal entries directly.

Companion review: architecture critique (2026-06-11) — computed-not-materialized
permissions, typed-not-generic drafts, allowlist portal routing.

**USER-ACCESS-01 corrections applied (2026-06-13):** snake_case permission keys,
flat effective-permission model (no inheritance), owner lockout guard, separation
of duties, UA-P1 / UA-P1b scope split, migration cleanup notes.

---

## 1. Schema (all additive — `migrate_schema()` ALTER TABLE pattern)

### 1.1 `user_permission_overrides` (new table)

| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| company_id | Integer, indexed | auto-stamped (`before_flush`) |
| user_id | Integer FK users.id, indexed | |
| permission_key | String(100) | must exist in `PERMISSION_REGISTRY` |
| mode | String(10) | `grant` \| `deny` |
| created_by_id | Integer FK users.id | who clicked the checkbox |
| created_at | DateTime | |

Unique constraint: `(company_id, user_id, permission_key)` — one row per key;
flipping grant↔deny updates the row; clearing the override deletes it.
**Every insert/update/delete writes an `AuditLog` entry** (action `Permission`,
entity `UserPermissionOverride`).

### 1.2 Role templates

No new table. `CompanyUser.role` remains the template name. Allowed values extend
from `{owner, manager, viewer}` to `{owner, manager, accountant, cashier, staff, viewer}`.
Template definitions live in code (`PERMISSION_TEMPLATES`), not the DB — template
improvements propagate to all users instantly because effective permissions are
**computed at check time, never materialized**.

**No custom DB-defined roles in v1** — deferred; templates are code-only.

### 1.3 Draft tables (typed — one per capture type)

Common columns on all four (the "draft spine"):

```
id · company_id · created_by_id · status · created_at · submitted_at
reviewed_by_id · reviewed_at · review_note
```

`status ∈ {draft, submitted, approved, rejected, returned}`.

| Table | Typed payload columns | Posted ref column |
|---|---|---|
| `expense_drafts` | date, amount, currency, payment_method (Cash only in v1), tx_category_id, tx_subcategory_id, description | `expense_record_id` |
| `salary_drafts` | date, worker_id FK, gross_amount, deductions, net_amount, pay_period, notes | `worker_movement_id` |
| `sales_total_drafts` | date, cash_total, card_total, notes | `cash_sale_id`, `card_sale_id` |
| `cash_count_drafts` | date, counted_amount, currency, notes | `cash_reconciliation_id` |

Rules: rows are editable only in `draft`/`returned`; immutable after `approved`
(corrections = void the posted record via existing void functions, then new draft).
Posted-ref columns are the idempotency anchor (§5).

### 1.4 `draft_attachments` (new table, shared)

| Column | Notes |
|---|---|
| id, company_id, uploaded_by_id, created_at | standard |
| draft_type | `expense` \| `salary` \| `sales_total` \| `cash_count` |
| draft_id | id within the typed table |
| file_path | relative path under the uploads root — never user-controlled |
| original_name | display only; never used in the filesystem path |
| mime, size_bytes, sha256 | validated at upload (magic bytes, not extension) |

**File storage:** `uploads/{company_id}/drafts/{yyyy-mm}/{uuid}.{ext}` on disk —
no SQLite blobs. Caps: 10 MB/file, jpg/png/webp/pdf only, max 5 attachments/draft.
Retention: archive candidates after the fiscal year containing the draft is
closed (policy documented now, job built in SC-P3).

---

## 2. Permission keys (`PERMISSION_REGISTRY`)

### 2.1 Naming convention

**All keys use existing project convention:** `snake_case` **`verb_object`** (or
`verb_object_qualifier`). **No dotted namespaces** (e.g. ~~`capture.expense_draft`~~,
~~`admin.permissions`~~).

Examples (existing + new):

| Key | Meaning |
|---|---|
| `create_transaction` | (existing) |
| `upload_receipts` | attach receipt photos to own drafts |
| `submit_expense_drafts` | create/submit cash expense drafts |
| `submit_salary_drafts` | create/submit worker-salary-paid drafts |
| `submit_sales_totals` | enter daily sales totals (+ Z-report photo attachment) |
| `submit_cash_count_drafts` | enter daily cash counts |
| `approve_expense_drafts` | approve expense drafts in inbox |
| `approve_salary_drafts` | approve salary drafts in inbox |
| `approve_sales_verification` | approve external sales verification / sales-total drafts |
| `approve_cash_count` | approve cash-count drafts |
| `approve_pos_report` | approve POS / Z-report aligned sales submissions |
| `manage_permissions` | edit per-user overrides (owner-locked) |

Existing `_PERMISSIONS` action names become registry keys **unchanged** (zero churn
at the 135 `_can()` call sites). New Staff Capture keys follow the table above.

Registry entries carry: key, i18n label key, category (for the owner UI grouping),
and `owner_locked: bool` (keys that overrides can never grant to non-owners:
`manage_permissions`, `allocate_profit`, `void_profit_allocation`, year-end close).

**Contract rule (enforced by test):** every nav page and every action handler
declares a registry key. New pages without one fail CI — default-deny.

### 2.2 No permission inheritance

Permissions are **flat**. There is no role hierarchy and no implied access.

```
effective(user, company) = template_keys(role) ∪ grants − denies
```

Rules:

1. **Deny wins** over grant and over template.
2. **No role hierarchy** — `manager` does not inherit `owner`; each template lists
   every key explicitly.
3. **No wildcard permissions** — no `*`, no prefix globs, no category wildcards.
4. **No implied permissions** — holding `approve_expense_drafts` does not grant
   `submit_expense_drafts` or `upload_receipts` unless the template or a grant
   row says so.
5. **No `manage_*` pattern matching** — `manage_recipe_costing` grants only that
   key; it does not unlock other `manage_*` keys.
6. **Templates duplicate keys explicitly** — each `PERMISSION_TEMPLATES[role]` is
   a complete flat set; nothing is derived from another role at runtime.

`owner_locked` keys ignore grants for non-owner templates — enforced in the
resolver, not just hidden in the UI.

---

## 3. Default role matrix

| Key group | Owner | Manager | Accountant | Cashier | Staff | Viewer |
|---|---|---|---|---|---|---|
| Full ERP pages (existing perms) | ✅ | ✅ (minus owner-locked) | read-only reports + ledgers | — | — | read-only (existing) |
| `upload_receipts` | ✅ | ✅ | — | ✅ | ✅ | — |
| `submit_expense_drafts` | ✅ | ✅ | — | ✅ | — | — |
| `submit_salary_drafts` | ✅ | ✅ | — | — | — | — |
| `submit_sales_totals` | ✅ | ✅ | — | ✅ | — | — |
| `submit_cash_count_drafts` | ✅ | ✅ | — | — (grantable) | — | — |
| `approve_expense_drafts` | ✅ | ✅ | — (grantable) | — | — | — |
| `approve_salary_drafts` | ✅ | ✅ | — (grantable) | — | — | — |
| `approve_sales_verification` | ✅ | ✅ | — (grantable) | — | — | — |
| `approve_cash_count` | ✅ | ✅ | — (grantable) | — | — | — |
| `approve_pos_report` | ✅ | ✅ | — (grantable) | — | — | — |
| `manage_permissions` | ✅ | — | — | — | — | — |

**Portal routing rule:** after auth, if a user's effective permissions contain only
Staff Capture submit/upload keys (and no full-ERP page keys) → render the Staff
Portal **instead of** the ERP (allowlist dispatch at the top of `main()`; the ERP
nav is never constructed). Owner/manager see capture features inside the full ERP.

---

## 4. Override rules

1. **Deny beats grant** (explicit deny is final).
2. Template switch keeps existing override rows; the permission screen shows a
   "review overrides" prompt when they now duplicate or contradict the template.
3. Overrides are per `(company, user)` — multi-company users have independent sets.
4. `_can(action)` keeps its exact signature; internals change from
   `role in _PERMISSIONS[action]` to `action in effective(...)` with a per-request
   cache. Existing owner/manager/viewer behavior must be byte-identical
   (regression-tested against the current `_PERMISSIONS` dict as template seed).

### 4.1 Owner lockout guard

The system **must reject** any permission change that would leave a company with
**no active owner** able to `manage_permissions`.

Reject (with plain error, no partial apply):

- **Denying `manage_permissions`** to the last active owner (via deny override or
  template change).
- **Changing or removing the last owner's template** if the resulting effective set
  would drop `manage_permissions`.
- **Self-lockout** — the sole active owner cannot save a change that removes their
  own `manage_permissions`.

Enforced in `services/user_access.py` on every override/template mutation, not only
in the UI.

### 4.2 Separation of duties

A user **cannot approve their own draft**, even if they hold the relevant
`approve_*` permission.

Applies to all Staff Capture approval flows (expense, salary, sales totals, cash
count, POS report). The approval service checks `draft.created_by_id != reviewer_id`
before posting. Owner emergency override is **not** in v1.

---

## 5. Approval workflow

```
draft ──submit──▶ submitted ──approve──▶ approved (immutable, refs posted records)
                     │  ▲                    │ posts via EXISTING functions only
                     │  └──resubmit── returned
                     └──reject──▶ rejected (terminal)
```

- **Approve** (single transaction): re-validate payload (active category/worker,
  parseable amounts) → **separation-of-duties check** (§4.2) → call the mapped
  posting function → store posted-ref id(s) → set `approved` → `log_audit`.
  **Idempotency:** approval first checks posted-ref IS NULL inside the transaction;
  a double-tap or rerun cannot double-post.
- **Posting map:** expense → existing expense save path (`reference_type` Expense);
  salary → existing worker Salary movement posting; sales totals → existing
  `post_cash_sale` + `post_card_sale` (card path automatically respects the POS
  Settlement clearing toggle — drafts inherit 1150 routing for free);
  cash count → existing Cash Reconciliation creation (inherits its variance-approval
  rules).
- **Closed-period collision:** `create_journal_entry`'s period lock remains the
  authority; the inbox catches the `ValueError` and offers "edit date / return /
  reject" — never a stack trace. Manager edits to a submitted draft before
  approval are allowed and audit-logged.
- **Return** requires a `review_note`; staff portal shows it and allows resubmit.
- **No bulk approve.** One draft per decision, attachment rendered beside the
  numbers. This is a control, not a UX gap.
- Staff see only their own drafts (`created_by_id` filter on top of `cq()`).

---

## 6. Tests (~40, by suite)

**`test_user_access01_permissions.py`** — resolver units: template-only, grant adds,
deny removes, deny-beats-grant, owner-locked grant ignored, unknown key → False,
no wildcard/implied/manage_* expansion, multi-company isolation; `_can` backward-compat
sweep (every existing `_PERMISSIONS` entry resolves identically for
owner/manager/viewer); override CRUD writes AuditLog; **owner lockout guard**
(three reject cases in §4.1); registry contract (every nav page + action handler
declares a key).

**`test_staff_capture01_drafts.py`** — state machine per type (legal/illegal
transitions); immutability after approval; staff-sees-own-only; company scoping;
attachment validation (size cap, MIME sniff vs spoofed extension, path is
UUID-based, traversal attempt rejected); attachment↔draft type/id integrity.

**`test_staff_capture01_approval.py`** — posting-map per type with JE assertions
(reuse existing posting test fixtures: expense → correct GL pair; sales totals →
cash + card sales incl. clearing-ON 1150 routing; salary → worker movement;
cash count → recon row); idempotent approve (second call no-ops); **self-approval
rejected** (§4.2); closed-period approve surfaces friendly error and leaves draft
`submitted`; reject/return leave no posted refs; review_note required on return.

**`test_staff_portal_gate.py`** — the security contract: capture-only session
renders the portal and **cannot reach any ERP `render_*`** (allowlist assertion);
portal hides non-granted capture actions; owner/manager still get the full ERP;
viewer unchanged.

Plus: i18n completeness (EN/TR) for all new keys; locale sweep extension.

---

## 7. Implementation phases

| Phase | Contents | Gate to next |
|---|---|---|
| **UA-P1** | `user_permission_overrides` model · `PERMISSION_REGISTRY` · `PERMISSION_TEMPLATES` · `services/user_access.py` (effective resolver, override CRUD, owner lockout guard) · `_can()` resolver swap · tests. **No UI.** Zero staff features; existing owner/manager/viewer behavior unchanged (regression suite). | Host suite green; resolver parity with `_PERMISSIONS` seed |
| **UA-P1b** | Thin owner permission UI — per-user override checkboxes, effective-permissions viewer, audit trail display. Uses `services/user_access.py` only; no permission logic in `app.py`. | Manual: owner can grant/deny; lockout guard surfaces errors |
| **SC-P1** | Draft spine + `expense_drafts` + `draft_attachments` + portal (expense draft + receipt upload only) + approval inbox (expense only) + portal gate. | One real expense flows staff→approve→GL correctly on host data |
| **SC-P2** | `sales_total_drafts` (+ Z-report attachment) + `salary_drafts` + `cash_count_drafts`; inbox grows the three types. | Each type's posting map verified against existing tests |
| **SC-P3** | Returned-flow polish, staff submission feed, retention/archive job, OBS-01 review of real usage. | — |

**Explicitly NOT in v1** (binding): separate mobile app, OCR, offline capture,
push notifications, approval delegation, editing approved drafts, staff seeing
each other's drafts, per-field permissions, custom role templates, accountant
portal.

**Two-year maintenance commitments made now:** default-deny registry contract
test; draft↔posting field-map contract tests; upload retention policy; the
effective-permissions viewer ships **with UA-P1b**, not later.

---

## 8. Migration cleanup (USER-ACCESS-01)

Expected temporary and deferred items when UA-P1 / UA-P1b land:

| Item | Treatment |
|---|---|
| `_PERMISSIONS` dict in `app.py` | **Retained temporarily** as the seed for `PERMISSION_TEMPLATES` until templates are fully extracted and regression-tested; then read-only reference, not runtime source |
| Custom DB-defined roles | **Deferred** — templates stay code-only in v1 |
| Streamlit per-request permission cache | **Temporary app-layer glue** inside `_can()` until FastAPI/React migration; replace with request-scoped context or API middleware |
| Denied-attempt logging | **Deferred** — resolver returns `False` only; audit of failed `_can` checks is a follow-up (TD-UA) |

Service layer (`services/user_access.py`) is the long-term owner of effective
permission computation; UI and `_can()` are thin callers.
