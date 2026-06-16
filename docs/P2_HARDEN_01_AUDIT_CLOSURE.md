# P2-HARDEN-01 — Company Stamp Audit Closure

**Status:** ✅ **Closed by verification** (2026-06-16)  
**Tag:** `p2-harden-01-company-stamp-audit`  
**Baseline:** full suite green at closure (see `tests/test_roadmap_sync_01.py`)

## Verdict

**No runtime changes required.** FastAPI P2 write paths use **explicit service-layer `company_id` stamping**. The H-01 matrix and H-02 fixture fidelity tests enforce this without Streamlit `before_flush` hooks. **Silent auto-stamp hooks are rejected** (H-03 deferred).

## Slice status

| Slice | Status | Evidence |
|-------|--------|----------|
| **H-01** — Company stamp matrix | ✅ Complete | `tests/test_p2_harden_01_company_stamp_matrix.py` |
| **H-02** — P2 fixture hook cleanup | ✅ Complete | `TestP2FixtureFidelity` — no `before_flush` in `test_fastapi_p2_*.py` |
| **H-03** — Systemic API stamp hook | ⏸️ **Deferred / auto-stamp rejected** | [P2_HARDEN_01_H03_AUDIT.md](./P2_HARDEN_01_H03_AUDIT.md) · `tests/test_p2_harden_01_h03_audit.py` |

## Standing rules (locked)

1. **Explicit `company_id` on service constructors and `create_journal_entry(..., company_id=...)`** is the standard.
2. **No silent `before_flush` auto-stamping** on API sessions.
3. **No hidden ambient `company_id` mutation** via contextvars for stamping.
4. Streamlit `_stamp_company_id_on_new_objects` remains Streamlit-only; `api/dependencies.get_db()` yields a bare session with **no listener**.
5. Kernel-created rows with NULL risk stay covered by **wrapper post-stamps** (`write_partner_worker._stamp_company_on_movement`, `write_closing.allocate`).

## Audit artifacts

- [P2_HARDEN_01_COMPANY_STAMP_AUDIT.md](./P2_HARDEN_01_COMPANY_STAMP_AUDIT.md) — route/service matrix (2026-06-16 refresh)
- [P2_HARDEN_01_H03_AUDIT.md](./P2_HARDEN_01_H03_AUDIT.md) — defer/reject systemic auto-stamp

## Optional follow-ups (not blocking closure)

- Reconciliation match: extra `BankTransaction` / JE stamp assertions in P2 tests (nice-to-have)
- **Fail-loud guard** (raise on NULL tenant `company_id` at flush) — **only at FastAPI runtime cutover**, never silent auto-fill

## Verification

```bash
pytest tests/test_p2_harden_01_company_stamp_matrix.py
pytest tests/test_p2_harden_01_h03_audit.py
pytest tests/test_fastapi_p2_*.py
pytest tests/
```

## Not in scope

- PostgreSQL production cutover
- Enabling `ERP_API_WRITE_*` flags globally (remain off until operator decision)
- React migration
