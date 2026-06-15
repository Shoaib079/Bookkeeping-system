# RECEIPT-AI-02-IMPL-5 — Learned Prefill in Receipt Capture

**Status:** Implemented (2026-06). Surfaces learned vendor mappings as editable prefill hints in Receipt Capture. **No auto-post.**

## What was added

- **`services/receipt_learning_prefill.py`** — `get_learned_receipt_suggestion`, `LearnedReceiptSuggestion`, `apply_learned_category_prefill`, `tier_allows_prefill`.
- **Adapter helpers** in `services/receipt_ai_adapter.py` — `resolve_receipt_capture_vendor`, re-exported `get_learned_receipt_suggestion`, learned prefill in `create_receipt_capture_draft`.
- **UI** in `ui/staff_capture.py` — category/subcategory default from learned mapping when tier ≥ prefill (80%); confidence captions; advisory payment hint.
- **Locales** — `sc.rcpt.learned.*` keys.
- **`tests/test_receipt_ai_02_impl_5_learning_prefill.py`**

## Prefill rules

| Tier | Confidence | Category prefill |
|---|---|---|
| `manual` | < 80% | No — show low-confidence caption only |
| `prefill` | 80–95% | Yes — user can override |
| `auto_post_eligible` | > 95% + N approvals | Yes (still no auto-post in this slice) |
| `trusted` | > 99% + many approvals | Yes (still no auto-post) |

Payment suggestions are **always advisory** — shown as caption only, never applied to the payment selectbox automatically.

## Flow

1. User enters vendor text or uses sample extraction → `resolve_receipt_capture_vendor`.
2. `get_learned_receipt_suggestion(session, company_id, vendor)` reads `ReceiptLearningMap` via `PersistentLearningStore`.
3. UI sets category/subcategory widget defaults when vendor changes and tier allows prefill.
4. On draft create, adapter applies learned category when `tx_category_id` was not passed.

## Not in this slice

- No auto-submit, approve, or post.
- No OCR/AI API, POS AI, or cash/card reconciliation.
- No schema changes.
- No learning writes on prefill (read-only).

## Run

```bash
pytest tests/test_receipt_ai_02_learning_service.py
pytest tests/test_receipt_ai_02_impl_3_learning_map.py
pytest tests/test_receipt_ai_02_impl_4_void_reversal.py
pytest tests/test_receipt_ai_02_impl_5_learning_prefill.py
pytest
```
