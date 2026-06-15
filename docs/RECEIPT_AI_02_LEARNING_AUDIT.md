# RECEIPT-AI-02 — Learning Engine Audit

**Mode:** Audit only. **No schema change, no learning table, no auto-post, no OCR/AI API, no posting change, no UI change.** Designs how Receipt-AI learns from user-approved drafts before any learning table or auto-post logic is built.

## Headline

The pieces needed to learn already exist except **one persisted artifact**: the **AI's original suggestion is not stored** alongside the draft. The `ExpenseDraft` records the **human-confirmed final** values, the `DraftAttachment.sha256` gives receipt identity, and `normalize_vendor_signature` (in `services/receipt_ai.py`) gives the stable learning key — so **learning on approval** is reachable now. But **learning from corrections** and the RECEIPT-AI-08 feedback loop need the *suggested* values captured too (a future, minimal store). Learning must also be **void-aware**: a posted draft that is later reversed must not reinforce.

## 1. Current reusable data map

| Asset | Use for learning | Evidence |
|---|---|---|
| **`ExpenseDraft`** | Approval lifecycle: `created_by_id`, `status` (draft→submitted→approved/…), `reviewed_by_id`, `reviewed_at`, `review_note`, **`expense_record_id`** (set on post = "this draft posted"), `tx_category_id`, `tx_subcategory_id`, `payment_method`, `amount`, `currency`, `description`. The **human-confirmed mapping** = ground truth. | `models.py:1182-1207`; `services/staff_capture.py:622-674` |
| **`DraftAttachment.sha256`** | Receipt identity / dedup / per-receipt linkage to the learned event. | `models.py:1209-1226` |
| **`normalize_vendor_signature`** | Stable vendor key ("BİM"/"BIM"/"Bim" → "BIM") — the learning key for vendor→X. | `services/receipt_ai.py:209` |
| **`TransactionCategory` / `TransactionSubcategory`** | Learning targets (category/subcategory ids). | `models.py:479-491` |
| **`Vendor`** | Vendor target / create-if-missing. | `models.py:254` |
| **`Product`** | Item target (item-text → product). | `models.py:377` |
| **`AuditLog`** | Append-only, **company-scoped** event log (`action`, `entity_type`, `entity_id`, `description`, `performed_by`, `company_id`). Good for *recording* learning events; **not** a queryable mapping store. | `models.py:465-476` |
| **Registry settings** | `get_setting` / `get_effective_config` — feature-flag the learning/auto-post tiers per company. | `registry/` |
| **Permissions** | `submit_expense_drafts` / `approve_expense_drafts` / `upload_receipts`; approval is the privileged learning trigger. | (S5) |
| **`receipt_ai` DTOs** | `DraftSuggestion`, `ReceiptExtraction` already carry vendor_signature, category, payment + confidence — the suggestion side of the diff. | `services/receipt_ai.py` |

**Gap:** the draft stores only the **final** values. The **original AI suggestion** (what the extractor proposed) is **not persisted**, so a suggestion-vs-approved diff (correction signal) cannot be reconstructed after the fact. This is the one missing artifact.

## 2. Proposed learning model

A pure, company-scoped learning service (future `services/receipt_learning`, or an extension of `receipt_ai`) over an **injected store interface** (so the table is swappable / FastAPI-ready). It learns these mappings, all keyed by `company_id`:

- **`vendor_signature → category`** (primary).
- **`vendor_signature → subcategory`**.
- **`vendor_signature → payment_method`** (advisory; never drives posting/settlement).
- **`item_text → product/item`** (when item tracking is enabled).
- **`source/format signature → document type`** (shared with POS-AI per AI-LEARNING-01).

**When learning happens:**
- **On approval — always.** The approved, **posted** draft (`expense_record_id` set) is the ground truth; `record_approval(company_id, vendor_signature, category_id, payment_method, …)` increments the mapping.
- **On correction — only with the captured suggestion.** If the human changed the AI's suggestion before approving, that is the strongest signal — but it requires persisting the original suggestion (see §5). Until then, correction-learning is **deferred**; approval-learning works now.
- **Never on draft creation / submission** (not yet ground truth) and **never on a later-voided posting** (must be reversed out).

## 3. Confidence model

Per mapping `(company_id, vendor_signature → target)`:

- **`approval_count`** — times this exact mapping was approved.
- **`consistency`** = `approvals_for_this_target / total_approvals_for_this_signature` — penalizes a vendor that maps to several categories.
- **`recency`** — recent approvals weigh more (decay).
- **`correction_penalty`** — later corrections/voids reduce confidence.
- **Confidence** = a bounded function of the above; conflicting history → low confidence regardless of count.

**Thresholds (advisory; reuse the RECEIPT-AI-06 tiers; owner-tunable later):**
- **< 80%** → manual review (no prefill).
- **80–95%** → prefill + user confirm.
- **> 95% + ≥ N approvals** → *eligible* for trusted auto-post (still owner-gated).
- **> 99% + many approvals** → trusted-vendor tier.
Numbers are policy, not hard-coded accounting; they live behind config.

## 4. Safety rules

- **Learn only from approved + posted, not-voided** drafts (`expense_record_id` set **and** the posting not later reversed). A void/reversal must **decrement/invalidate** the reinforcement (RECEIPT-AI-08 feedback).
- **Never auto-learn** for: payroll, taxes, bank transfers, large/outlier amounts, multi-category-ambiguous receipts, low extraction confidence, conflicting payment evidence, or a **blank/Unknown vendor signature**.
- **Company isolation** — every mapping keyed by `company_id`; **never** shared across companies.
- **Payment learning is advisory only** — never triggers auto-post, never creates a `BankTransaction`, never settles card/bank.
- **Suggestion, never silent action** — learning prefills; the human still approves; auto-post stays owner-enabled + confidence-gated + audited + void-reversible (AI-LEARNING-01).
- **Minimum count before surfacing** — a single approval does not make a confident mapping.

## 5. Future schema proposal (NOT created here)

- **`receipt_learning_map`** (company-scoped): `company_id`, `signature_type` ∈ {`vendor_category`, `vendor_subcategory`, `vendor_payment`, `item_product`, `source_format`}, `signature_key` (e.g. normalized vendor signature), `target_kind`, `target_id` / `target_value`, `approval_count`, `correction_count`, `last_approved_at`, `confidence_cached`. Unique on `(company_id, signature_type, signature_key, target)`.
- **Capture the original suggestion** to enable correction-learning + the RECEIPT-AI-08 loop: either a minimal `ai_suggestion_json` column on `ExpenseDraft` **or** a separate `receipt_extraction` row linked by draft id / attachment sha256. (Choice deferred; both are additive, migration-safe.)
- **Void-awareness** — reconcile learned reinforcement when a posted draft is voided (decrement the mapping).
- All additive; nothing in this audit creates or alters tables.

## 6. Contract tests (for the implementation slice)

- **Learn only on approval+post:** `record_approval` is invoked only for a draft with `expense_record_id` set; draft creation/submission never learns.
- **Void reverses learning:** voiding a posted draft decrements/invalidates its mapping (no net reinforcement).
- **Company isolation:** a mapping learned for company A is never suggested for company B.
- **Blank/Unknown vendor not learned:** `normalize_vendor_signature(...) is None` → no mapping written.
- **Consistency lowers confidence:** a vendor approved to two different categories yields lower confidence than a vendor consistently approved to one.
- **Threshold tiers:** confidence maps to the manual / prefill / auto-post-eligible / trusted tiers (advisory).
- **Never-learn list honored:** payroll/tax/bank-transfer categories, large/outlier amounts, and conflicting payment evidence do not produce a learned mapping.
- **Pure + serializable:** the learning service has no Streamlit import, explicit `company_id`, DTOs round-trip through JSON; the store is an injected interface.

## 7. Implementation slices (for Cursor — DO NOT implement here)

- **RECEIPT-AI-02-IMPL-1 — pure learning service (no table):** ✅ `services/receipt_learning.py` + in-memory store — see [RECEIPT_AI_02_IMPL_1.md](./RECEIPT_AI_02_IMPL_1.md).
- **RECEIPT-AI-02-IMPL-2 — capture original suggestion:** ✅ `ReceiptDraftSuggestion` table + `services/receipt_suggestion_capture.py` — see [RECEIPT_AI_02_IMPL_2.md](./RECEIPT_AI_02_IMPL_2.md). Closes the captured-suggestion gap for future correction-learning; **does not learn yet**.
- **RECEIPT-AI-02-IMPL-3 — persistent `receipt_learning_map`:** the real table + Alembic, behind the existing learning feature flag; write only on approval.
- **RECEIPT-AI-02-IMPL-4 — void-aware reconciliation:** decrement learning on void/reversal.
- **RECEIPT-AI-02-IMPL-5 — surface suggestions in capture UI:** prefill from learned mappings (still approval-first). Auto-post remains a separate, later, owner-gated slice (RECEIPT-AI-07).

## 8. Risk assessment

**Audit: LOW.** Nothing changes. The approval lifecycle, receipt identity, vendor key, targets, audit log, settings, and permissions all already exist, so an approval-driven learner is low-risk and additive. Real risk concentrates **later**: (a) **learning from mistakes** — mitigated by learn-only-from-approved-and-not-voided, void-aware decrement, minimum counts, and consistency penalties; (b) **the missing original-suggestion artifact** — correction-learning is deferred until it is captured (additive); (c) **auto-post** — out of scope here and gated by owner enablement + confidence + audit + void-reversibility. Company isolation and advisory-only payment learning bound the blast radius.

## No-change statement (RECEIPT-AI-02 audit)

- **No schema change, no learning table, no auto-post, no OCR/AI API, no posting change, no UI change, no `app.py`/`models.py` edit.** Reusable-data map + learning model + confidence model + safety rules + future schema proposal + contract tests + slices + risk only.

---

*Audit only. Reusable now: ExpenseDraft approval lifecycle (expense_record_id = posted ground truth), DraftAttachment.sha256 (receipt identity), normalize_vendor_signature (stable key), TransactionCategory/Subcategory + Vendor + Product (targets), AuditLog (company-scoped event log), registry settings (flags), permissions. Learn vendor→category/subcategory/payment, item→product, source→type — all company-scoped, **on approval** (posted, not-voided); correction-learning is **deferred** because the original AI suggestion is **not persisted today** (the one gap). Confidence = f(approval_count, consistency, recency, correction_penalty); tiers <80 manual / 80–95 prefill / >95+N auto-post-eligible / >99 trusted (owner-tunable, advisory). Safety: learn only from approved+posted+not-voided; void decrements; never learn payroll/tax/transfer/large/ambiguous/blank-vendor; company isolation; payment advisory only; never auto-create bank txn. Future (additive, not built): receipt_learning_map table + captured suggestion + void reconciliation. Risk LOW — additive, approval-driven; auto-post out of scope and fully gated.*
