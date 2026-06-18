# DUAL-RUNTIME-01 — Operating Model

**Status:** ✅ **Active operating model** (documentation only)  
**Date:** 2026-06-19  
**Tag:** `dual-runtime-01-operating-model`  
**Authority:** Post BACKUP-01 · post OPERATOR-ROLLOUT OR-01–OR11 · Streamlit-primary launch

---

## 1. Summary

This project runs **two UI runtimes in parallel** with **one accounting truth** on local SQLite. PostgreSQL is for **staging and automated validation only** until a deliberate cloud/server deployment is chosen.

| Runtime | Database | Role |
|---------|----------|------|
| **Streamlit** | SQLite (`erp_data.db`) | **Primary** — real daily bookkeeping |
| **FastAPI + React** | Same SQLite or a **backup copy** | **Parallel validation** — read/compare when needed |
| **PostgreSQL** | Disposable test DB (`erp_pytest`) | **Staging / pytest matrix only** — not production |

**Not in scope today:** production PostgreSQL cutover · production React write flags · copying staging env templates to production without sign-off.

---

## 2. Operating rules (locked)

1. **Streamlit + SQLite** is the system of record for day-to-day operations.
2. **FastAPI + React** may run alongside for read-only validation or controlled staging smoke — never as the default operator path until explicitly approved.
3. **PostgreSQL** is used only for boundary-matrix and migration-readiness tests on a **disposable** database — never for live books.
4. **Production PostgreSQL** becomes appropriate only when cloud/server deployment is chosen and operator cutover runbooks are approved (see §7).
5. **Backup before parallel use** — copy `erp_data.db` before pointing FastAPI/React or experiments at live data (see §6).

---

## 3. How to run Streamlit (primary)

From repo root:

```bash
pip install -r requirements.txt
streamlit run app.py
```

- Default URL: `http://localhost:8501`
- Database: `erp_data.db` at repo root (via `paths.get_database_url()` unless `DATABASE_URL` is set)
- This is the **only** path for recording real transactions in the current operating model.

**Docker (optional local dev):** see [ROADMAP.md § Docker Setup](../ROADMAP.md#docker-setup-development) — mounts the same `erp_data.db` volume; still Streamlit-primary.

---

## 4. How to run FastAPI + React (read-only validation)

Use this when you want to **compare** React read pages or API responses against books — not to replace Streamlit for daily entry.

### 4.1 Recommended: validate against a backup copy

```bash
# 1. Backup live DB first (see §6)
TS=$(date +%Y%m%d_%H%M%S)
cp erp_data.db "backups/erp_data_validation_${TS}.db"

# 2. Point API at the copy (optional but safer than live file)
export DATABASE_URL="sqlite:///$(pwd)/backups/erp_data_validation_${TS}.db"

# 3. Read-only flags only — NO write flags, NO COMMIT_MODE_*, NO ERP_API_WRITE_*
export VITE_ERP_REACT_PAGES=1
# Do NOT set VITE_ERP_REACT_WRITE_* or ERP_API_WRITE_*

# 4. Start API + frontend (separate terminals)
uvicorn api.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
cd frontend && npm run dev
```

- Frontend default: `http://localhost:5173`
- API default: `http://127.0.0.1:8000`
- Requires valid JWT + `X-Company-Id` for authenticated routes (same as staging smoke docs).

### 4.2 What “read-only” means here

| Setting | Read-only validation | Staging write smoke (OR-03+) |
|---------|---------------------|------------------------------|
| `VITE_ERP_REACT_PAGES` | `1` | `1` |
| `VITE_ERP_REACT_WRITE_*` | **unset** | per staging template |
| `ERP_API_WRITE_*` | **unset** | per `config/staging/api.env.example` |
| `COMMIT_MODE_*` | **unset** | staging uvicorn only |

**Production:** React write flags remain **off** until operator sign-off. Staging templates live under `config/staging/` — do not copy to production.

Reference: [OPERATOR_ROLLOUT_OR01_REACT_READ_STAGING.md](./OPERATOR_ROLLOUT_OR01_REACT_READ_STAGING.md)

---

## 5. Critical warnings

### 5.1 Do not run pytest against the production database

The full suite (`pytest tests/`) assumes **isolated** fixtures and disposable databases. Never:

- Set `DATABASE_URL` to your live `erp_data.db` before running tests
- Run migration/cutover tests against production SQLite
- Export `COMMIT_MODE_*=boundary` during a full `pytest tests/` run (breaks default-internal characterization tests)

Run tests from repo root with production env vars **unset**:

```bash
unset DATABASE_URL COMMIT_MODE_* ERP_TEST_POSTGRES_URL
pytest tests/ -q
```

### 5.2 Do not point `ERP_TEST_POSTGRES_URL` at production

PostgreSQL tests use a **disposable** database only:

```bash
# config/staging/postgres.env.example — safe pattern
ERP_TEST_POSTGRES_URL=postgresql+psycopg://postgres@localhost/erp_pytest
```

**Never** use production hostnames, managed-cloud instances, or shared staging databases that hold real books. See [config/staging/README.md](../config/staging/README.md).

### 5.3 Do not enable React write in production

`VITE_ERP_REACT_WRITE_*` and `ERP_API_WRITE_*` are staging/operator-cutover gates. Daily production use stays on Streamlit until a signed rollout slice says otherwise.

---

## 6. Backup-before-use rule

Before any session that might touch live data through FastAPI, experiments, or manual DB work:

1. Stop Streamlit (and any uvicorn using the same file) if overwriting `erp_data.db`.
2. Copy the live database:

```bash
TS=$(date +%Y%m%d_%H%M%S)
cp erp_data.db "backups/erp_data_pre_validation_${TS}.db"
ls -la "backups/erp_data_pre_validation_${TS}.db"
```

3. Verify backup size matches source (byte count should match).

Pre-observations checkpoint: [BACKUP_01_PRE_OBSERVATIONS.md](./BACKUP_01_PRE_OBSERVATIONS.md) · tag `backup-01-pre-observations`.

---

## 7. When PostgreSQL production becomes appropriate

PostgreSQL as the **runtime** database for live bookkeeping is **deferred**. Consider it only when **all** of the following are true:

| Gate | Rationale |
|------|-----------|
| **Cloud or server deployment chosen** | Local SQLite remains correct for single-machine daily use |
| **Operator sign-off** | Human approval after staging OR-01–OR11 and PH-05 checklists |
| **Dedicated PG instance** | Not the disposable `erp_pytest` test DB |
| **Backup + rollback runbook** | P3.8-style backup before Alembic/cutover; tested restore |
| **MD-04c / money cutover plan** | Numeric migration validated on staging PG first |
| **Dual-run parity green** | SQLite ↔ PG characterization tests pass on staging |

Until then, PostgreSQL stays in the **staging/test validation** lane only (`ERP_TEST_POSTGRES_URL`, optional_postgres markers).

---

## 8. Quick reference

| Task | Command / location |
|------|-------------------|
| Daily bookkeeping | `streamlit run app.py` → `erp_data.db` |
| React read validation | `VITE_ERP_REACT_PAGES=1` + uvicorn + `npm run dev` |
| PG boundary tests | `config/staging/postgres.env.example` + `-m optional_postgres` |
| Staging write smoke | `config/staging/*.env.example` — **staging only** |
| Full test gate | `pytest tests/ -q` (no production env) |
| Roadmap | [ROADMAP.md § DUAL-RUNTIME-01](../ROADMAP.md#dual-runtime-01--operating-model) |

---

## 9. Scope compliance (this slice)

- Documentation only — no code, schema, env, or production changes
- No production PostgreSQL cutover
- No React write production enablement
