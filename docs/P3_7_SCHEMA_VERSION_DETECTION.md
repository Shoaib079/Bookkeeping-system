# P3.7 — Read-Only Alembic Schema Version Detection

**Status:** Shipped (read-only utility + tests)  
**Mode:** Small runtime helper + contract tests. **No migration execution.**

**Related:** [P3.4-D Baseline Migration](./P3_4_D_BASELINE_MIGRATION.md) · `services/schema_version.py`

---

## Purpose

Provide **safe, read-only** inspection of the database’s Alembic stamp vs local revision files so future startup/cutover logic (P3.8+) can branch without guessing.

| Does | Does not |
|------|----------|
| `SELECT` from `alembic_version` when present | `alembic upgrade` |
| Parse local `alembic/versions/*.py` for head | `alembic stamp` |
| Return status + human message | `CREATE TABLE`, `ALTER`, or any DDL |
| Work on SQLite today; dialect-neutral reads | Make Alembic authoritative |
| | Remove or disable `migrate_schema()` |

**`migrate_schema()` remains authoritative** for schema evolution until an approved cutover task.

---

## API

```python
from services.schema_version import detect_schema_version, detect_schema_version_from_session

info = detect_schema_version(engine)          # Engine or Connection
info = detect_schema_version_from_session(session)

info.status          # str — see below
info.db_revision     # str | None — value in alembic_version
info.head_revision   # str | None — from local files (currently "0001")
info.message         # human-readable explanation
info.known_revisions # tuple of revision ids parsed from disk
```

Helpers: `discover_local_revisions()`, `resolve_head_revision()`, `format_schema_version_summary()`.

---

## Status meanings

| Status | When | Typical meaning |
|--------|------|-----------------|
| **`unstamped`** | No `alembic_version` table, or table has zero rows | Legacy DB evolved via `migrate_schema()` only; not Alembic-stamped yet |
| **`at_head`** | Exactly one row; `version_num` equals local head | DB stamp matches newest local revision (today: `0001`) |
| **`behind_head`** | One row; revision is in local files but not head | Stamped DB needs `upgrade` after cutover (e.g. DB at `0001`, code head `0002`) |
| **`ahead_of_code`** | One row; revision sorts after local head and is **not** in local files | DB was stamped/upgraded with newer migrations than this deployment |
| **`unknown`** | Multiple rows, empty `version_num`, or unrecognized single value | Do not auto-upgrade; investigate manually |

Classification uses local revision file graph when available; unrecognized ids that sort before head (e.g. fake `0000`) map to **`unknown`**.

---

## Safety / rollback notes

- **Read-only:** detection never writes schema or data.
- **Multiple `alembic_version` rows:** always **`unknown`** — Alembic expects a single row; duplicates imply manual intervention.
- **Missing table:** normal for existing SQLite installs pre-stamp; **`unstamped`** is expected, not an error.
- **Rollback:** this module does not perform rollbacks. If cutover mis-stamps, restore from backup and re-run detection; do not rely on detection to fix state.
- **Production today:** all live DBs are expected **`unstamped`** until P3.8+ explicitly stamps after backup.

---

## How future P3.8 cutover will use this

1. **Startup (read-only):** call `detect_schema_version()` after opening the DB session.
2. **Branching (later phase, not P3.7):**
   - `unstamped` → continue `migrate_schema()` (current behavior).
   - `at_head` → candidate to skip redundant DDL once equivalence is proven.
   - `behind_head` / `ahead_of_code` / `unknown` → log warning; block auto-upgrade until operator resolves.
3. **Stamping / upgrade:** separate, explicit operator-approved steps — **not** triggered by this module.

P3.7 only delivers the detector; it does **not** wire into `app.py`, FastAPI startup, or UI.

---

## How to run tests

```bash
pytest tests/test_p3_7_schema_version_detection.py
pytest
```

Tests use in-memory SQLite only; production `erp_data.db` is not required.

---

*Read-only detection only — no upgrade, no stamp, `migrate_schema()` still authoritative.*
