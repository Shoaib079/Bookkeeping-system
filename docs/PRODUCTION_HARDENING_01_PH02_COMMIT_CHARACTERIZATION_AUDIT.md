# PRODUCTION-HARDENING-01-PH02 — Commit Characterization Extension

**Mode:** Test + contract updates only. **No accounting / GL / posting behavior change.**

**Date:** 2026-06-05  
**Authority:** Implements slice **PRODUCTION-HARDENING-01-PH02** from [PH-01 audit §4](./PRODUCTION_HARDENING_01_PH01_REGISTER_CLEANUP_AUDIT.md).  
**Tag:** `production-hardening-01-ph02-commit-characterization`

**Prerequisites:** [PH-01](./PRODUCTION_HARDENING_01_PH01_REGISTER_CLEANUP_AUDIT.md) · [FASTAPI-REACT-04](./FASTAPI_REACT_04_READ_API_BOUNDARY_AUDIT.md) · [FASTAPI-REACT-14](./FASTAPI_REACT_14_REACT_WRITE_BANKING_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| `bank_transaction` P0 dual-run characterization | ✅ `test_fastapi_p0_commit_ownership_banking.py` |
| `post_equity_movement` P0 dual-run characterization | ✅ `test_fastapi_p0_commit_ownership_movements.py` (existing equity_contribution) |
| `commit_boundary_contract.py` mapping updated | ✅ Both families off scaffold |
| `BANKING_TABLES` snapshot helper | ✅ `tests/helpers/commit_parity.py` |

**Posting / GL behavior:** **UNCHANGED** — default `internal`; characterization only.

---

## 2. Families extended

| Family | Write path | Characterization test | Flows pinned |
|--------|------------|----------------------|--------------|
| **`bank_transaction`** | `services/write_banking.create_manual_bank_transaction` | `tests/test_fastapi_p0_commit_ownership_banking.py` | deposit · withdrawal · closed-period rollback · audit atomic |
| **`post_equity_movement`** | `posting.post_capital_contribution` + app audit | `tests/test_fastapi_p0_commit_ownership_movements.py` | equity_contribution internal vs boundary (pre-existing) |

Previously both families pointed at `tests/test_fastapi_p0_commit_ownership_scaffold.py` (harness-only, not family-specific).

---

## 3. Contract updates

`registry/commit_boundary_contract.py`:

| Family | Before | After |
|--------|--------|-------|
| `bank_transaction` | scaffold | `test_fastapi_p0_commit_ownership_banking.py` |
| `post_equity_movement` | scaffold | `test_fastapi_p0_commit_ownership_movements.py` |

Scaffold test remains for harness + default-mode pins (`test_fastapi_p0_commit_ownership_scaffold.py`).

---

## 4. Deferred (out of PH-02 scope)

| Item | Notes |
|------|-------|
| **PRODUCTION-HARDENING-03** | PostgreSQL matrix execution + launch checklist |
| **PRODUCTION-HARDENING-04** | `COMMIT_MODE_*` operator rollout characterization |
| **PRODUCTION-HARDENING-05** | Epic closure gate |
| **bank_transaction PG matrix** | Optional PG parity when `ERP_TEST_POSTGRES_URL` set |
| **equity_movement PG matrix** | Optional PG parity when `ERP_TEST_POSTGRES_URL` set |
| **production COMMIT_MODE_* flip** | Operator rollout after PH-03–04 green |

---

## 5. What must NOT change (verified)

- Default commit mode (`internal`)
- Journal math and GL pairs
- Streamlit primary UI
- No new API routes
- No new React pages
- No Docker file edits

---

## 6. Test plan

```bash
pytest tests/test_fastapi_p0_commit_ownership_banking.py \
  tests/test_fastapi_p0_commit_ownership_movements.py -q
pytest tests/test_production_hardening_01_ph02_commit_characterization.py -q
pytest tests/test_fastapi_react_04_read_api_boundary.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**PRODUCTION-HARDENING-01-PH03** — PostgreSQL matrix execution audit + launch-readiness checklist.
