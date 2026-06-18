# PRODUCTION-HARDENING-01-PH05 — Launch-Readiness Verification Gate + Epic Closure

**Mode:** Verification gate + epic closure. **No accounting / GL / posting behavior change.**

**Date:** 2026-06-05  
**Authority:** Closes **PRODUCTION-HARDENING-01** after [PH-04](./PRODUCTION_HARDENING_01_PH04_COMMIT_MODE_ROLLOUT_AUDIT.md).  
**Tag:** `production-hardening-01-ph05-launch-readiness`

**Prerequisites:** PH-01 through PH-04 complete

---

## 1. Executive summary

| Item | Status |
|------|--------|
| PH-01 register cleanup | ✅ Complete |
| PH-02 commit characterization | ✅ Complete |
| PH-03 PG matrix + launch checklist | ✅ Complete |
| PH-04 COMMIT_MODE operator rollout | ✅ Complete |
| PH-05 verification gate | ✅ **This slice** |
| **PRODUCTION-HARDENING-01 epic** | ✅ **Complete** |

**Posting / GL behavior:** **UNCHANGED** — verification and documentation only.

---

## 2. Epic slice inventory

| Slice | Tag | Gate test |
|-------|-----|-----------|
| PH-01 | `production-hardening-01-ph01-register-cleanup` | `test_production_hardening_01_ph01_register_cleanup.py` |
| PH-02 | `production-hardening-01-ph02-commit-characterization` | `test_production_hardening_01_ph02_commit_characterization.py` |
| PH-03 | `production-hardening-01-ph03-pg-matrix-execution` | `test_production_hardening_01_ph03_pg_matrix_execution.py` |
| PH-04 | `production-hardening-01-ph04-commit-mode-rollout` | `test_production_hardening_01_ph04_commit_mode_rollout.py` |
| PH-05 | `production-hardening-01-ph05-launch-readiness` | `test_production_hardening_01_ph05_launch_readiness.py` |

Machine-readable: `registry/launch_readiness_gate_contract.py`.

---

## 3. Launch-readiness verdict

### Streamlit-primary launch

| Gate | Verdict |
|------|---------|
| Core ERP + accounting | ✅ Ready |
| Full SQLite pytest suite | ✅ Required gate |
| **Launch blockers** | **0 launch blockers** |

Streamlit-only production requires no further PRODUCTION-HARDENING work.

### FastAPI/React API-write production path

| Gate | Verdict |
|------|---------|
| Engineering characterization (PH-01–04) | ✅ Complete |
| Default `internal` commit mode in CI | ✅ Verified |
| **Remaining work** | **operator deferrals only** |

Operator actions before API-primary cutover (not code blockers):

- Per-route `ERP_API_WRITE_*` flags
- `VITE_ERP_REACT_PAGES=1`
- `COMMIT_MODE_*=boundary` production flip (with operator sign-off)
- `ERP_TEST_POSTGRES_URL` PG matrix green on staging

---

## 4. Intentional post-epic deferrals

| Item | Notes |
|------|-------|
| **TD-PS-03** | Route-layer DTO adapters — not a Streamlit launch blocker |
| **CI optional_postgres job** | Requires managed test DB in CI |
| **production operator sign-off** | Human gate before prod `COMMIT_MODE_*` flip |

These are **not** PRODUCTION-HARDENING epic blockers.

---

## 5. Verification gate

Run before any API-write production cutover:

```bash
pytest tests/test_production_hardening_01_ph01_register_cleanup.py \
  tests/test_production_hardening_01_ph02_commit_characterization.py \
  tests/test_production_hardening_01_ph03_pg_matrix_execution.py \
  tests/test_production_hardening_01_ph04_commit_mode_rollout.py \
  tests/test_production_hardening_01_ph05_launch_readiness.py -q

pytest tests/ -q

# Optional staging PG matrix:
export ERP_TEST_POSTGRES_URL='postgresql+psycopg://localhost/erp_pytest'
pytest tests/test_fastapi_react_07_pg_boundary_matrix.py \
  tests/test_production_hardening_01_ph03_pg_matrix_execution.py \
  -m optional_postgres -q
```

---

## 6. What must NOT change (verified)

- Default commit mode (`internal`) in code and CI
- Journal math and GL pairs
- Streamlit primary UI
- No production deployment env edits from this epic
- Frozen `FRxx_DEFERRED_ITEMS` blocks unchanged

---

## 7. Test plan

```bash
pytest tests/test_production_hardening_01_ph05_launch_readiness.py -q
pytest tests/ -q
```

---

## 8. Epic closure

**PRODUCTION-HARDENING-01** is **complete**. Post-FR-50 production hardening is closed.

No further PH slices planned. Operator rollout and API-write cutover proceed under runbooks from PH-03 and PH-04 when explicitly approved.
