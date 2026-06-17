# FASTAPI-REACT-22 — Bank / Worker / Partner Write Pickers

**Mode:** Write-tab picker UX with thin P1 list API extraction. No write API changes.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-22** from [FASTAPI_REACT_21 audit §8](./FASTAPI_REACT_21_REACT_READ_PICKERS_AUDIT.md).  
**Tag:** `fastapi-react-22-react-write-pickers`

**Prerequisites:** [FASTAPI-REACT-08](./FASTAPI_REACT_08_REACT_WRITE_AUDIT.md) · FR-21 read pickers

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Bank account picker on write tabs | ✅ `/api/v1/bank-accounts` |
| Worker picker on worker write tab | ✅ `/api/v1/workers` |
| Partner picker on partner write tab | ✅ reuses `/api/v1/partners` |
| Shared components | ✅ `BankAccountPicker`, `WorkerPicker`, `PartnerPicker` |
| Write feature flags | ✅ unchanged cumulative `VITE_ERP_REACT_WRITE_*` |

**Accounting / GL behavior:** **UNCHANGED** — list reads only; write POST bodies unchanged.

---

## 2. Picker inventory

| Write tab | Field | Component | List API |
|-----------|-------|-----------|----------|
| Sale (Card) | Card bank account | `BankAccountPicker` (`excludeCreditCard`) | `/api/v1/bank-accounts` |
| Expense (Bank) | Bank account | `BankAccountPicker` | `/api/v1/bank-accounts` |
| Purchase (Bank) | Bank account | `BankAccountPicker` | `/api/v1/bank-accounts` |
| Receivable (Bank) | Bank account | `BankAccountPicker` | `/api/v1/bank-accounts` |
| Banking | Source / destination | `BankAccountPicker` | `/api/v1/bank-accounts` |
| Partner | Partner | `PartnerPicker` | `/api/v1/partners` |
| Partner | Bank account | `BankAccountPicker` | `/api/v1/bank-accounts` |
| Worker | Worker | `WorkerPicker` | `/api/v1/workers` |
| Worker | Bank account | `BankAccountPicker` | `/api/v1/bank-accounts` |

---

## 3. P1 read API additions (thin extraction)

| Path | Service |
|------|---------|
| `/api/v1/bank-accounts` | `read_bank_accounts.compute_bank_accounts_list` |
| `/api/v1/workers` | `read_workers.compute_workers_list` |

Frozen in `registry/api_read_contract.py`. Partner list unchanged from FR-21.

---

## 4. Feature flags (unchanged)

Write tabs remain behind cumulative `VITE_ERP_REACT_WRITE_*` + matching `ERP_API_WRITE_*` server flags. Pickers use the same read session as existing write forms (`ReadApiSetup` + `getReadSession`).

---

## 5. Client validation

| Case | Message |
|------|---------|
| Card sale without bank account | `No bank account selected.` |
| Bank payment tabs without account | `No bank account selected.` |
| Partner tab without partner | `Select a partner.` |
| Worker tab without worker | `Select a worker.` |

---

## 6. What must NOT change (verified)

- Streamlit primary UI
- No GL / posting kernel edits
- `apiGet` only in pickers; `apiPost` only in `writeClient.ts`
- Docker untouched
- Reconcile/closing tabs still use numeric ids (deferred)

---

## 7. Deferred (out of FR-22 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-23** | Full match-type payload forms |
| **statement row picker** | Reconcile tab |
| **fiscal period picker** | Closing tab |
| **receivable sale picker** | Credit sale id still numeric |
| **production COMMIT_MODE_* flip** | Separate ops slice |

---

## 8. Test plan

```bash
pytest tests/test_fastapi_react_22_react_write_pickers.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 9. Recommendation / next slice

**FASTAPI-REACT-23** — full match-type payload forms, statement row picker, fiscal period picker.
