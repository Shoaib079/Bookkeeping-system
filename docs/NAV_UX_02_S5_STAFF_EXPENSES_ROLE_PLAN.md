# NAV-UX-02-S5 — Staff Expenses Role-Gate Review: Decision Plan

**Mode:** Planning + **S5-IMPL-1 implemented (2026-06).** Staff Expenses nav visibility is permission-derived; page gate and default role→permission mapping unchanged.

## Headline finding

There are **two different gates** on Staff Expenses, and they **disagree**:

1. **Navigation gate (owner-only):** `NAV_STAFF_EXPENSE_CAPTURE` sits in the `transactions` accordion (`app.py:3430`) but appears **only** in the owner `_NAV_ROLE_PAGES` list — absent from manager/cashier/partner/viewer. So only an **owner** sees the sidebar entry.
2. **Page gate (granular permissions):** `render_staff_expense_capture` (`ui/staff_capture.py:419-461`) is **already permission-driven** — it requires `submit_expense_drafts` **or** `approve_expense_drafts`, and gates receipts on `upload_receipts`.

The page was **built for a staff-submit / manager-approve workflow**, but the **navigation layer hides it from everyone except the owner** — so the staff and approvers the feature is designed for **cannot reach it**. The gate mismatch, not the page, is the defect.

## 1. Exposure map

| Aspect | Current state | Evidence |
|---|---|---|
| route_key | `NAV_STAFF_EXPENSE_CAPTURE` ("Staff Expenses") | `registry/nav_keys.py:12` |
| render_fn | `render_staff_expense_capture` | `ui/staff_capture.py:419` |
| desktop placement | accordion `transactions` | `app.py:3430` |
| mobile placement | not in any mobile hub | `_MOBILE_HUB_CONFIG` (absent) |
| **nav role gate** | **owner-only** (owner `_NAV_ROLE_PAGES` only) | `app.py:3490+` |
| **page permission gate** | `submit_expense_drafts` OR `approve_expense_drafts`; `upload_receipts` for attachments | `ui/staff_capture.py:422-427,237` |
| posts to GL? | **only on approval** | `ui/staff_capture.py:385-394` → `post_fn=_staff_capture_post_expense_draft` (`app.py:5673`) |

## 2. Workflow analysis

`render_staff_expense_capture` is a **draft lifecycle with approval-gated posting** — three tabs by permission:

- **Submit (perm `submit_expense_drafts`):** create/update an **expense draft** (date, amount, category, description, Cash) + attach receipts (`upload_receipts`). Draft statuses: draft → submitted → returned/approved/rejected (`EDITABLE_STATUSES`, `review_note`, `submitted_note`). **Creating/submitting a draft does NOT post to the ledger.**
- **My Submissions (perm `submit_expense_drafts`):** list own drafts + reopen editable ones.
- **Inbox / Review (perm `approve_expense_drafts`):** reviewer approves / returns / rejects a submitted draft. **Approval is the only action that posts a real accounting entry** — `approve_expense_draft(..., post_fn=erp._staff_capture_post_expense_draft)` creates the `ExpenseRecord` / GL posting.

So the page already implements **draft → approval → post**, with a clean separation: submission is non-accounting, approval is the GL-posting boundary.

## 3. Does it create drafts / approvals / payments / posted entries?

- **Drafts:** yes (`expense_drafts` table, status workflow). Non-accounting.
- **Approvals:** yes (approve/return/reject in the inbox).
- **Posted accounting entries:** **only on approval** (`post_fn` → `ExpenseRecord`/GL). Submission alone never posts.
- **Payments / payroll:** **no.** Despite the "Staff Expenses" label, this is **staff-submitted expense capture** (e.g. a staff member buys supplies, attaches the receipt, submits for approval) — **not** salaries, advances, or repayments. Those live in **Workers** (`NAV_WORKERS`), a separate page. The §"security sensitivity / payroll-like data" concern is therefore **misattributed** to this page; it applies to Workers, not Staff Expenses.

## 4. Who should access it?

- **Submitters (staff / cashier / manager with `submit_expense_drafts`)** — yes; submitting is the page's purpose and is non-accounting.
- **Approvers (manager / owner with `approve_expense_drafts`)** — yes; approval is the GL-posting step and is correctly the higher-privilege action.
- **Today:** only the **owner** sees the nav entry, so neither staff submitters nor manager approvers can reach a feature explicitly built for them. **The nav gate is too narrow.**

## 5. Role recommendation — classification **B + D**

- **B — Needs wider access (at the nav layer):** surface Staff Expenses to the roles the workflow targets, so submitters and approvers can reach it. **Not A** (owner-only is wrong for a staff/approver workflow); **not C** (the page is already internally protected, so it is not over-exposed).
- **D — Needs/uses granular permission (preferred mechanism):** the page is **already** permission-driven. The durable fix is to make **nav visibility derive from permissions** — show Staff Expenses iff the user has `submit_expense_drafts` **or** `approve_expense_drafts` — instead of a static owner-only role list. This aligns the two gates and is migration-ready.
- **Security stays intact:** because the page enforces the permissions internally, widening nav visibility **grants no capability** beyond what the permission already allows; the approval/posting action remains gated to `approve_expense_drafts`. The implementation slice must **verify the default role→permission mapping** (e.g. confirm which roles hold `submit_expense_drafts` / `approve_expense_drafts` by default) so widening the nav cannot unintentionally surface approval/posting to an unintended role.

## 6. Future FastAPI permission model

The existing permissions map directly to API scopes:

- `submit_expense_drafts` → create/update/submit drafts (non-posting).
- `approve_expense_drafts` → approve (the **GL-posting boundary**), return, reject.
- `upload_receipts` → attachments.

Nav/route visibility contract: **visible iff `has(submit_expense_drafts) or has(approve_expense_drafts)`** — permission-derived on both Streamlit and React, not role-hardcoded. Approval remains the single privileged, posting action (mirrors the P2.x write-service boundary: explicit permission, audit, commit at the boundary).

## 7. React / API contract (freeze)

- **Route:** `NAV_STAFF_EXPENSE_CAPTURE` → `/expenses/staff-capture` (1:1, matches the audit).
- **API (future):** `POST /api/v1/expense-drafts` (create), `PATCH /api/v1/expense-drafts/{id}` (update), `POST /api/v1/expense-drafts/{id}/submit`, `POST /api/v1/expense-drafts/{id}/approve` (posts to GL), `/return`, `/reject`, `POST /api/v1/expense-drafts/{id}/attachments`.
- **Gating:** create/update/submit → `submit_expense_drafts`; approve/return/reject → `approve_expense_drafts`; attachments → `upload_receipts`. Approve is the only posting endpoint.

## 8. Contract tests (for the implementation slice)

- **Page is permission-gated, not role-gated:** `render_staff_expense_capture` requires `submit_expense_drafts` or `approve_expense_drafts` (structural assertion over `ui/staff_capture.py:422-427`).
- **Submission does not post:** creating/submitting a draft makes no `ExpenseRecord`/GL entry; only `approve_expense_draft` calls `post_fn` (structural over `ui/staff_capture.py:385-394`).
- **Approval is the posting boundary:** approve path passes `post_fn=_staff_capture_post_expense_draft`.
- **Nav visibility permission-derived (after impl):** Staff Expenses is shown iff the user has submit or approve permission — not owner-only; assert a submitter/approver role/permission can see it.
- **Not payroll:** Staff Expenses handles expense drafts/receipts; salaries/advances/repayments remain in Workers (`NAV_WORKERS`) — guard against conflation.
- **Default mapping verified:** the default role→permission seed does not grant `approve_expense_drafts` to an unintended role when nav is widened.

## 9. Implementation slices (for Cursor — DO NOT implement yet)

- **NAV-UX-02-S5-IMPL-1 — permission-derived nav visibility:** **Implemented (2026-06)** — `_can_view_staff_expense_capture()` + `_apply_permission_nav_overrides()` in `app.py`; nav shown iff `submit_expense_drafts` or `approve_expense_drafts`; default mapping verified; contract tests in `tests/test_nav_ux_02_s5_staff_expenses_structural_contract.py`. No `_NAV_ROLE_PAGES` template change.
- **NAV-UX-02-S5-IMPL-2 — mobile surface:** add Staff Expenses to the appropriate mobile surface (e.g. a transactions/expenses entry) under the same permission check, for parity with desktop.
- **NAV-UX-02-S5-IMPL-3 — React/API contract freeze:** freeze the §7 route + endpoint + permission map as the migration contract.
- **(No slice) approval posting boundary:** already correct — approval posts via `post_fn`; submission does not.

## 10. Risk assessment

**LOW–MODERATE.** This touches who can **see/reach** a posting-capable workflow, so it warrants care — but the page already enforces granular permissions, so widening the **nav** grants **no new capability**: a user without the permission still hits the in-page `sc.no_permission` guard, and approval (the GL-posting action) stays behind `approve_expense_drafts`. The genuine risk is purely the **default role→permission mapping**: the implementation slice must confirm that surfacing the nav does not expose approval/posting to a role that unexpectedly holds `approve_expense_drafts`. No route deletion, no accounting-logic change, no schema change. Workers (payroll/advances) is unaffected and out of scope.

## No-change statement (NAV-UX-02-S5 planning)

- **No role change, no UI change, no route deleted, no cleanup, no `app.py`/`ui/` edit.** Exposure map + workflow analysis + role recommendation + future permission model + React/API contract + contract tests + slices + risk only; execution is the separately-approved NAV-UX-02-S5-IMPL slices.

---

*Planning only. Staff Expenses has a gate mismatch: the nav entry is owner-only while the page (`ui/staff_capture.py`) is already permission-gated (`submit_expense_drafts` / `approve_expense_drafts` / `upload_receipts`). The page is a draft → submit → approve workflow; submission does not post, **approval is the GL-posting boundary** (`post_fn=_staff_capture_post_expense_draft`). It is expense capture **by** staff, not payroll/salaries/advances (those are Workers). Recommendation B + D: widen access at the nav layer by making nav visibility permission-derived (show iff submit or approve permission), matching the page's own gate; approval stays gated; verify the default role→permission mapping. React/API contract: /expenses/staff-capture with submit/approve/upload endpoints, approve the only posting endpoint. Risk LOW–MODERATE — nav widening grants no capability beyond existing permissions; only the default role→permission mapping needs verification. No role/route/render change in this slice.*
