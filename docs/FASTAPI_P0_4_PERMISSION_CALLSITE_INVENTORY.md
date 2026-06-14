# FASTAPI-P0.4d — Permission Call-Site Inventory

**Mode:** Inventory + classification only. No code, no implementation, no behavior change.
**Inputs:** `docs/FASTAPI_P0_4_PERMISSION_BOUNDARY_PLAN.md`, `app.py`, `services/permissions.py`, `services/context.py`.
**Boundary status:** `services/permissions.py` already exposes `check_permission`, `require_permission`, `require_company`, `require_company_membership` (P0.4a shipped). `services/context.py` has `RequestContext` + builder. This doc catalogs every check so the convergence (P0.4c) and the future API route guards know exactly what to protect.

---

## Headline finding (the one that matters for API security)

**Action protection in the Streamlit app is overwhelmingly presentation-level.** ~110 `_can(...)` sites; the large majority are **`disabled=not _can(<action>)`** on buttons / `st.form_submit_button`, or **show/hide** (`if _can(...):`). The underlying mutation (post sale, void, pay, post JE, allocate, close) generally has **no separate top-of-handler `require_permission`** — the gate is the disabled control. A smaller set are real **`if not _can(...): return/st.error`** page/view guards.

**Implication:** for FastAPI, the `disabled=`/show-hide checks are **not** a security boundary. **Every write route must call `require_permission(ctx, <same action>)`** server-side, mapping the action key from the corresponding `disabled=` check. The page guards become route guards too, but they mostly protect *views*, not individual writes.

---

## Category counts (approximate)

| Category | Count | Form |
|----------|-------|------|
| 1. Authorization **action/view gate** (`if not _can: return/error`) | ~20 | top-of-handler guards |
| 2. **UI visibility only** (`disabled=not _can`, `if _can:` show/hide) | ~90 | control enable / render |
| 3. **Tenant scoping** (`current_company_required`, `cq(...)`) | 100s | query filter |
| 4. **Membership gate** (`CompanyUser` at login/switch) | ~6 | binding-time validation |
| 5. **Raw-role drift risk** | 3 | `_require_role`, `_nav_role` |

---

## 1. Authorization — action / view gates (`if not _can(...): return / st.error`)

Genuine server-side guards (block the handler). Mostly **view-access**; each future route re-checks with `require_permission`.

| Line | Action key | Protects |
|------|-----------|----------|
| 3912 | `create_transaction` | New Transaction page |
| 7667 / 7713 | `upload_attachment` / `view_attachment` | attachment panels |
| 7975 / 8053 | `view_year_end_close` / `perform_year_end_close` | YEC page / close |
| 8867 | `view_partner_accounts` | Partner Accounts page |
| 9318 | `view_workers` | Workers page |
| 16150 / 17467 | `import_bank_statement` / `view_bank_statement_import` | banking import |
| 19036 | `manage_recurring_templates` OR `post_recurring_draft` | recurring page |
| 19435 / 19631 | `create_reconciliation` / `approve_reconciliation` | cash recon |
| 19938 / 20083 | `view_eod` / `close_day` | EOD close |
| 22089…22845 (×6) | `view_management_reports` | report tabs (P&L/BS/CF/etc.) |

## 2. UI visibility only (`disabled=not _can(...)`, show/hide)

**Not sufficient for API security.** The bulk of `_can` sites. Representative actions and where they gate a control whose underlying write needs a server-side guard later:

| Action key | Example sites | Underlying write needing `require_permission` on the API |
|-----------|---------------|----------------------------------------------------------|
| `create_transaction` | 18402, 18602, 18863, 21428 | create sale / expense / purchase / payable |
| `void_transaction` | 18497, 18991, 21532, 18801 | void sale / expense / purchase / payable |
| `edit_transaction` | 18736, 18758, 21744, 14965, 15312 | pay payable, record receivable payment, edit txn |
| `post_manual_journal` | 10175–10522, 21128 | opening balances, manual JE |
| `manage_banking` | 20806–21077 | add account, bank txn, void bank txn |
| `manage_inventory` | 20366–20627 | product add/edit, inventory adjust/void |
| `manage_categories` | 23322–23520 | category CRUD |
| `create_customer_vendor` / `edit_customer_vendor` | 11742–23278, 18166–20261 | customer/vendor CRUD |
| `post_partner_movement` / `void_partner_movement` / `allocate_profit` / `void_profit_allocation` | 9015–9201, 8391–8479 | partner movements, allocation |
| `post_worker_movement` / `void_worker_movement` / `manage_workers` | 9350–9661 | worker movements |
| `post_equity_movement` | 9793–9934 | capital / drawing |
| `close_fiscal_period` / `void_year_end_close` | 8301/8546, 8024 | period/year close |
| `void_reconciliation` / `void_eod` | 19516, 19990 | recon / EOD void |
| `manage_budget` | 21862 | budget save |
| `post_recurring_draft` | 19189 | recurring post |
| `delete_attachment` | 7745 | attachment delete |

(Read-side `view_statement` at 18268/20267 and `view_management_reports` show/hide are visibility for read endpoints.)

## 3. Tenant scoping (not authorization)

- `current_company_required()` (def `app.py:2967`) — fail-loud active company.
- `cq(session, Model)` (def `app.py:2984`) → `session.query(Model).filter(company_id == current_company_required())` — **hundreds** of call sites; every business read/write is company-filtered here.
- Posting/void **service shims** pass `company_id=current_company_required()` (e.g. `:2367–2507, 5985, 6249`).

For the API these map to **`require_company(ctx)`** + explicit `company_id` from the request context — never client-trusted, never ambient.

## 4. Membership gate

- `CompanyUser` validation at **login / company switch** (`:4578, :4794, :4957`) sets `active_company_role` (`:4576`) from `membership.role`; enumeration for the picker (`:1006, :4538, :4686, :4913`).
- Today this runs at **binding time** (active company is server-set from validated memberships), so per-action membership re-checks are unnecessary in Streamlit.
- For the API: **`require_company_membership(session, ctx)` must run per request** (a client-supplied `company_id` cannot be trusted).

## 5. Raw-role drift risk (full list — surface is small)

| Site | Form | Classification | Recommendation |
|------|------|----------------|----------------|
| `app.py:24564` | `if _require_role("owner")` → renders `render_member_roster_summary` | **UI visibility (read-only display)** of the team roster in Company Setup | Presentation-only; not a security boundary. For consistency, converge to `_can("manage_users")` (owner-only) — equivalent decision, removes the raw-role form. The roster *write* actions are guarded elsewhere by `manage_permissions`/`manage_users`. |
| `app.py:1066` | `_nav_role = _current_company_role() or user.get("role","viewer")` | **UI visibility** (nav page list) | Presentation-only (nav filtering via `_NAV_ROLE_PAGES`). Keep; document as visibility. |
| `app.py:1241` | same `_nav_role` (chrome) | **UI visibility** | Same. |
| `_require_role` def (`:2936`) + internal `role = _current_company_role() or u["role"]` | resolver fallback | internal | Keep until its one caller converges; then `_require_role` can be retired. |

**No scattered business-logic `role ==`/`role in` comparisons exist** — the app is already permission-centric via `_can`. The only raw-role *caller* is the single owner-roster visibility check above. This is a clean state: convergence is low-risk.

---

## Action-key → API implication map

| Action key | Predominant category today | FastAPI route guard |
|-----------|----------------------------|---------------------|
| `create_transaction`, `edit_transaction`, `void_transaction` | visibility (`disabled=`) | `require_permission` on every txn write route |
| `post_manual_journal` | visibility | `require_permission` on JE/opening-balance routes |
| `manage_banking`, `manage_inventory`, `manage_categories`, `create/edit_customer_vendor` | visibility | `require_permission` on each CRUD route |
| `post/void_partner_movement`, `allocate_profit`, `void_profit_allocation` | visibility | `require_permission` (+ owner-locked) |
| `post/void_worker_movement`, `manage_workers` | visibility | `require_permission` |
| `post_equity_movement` | visibility (owner-locked) | `require_permission` |
| `close_fiscal_period`, `perform/void_year_end_close` | mixed gate + visibility | `require_permission` (+ company) |
| `create/submit/approve/reject/void_reconciliation`, `close_day`, `void_eod` | mixed | `require_permission` |
| `import_bank_statement` | gate + visibility | `require_permission` |
| `manage_budget`, `manage_recurring_templates`, `post_recurring_draft` | visibility | `require_permission` |
| `upload/delete_attachment` | gate + visibility | `require_permission` |
| `view_*` (year_end, partner_accounts, workers, eod, bank_statement_import, management_reports, statement) | view gate / visibility | `require_permission` on read routes |

All map to **existing action keys** already resolved by `check_permission` — no new permissions invented.

---

## What must not change (P0.4d is inventory only)

- No allow/deny outcome changes; no convergence performed here (this is the catalog that authorizes P0.4c convergence + future route guards).
- `_NAV_ROLE_PAGES` nav visibility unchanged.
- Tenant scoping (`cq`/`current_company_required`) unchanged.
- Membership binding at login/switch unchanged.
- The single `_require_role("owner")` visibility check stays until convergence (documented as presentation-only).

**Net:** authorization in Streamlit is mostly **UI-visibility** (`disabled=`/show-hide), with ~20 real view gates; tenant scoping is pervasive via `cq`; membership is validated at binding time; and raw-role drift is a **single owner-roster visibility check**. The FastAPI implication is unambiguous — **every write route must `require_permission` server-side** using the same action keys, and **`require_company` + `require_company_membership` must run per request** — because the current controls protect the UI, not the action.

---

*Inventory only. No code, no implementation, behavior preserved. This catalog is the input to P0.4c (`_can`/`_require_role` convergence) and to the P2 write-endpoint guard list.*
