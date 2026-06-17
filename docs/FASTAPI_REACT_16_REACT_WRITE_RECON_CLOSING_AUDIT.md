# FASTAPI-REACT-16 — Reconciliation/Closing Write Tabs (New Transaction)

**Mode:** Reconcile + Closing tabs on existing write page. No accounting logic in React.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-16** from [FASTAPI_REACT_15 audit §8](./FASTAPI_REACT_15_REACT_WRITE_PARTNER_WORKER_AUDIT.md).  
**Tag:** `fastapi-react-16-react-write-recon-closing`

**Prerequisites:** [FASTAPI-REACT-08](./FASTAPI_REACT_08_REACT_WRITE_AUDIT.md) · P2.8 reconciliation · P2.9 closing write APIs

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Reconcile tab on `/transactions/new` | ✅ |
| Closing tab on `/transactions/new` | ✅ |
| Reconciliation APIs | ✅ `POST /api/v1/reconciliation/match` · `.../unmatch` |
| Match types | ✅ generic_deposit · bank_charge · deposit_clearing · vendor_outflow · partner · worker · equity · cc_bill_payment |
| Closing APIs | ✅ `POST /api/v1/periods/{id}/close` · `.../profit-allocations` · `.../void` |
| Client gates | ✅ `VITE_ERP_REACT_WRITE_RECONCILIATION` · `VITE_ERP_REACT_WRITE_CLOSING` |
| Server gates | ✅ `ERP_API_WRITE_RECONCILIATION` · `ERP_API_WRITE_CLOSING` |
| P2 write UI coverage | ✅ **Complete** (all transactional write families) |

**Accounting / GL behavior:** **UNCHANGED** — recon/closing via existing P2 kernels.

---

## 2. Form inventory

### Reconcile tab (Match | Unmatch)

| Action | Fields |
|--------|--------|
| **Match** | `statement_row_id`, `match_type`, optional `credit_account_name` (required for `generic_deposit`) |
| **Unmatch** | `statement_row_id`, `reason` |

### Closing tab (Close | Allocate | Void)

| Action | Fields |
|--------|--------|
| **Close period** | `period_id` (path) |
| **Profit allocation** | `period_id`, optional `notes` |
| **Void allocation** | `allocation_id` (path), `reason` |

Contract: `registry/react_write_contract.py` → `ALLOWED_RECONCILIATION_MATCH_TYPES`, `CLOSING_WRITE_ACTIONS`.

---

## 3. Feature flags

| Env | Effect |
|-----|--------|
| `VITE_ERP_REACT_WRITE_RECONCILIATION` | Reconcile tab |
| `VITE_ERP_REACT_WRITE_CLOSING` | Closing tab |
| `ERP_API_WRITE_RECONCILIATION` / `ERP_API_WRITE_CLOSING` | 404 when off |

`reactWriteEnabled()` includes reconciliation and closing flags.

---

## 4. Client validation (UX only)

| Rule | Mirrors P2 |
|------|------------|
| Unmatch/void reason required | `VOID_REASON_REQUIRED_MSG` |
| `generic_deposit` requires `credit_account_name` | P2 generic deposit test |

Complex match-type payloads (partner/worker/vendor fields) deferred — API authoritative.

---

## 5. What must NOT change (verified)

- Streamlit primary UI
- No new FastAPI routes
- No GL / posting kernel edits in React
- Other write tabs unchanged
- `apiPost` only in `writeClient.ts`

---

## 6. Deferred (out of FR-16 scope)

| Item | Notes |
|------|-------|
| **full match-type payload forms** | vendor/partner/worker recon fields |
| **statement row picker** | id text fields only |
| **fiscal period picker** | id text fields only |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 7. Test plan

```bash
pytest tests/test_fastapi_react_16_react_write_recon_closing.py -q
pytest tests/ -q
```

**Dev smoke:**
```bash
ERP_API_WRITE_RECONCILIATION=1 ERP_API_WRITE_CLOSING=1 uvicorn api.main:create_app --factory --reload
cd frontend && VITE_ERP_REACT_PAGES=1 VITE_ERP_REACT_WRITE_RECONCILIATION=1 VITE_ERP_REACT_WRITE_CLOSING=1 npm run dev
```

---

## 8. Recommendation / next slice

**FASTAPI-REACT-17** — expand read pages, match-type payload forms, or production rollout helpers.
