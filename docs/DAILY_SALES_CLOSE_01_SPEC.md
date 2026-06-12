# DAILY-SALES-CLOSE-01 — External Sales Verification Design

**Status:** Design approved for review — **NOT** scheduled for implementation.  
**Scope guard:** **Verification only.** No accounting entries. No journal entries. No GL
impact. No bank impact. No calls to `create_journal_entry`, `post_*`, or cash
reconciliation posting paths.

**Architecture:** Follows **[ARCHITECTURE-PROTECTION-01](../ROADMAP.md#architecture-protection-01--service-first-development-rule)** —
models → `services/` → tests → minimal Streamlit UI.

**Companion docs:** [ROADMAP.md](../ROADMAP.md) · [ROADMAP § VENDOR-NEUTRAL-01](../ROADMAP.md#vendor-neutral-01--vendor-neutral-architecture-rule) · [USER_ACCESS_STAFF_CAPTURE_SPEC.md](./USER_ACCESS_STAFF_CAPTURE_SPEC.md) · [ARCHITECTURE_HANDOFF.md](../ARCHITECTURE_HANDOFF.md)

---

## 1. Purpose

Give managers a **daily, source-neutral sales verification** workflow built around an
**External Sales Source**:

1. Record totals from **any** external system (POS terminal, restaurant software, Z-report,
   spreadsheet, or manual count) — identified by free-text `source_name`, not by hardcoded
   product integration.
2. Compare against **ERP booked sales** for the same company and business date (read-only
   from non-void `Sale` rows).
3. Surface **variances** with clear status — without creating, adjusting, or posting any
   accounting transaction.

Examples of valid `source_name` values (documentation only — **not** enums or code paths):
*Suitable POS*, *Wolvox*, *Manual*, *Square*, *iKentoo*, *spreadsheet export*.

This closes the gap between “external source says X” and “ERP shows Y” **before** month-end,
without duplicating sales entry (Add Transaction / staff drafts) or replacing cash
reconciliation (physical till vs GL cash).

**Success criteria:**

- Works with **any** POS or restaurant system via manual entry in Phase 1.
- **No provider-specific logic** in Phase 1.
- ERP totals are always **read-only computed** from existing `Sale` data.
- Variance is explainable, auditable, and visible on the Closings workflow.
- Service layer is reusable by future FastAPI endpoints, React UI, and per-provider import
  adapters (later phases only).

---

## 2. Non-goals

| Item | Reason |
|------|--------|
| Journal entries / GL posting / bank updates | Hard rule — verification only |
| Auto-correcting ERP sales to match external source | Posting stays in Add Transaction / approval flows |
| Hardcoded Suitable, Wolvox, or any named POS integration (Phase 1) | Source-neutral by design |
| Provider-specific parsers, APIs, or field mapping (Phase 1) | Manual entry only; adapters deferred |
| OCR / Z-report image parsing (Phase 1) | Attachment is evidence metadata only |
| Replacing **End-of-Day Close** | EOD remains a separate management snapshot |
| Replacing **Cash Reconciliation** | Cash recon = physical count vs GL cash |
| Replacing **STAFF-CAPTURE** `sales_total_drafts` | Staff drafts **post** sales; this **verifies** |
| Recipe costing, inventory, VAT depth | Out of scope |
| Permission matrix / staff portal UI (Phase 1) | Owner/manager only initially |

---

## 3. Source-neutral requirements

### 3.1 Design rules (binding)

1. **No provider-specific logic in Phase 1** — no `if source == "wolvox"` branches.
2. **No hardcoded Suitable / Wolvox behaviour** — those names may appear only as examples
   in documentation.
3. **Generic External Sales Source** — user describes the system in `source_name` (free text).
4. **Optional `source_type` category** — coarse label for filtering/reporting only; never
   drives posting or provider adapters in Phase 1.
5. **Phase 1 = manual entry + verification only.**
6. **Future import adapters** may be added per provider in later phases; each adapter writes
   the same generic record shape — not in scope now.
7. **No accounting impact** — verification records are operational audit data only.

### 3.2 Comparison model

| Side | Origin | Phase 1 |
|------|--------|---------|
| **ERP** | Sum of non-void `Sale` rows for `business_date` | Always computed in service layer |
| **External** | User-entered totals from any source | Manual entry only |

**ERP channel semantics** (fixed, from existing `Sale.sale_type`):

- `cash` → Cash sales
- `card` → Card sales
- `credit` → Credit / house-account sales (ERP term)

**External breakdown** (all optional except primary total):

- `cash`, `card`, `online` — user maps their POS labels at entry time; `online` is an
  external label (may include card-not-present, delivery platforms, etc.) and is **not**
  required to equal ERP `card` or `credit`.

**Totals hierarchy:**

- `external_total` — primary external gross (required on verify)
- `z_report_total` — optional; Z-report / end-of-day slip figure when available
- Service compares `external_total` (and optional breakdown) to ERP `erp_total` (and breakdown)

### 3.3 Other constraints

- **Currency:** company base currency only in Phase 1.
- **Business date:** calendar date aligned with `Sale.date`; no shift logic in Phase 1.
- **Voided sales:** excluded from ERP side (`Sale.is_void == False`).
- **Branch / location:** optional; supports multi-site businesses without provider coupling.

### 3.4 Optional `source_type` categories (metadata only)

| Value | Typical use (examples) |
|-------|------------------------|
| `POS` | Terminal or restaurant POS day-end |
| `ERP` | Totals from another ERP export |
| `MANUAL` | Hand-counted or manager estimate |
| `Z_REPORT` | Z-report / X-report slip totals |
| `EXCEL_UPLOAD` | Spreadsheet figures (manual transcription in P1) |
| `OTHER` | Uncategorized |

`source_type` is **nullable** in Phase 1. It does not enable import pipelines until a
future adapter phase explicitly registers one.

---

## 4. Relationship to existing modules

```
External Sales Source (any system — manual entry in P1)
        ↓
External Sales Verification  ←── compare ──→  ERP Sale totals (read-only)
        ↓ (status + variance only)
EOD checklist warning hook (read-only, optional)
```

| Module | Interaction |
|--------|-------------|
| **Sale** / Add Transaction | ERP comparison source only |
| **EndOfDayClose** | Optional warning if no verification for date (does not block close) |
| **DailyCashReconciliation** | Independent |
| **STAFF-CAPTURE `sales_total_drafts`** | Orthogonal — drafts post; this verifies |
| **Banking / POS Settlement** | No coupling in Phase 1 |

---

## 5. Database model proposal

Table name: `external_sales_verifications` (entity: **External Sales Verification**).

All tables are **additive** via `migrate_schema()` / `Base.metadata.create_all`.
`company_id` auto-stamped on flush.

### 5.1 `external_sales_verifications`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `company_id` | Integer, indexed | |
| `business_date` | Date, indexed | Day being verified |
| `source_name` | String(200), **required** | Free text — e.g. *Suitable POS*, *Wolvox*, *Manual*, *Other POS* |
| `source_type` | String(30), nullable | Optional category: `POS` \| `ERP` \| `MANUAL` \| `Z_REPORT` \| `EXCEL_UPLOAD` \| `OTHER` |
| `branch_location` | String(200), nullable | Branch, store, or service point |
| `status` | String(30) | `draft` \| `verified` \| `voided` |
| **External totals (declared)** | | |
| `external_total` | Float | Primary external gross — **required on verify** |
| `z_report_total` | Float, nullable | Z-report total if available |
| `external_cash` | Float, nullable | Cash breakdown if available |
| `external_card` | Float, nullable | Card breakdown if available |
| `external_online` | Float, nullable | Online / delivery / other digital if available |
| **ERP snapshot (computed at verify)** | | |
| `erp_total` | Float | Sum of all sale types |
| `erp_cash` | Float | Cash `Sale` sum |
| `erp_card` | Float | Card `Sale` sum |
| `erp_credit` | Float | Credit `Sale` sum |
| **Variance** | | |
| `variance_total` | Float | `external_total - erp_total` |
| `variance_cash` | Float, nullable | Only if both sides have cash breakdown |
| `variance_card` | Float, nullable | Only if both sides have card breakdown |
| `variance_online` | Float, nullable | `external_online - erp_credit` when online entered |
| `z_report_variance` | Float, nullable | `z_report_total - erp_total` when Z total entered |
| `variance_type` | String(30) | See §7 |
| `within_tolerance` | Boolean | Primary total (+ entered breakdowns) within tolerance |
| `variance_acknowledged` | Boolean, default False | |
| `variance_ack_note` | Text, nullable | Required when material variance on verify |
| `notes` | Text, nullable | General notes |
| `verified_by_id` | Integer FK `users.id`, nullable | |
| `verified_at` | DateTime, nullable | |
| `created_by_id` | Integer FK `users.id` | |
| `created_at` | DateTime | |
| `updated_at` | DateTime, nullable | |
| `is_void` | Boolean, default False, indexed | |
| `voided_by_id` | Integer FK `users.id`, nullable | |
| `voided_at` | DateTime, nullable | |
| `void_reason` | Text, nullable | |
| `sale_count_snapshot` | Integer | Stale detection |
| `attachment_count` | Integer, default 0 | |

**Constraints:**

- At most one **active** (`is_void == False`) row per
  `(company_id, business_date, branch_location)` — empty/null `branch_location` = default
  site (app-enforced + tested).
- `source_name` must be non-empty trimmed text (service validation).
- If breakdown fields are provided, service warns when
  `external_cash + external_card + external_online` differs from `external_total` by more
  than tolerance — **warning only**, does not block save (POS reports vary).

### 5.2 `external_sales_verification_attachments` (optional — DSC-P3)

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `verification_id` | Integer FK, indexed | |
| `company_id` | Integer | |
| `uploaded_by_id` | Integer FK `users.id` | |
| `file_path` | String | `uploads/{company_id}/ext_sales_verify/{yyyy-mm}/{uuid}.ext` |
| `original_name` | String | Display only |
| `mime` | String | jpg/png/webp/pdf |
| `size_bytes` | Integer | Max 10 MB |
| `sha256` | String(64) | |
| `attachment_kind` | String(30), nullable | e.g. `z_report`, `screenshot`, `export_file` — free category, not provider |
| `created_at` | DateTime | |

No OCR. Metadata only.

### 5.3 Audit

`log_audit()` on create / verify / void / attachment with
`entity_type = "ExternalSalesVerification"`. No `JournalEntry` or `BankTransaction` rows.

---

## 6. Service layer proposal

**Location:** `services/daily_sales_close.py` (module name may stay for roadmap ID; entity is
**External Sales Verification**).

### 6.1 Dataclasses (API-safe, no ORM)

```python
@dataclass(frozen=True)
class ErpSalesTotals:
    business_date: datetime.date
    total: float
    cash: float
    card: float
    credit: float
    sale_count: int

@dataclass(frozen=True)
class ExternalSalesTotals:
    external_total: float
    z_report_total: float | None = None
    cash: float | None = None
    card: float | None = None
    online: float | None = None

@dataclass(frozen=True)
class ExternalSalesSource:
    source_name: str
    source_type: str | None = None
    branch_location: str | None = None

@dataclass(frozen=True)
class SalesVarianceResult:
    variance_total: float
    variance_cash: float | None
    variance_card: float | None
    variance_online: float | None
    z_report_variance: float | None
    variance_type: str
    within_tolerance: bool
    breakdown_warnings: tuple[str, ...]
```

### 6.2 Public functions (no Streamlit; no provider branches)

| Function | Responsibility |
|----------|----------------|
| `compute_erp_sales_totals(session, business_date) -> ErpSalesTotals` | Read-only `Sale` sums |
| `compute_variance(external, erp, *, tolerance) -> SalesVarianceResult` | Pure math; optional breakdowns |
| `validate_external_source(source: ExternalSalesSource) -> str \| None` | `source_name` required |
| `validate_external_totals(external) -> str \| None` | `external_total` required; negatives rejected |
| `get_active_verification(session, business_date, branch?) -> row \| None` | |
| `save_draft(session, business_date, source, external, user_id, notes?) -> tuple[int, str]` | |
| `verify_external_sales(session, id, user_id, *, ack_note?) -> tuple[int, str]` | Snapshot ERP; set verified |
| `void_verification(session, id, user_id, reason) -> str` | No GL reversal |
| `is_verification_stale(session, row) -> bool` | |
| `eod_verification_warning(session, business_date) -> str \| None` | EOD hook |
| `list_verifications(session, date_from, date_to, branch?) -> list` | History |

**Explicitly absent in Phase 1:** `import_wolvox`, `import_suitable_pos`, or any
`parse_<vendor>` function.

### 6.3 Future adapter interface (Phase DSC-P4+ — design only)

```python
class ExternalSalesImportAdapter(Protocol):
    provider_key: str  # e.g. "wolvox_csv" — registered at runtime, not in core schema

    def parse(self, payload: bytes) -> ExternalSalesTotals: ...
```

Adapters populate the **same** generic record. Core service never imports adapter modules
until explicitly wired.

### 6.4 Hard guards (service + CI contract test)

Service module must not import: `create_journal_entry`, `post_cash_sale`, `post_card_sale`,
`post_credit_sale`, `submit_reconciliation`, or any provider-specific module.

---

## 7. Status and variance rules

### 7.1 Tolerance

Default **0.01** base currency. Optional future registry key
`operations.sales_verify_tolerance`.

### 7.2 Variance classification (`variance_type`)

Evaluated on **primary** `variance_total` first; breakdown variances refine classification
when both sides provided:

| Type | Condition |
|------|-----------|
| `balanced` | `|variance_total|` ≤ tolerance; all entered breakdown variances ≤ tolerance |
| `total_variance` | Total outside tolerance; no breakdown entered |
| `cash_variance` | Cash breakdown variance outside tolerance |
| `card_variance` | Card breakdown variance outside tolerance |
| `online_variance` | Online vs ERP credit variance outside tolerance |
| `z_report_variance` | Z-report total entered and differs from ERP beyond tolerance |
| `multi_variance` | Multiple categories outside tolerance |

### 7.3 Status transitions

```
draft ──verify──▶ verified
  │                  │
  └──void────────────┴──void──▶ voided
```

| Transition | Rules |
|------------|-------|
| **draft → verified** | Recompute ERP snapshot; material `variance_total` requires `variance_ack_note` |
| **verified → void** | Reason required; no delete |
| **void → new record** | New active row allowed for same `(company, date, branch)` |

Stale verified records show warning if `sale_count_snapshot` changed (same pattern as EOD).

### 7.4 EOD hook (DSC-P3)

Warning only when no active verification for `business_date`:

```text
"No external sales verification recorded for this date."
```

Does not block `close_day()`.

---

## 8. Test plan

Implement **before** Streamlit UI. No tests assert provider-specific code paths exist.

### 8.1 `tests/test_daily_sales_close_service.py` (~28 tests)

| Area | Cases |
|------|-------|
| `compute_erp_sales_totals` | Empty day; mixed types; void excluded; company isolation |
| `compute_variance` | Balanced; total-only; breakdown optional; Z-report variance; tolerance edge |
| `validate_external_source` | Empty `source_name` rejected; any text accepted (*Wolvox*, *Manual*, etc.) |
| `validate_external_totals` | Missing total rejected; optional breakdowns allowed |
| **No provider branches** | Service source scan: no `wolvox`, `suitable`, `suitable_pos` identifiers |
| `save_draft` / `verify` / `void` | Same as prior design; branch uniqueness |
| `is_verification_stale` / EOD warning | |
| **Posting guard** | No `create_journal_entry` / `post_*` imports |

### 8.2 `tests/test_daily_sales_close_models.py` (~5 tests)

Model create; `company_id` stamp; unique `(company, date, branch)` active constraint.

### 8.3 `tests/test_daily_sales_close_ui_contract.py` (~6 tests, DSC-P2)

- Renderer uses service only
- UI has free-text `source_name`, not provider enum select
- No posting imports in page source

### 8.4 Regression

`tests/test_end_of_day_close.py` unchanged until DSC-P3 hook.

---

## 9. Minimal Streamlit UI proposal (DSC-P2)

Thin `render_external_sales_verification(session)` in `app.py` — **no business rules**.

### 9.1 Navigation

Under **Closings**:

```text
Closings
  ├── Cash Reconciliation       (existing — may post JE)
  ├── External Sales Verification   (NEW — no posting)
  └── End-of-Day Close          (existing)
```

Nav key: `NAV_EXTERNAL_SALES_VERIFICATION` (i18n: “External Sales Verification”).

### 9.2 Tab 1 — Verify

| Field | Widget | Notes |
|-------|--------|-------|
| Business date | `render_preferred_date_input` | |
| **Source name** | `st.text_input` | **Required** free text |
| Source type | `st.selectbox` | Optional category; includes `—` (none) |
| Branch / location | `st.text_input` | Optional |
| External total | `amount_input` | Required |
| Z-report total | `amount_input` | Optional |
| Cash / Card / Online | `amount_input` | Optional breakdown |
| ERP totals | read-only metrics | From service |
| Variance | read-only | From service |
| Notes | `st.text_area` | |
| Attachment | file uploader (DSC-P3) | Optional metadata |

Actions: **Save draft** · **Verify** (ack if variance) · **Void**

**No** dropdown of hardcoded POS products. User types the source name.

### 9.3 Tab 2 — History

Date range filter; table columns: Date, Source name, Type, Branch, External total, ERP
total, Variance, Status, Verified by.

### 9.4 Permissions (Phase 1)

`view_external_sales_verification` · `verify_external_sales` · `void_external_sales_verification`  
Mapped to owner + manager until USER-ACCESS-01.

---

## 10. Implementation phases

| Phase | Deliverable | Gate |
|-------|-------------|------|
| **DSC-P1** | Models + service + tests (generic only) | Posting-guard + no-provider-branch tests pass |
| **DSC-P2** | Minimal Streamlit + nav + UI contract | Manual verify with arbitrary `source_name` |
| **DSC-P3** | Attachment metadata + EOD warning + export | |
| **DSC-P4** | **Optional per-provider import adapters** (separate modules) | Each adapter tested in isolation; core unchanged |

**OBS-01 gate:** Schedule DSC-P1 after repeated friction or explicit owner approval.

---

## 11. Open decisions

1. TR locale strings for nav and `source_type` categories.
2. Void-and-reverify only vs edit verified record (recommend: void-and-reverify).
3. Tolerance constant vs registry setting in P1.
4. Whether `z_report_total` variance is shown alongside or instead of `external_total` when both present (recommend: show both; primary compare remains `external_total`).

---

## 12. Summary

| Question | Answer |
|----------|--------|
| Hardcoded POS systems? | **No** — `source_name` is free text |
| Suitable / Wolvox in code? | **No** — examples in docs only |
| Phase 1 | Manual entry + verification |
| Does it post? | **Never** |
| ERP side | Read-only `Sale` sums |
| Logic location | `services/daily_sales_close.py` |
| Future imports | Optional adapters in DSC-P4+, same record shape |

*Update [ROADMAP.md](../ROADMAP.md) when DSC-P1 is scheduled.*
