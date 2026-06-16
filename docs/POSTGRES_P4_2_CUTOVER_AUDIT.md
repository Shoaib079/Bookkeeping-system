# POSTGRES-P4.2 — Production Runtime Cutover Readiness Audit

**Mode:** Audit only. **No implementation, no schema change, no Alembic change, no runtime DB switch, no feature flag flipped.** Assesses readiness for a **PostgreSQL production runtime cutover** after the FastAPI / Banking / Auth / Money-Decimal progress.

## Verdict — **NOT READY**

A PostgreSQL **production** runtime cutover is **not ready**. Two hard blockers stand independently of everything else: **(1) Alembic is not yet authoritative** (the flag defaults off and `migrate_schema()` still runs the schema — and `migrate_schema()` cannot run on PostgreSQL), and **(2) the Money-Decimal NUMERIC migration is unimplemented** (`models.py` has **0** `Numeric` columns; no `0002` revision; MD-05 is a plan). A Float-on-PG swap would be *arithmetically* identical (P3.1 R4) but would defer the NUMERIC conversion onto a **populated production PG** DB — harder and riskier than converting on SQLite first — so it is not recommended as the cutover path.

## Status check (the ten items)

| # | Area | Status |
|---|------|--------|
| 1 | **SQLite runtime vs PG test-only** | ✅ As designed — SQLite is production runtime; PG is test-only (`DATABASE_URL = sqlite:///erp_data.db`). |
| 2 | **Alembic authority** | 🟡 Wiring exists (`prepare_schema_startup_authoritative`, `_run_schema_startup`), but `ERP_ALEMBIC_AUTHORITATIVE` **defaults off**; authority **not flipped**; bake-in (P3.8-L) not completed. |
| 3 | **`migrate_schema()` role** | 🟡 **Still authoritative** and runs first; **SQLite-only DDL/PRAGMA — invalid on PG.** PG requires Alembic-only schema. |
| 4 | **MONEY-DECIMAL-01..05** | 🟡 MD-01 (audit), MD-02 (golden vectors), MD-03 (`money.py`), MD-04a/04b (helpers) **done**; **MD-05 = plan only**; **models still `Float` (0 `Numeric`)**; no `0002`. |
| 5 | **FastAPI P0/P1/P2** | ✅ Service layer + JWT auth + P2 write families green and **engine-agnostic**; commit ownership centralized; PG-ready at the service layer. |
| 6 | **Banking-service risks** | ✅ Write services stamp `company_id` explicitly; engine-agnostic; residual items are **UX**, not PG blockers. |
| 7 | **Auth-session risks** | ✅ Restore cookie works (secret-gated); residual **non-HttpOnly** hardening is PG-independent (AUTH-SESSION-02 backlog). |
| 8 | **P2-HARDEN-01** | ✅ H01/H02 complete; **H03 deferred** (audited) — explicit stamping is the standard; not a PG blocker. |
| 9 | **Optional PG tests** | 🟡 Present: `test_p3_1_postgres_compatibility_audit`, `test_p3_2_postgres_fixture`, `test_p4_0_postgres_enablement_plan`, `test_p4_1_local_postgres_validation`. **Missing:** `0002` migration test, dual-run parity, golden vectors under the Decimal path. |
| 10 | **Exact blockers** | See the blocker list below. |

## Blocker list (must clear before production PG runtime)

1. **Alembic not authoritative.** Complete the P3.8 flag-gated cutover + P3.8-L bake-in so `ERP_ALEMBIC_AUTHORITATIVE=1` is proven on SQLite; **`migrate_schema()` cannot run on PG**, so PG schema must be Alembic-only. **(Hard.)**
2. **Money-Decimal NUMERIC unimplemented.** Land MD-05-IMPL-1..5 (author `0002`, switch models to `Numeric(asdecimal=True)`, route services through `services/money.py`, quantize data, **on SQLite first**) so PG carries money exactly. Cutting over with Float defers a populated-PG conversion. **(Hard.)**
3. **PG schema build path.** PG DBs must be created via `alembic upgrade head` (P4.0) **including `0002`** — never `migrate_schema()`. Requires (1) and (2). **(Hard.)**
4. **PG dual-run parity not proven on production-shaped data.** P4.1 is local validation only; production cutover needs full **dual-run parity** (posting + P&L/BS/CF/Trial Balance **to the cent**) and golden vectors under the Decimal path. **(Hard.)**
5. **SQLite→PG data migration project.** A separate, characterized export/load + **verify balances/reports** project (per P4.0); not built. **(Hard.)**

## Nice-to-have list (not blockers)

- **AUTH-SESSION-02** server-set **HttpOnly** cookie + JWT refresh unification (security hardening; PG-independent).
- **P2-HARDEN-01-H03** fail-loud stamp guard (deferred; explicit stamping already sufficient).
- **Banking UX** residual items (BANKING-UX cockpit polish) — unrelated to the engine.
- **Percentage/quantity** columns staying Float — out of money scope; revisit separately.

## Required tests (before cutover)

- **`0002` migration smoke (SQLite):** `upgrade 0001→0002` on a DB copy; app starts; representative post/read works.
- **PG migration test:** build to head incl. `0002` on `ERP_TEST_POSTGRES_URL`; columns are `NUMERIC(19,2/4/8)`; values exact.
- **Golden vectors under Decimal:** MD-02 vectors reproduce exactly through the Numeric/Decimal path.
- **Dual-run parity (PG vs SQLite):** posting kernel + reports identical to the cent on a representative dataset.
- **Schema equivalence + constraint preservation:** PG schema (Alembic) == SQLite reference (tables/columns/indexes/uniques/FKs).
- **Startup authority tests:** `ERP_ALEMBIC_AUTHORITATIVE=1` decision matrix green (P3.8 series) on the target DB states.
- **Full suite green** on the cutover commit.

## Required implementation slices (sequenced — NOT in this audit)

1. **P3.8 finish:** flag-gated Alembic authority + P3.8-L bake-in (SQLite).
2. **MD-05-IMPL-1..5:** `0002` Numeric migration + model switch + service routing + quantization (SQLite first).
3. **P4.x PG build:** PG schema via Alembic incl. `0002`; optional_postgres suite green.
4. **Dual-run parity + golden-under-Decimal** on PG.
5. **SQLite→PG data migration project** (export/load + verify balances/reports).
6. **Flag-gated PG runtime cutover** (backup + owner confirmation), reusing the P3.8 machinery; SQLite remains the rollback target.

## Cutover checklist (when the blockers clear)

- [ ] Full `pytest` green on the cutover commit.
- [ ] `ERP_ALEMBIC_AUTHORITATIVE=1` proven + baked-in on SQLite; `migrate_schema()` retired-or-legacy-no-op.
- [ ] `0002` money-Numeric applied; models `Numeric`; services route through `money.py`.
- [ ] PG built via `alembic upgrade head` (incl. `0002`); schema equivalence + constraint preservation verified.
- [ ] Dual-run parity green (posting + reports to the cent); golden vectors green under Decimal.
- [ ] Production data migrated + **balances/reports verified** against the SQLite source.
- [ ] **Backup taken** (SQLite source + PG `pg_dump`) and **operator/owner confirmation** recorded.
- [ ] Rollback rehearsed (below).

## Rollback plan

- **Keep SQLite as the rollback target** — do not decommission the SQLite source until PG is proven in production.
- **Revert `DATABASE_URL`** to SQLite and restart to fall back; restore the **pre-cutover backup** (SQLite file and/or `pg_restore`) if data was touched.
- **Never hand-edit accounting tables** — recovery is restore-from-backup only (void-not-delete policy).
- **Flag-off** any cutover flag to return to the retained SQLite + `migrate_schema()` path.

## ROADMAP.md update recommendation

- Record **POSTGRES-P4.2 = NOT READY** with the five hard blockers and the sequenced slices above.
- State the **mandatory order**: P3.8 Alembic authority + bake-in → **MD-05 NUMERIC on SQLite** → PG build via Alembic (incl. `0002`) → dual-run parity + golden-under-Decimal → SQLite→PG data migration → flag-gated PG cutover (backup + owner confirmation).
- Note that a **Float-on-PG swap is arithmetically safe but not recommended** (defers a populated-PG NUMERIC conversion); the intended end-state is NUMERIC-on-PG.
- Reuse the **P3.8 flag-gated, backup-first** cutover machinery; SQLite stays the rollback target.

## Test run note

This audit changes no code; the FastAPI/Banking/Auth/Money/P2-HARDEN suites remain as they are. pytest cannot run in this sandbox (no `sqlalchemy`); run locally. This audit adds only a doc + a pure-stdlib doc-contract test.

## No-change statement (POSTGRES-P4.2 audit)

- **No implementation, no schema change, no Alembic change, no runtime DB switch, no feature flag flipped, no `app.py`/`models.py` edit.** Verdict + blockers + nice-to-haves + required tests + required slices + cutover checklist + rollback + ROADMAP recommendation only.

---

*Audit only. Verdict: **NOT READY** for PostgreSQL production runtime cutover. Two hard, independent blockers: Alembic is not yet authoritative (flag default off; `migrate_schema()` still authoritative and SQLite-only — invalid on PG) and the Money-Decimal NUMERIC migration is unimplemented (models still Float, 0 Numeric, no `0002`; MD-05 is a plan). Plus: PG must be Alembic-built incl. `0002`, dual-run parity is unproven on production-shaped data (only P4.1 local validation exists), and a characterized SQLite→PG data-migration project is not built. Engine-agnostic layers (FastAPI P0/P1/P2, Banking write services, Auth restore cookie, P2-HARDEN H01/H02) are PG-ready; H03 deferred and Auth HttpOnly hardening are non-blockers. Mandatory order: finish P3.8 Alembic authority + bake-in → MD-05 NUMERIC on SQLite → PG build via Alembic → dual-run parity + golden-under-Decimal → data migration → flag-gated PG cutover with backup + owner confirmation. A Float-on-PG swap is arithmetically safe (P3.1 R4) but not recommended (defers a populated-PG conversion). Rollback = keep SQLite as the target, revert DATABASE_URL, restore backup, never hand-edit accounting tables.*
