# FASTAPI-REACT-01 — Posting Boundary Hardening (PS-P7)

**Mode:** Boundary hardening only. **No accounting behavior change.**

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-01** from [FASTAPI_REACT_00_AUDIT](./FASTAPI_REACT_00_AUDIT.md).  
**Tag:** `fastapi-react-01-posting-boundary-hardening`

---

## 1. Executive summary

| Item | Status |
|------|--------|
| GL kernels | ✅ `services/posting.py` — unchanged math/commit semantics |
| Boundary scopes | ✅ Extracted to `services/posting_boundary.py` |
| Streamlit | Caller only — shims delegate + audit + ambient `company_id` |
| DTO readiness | 🟡 Additive wrappers (`PostingResult`, `create_journal_entry_result`) — legacy ORM returns preserved |
| API routes | ⬜ Not expanded (out of scope) |
| React | ⬜ Not started (out of scope) |

**Posting behavior:** **UNCHANGED** — journal pairs, balances, void cascades, reconciliation orchestration, and default `internal` commit mode are identical.

---

## 2. Characterization — posting ownership map

| Layer | Owner | Responsibility |
|-------|-------|----------------|
| **`services/posting.py`** | GL kernel | `create_journal_entry`, post/void families, DTO builders |
| **`services/posting_boundary.py`** | Unit-of-work boundary | `posting_boundary_scope`, `recon_boundary_scope`, `void_boundary_scope` |
| **`services/commit_modes.py`** | Commit policy | Per-family `internal` / `boundary` (default **internal**) |
| **`services/unit_of_work.py`** | Transaction shell | `boundary_commit_scope`, `boundary_depth` |
| **`services/audit.py`** | Audit persistence | `log_audit` (flush-only under boundary mode) |
| **`app.py` shims** | Streamlit adapter | Delegate to service; resolve ambient `company_id`; wrap audit; apply boundary scopes |
| **`reconciliation/match_post.py`** | Orchestration | Statement row + bank txn + JE; lazy `import app` (deferred) |

### 2.1 `app.py` shim inventory (delegates to `posting_service.*`)

**Period guard / core JE**

- `_entry_date_posting_blocked` → `entry_date_posting_blocked`
- `create_journal_entry` → `create_journal_entry` (+ `resolve_company_id_for_posting`)
- `create_reversing_journal_entry`, `reverse_journal_entries_for`

**Sales / AR**

- `post_cash_sale`, `post_card_sale`, `post_credit_sale`, `post_receivable_payment`
- `compute_sale_balance_status`, `resolve_payment_credit_account`, `card_settlement_on`
- `void_sale`

**Purchases / AP**

- `post_purchase`, `post_payable_creation`, `post_payable_payment`
- `resolve_purchase_debit_account`, `purchase_ref_type`, `linked_purchase_payable`
- `void_purchase`, `void_purchase_linked_payable`, `void_payable`

**Expenses / payroll**

- `post_expense`, `post_salary`, `void_expense`

**Banking**

- `post_bank_transaction`, `post_bank_transfer`, `void_bank_transaction`
- `sync_company_cc_subledger`

**Equity**

- `post_capital_contribution`, `post_owner_drawing`, `void_equity_movement`

**Partner / worker / allocation / close**

- `post_partner_movement`, `void_partner_movement`
- `post_worker_movement`, `void_worker_movement`
- `_validate_partner_shares`, `_get_period_net_income_from_je`
- `allocate_profit_to_partners`, `void_profit_allocation`, `_allocate_all_pending`
- `close_fiscal_period`, `perform_year_end_close`, `void_year_end_close`
- `_get_year_bounds`, `_check_period_continuity`

**Reconciliation / inventory**

- `void_reconciliation`, `void_eod_close`, `void_inventory_transaction`
- `get_account_by_name`

**Boundary-wrapped post families** (via `posting_boundary_scope`)

- `post_cash_sale`, `post_expense`, `post_purchase`, `post_payable_payment`
- `post_receivable_payment`, `post_capital_contribution`, `post_owner_drawing`
- `post_partner_movement`, `post_worker_movement`
- `allocate_profit_to_partners`, `perform_year_end_close`, `close_fiscal_period`

**Boundary-wrapped void / recon** (via `void_boundary_scope` / `recon_boundary_scope`)

- All `void_*` shims with audit
- Reconciliation UI match/post paths (`recon_boundary_scope`)

### 2.2 Remaining in `app.py` (not posting kernels — do not extract here)

| Symbol | Notes |
|--------|-------|
| `log_audit` | Delegates to `services/audit.py` |
| `calculate_account_balance*` / `sync_account_balances` | Read/cache helpers (TD-PS-06) |
| `_stamp_company_id_on_new_objects` | Streamlit `before_flush` hook |
| Direct `boundary_commit_scope` in UI save handlers | Intentional outer transaction shells |

---

## 3. API-ready inputs/outputs

### 3.1 Ready today

| Surface | Input | Output | JSON |
|---------|-------|--------|------|
| `PostingResult` | persisted JE | frozen dataclass | `to_dict()` |
| `VoidResult`, `PaymentResult`, `AllocationResult`, … | post/void ops | frozen dataclass | `to_dict()` |
| `create_journal_entry_result` | same as `create_journal_entry` | `PostingResult` | additive only |
| `resolve_company_id_for_posting` | explicit + ambient | `int \| None` | explicit for API handlers |
| Post/void kernels | `session` + explicit `company_id` | ORM / bool / tuple | FastAPI P2 already wraps |

### 3.2 Documented gaps (deferred — not fixed in FASTAPI-REACT-01)

| ID | Gap | Impact |
|----|-----|--------|
| **TD-PS-01** | Default `internal` commits inside kernels | API must hoist to boundary mode per request |
| **TD-PS-03** | Legacy shims still return ORM objects | React needs DTO adapters at route layer |
| **TD-PS-06** | Read helpers (`calculate_account_balance*`) still in `app.py` | API should use `services/read_balances` |
| **TD-PS-07** | Ambient `_current_company_id()` in Streamlit shims | API must pass explicit `company_id` always |
| **TD-PS-04** | Kernel rollback discards pending work on guard failure | Reconciliation edge case |
| **TD-POSTING-06** | `reconciliation/match_post.py` lazy `import app` | Service boundary incomplete |
| **PS-P6-5** | Reconciliation JE company stamp vs explicit row stamp | Multi-tenant correctness review |

---

## 4. Changes in this slice

1. **`services/posting_boundary.py`** — centralizes boundary scope helpers (moved from `app.py`).
2. **`services/posting.py`** — additive `resolve_company_id_for_posting`, `create_journal_entry_result` (no kernel edits).
3. **`app.py`** — shims use `posting_boundary_scope` / `recon_boundary_scope` / `void_boundary_scope`; removed duplicate `_recon_boundary_scope` / `_void_boundary_scope`.
4. **Tests** — `tests/test_fastapi_react_01_posting_boundary.py` locks contracts.
5. **ROADMAP / POSTING_SERVICE_01_STATUS** — PS-P7 boundary slice marked complete; debt items remain documented.

---

## 5. What must NOT change (verified)

- Journal debit/credit math and balance rules
- Void reversal pairing and cascade order
- Reconciliation match/post orchestration logic
- Default commit mode (`internal`)
- Existing characterization tests (`test_posting_service01_*`, `test_fastapi_p0_*`)

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_01_posting_boundary.py \
  tests/test_posting_service01_*.py \
  tests/test_fastapi_p0_*.py -q

pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-02** (or parallel **P2-HARDEN-01**) — explicit `company_id` on all API write paths and boundary commit mode flip behind integration tests. **Defer React** until write boundary parity is proven on PostgreSQL test runtime.
