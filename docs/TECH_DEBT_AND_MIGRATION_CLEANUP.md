# Technical Debt & Migration Cleanup Register

**Purpose:** Living register of service-layer extraction, FastAPI/React prep, and cross-cutting migration debt.  
**Governance:** [MIGRATION-READINESS-01](../ROADMAP.md#migration-readiness-01--fastapireact-ready-service-checklist) · [FUTURE-MIGRATION-01](../ROADMAP.md#future-architecture--long-term-roadmap)

**When to update:** Whenever migration-prep debt is identified, scheduled, or resolved. Required by [MIGRATION-READINESS-01](../ROADMAP.md#migration-readiness-01--fastapireact-ready-service-checklist) item 8.

**Status key:** `Open` · `Scheduled` · `In progress` · `Resolved` · `Won't fix`

---

## Governance (TD-GOV)

| ID | Item | Priority | Status | Notes |
|----|------|----------|--------|-------|
| **TD-GOV-01** | Document **MIGRATION-READINESS-01** in `ROADMAP.md`, `ARCHITECTURE_HANDOFF.md`, `CLAUDE.md`, and Cursor rules; use DSC-P1 as reference implementation checklist | High | **Resolved** | Adopted 2026-06-05 |
| **TD-GOV-02** | Maintain this register (`TECH_DEBT_AND_MIGRATION_CLEANUP.md`) as the canonical tech-debt log for service extraction and API prep | High | **Resolved** | Created 2026-06-05 |

---

## DSC-P1 / External Sales Verification (TD-DSC)

| ID | Item | Priority | Status | When / trigger |
|----|------|----------|--------|----------------|
| **TD-DSC-01** | **Duplicate ERP sales aggregation** — `services/daily_sales_close.compute_erp_sales_totals` vs `app.calculate_eod_snapshot` inner `_sale_sum` logic; extract shared helper (e.g. `services/sales_daily_totals.py`) and point both callers at it | High | Open | Before DSC-P3 EOD warning hook |
| **TD-DSC-02** | **Service commits internally** — `save_draft`, `verify_external_sales`, and `void_verification` call `session.commit()` twice (data + audit); refactor to `flush()` + optional caller `commit` for FastAPI transaction control | Medium | Open | FastAPI Phase B |
| **TD-DSC-03** | **Error surface** — plain English `error` strings on `MutationResult`; add stable `error_code` (e.g. `ESV_SOURCE_REQUIRED`) for React/FastAPI clients | Medium | Open | Before FastAPI exposure |
| **TD-DSC-04** | **Module naming** — `services/daily_sales_close.py` vs entity `ExternalSalesVerification`; consider `external_sales_verification.py` with backward-compatible re-export | Low | Open | Optional clarity pass |
| **TD-DSC-05** | **Registry tolerance** — hardcoded `DEFAULT_TOLERANCE = 0.01`; wire `operations.sales_verify_tolerance` registry key per spec | Medium | Open | DSC-P2+ |
| **TD-DSC-06** | **Stale snapshot** — `sale_count_snapshot` only; amount edits without count change do not flag stale (same limitation as EOD); document or extend | Low | Open | DSC-P3+ |
| **TD-DSC-07** | **Roadmap / docs drift** — keep DSC phase status current in `ROADMAP.md` and spec §10 as P2–P4 land | Low | **Resolved** | DSC-P1 marked complete 2026-06-05 |

---

## Global migration (TD-MIG)

Inherited cross-cutting debt — not introduced by DSC-P1 alone.

| ID | Item | Priority | Status | When / trigger |
|----|------|----------|--------|----------------|
| **TD-MIG-01** | Extract remaining `app.py` business logic into `services/` ([FUTURE-MIGRATION-01](../ROADMAP.md#future-architecture--long-term-roadmap) Phase A) | High | Open | Incremental per module |
| **TD-MIG-02** | Replace Streamlit `cq()` / `_current_company_id()` with explicit `company_id` in all new services; migrate legacy callers incrementally | High | Open | Per new service module |
| **TD-MIG-03** | SQLite → PostgreSQL: validate partial unique index `uq_esv_active` (`COALESCE(branch_location,'')`) and equivalent constraints on Postgres | Medium | Open | Pre-PostgreSQL cutover |
| **TD-MIG-04** | Float → `Decimal` for money fields across models and services | Low | Open | Global migration prep |
| **TD-MIG-05** | SQLAlchemy 1.x `session.query()` → 2.0 `select()` style | Low | Open | Global migration prep |

---

## Reference implementation

**DSC-P1** (`services/daily_sales_close.py`) is the first module built under:

- [ARCHITECTURE-PROTECTION-01](../ROADMAP.md#architecture-protection-01--service-first-development-rule)
- [VENDOR-NEUTRAL-01](../ROADMAP.md#vendor-neutral-01--vendor-neutral-architecture-rule)
- [MIGRATION-READINESS-01](../ROADMAP.md#migration-readiness-01--fastapireact-ready-service-checklist)

Audit source: DSC-P1 migration readiness review (2026-06-05).

---

*Update this file when debt items are added, scheduled, or resolved.*
