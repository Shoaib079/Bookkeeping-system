# FASTAPI-REACT-13 — Receivable Payment Write Tab (New Transaction)

**Mode:** Receivable payment tab on existing write page. No accounting logic in React.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-13** from [FASTAPI_REACT_12 audit §8](./FASTAPI_REACT_12_REACT_WRITE_PURCHASE_AUDIT.md).  
**Tag:** `fastapi-react-13-react-write-receivable-payment`

**Prerequisites:** [FASTAPI-REACT-08](./FASTAPI_REACT_08_REACT_WRITE_AUDIT.md) · P2.4 receivable payment write API

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Receivable tab on `/transactions/new` | ✅ |
| Write API | ✅ `POST /api/v1/receivable-payments` (existing P2.4) |
| Client write gate | ✅ `VITE_ERP_REACT_WRITE_RECEIVABLE_PAYMENTS=1` |
| Server write gate | ✅ `ERP_API_WRITE_RECEIVABLE_PAYMENTS=1` |
| Payment methods | ✅ Cash · Bank |
| Credit sale target | ✅ `sale_id` numeric field (+ optional `customer_name`) |
| Bank `bank_account_id` | ✅ numeric dev field (Bank method) |
| Bank transaction write | ⬜ **Deferred** — FR-14 |

**Accounting / GL behavior:** **UNCHANGED** — receivable payment → GL via existing API.

---

## 2. Form inventory

| Field | Notes |
|-------|-------|
| `payment_method` | Cash or Bank |
| `date` / `amount` / `currency` / `notes` | Shared write-page fields |
| `sale_id` | Required — open credit sale id |
| `customer_name` | Optional cross-check against sale customer |
| `bank_account_id` | Required when `payment_method` is Bank |

Contract: `registry/react_write_contract.py` → `ALLOWED_RECEIVABLE_PAYMENT_METHODS`.

---

## 3. Feature flags

| Env | Effect |
|-----|--------|
| `VITE_ERP_REACT_PAGES` | Shell |
| `VITE_ERP_REACT_WRITE_RECEIVABLE_PAYMENTS` | Receivable tab |
| `ERP_API_WRITE_RECEIVABLE_PAYMENTS` | 404 when off |

`reactWriteEnabled()` includes receivable payments flag (sales **or** expenses **or** voids **or** purchases **or** receivable payments).

---

## 4. Client validation (UX only)

| Rule | Mirrors P2 |
|------|------------|
| `sale_id` required | `_resolve_credit_sale` |
| Bank requires `bank_account_id` | `BANK_NOT_SELECTED_MSG` |

API remains authoritative for business rules (overpay, non-credit sale, etc.).

---

## 5. What must NOT change (verified)

- Streamlit primary UI
- No new FastAPI routes
- No GL / posting kernel edits in React
- Sale/expense/void/purchase tabs unchanged
- `apiPost` only in `writeClient.ts`

---

## 6. Deferred (out of FR-13 scope)

| Item | Notes |
|------|-------|
| **bank transaction write** | P2 bank tx API — FR-14 |
| **receivable sale picker** | No open-AR list wired in React |
| **bank account picker** | No bank list read API in P1 |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 7. Test plan

```bash
pytest tests/test_fastapi_react_13_react_write_receivable_payment.py -q
pytest tests/ -q
```

**Dev smoke:**
```bash
ERP_API_WRITE_RECEIVABLE_PAYMENTS=1 uvicorn api.main:create_app --factory --reload
cd frontend && VITE_ERP_REACT_PAGES=1 VITE_ERP_REACT_WRITE_RECEIVABLE_PAYMENTS=1 npm run dev
```

---

## 8. Recommendation / next slice

**FASTAPI-REACT-14** — bank transaction write tab on `/transactions/new`.
