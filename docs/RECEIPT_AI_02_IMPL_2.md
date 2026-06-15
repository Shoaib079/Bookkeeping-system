# RECEIPT-AI-02-IMPL-2 — Original Suggestion Capture

**Status:** Implemented (2026-06). **Capture only** — enables future correction-learning; does not call `receipt_learning` yet.

## What was added

- **`models.ReceiptDraftSuggestion`** — additive table `receipt_draft_suggestions` (one row per draft, immutable after create).
- **`services/receipt_suggestion_capture.py`** — `capture_draft_suggestion`, `get_captured_suggestion`, DTOs.
- **Wiring** in `services/receipt_ai_adapter.py` — capture on receipt-capture draft creation only.
- **`tests/test_receipt_ai_02_impl_2_suggestion_capture.py`**

## Why a separate table (not `ExpenseDraft.ai_suggestion_json`)

- Keeps `ExpenseDraft` as human-final values only.
- Links `attachment_sha256` without denormalizing onto the draft row.
- Unique `(company_id, draft_id)` enforces one immutable original snapshot.
- Migration-safe additive table; indexes added in `migrate_schema`.

## Stored fields

`vendor_signature`, `vendor_text`, `suggested_category_id`, `suggested_subcategory_id`, `suggested_payment_method`, `suggested_payment_confidence`, `suggested_payment_evidence`, `suggested_items`, `extraction_confidence`, `raw_text`, `source` (`manual` | `sample_extractor` | future `ocr`), `created_by_id`, `created_at`, plus full `snapshot_json` of the `DraftSuggestion`.

## Future correction-learning

When a draft is approved, a later slice can diff:

- **Suggested** — `ReceiptDraftSuggestion` (this slice)
- **Approved** — final `ExpenseDraft` + posted `ExpenseRecord`

That powers correction penalties in `receipt_learning` (RECEIPT-AI-02-IMPL-4+).

## Rules (this slice)

- Capture at **receipt draft creation** only.
- Second capture for same draft is **skipped** (no overwrite).
- **No learning**, **no posting**, **no UI change**, **no OCR**.

## Run

```bash
pytest tests/test_receipt_ai_02_learning_service.py
pytest tests/test_receipt_ai_02_impl_2_suggestion_capture.py
pytest
```
