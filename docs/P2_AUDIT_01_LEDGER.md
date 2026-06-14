# P2-AUDIT-01 — FastAPI P2 Write API Ledger

Running ledger of implementation findings, parity gaps, and follow-ups discovered while shipping P2.1–P2.x write slices. Append dated entries; do not re-audit closed items from scratch.

**Related:** [fastapi_p2_write_api_inventory.md](./fastapi_p2_write_api_inventory.md) · [TECH_DEBT_AND_MIGRATION_CLEANUP.md](./TECH_DEBT_AND_MIGRATION_CLEANUP.md) · [AUDIT_HISTORY.md](./AUDIT_HISTORY.md)

---

## 2026-06-14 — P2.9 finding: API sessions lack Streamlit `before_flush` company stamp

**Slice:** P2.9 — Closing / allocation / YEC write API

**Symptom:** Profit allocation via the API wrapper could succeed on the first call but fail to block a duplicate allocation for the same fiscal period on a second call, even though Streamlit blocked the duplicate.

**Root cause:** API test sessions (and FastAPI `get_db` / `SessionLocal` in general) do not install Streamlit’s `Session.before_flush` hook (`app._stamp_company_id_on_new_objects`). In Streamlit, that hook stamps `company_id` on new ORM rows at flush time. The allocation kernel (`allocate_profit_to_partners`) creates `PartnerProfitAllocation` without setting `company_id` explicitly; the duplicate-allocation guard queries `PartnerProfitAllocation.company_id == company_id`. When `company_id` stayed `None` on the row, the guard did not see the first allocation and allowed a second post.

**Fix (P2.9):** `services/write_closing.py` — after kernel success, wrapper-side stamp: if `allocation.company_id is None`, set `allocation.company_id = company_id` before audit/commit. Preserves kernel behavior; restores parity with the Streamlit stamp hook for this path only.

**Tests:** Covered in `tests/test_fastapi_p2_closing_write.py` (duplicate allocation rejection + `PartnerProfitAllocation.company_id` assertion).

**Follow-up registered:** **P2-HARDEN-01** — audit whether all API-created ORM rows receive explicit `company_id` (or an API-session equivalent of the Streamlit `before_flush` stamp) without relying on Streamlit-only hooks. See [ROADMAP § P2-HARDEN-01](../ROADMAP.md#p2-harden-01--company-stamp-audit) · [TECH_DEBT § P2-HARDEN-01](./TECH_DEBT_AND_MIGRATION_CLEANUP.md#p2-harden-01-2026-06-14).
