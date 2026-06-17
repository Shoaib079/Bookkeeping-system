# FASTAPI-REACT-11 — Void Write Tab (New Transaction)

**Mode:** Void tab on existing write page. No accounting logic in React.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-11** from [FASTAPI_REACT_10 audit §8](./FASTAPI_REACT_10_REACT_WRITE_PAYMENT_METHODS_AUDIT.md).  
**Tag:** `fastapi-react-11-react-write-void`

**Prerequisites:** [FASTAPI-REACT-08](./FASTAPI_REACT_08_REACT_WRITE_AUDIT.md) · P2.5 void write API · FR-07 void boundary matrix

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Void tab on `/transactions/new` | ✅ |
| Write API | ✅ `POST /api/v1/voids` (existing P2.5) |
| Client write gate | ✅ `VITE_ERP_REACT_WRITE_VOIDS=1` |
| Server write gate | ✅ `ERP_API_WRITE_VOIDS=1` |
| Supported targets | ✅ Sale · ExpenseRecord · Purchase · Payable · BankTransaction |
| Purchase write tab | ⬜ **Deferred** — FR-12 |

**Accounting / GL behavior:** **UNCHANGED** — void → reverse → audit via existing API.

---

## 2. Form inventory

| Field | Notes |
|-------|-------|
| `target_type` | Select from P2.5 supported types |
| `target_id` | Numeric record id |
| `reason` | Required non-blank (pinned P2 string) |

Contract: `registry/react_write_contract.py` → `VOID_TARGET_TYPES`.

---

## 3. Feature flags

| Env | Effect |
|-----|--------|
| `VITE_ERP_REACT_PAGES` | Shell |
| `VITE_ERP_REACT_WRITE_VOIDS` | Void tab |
| `ERP_API_WRITE_VOIDS` | 404 when off |

`reactWriteEnabled()` includes voids flag (sales **or** expenses **or** voids).

---

## 4. What must NOT change (verified)

- Streamlit primary UI
- No new FastAPI routes
- No GL / posting kernel edits in React
- Sale/expense tabs unchanged
- `apiPost` only in `writeClient.ts`

---

## 5. Deferred (out of FR-11 scope)

| Item | Notes |
|------|-------|
| **purchase write page** | P2.3 — FR-12 |
| **receivable payment write** | P2.4 |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_11_react_write_void.py -q
pytest tests/ -q
```

**Dev smoke:**
```bash
ERP_API_WRITE_VOIDS=1 uvicorn api.main:create_app --factory --reload
cd frontend && VITE_ERP_REACT_PAGES=1 VITE_ERP_REACT_WRITE_VOIDS=1 npm run dev
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-12** — purchase write tab on `/transactions/new`.
