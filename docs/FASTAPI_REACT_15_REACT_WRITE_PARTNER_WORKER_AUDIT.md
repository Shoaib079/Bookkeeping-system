# FASTAPI-REACT-15 — Partner/Worker Movement Write Tabs (New Transaction)

**Mode:** Partner + Worker tabs on existing write page. No accounting logic in React.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-15** from [FASTAPI_REACT_14 audit §8](./FASTAPI_REACT_14_REACT_WRITE_BANKING_AUDIT.md).  
**Tag:** `fastapi-react-15-react-write-partner-worker`

**Prerequisites:** [FASTAPI-REACT-08](./FASTAPI_REACT_08_REACT_WRITE_AUDIT.md) · P2.6 partner/worker write APIs

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Partner tab on `/transactions/new` | ✅ |
| Worker tab on `/transactions/new` | ✅ |
| Write APIs | ✅ `POST /api/v1/partner-movements` · `POST /api/v1/worker-payments` (P2.6) |
| Client write gate | ✅ `VITE_ERP_REACT_WRITE_PARTNER_WORKER=1` |
| Server write gate | ✅ `ERP_API_WRITE_PARTNER_WORKER=1` |
| Partner movement types | ✅ CapitalContribution · Drawing · Salary · Advance · Repayment · AdvanceOffset |
| Worker movement types | ✅ Salary · Advance · Repayment |
| Reconciliation/closing write | ⬜ **Deferred** — FR-16 |

**Accounting / GL behavior:** **UNCHANGED** — partner/worker posts via existing P2 kernels.

---

## 2. Form inventory

### Partner tab

| Field | Notes |
|-------|-------|
| `partner_id` | Required numeric id |
| `movement_type` | P2.6 supported types |
| `amount` | Required |
| `date` / `notes` | Shared write-page fields |
| `bank_account_id` | Required except `AdvanceOffset` |

### Worker tab

| Field | Notes |
|-------|-------|
| `worker_id` | Required numeric id |
| `movement_type` | Salary · Advance · Repayment |
| `date` / `notes` | Shared write-page fields |
| `bank_account_id` | Always required |
| `gross_salary` | Required for Salary |
| `amount` | Required for Advance/Repayment |
| `deductions` / `advance_recovery` / `pay_period` | Optional Salary fields |

Contract: `registry/react_write_contract.py` → `ALLOWED_*_MOVEMENT_TYPES`.

---

## 3. Feature flags

| Env | Effect |
|-----|--------|
| `VITE_ERP_REACT_PAGES` | Shell |
| `VITE_ERP_REACT_WRITE_PARTNER_WORKER` | Partner + Worker tabs |
| `ERP_API_WRITE_PARTNER_WORKER` | 404 when off |

`reactWriteEnabled()` includes partner/worker flag.

---

## 4. Client validation (UX only)

| Rule | Mirrors P2 |
|------|------------|
| Partner amount > 0 | `INVALID_AMOUNT_MSG` |
| Partner bank except AdvanceOffset | `BANK_NOT_FOUND_MSG` path |
| Worker bank always required | P2 worker schema |
| Salary requires `gross_salary` | P2 salary test |
| Advance/Repayment requires `amount` | P2 advance test |

API remains authoritative.

---

## 5. What must NOT change (verified)

- Streamlit primary UI
- No new FastAPI routes
- No GL / posting kernel edits in React
- Other write tabs unchanged
- `apiPost` only in `writeClient.ts`

---

## 6. Deferred (out of FR-15 scope)

| Item | Notes |
|------|-------|
| **reconciliation write** | P2 recon match/unmatch — FR-16 |
| **closing write** | P2 closing endpoints — FR-16 |
| **partner picker** | id text fields only |
| **worker picker** | id text fields only |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 7. Test plan

```bash
pytest tests/test_fastapi_react_15_react_write_partner_worker.py -q
pytest tests/ -q
```

**Dev smoke:**
```bash
ERP_API_WRITE_PARTNER_WORKER=1 uvicorn api.main:create_app --factory --reload
cd frontend && VITE_ERP_REACT_PAGES=1 VITE_ERP_REACT_WRITE_PARTNER_WORKER=1 npm run dev
```

---

## 8. Recommendation / next slice

**FASTAPI-REACT-16** — reconciliation/closing write UI on dedicated routes or extended write page.
