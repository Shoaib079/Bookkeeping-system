# P3.1 — PostgreSQL Compatibility Audit

**Mode:** Audit + documentation + lightweight contract test only. No DB migration, no Alembic, no PostgreSQL switch, no runtime/accounting/API/UI change.
**Scope:** identify everything that may break or behave differently moving SQLite → PostgreSQL.
**Verdict:** the ORM models and the service/query layer are largely portable; **the single largest blocker is the SQLite-specific schema-evolution layer** (`migrate_schema`, `PRAGMA`, raw `sqlite3` table rebuild, `sqlite_master`, a `WHERE is_void = 0` partial index) plus the `db.py` `PRAGMA` connect listener. **Money is `Float` (IEEE-754 double) in both engines, so the raw engine swap preserves accounting arithmetic exactly**; a future `NUMERIC` precision project is separate and must be characterized.

## Executive summary

| Theme | State | PG move impact |
|-------|-------|----------------|
| ORM models (types/FK/indexes/constraints) | SQLAlchemy-portable | Low — `create_all` works on PG |
| Money (`Float`) | IEEE-754 double both engines | **None for the swap** (identical arithmetic); NUMERIC = separate future project |
| Queries (filters, aggregates, `ilike`) | SQLAlchemy-abstracted | Low — a few notes (LIKE case, GROUP BY strictness) |
| Datetime (`datetime.now()`, naive) | naive local, `DateTime` (no tz) | None (PG `timestamp` stores naive identically); tz = future design note |
| **Schema evolution (`migrate_schema`, PRAGMA, raw sqlite3 rebuild)** | **SQLite-only DDL** | **High — must be replaced by Alembic (P3.2)** |
| `db.py` `PRAGMA foreign_keys=ON` connect listener | SQLite-only | **High — errors on PG; needs dialect guard (P3.2)** |
| FK enforcement | already ON via pragma | None new (PG enforces natively) |
| IDs / sequences | Integer PK autoincrement | Low — audit tests for hardcoded ids (P3.2) |
| Transactions / commit ownership | engine-agnostic (`unit_of_work`) | Low |
| Test infra (in-memory SQLite + StaticPool) | SQLite-only fixtures | Medium — PG fixtures needed for dual-engine tests (P3.2) |

## Risk table

| # | Risk area | SQLite today | PostgreSQL difference | Severity | Recommendation |
|---|-----------|--------------|------------------------|----------|----------------|
| R1 | **Schema-evolution DDL** (`migrate_schema`, `_column_exists` via `PRAGMA table_info`, raw `sqlite3` table rebuild with `PRAGMA foreign_keys=OFF`, `sqlite_master`) | works | `PRAGMA`/`sqlite_master`/rebuild **not valid on PG** | **High** | Replace with **Alembic** migrations (P3.2) |
| R2 | **`db.py` connect listener** `PRAGMA foreign_keys = ON` | required | `PRAGMA` **errors on PG** | **High** | Dialect-guard the listener (`if dialect == "sqlite"`) — propose in P3.2 |
| R3 | **SQLite SQL functions / DDL idioms** (`PRAGMA`, partial index `WHERE is_void = 0`, `CREATE INDEX IF NOT EXISTS`, one-col `ADD COLUMN`) | works | `is_void = 0` is a **boolean=integer type error** on PG; PRAGMA invalid | **High** | Move index/partial-index DDL into Alembic with `is_void IS FALSE` (P3.2) |
| R4 | **Decimal / money precision** (`Float` columns; kernel `round()` on floats) | IEEE-754 double | IEEE-754 double — **identical**; `NUMERIC` would change rounding | **Medium (future)** | Keep `Float` for the swap; **separate NUMERIC project, characterized for parity** |
| R5 | **Foreign keys** | enforced via pragma | enforced natively (always) | **Low** | No change; FKs already enforced — no new violations expected |
| R6 | **Datetime / timezone** | `datetime.now()` naive, `DateTime` no tz | `timestamp without time zone` stores naive identically | **Low** | No change for swap; tz-aware = future multi-region design note |
| R7 | **Transaction behavior** | autocommit-ish, looser isolation | MVCC, stricter | **Low** | `unit_of_work` boundary is engine-agnostic; re-run dual-run parity on PG (P3.2) |
| R8 | **IDs / sequences** | INTEGER PK autoincrement | SERIAL/IDENTITY (monotonic) | **Low** | Audit tests for hardcoded id values / id-reuse assumptions (P3.2) |
| R9 | **LIKE case-sensitivity** | `LIKE` ASCII case-**insensitive** | `LIKE` case-**sensitive** (`ILIKE` for insensitive) | **Low** | `posting.py` transfer-pairing `.like("Transfer from {name}%")` uses exact-case generated text → safe; document the difference |
| R10 | **GROUP BY strictness** | lenient | every non-aggregate selected col must be grouped | **Low–Med** | Audit each `.group_by` site (P3.2); current aggregates are mostly scalar `func.sum(...)` |

## Detailed findings

### Query portability findings
- **No SQL `strftime`/date-formatting in queries.** All `strftime` usages are **Python-side** display/formatting (`exports.py`, `ui/permissions.py`, invoice-number stamps in `write_sales.py`/`staff_capture.py`) — engine-agnostic. Date filtering compares Python `date` objects against `Date` columns → portable.
- **`ilike`** (`recipe_costing.py` ×3) is portable — SQLAlchemy emits `LOWER(x) LIKE LOWER(y)` on SQLite and native `ILIKE` on PG.
- **`.like()`** for bank-transfer pairing (`posting.py:1627`, `"Transfer from {acct.name}%"`) — the only `LIKE` in business logic. SQLite matches ASCII case-insensitively, PG case-sensitively; the predicate compares against text the app itself generated with the same casing, so behavior is unchanged. Flagged (R9).
- **Raw `text()` SQL:** portable `SELECT id FROM companies` reads (`app.py:657/685/710/735`) work on PG. **`text("PRAGMA …")` / `sqlite_master` / table-rebuild** (`app.py:1645/1719–1731/1757/1787/1946`) are SQLite-only (R1/R3).
- **NULL comparisons** use SQLAlchemy `== None`/`.is_(None)` → `IS NULL` on both. Portable.
- **GROUP BY:** scan needed (R10); current aggregate reads are predominantly scalar `func.sum/count(...).filter(...)` without non-aggregate projections.

### Model portability findings
- Column types: `Float` (money), `Boolean`, `Date`, `DateTime`, `String`, `Integer`, `Text`, plus `ForeignKey`, `UniqueConstraint`, and `Index` — all SQLAlchemy-portable; `Base.metadata.create_all` produces valid PG DDL.
- **Booleans:** filtered via `== True/False` (`# noqa: E712`) — abstracted by SQLAlchemy (0/1 in SQLite, true/false in PG). Python-side `default=` values (not `server_default`) → portable.
- **Partial unique index** `uq_yec_year … WHERE is_void = 0` (raw DDL in `migrate_schema`) — partial indexes exist on PG, but the predicate `is_void = 0` is a **boolean = integer type error** on PG; must become `is_void IS FALSE` under Alembic (R3).
- `company_id` columns are `nullable=True` (Phase-14A) — confirmed by the P2-HARDEN work; PG won't reject the (now-stamped) rows.

### Transaction / session findings
- Commit ownership is centralized in `services/unit_of_work.py` + `services/commit_modes.py` (boundary vs internal) — **engine-agnostic**. No SQLite-specific commit reliance.
- No tests depend on SQLite autocommit quirks; the dual-run parity harness (`tests/helpers/commit_parity.py`) is logic-level and re-usable on PG.
- The raw `sqlite3` rebuild path uses `PRAGMA foreign_keys=OFF` + `BEGIN` — a **migration mechanism**, replaced by Alembic; not a runtime transaction concern.

### Money precision findings
- All monetary columns are `Float` (e.g., `JournalEntryLine.debit/credit`, `*.amount/balance/paid_amount`). SQLite and PG both back `Float` with **IEEE-754 double precision**, so the kernel's `round()`-based accumulation produces **identical results** after the swap — accounting behavior is preserved with no change.
- A future move to `NUMERIC`/`Decimal` (the correct long-term representation) **changes rounding semantics** and is the **single most accounting-sensitive** change. It must be a dedicated project with golden-value characterization (the float accumulation order is already pinned by posting tests) — **not** bundled into the engine swap.

## Test migration plan
- Current fixtures use in-memory SQLite (`create_engine("sqlite://", poolclass=StaticPool)`) — fast and SQLite-only.
- For dual-engine confidence (P3.2): add an optional PG-backed fixture (e.g., `pytest-postgresql`/testcontainers) selected by env, reusing the same seed helpers; keep SQLite as the default fast path.
- Extend the **dual-run parity harness** to optionally run a flow on both engines and assert identical persisted state (the strongest portability guard).
- Audit tests for **hardcoded ID assumptions** (id == 1, id-reuse) and order-by-id expectations (R8).

## Recommended P3.2 tasks
- **P3.2-A — Alembic adoption:** replace `migrate_schema` / `_column_exists` / raw-`sqlite3` rebuild / `sqlite_master` / `CREATE INDEX IF NOT EXISTS` / partial index (`is_void IS FALSE`) with Alembic migrations (R1, R3).
- **P3.2-B — Engine dialect guard:** gate the `db.py` `PRAGMA foreign_keys=ON` connect listener on `dialect == "sqlite"` so PG connects cleanly (R2). Tiny runtime change — deferred to P3.2.
- **P3.2-C — Query portability sweep:** audit every `.group_by` for PG strictness; confirm `.like` case behavior; document any `text()` SQL (R9, R10).
- **P3.2-D — ID/sequence test audit:** scan tests for hardcoded ids / id-reuse / order-by-id assumptions (R8).
- **P3.2-E — PG test fixtures + dual-run extension:** optional PG fixture + dual-engine parity (test infra).
- **P3.2-F (future, separate):** `Float → NUMERIC` money precision project, characterized for rounding parity (R4) — **not** part of the engine swap.

## No-change decisions (P3.1)
- **No `Float → NUMERIC` change now** — the swap preserves accounting with `Float`; NUMERIC is a deliberate future project.
- **No `db.py` dialect guard now** — shipped in **P3.2-B** (`PRAGMA foreign_keys=ON` gated on `dialect.name == "sqlite"`).
- **No Alembic now** — documented only; P3.2-A.
- **No timezone-aware datetime change** — naive is consistent across engines; future design note.
- **No query rewrites** — `ilike`/date-filter/`text()` reads are portable; only documented.

---

*Audit only. No DB migration, no Alembic, no PG switch, no runtime/accounting/API/UI change. The portability blockers are concentrated in the SQLite-specific schema-evolution layer and the `db.py` PRAGMA listener (both → Alembic/dialect-guard in P3.2); the ORM/query/transaction layers are largely portable, and the `Float` money representation makes the raw engine swap behavior-preserving (NUMERIC is a separate, characterized future project).*
