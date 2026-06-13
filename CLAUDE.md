# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py

# Run all tests
pytest tests/

# Run a single test
pytest tests/test_models.py::test_customer_model_can_be_created
```

## Architecture

This is a single-file Streamlit accounting ERP. The entire UI and business logic lives in `app.py` (~5,500 lines). The supporting files are:

| File | Role |
|---|---|
| `db.py` | SQLAlchemy engine + `Base` + `SessionLocal`; connects to `erp_data.db` (SQLite) |
| `models.py` | All ORM models |
| `exports.py` | `df_to_excel_bytes` and `df_to_pdf_bytes` helpers used by every page |
| `registry/` | Phase 14D-B2a settings & module metadata catalog (`get_setting`, `get_effective_config`) |
| `docs/` | Project memory: banking/CC status, audit log, accounting decisions, test map |
| `ROADMAP.md` | Phase plan and status |
| `ARCHITECTURE_HANDOFF.md` | Non-coder architecture summary (stale for Phase 18; prefer `docs/`) |
| `settings.json.migrated` | Legacy settings file; settings now live in the database |

### Navigation flow

`main()` renders the sidebar via `_render_navigation_tree()` and dispatches to a top-level `render_*` function per `nav_selection` (`_PAGE_DISPATCH`). Page-transition logic clears transient `confirm_`, `void_`, `paying_` session-state keys to prevent stale dialogs from persisting across pages.

Sidebar filters (global search + date range) are stored in `st.session_state` and only rendered on Transaction History and Reports pages.

### Database session lifecycle

`get_session()` returns `SessionLocal()`. In `main()`, every page call happens inside `with get_session() as session:`, which also runs all startup tasks (schema migrations, seeds) on each request.

### Schema evolution

- **`migrate_schema()`** runs on every startup. It issues `ALTER TABLE ADD COLUMN` statements and silently rolls back if the column already exists — safe to run repeatedly.
- **`MigrationFlag`** table guards one-time operations: `initialize_chart_of_accounts`, `migrate_sales_v1`, `migrate_expenses_v1`, `initialize_categories_v1`. These must never re-run after the first success.

### Double-entry accounting

All financial transactions post through `create_journal_entry(session, date, description, reference_type, reference_id, lines)` where `lines` is a list of `(account_id, debit, credit)` tuples. This function:
1. Blocks posting to closed fiscal periods (except `reference_type="PeriodClose"`) and closed fiscal years.
2. Enforces `sum(debit) == sum(credit)` within 1 cent — rolls back and raises `ValueError` if unbalanced.
3. Does **not** update `ChartOfAccounts.balance` in-place. Balance reads use `calculate_account_balance()` (derived from journal lines). `sync_account_balances()` runs at startup to refresh the cached `balance` column.

Convenience wrappers like `post_cash_sale`, `post_purchase`, `post_expense`, etc. call `create_journal_entry` with the correct account pairs and `reference_type` strings.

### Void/reversal pattern

Each transactional entity has a `void_*()` function (e.g. `void_sale`, `void_purchase`). Voiding:
1. Calls `create_reversing_journal_entry()` which swaps every debit/credit from the original journal entry.
2. Sets `is_void=True`, `voided_at`, `void_reason` on the record.
3. Writes an `AuditLog` entry.

Credit purchases cascade void to their auto-created `Payable`. Bank transfer voids cascade to the paired destination transaction.

### Legacy model migration

`CashSale`, `CreditSale`, `Salary`, and `Expense` tables exist only for backward compatibility. On first startup they are migrated into the unified `Sale` and `ExpenseRecord` tables. New code should only write to `Sale` and `ExpenseRecord`.

### Amount input

Use `amount_input(label, key, ...)` instead of `st.number_input` for monetary fields. It wraps a text input and calls `_parse_amount_str()` which handles both US (`1,000.50`) and European (`1.000,50`) number formats.

### Export

Call `render_export_buttons(df, prefix)` to add an Excel/PDF download popover to any page. The `prefix` string becomes the filename stem and PDF title.

## ARCHITECTURE-PROTECTION-01 (active)

All new modules must be **service-first** and **migration-safe**. Required order:

1. Database models (`models.py`)
2. Service / business logic (`services/` or `registry/` — not `app.py`)
3. Tests (`tests/`)
4. Minimal Streamlit UI in `app.py` only if useful

**Strict:** Streamlit must not own business logic. Accounting rules live in reusable services. Tests are authoritative.

**Pause before deep Streamlit UI** for: login/auth, staff portal, mobile uploads, permission dashboards, approval inboxes, advanced admin/settings.

**Prefer services now:** accounting, reports, Daily Sales Close, Recipe Costing.

See [ROADMAP.md § ARCHITECTURE-PROTECTION-01](./ROADMAP.md#architecture-protection-01--service-first-development-rule) and [FUTURE-MIGRATION-01](./ROADMAP.md#future-architecture--long-term-roadmap).

## VENDOR-NEUTRAL-01 (active)

Core code must **not** depend on named POS/vendor products. Use generic **External Sales Source** fields: free-text `source_name`, optional `source_type` category, optional `branch_location`. No vendor enums, settings keys, or service branches in core. Vendor names in docs = examples only. Banking “POS Settlement” = card clearing, not a POS product. Optional vendor adapters live outside core later.

See [ROADMAP.md § VENDOR-NEUTRAL-01](./ROADMAP.md#vendor-neutral-01--vendor-neutral-architecture-rule) · [ARCHITECTURE-PROTECTION-01](#architecture-protection-01-active) · [DAILY_SALES_CLOSE_01_SPEC.md](./docs/DAILY_SALES_CLOSE_01_SPEC.md).

## MIGRATION-READINESS-01 (active)

Design every `services/` module for future **FastAPI + React** callers:

- **Explicit inputs** — `company_id`, `user_id`, DTOs; no `cq()` or Streamlit in services
- **Serializable outputs** — frozen dataclasses with `to_dict()`; no ORM at public boundary
- **Validation separate from UI** — pure `validate_*` / `compute_*` functions
- **Tests without Streamlit** — in-memory DB + explicit tenant context
- **Log debt** — [TECH_DEBT_AND_MIGRATION_CLEANUP.md](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md)

**Exemplar:** DSC-P1 — `services/daily_sales_close.py`. UI exemplar: DSC-P2 — `ui/external_sales_verification.py`.

**Implementation reports:** End every completion report with the **Migration Cleanup** section (5 parts) — see [TECH_DEBT template](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md#implementation-report--migration-cleanup-template).

See [ROADMAP.md § MIGRATION-READINESS-01](./ROADMAP.md#migration-readiness-01--fastapireact-ready-service-checklist) · [ROADMAP.md § FUTURE-MIGRATION-01](./ROADMAP.md#future-architecture--long-term-roadmap) · [ARCHITECTURE-PROTECTION-01](#architecture-protection-01-active).

## Project memory — documentation gate

**No task is complete until documentation is updated** after every feature, bug fix, accounting change, audit, migration, or major test addition:

1. `docs/BANKING_RECON_CC_STATUS.md` — if feature status changed
2. `docs/AUDIT_HISTORY.md` — append a dated entry for every completed session
3. `docs/ACCOUNTING_DECISIONS.md` — if accounting behavior changed
4. `docs/TEST_COVERAGE_MAP.md` — if tests were added or modified
5. `docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md` — if migration-prep or service-layer debt is identified or resolved

Cursor rule: `.cursor/rules/erp-project-memory.mdc` (also under `registry/.cursor/rules/`).
