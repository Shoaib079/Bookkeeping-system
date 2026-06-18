# PRODUCTION-HARDENING-01-PH01 — Register Cleanup

**Mode:** Docs + contract cleanup only. **No accounting / GL / posting behavior change.**

**Date:** 2026-06-05  
**Authority:** Follows **FASTAPI-REACT-50** epic closure; folds post-FR-50 ops work into **PRODUCTION-HARDENING-01**.  
**Tag:** `production-hardening-01-ph01-register-cleanup`

**Prerequisites:** [FASTAPI-REACT-50](./FASTAPI_REACT_50_REACT_READ_RECIPE_COSTING_AUDIT.md) (42 real React read pages, 0 NAV placeholders)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| FASTAPI-REACT epic table — FR-13–16 rows | ✅ Added |
| FASTAPI-REACT-51+ superseded by PRODUCTION-HARDENING-01 | ✅ Documented |
| Stale `DEFERRED_ITEMS` in `react_pages_contract` | ✅ `FASTAPI-REACT-42` removed |
| Stale `DEFERRED_ITEMS` in `react_write_contract` | ✅ `FASTAPI-REACT-42` removed |
| Stale `DEFERRED_ITEMS` in `pg_boundary_contract` | ✅ `React write pages` removed (FR-08–24 shipped) |
| Status register — React migration | ✅ Updated (read complete, write partial) |
| Status register — FastAPI foundation | ✅ Nuanced (strong partial; Streamlit primary) |
| `production_hardening_contract.py` | ✅ New SSOT for PH epic |

**Accounting / GL behavior:** **UNCHANGED** — register hygiene only.

---

## 2. ROADMAP gaps closed

### Epic table (FASTAPI-REACT section)

Missing write slices restored between FR-12 and FR-17:

| Slice | Scope |
|-------|--------|
| **FASTAPI-REACT-13** | Receivable payment write tab |
| **FASTAPI-REACT-14** | Bank transaction write tab |
| **FASTAPI-REACT-15** | Partner + worker write tabs |
| **FASTAPI-REACT-16** | Reconciliation + closing write tabs |

### Epic succession

**FASTAPI-REACT-51+** (ops / production rollout) is superseded by **PRODUCTION-HARDENING-01** slices PH-02 through PH-05. FR-50 frozen deferred items (`FR50_DEFERRED_ITEMS`) are **not** mutated — audit regression tests depend on immutability.

### Status register

| Key | Before | After |
|-----|--------|-------|
| **React migration** | Not started | Read pages complete (42); write tabs partial (FR-08–24); Streamlit primary |
| **FastAPI foundation** | Partial (strong) | Partial (strong) — P0/P1/P2 + React read/write behind flags; not production API-primary |

---

## 3. Stale contract deferred cleanup

| Contract | Removed stale item | Rationale |
|----------|-------------------|-----------|
| `registry/react_pages_contract.py` → `DEFERRED_ITEMS` | `FASTAPI-REACT-42` | FR-42 complete |
| `registry/react_write_contract.py` → `DEFERRED_ITEMS` | `FASTAPI-REACT-42` | FR-42 complete |
| `registry/pg_boundary_contract.py` → `DEFERRED_ITEMS` | `React write pages` | FR-08–24 write tabs shipped |

Active global deferred now points at **PRODUCTION-HARDENING-02** and **production COMMIT_MODE_* flip**.

Historical FR-07 audit still documents `React write pages` as deferred at slice time — frozen audit; PH-01 only updates the live contract pointer.

---

## 4. PRODUCTION-HARDENING-01 epic plan

| Slice | Scope | Status |
|-------|--------|--------|
| **PRODUCTION-HARDENING-01-PH01** | ROADMAP + stale contract deferred cleanup | ✅ **Complete** |
| **PRODUCTION-HARDENING-01-PH02** | `bank_transaction` + `equity_movement` commit characterization beyond scaffold | 📋 Planned |
| **PRODUCTION-HARDENING-01-PH03** | PostgreSQL matrix execution audit + launch-readiness checklist | 📋 Planned |
| **PRODUCTION-HARDENING-01-PH04** | `COMMIT_MODE_*` operator rollout characterization (test/staging only) | 📋 Planned |
| **PRODUCTION-HARDENING-01-PH05** | Launch-readiness verification gate + epic closure | 📋 Planned |

**Hard rules (entire epic):** No accounting changes · no GL changes · no posting math changes · no React redesign · no new ERP features · Streamlit remains primary until operator cutover.

---

## 5. Deferred (out of PH-01 scope)

| Item | Notes |
|------|-------|
| **PRODUCTION-HARDENING-02** | Extend scaffold families `bank_transaction`, `equity_movement` |
| **PRODUCTION-HARDENING-03** | PG matrix with `ERP_TEST_POSTGRES_URL` + ops checklist |
| **PRODUCTION-HARDENING-04** | `COMMIT_MODE_*` flip characterization — no prod flip without operator |
| **PRODUCTION-HARDENING-05** | Epic closure gate |
| **production COMMIT_MODE_* flip** | Operator rollout after PH-02–04 green |

---

## 6. What must NOT change (verified)

- Default commit mode (`internal`)
- Journal math and GL pairs
- Streamlit primary UI
- Frozen `FRxx_DEFERRED_ITEMS` blocks in react contracts
- No new API routes
- No new React pages
- No Docker file edits

---

## 7. Test plan

```bash
pytest tests/test_production_hardening_01_ph01_register_cleanup.py -q
pytest tests/ -q
```

---

## 8. Recommendation / next slice

**PRODUCTION-HARDENING-01-PH02** — extend `bank_transaction` + `equity_movement` commit characterization beyond scaffold tests.
