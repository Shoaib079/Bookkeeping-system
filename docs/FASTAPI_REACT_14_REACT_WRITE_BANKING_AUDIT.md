# FASTAPI-REACT-14 — Bank Transaction Write Tab (New Transaction)

**Mode:** Banking tab on existing write page. No accounting logic in React.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-14** from [FASTAPI_REACT_13 audit §8](./FASTAPI_REACT_13_REACT_WRITE_RECEIVABLE_PAYMENT_AUDIT.md).  
**Tag:** `fastapi-react-14-react-write-banking`

**Prerequisites:** [FASTAPI-REACT-08](./FASTAPI_REACT_08_REACT_WRITE_AUDIT.md) · P2.7 bank transaction write API

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Banking tab on `/transactions/new` | ✅ |
| Write API | ✅ `POST /api/v1/bank-transactions` (existing P2.7) |
| Client write gate | ✅ `VITE_ERP_REACT_WRITE_BANKING=1` |
| Server write gate | ✅ `ERP_API_WRITE_BANKING=1` |
| Transaction types | ✅ deposit · withdrawal · transfer |
| `bank_account_id` | ✅ numeric dev field |
| Transfer `destination_bank_account_id` | ✅ required when type is transfer |
| Partner/worker movement write | ⬜ **Deferred** — FR-15 |

**Accounting / GL behavior:** **UNCHANGED** — manual bank tx → sub-ledger + GL via existing API.

---

## 2. Form inventory

| Field | Notes |
|-------|-------|
| `transaction_type` | deposit, withdrawal, or transfer |
| `date` / `amount` / `notes` | Shared write-page fields |
| `bank_account_id` | Required source account id |
| `destination_bank_account_id` | Required for transfer (must differ) |
| `currency` | Optional override |

Contract: `registry/react_write_contract.py` → `ALLOWED_BANK_TRANSACTION_TYPES`.

---

## 3. Feature flags

| Env | Effect |
|-----|--------|
| `VITE_ERP_REACT_PAGES` | Shell |
| `VITE_ERP_REACT_WRITE_BANKING` | Banking tab |
| `ERP_API_WRITE_BANKING` | 404 when off |

`reactWriteEnabled()` includes banking flag (sales **or** expenses **or** voids **or** purchases **or** receivable payments **or** banking).

---

## 4. Client validation (UX only)

| Rule | Mirrors P2 |
|------|------------|
| `bank_account_id` required | `BANK_NOT_FOUND_MSG` path |
| Transfer requires distinct `destination_bank_account_id` | `DEST_ACCOUNT_MSG` |

API remains authoritative (CC deposit guard, statement-linked rows, etc.).

---

## 5. What must NOT change (verified)

- Streamlit primary UI
- No new FastAPI routes
- No GL / posting kernel edits in React
- Other write tabs unchanged
- `apiPost` only in `writeClient.ts`

---

## 6. Deferred (out of FR-14 scope)

| Item | Notes |
|------|-------|
| **partner movement write** | P2 partner API — FR-15 |
| **worker payment write** | P2 worker API — FR-15 |
| **bank account picker** | No bank list read API in P1 |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 7. Test plan

```bash
pytest tests/test_fastapi_react_14_react_write_banking.py -q
pytest tests/ -q
```

**Dev smoke:**
```bash
ERP_API_WRITE_BANKING=1 uvicorn api.main:create_app --factory --reload
cd frontend && VITE_ERP_REACT_PAGES=1 VITE_ERP_REACT_WRITE_BANKING=1 npm run dev
```

---

## 8. Recommendation / next slice

**FASTAPI-REACT-15** — partner/worker movement write tabs on `/transactions/new`.
