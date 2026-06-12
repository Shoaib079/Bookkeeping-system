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
| **TD-GOV-03** | **Migration Cleanup report section** required at end of every implementation report (5-part template below); codified in MIGRATION-READINESS-01 | High | **Resolved** | Adopted 2026-06-05 |

---

## Implementation report — Migration Cleanup template

Copy this section into every implementation completion report:

```markdown
## Migration Cleanup

### 1. Code to keep during FastAPI/React migration
- …

### 2. Code likely to replace during FastAPI/React migration
- …

### 3. Dead code found
- …

### 4. Temporary Streamlit-only code
- …

### 5. Items added to TECH_DEBT_AND_MIGRATION_CLEANUP.md
- …
```

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
| **TD-DSC-07** | **Roadmap / docs drift** — keep DSC phase status current in `ROADMAP.md` and spec §10 as P2–P4 land | Low | **Resolved** | 2026-06-05 — synced after DSC-P2: `ROADMAP.md`, `docs/DAILY_SALES_CLOSE_01_SPEC.md` §10, `docs/AUDIT_HISTORY.md`, `docs/TEST_COVERAGE_MAP.md`, `ARCHITECTURE_HANDOFF.md` |
| **TD-DSC-08** | **UI `_erp()` lazy import** — `ui/external_sales_verification.py` reaches into `app.py` for `_t`, `_can`, `amount_input`, `current_company_required`; replace with injected context or shared `ui/context.py` at API migration | Medium | Open | FastAPI Phase D |
| **TD-DSC-09** | **Widget session keys** — `esv_*` form keys and `esv_form_loaded_for` date-sync logic are Streamlit-only; React form state replaces entirely | Low | Open | React module for ESV |

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

## RC-P1 / Recipe Costing (TD-RC)

| ID | Item | Priority | Status | When / trigger |
|----|------|----------|--------|----------------|
| **TD-RC-01** | **Service commits internally** — `create_ingredient`, `save_recipe`, `bulk_update_costs`, etc. call `session.commit()`; refactor to `flush()` + caller-owned transaction for FastAPI | Medium | Open | FastAPI Phase B |
| **TD-RC-02** | **Error surface** — plain English `error` on `MutationResult`; add stable `error_code` (e.g. `RC_CYCLE_DETECTED`) for React/FastAPI | Medium | Open | Before FastAPI exposure |
| **TD-RC-03** | **Float money** — ingredient `cost_per_base_unit` and computed breakdown use `float`; migrate to `Decimal` with TD-MIG-04 | Low | Open | Global migration prep |
| **TD-RC-04** | **Unit registry** — hardcoded `_UNIT_FACTORS` map; optional registry/settings for locale-specific units | Low | Open | RC-P2+ |
| **TD-RC-05** | **Dual `compute_recipe_cost` dispatch** — pure graph vs DB via `isinstance(Session)`; split into `rollup_recipe_cost` + `compute_recipe_cost` at API migration | Low | Open | FastAPI Phase B |
| **TD-RC-06** | **Roadmap / spec drift** — add `RECIPE_COSTING_01_SPEC.md` and ROADMAP phase table when RC-P2+ lands | Low | Open | RC-P1b UI shipped 2026-06-05; spec file still pending |
| **TD-RC-09** | **Widget session keys** — `rc_*` draft line state and recipe editor keys are Streamlit-only; React form state replaces at API migration | Low | Open | RC-P1b UI |
| **TD-RC-10** | **UI `_erp()` lazy import** — `ui/recipe_costing.py` reaches into `app.py` for `_t`, `_can`, `amount_input`, `current_company_required`; replace with injected context or `ui/context.py` | Medium | Open | FastAPI Phase D |

### RC-P1b Migration Cleanup (2026-06-05)

#### 1. Code to keep during FastAPI/React migration
- All RC-P1 items (models, service, tests)
- `ui/recipe_costing.py` — three thin renderers; restaurant-friendly tree display
- Registry nav keys, permissions, EN/TR `rc.*` locales
- `tests/test_recipe_costing_ui_contract.py`

#### 2. Code likely to replace during FastAPI/React migration
- `ui/recipe_costing.py` → React recipe/ingredient modules
- `_erp()` lazy `app.py` import in UI — shared `ui/context.py` or API props
- `rc_*` Streamlit session keys for draft recipe lines
- Internal `session.commit()` in service (TD-RC-01)

#### 3. Dead code found
- None

#### 4. Temporary Streamlit-only code
- `ui/recipe_costing.py` entire module
- `rc_draft_lines`, `rc_loaded_recipe_id`, `rc_recipe_pick` session keys
- `_recipe_tree_markdown` presentation (reimplement in React)

#### 5. Future cleanup items (registered above)
- TD-RC-09, TD-RC-10 added this session

### RC-P1 Migration Cleanup (2026-06-05)

#### 1. Code to keep during FastAPI/React migration
- `models.Ingredient`, `models.Recipe`, `models.RecipeLine` — core schema; sub-recipe via `RecipeLine.sub_recipe_id` only (no SubRecipe table)
- `services/recipe_costing.py` — unit conversion, validation, cost rollup, `where_used`, CRUD mutations
- Frozen DTOs: `IngredientView`, `RecipeLineCost`, `RecipeCostBreakdown`, `WhereUsedEntry`, `ValidationResult`, `MutationResult`
- Tests: `tests/test_recipe_costing_service.py`, `tests/test_recipe_costing_models.py`
- `migrate_schema()` indexes for `ingredients`, `recipes`, `recipe_lines`

#### 2. Code likely to replace during FastAPI/React migration
- `compute_recipe_cost` Session dispatch — split into explicit API handler + pure `rollup` import
- `session.query()` style ORM access — SQLAlchemy 2.0 `select()` (TD-MIG-05)
- Internal `session.commit()` in service mutations — FastAPI dependency-injected unit of work
- `AuditLog` string `description` JSON blobs — structured audit event schema

#### 3. Dead code found
- None in RC-P1 scope (greenfield module)

#### 4. Temporary Streamlit-only code
- None — RC-P1 deliberately ships no UI, no `app.py` wiring, no Streamlit session keys

#### 5. Future cleanup items (registered above)
- TD-RC-01 through TD-RC-06 added this session

---

## Reference implementation

**DSC-P1** (`services/daily_sales_close.py`) is the first module built under:

- [ARCHITECTURE-PROTECTION-01](../ROADMAP.md#architecture-protection-01--service-first-development-rule)
- [VENDOR-NEUTRAL-01](../ROADMAP.md#vendor-neutral-01--vendor-neutral-architecture-rule)
- [MIGRATION-READINESS-01](../ROADMAP.md#migration-readiness-01--fastapireact-ready-service-checklist)

**RC-P1** (`services/recipe_costing.py`) follows the same pattern — second reference implementation under MIGRATION-READINESS-01.

Audit source: DSC-P1 migration readiness review (2026-06-05).

---

*Update this file when debt items are added, scheduled, or resolved.*
