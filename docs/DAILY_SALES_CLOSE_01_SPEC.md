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
- Service compares `external_total` (and optional breakdown) to ERP `erp_total` (and breakdown);
  `z_report_total` is a **secondary** compare when entered (see §3.2.1 and §7.5).

### 3.2.1 Verification basis (External Source, Z Report, or Both)

Managers may verify against one figure, the other, or both on the same record:

| Basis | What is entered | Primary ERP compare | Secondary ERP compare |
|-------|-----------------|---------------------|------------------------|
| **External Source only** | `external_total` (+ optional breakdown) | `external_total` vs `erp_total` | — |
| **Z Report only** | `z_report_total` only (no `external_total` on verify) | `z_report_total` vs `erp_total` | — |
| **Both** | `external_total` and `z_report_total` | `external_total` vs `erp_total` | `z_report_total` vs `erp_total` |

**Rules:**

1. **Verify requires at least one declared total** — `external_total` **or** `z_report_total`
   (or both). A draft may omit both until the user is ready.
2. **`external_total` is authoritative for primary variance** when both totals are present.
   `z_report_total` never replaces `external_total` as the primary compare; it adds a
   parallel `z_report_variance` and may surface `variance_type = z_report_variance` when
   that secondary compare is outside tolerance.
3. **External breakdown** (`external_cash` / `external_card` / `external_online`) applies
   only when `external_total` is entered; Z-report-only verification compares total to ERP
   total only (no Z breakdown in Phase 1).
4. **UI copy** should label the two sides clearly: “External source total” vs “Z-report
   total (optional)” so users know which figure drives primary vs secondary variance.

### 3.3 Other constraints

- **Currency:** company base currency only in Phase 1.
- **Business date:** calendar date aligned with `Sale.date`; no shift logic in Phase 1.
- **Voided sales:** excluded from ERP side (`Sale.is_void == False`).
- **Branch / location:** optional; supports multi-site businesses without provider coupling.
  Empty or whitespace-only input is normalized to **default site** (`NULL` in storage); see
  §5.1.1.

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
| `external_total` | Float, **nullable** | Primary external gross — **required on verify** when Z-only basis is not used (see §3.2.1) |
| `z_report_total` | Float, nullable | Z-report total if available |
| `external_cash` | Float, nullable | Cash breakdown if available |
| `external_card` | Float, nullable | Card breakdown if available |
| `external_online` | Float, nullable | Online / delivery / other digital if available |
| **ERP snapshot (computed at verify)** | | |
| `erp_total` | Float, **nullable** | Sum of all sale types — **NULL on draft**; set at verify |
| `erp_cash` | Float, **nullable** | Cash `Sale` sum — **NULL on draft** |
| `erp_card` | Float, **nullable** | Card `Sale` sum — **NULL on draft** |
| `erp_credit` | Float, **nullable** | Credit `Sale` sum — **NULL on draft** |
| **Variance** | | |
| `variance_total` | Float, **nullable** | `external_total - erp_total` when `external_total` entered; **NULL on draft** |
| `variance_cash` | Float, nullable | Only if both sides have cash breakdown |
| `variance_card` | Float, nullable | Only if both sides have card breakdown |
| `variance_online` | Float, nullable | `external_online - erp_credit` when online entered |
| `z_report_variance` | Float, nullable | `z_report_total - erp_total` when Z total entered |
| `variance_type` | String(30), **nullable** | See §7 — **NULL on draft** |
| `within_tolerance` | Boolean, **nullable** | **NULL on draft**; set at verify (see §7.2) |
| `variance_acknowledged` | Boolean, default False | Set `True` when verify succeeds with material variance and `ack_note` provided |
| `variance_ack_note` | Text, nullable | Required when **material variance** on verify (§7.2) |
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
| `sale_count_snapshot` | Integer, **nullable** | Stale detection — **NULL on draft**; set at verify |
| `attachment_count` | Integer, default 0 | |

### 5.1.1 Draft nullability (binding)

| Column group | On **draft** | On **verified** |
|--------------|--------------|-----------------|
| Identity (`source_name`, `source_type`, `branch_location`, `notes`) | May be partial; `source_name` required to save draft | `source_name` required |
| External totals | All nullable; user may save work-in-progress | At least one of `external_total` or `z_report_total` required (§3.2.1) |
| ERP snapshot | **All NULL** — never pre-filled with zeros on draft | All ERP columns populated from live `Sale` read at verify time |
| Variance fields | **All NULL** (`variance_*`, `variance_type`, `within_tolerance`) | Populated from `compute_variance` at verify |
| `verified_by_id` / `verified_at` | NULL | Set on verify |
| `sale_count_snapshot` | NULL | Set from ERP `sale_count` at verify |
| `variance_ack_note` / `variance_acknowledged` | NULL / False | `ack_note` required when material variance (§7.2) |

**Implementation rule:** Do not store `0.0` as a placeholder for unset draft ERP or variance
columns — use SQL `NULL` so drafts are distinguishable from “verified with zero sales.”

### 5.1.2 Branch normalization and active-row uniqueness (binding)

**Branch normalization** (`normalize_branch` in service):

1. Trim whitespace from user input.
2. Empty string `""` or whitespace-only → store **`NULL`** (default site).
3. Non-empty trimmed text → store as-is (max 200 chars).
4. Comparison and uniqueness always use the **normalized** value.

**Active row** = `is_void == False` (regardless of `status` draft vs verified).

**Uniqueness rule:** At most one active row per
`(company_id, business_date, normalized_branch)` where `normalized_branch` is `NULL` for the
default site.

| Scenario | Allowed? |
|----------|----------|
| One active draft for `(co, 2026-06-05, default)` | Yes |
| Second active row same company + date + default site | **No** — `save_draft` upserts or rejects with clear error |
| Active row `(co, 2026-06-05, NULL)` and active row `(co, 2026-06-05, "Branch A")` | Yes — different normalized branches |
| User enters `""` then `"  "` for same site on same date | **No** — both normalize to `NULL`; same uniqueness bucket |
| Voided row exists for `(co, date, branch)`; new active row for same key | Yes — void frees the slot |

**Draft upsert (recommended):** When `save_draft` targets an existing active draft for the
same `(company_id, business_date, normalized_branch)`, update that row in place rather than
inserting a duplicate.

**Status / void sync:** When `status = voided`, service sets `is_void = True`. Active rows
always have `is_void = False`. Never allow `status = verified` with `is_void = True`.

**Other constraints:**

- `source_name` must be non-empty trimmed text (service validation).
- If breakdown fields are provided, service warns when
  `external_cash + external_card + external_online` differs from `external_total` by more
  than tolerance — **warning only**, does not block save (POS reports vary); requires
  `external_total` to be non-null.

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
    external_total: float | None = None
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
    variance_total: float | None
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
| `validate_external_totals(external, *, for_verify: bool) -> str \| None` | Draft: optional totals; verify: at least one of `external_total` or `z_report_total`; negatives rejected |
| `normalize_branch(branch: str \| None) -> str \| None` | `""` / whitespace → `None`; else trimmed text |
| `get_active_verification(session, business_date, branch?) -> row \| None` | Uses `normalize_branch`; active = `is_void == False` |
| `save_draft(session, business_date, source, external, user_id, notes?) -> tuple[int, str]` | Upsert active draft for `(company, date, normalized branch)`; ERP/variance left NULL |
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

### 7.1 Tolerance constant

Default **0.01** base currency. Optional future registry key
`operations.sales_verify_tolerance`. Used by `compute_variance` and §7.2.

### 7.2 Material variance

**Material variance (binding definition):**

```text
material_variance = not within_tolerance
```

`within_tolerance` is computed at **verify** time by `compute_variance` and stored on the
row. It is `True` only when **every applicable compare** for the verification basis (§3.2.1)
is within tolerance:

| Compare | Applies when |
|---------|--------------|
| Primary total (`variance_total`) | `external_total` entered |
| Breakdown variances (cash / card / online) | Matching external breakdown entered |
| Secondary total (`z_report_variance`) | `z_report_total` entered |

If **any** applicable compare exceeds tolerance, `within_tolerance = False` → **material
variance**.

**Acknowledgement on verify:**

- `material_variance` and no `variance_ack_note` → verify **rejected**
- `material_variance` and non-empty `variance_ack_note` → verify **allowed**;
  `variance_acknowledged = True`

No material variance → `variance_ack_note` optional.

### 7.3 Variance classification (`variance_type`)

Evaluated at verify from applicable compares (§3.2.1). When both `external_total` and
`z_report_total` are present, **primary** classification uses `variance_total` first;
`z_report_variance` contributes to `within_tolerance` and may set or refine `variance_type`.

| Type | Condition |
|------|-----------|
| `balanced` | `within_tolerance` is `True` |
| `total_variance` | `external_total` entered; `|variance_total|` > tolerance; no breakdown variance driving a finer type |
| `cash_variance` | Cash breakdown variance outside tolerance |
| `card_variance` | Card breakdown variance outside tolerance |
| `online_variance` | Online vs ERP credit variance outside tolerance |
| `z_report_variance` | `z_report_total` entered; `|z_report_variance|` > tolerance; primary external total within tolerance (or not entered) |
| `multi_variance` | Multiple categories outside tolerance |

**Z-report-only verify:** When only `z_report_total` is entered, `variance_total` and
breakdown variances remain `NULL`; `within_tolerance` and `variance_type` derive from
`z_report_variance` alone.

### 7.4 Status transitions

```
draft ──verify──▶ verified
  │                  │
  └──void────────────┴──void──▶ voided
```

| Transition | Rules |
|------------|-------|
| **draft → verified** | Recompute ERP snapshot; reject if no declared total (§3.2.1); **material variance** (`not within_tolerance`) requires `variance_ack_note` |
| **verified → void** | Reason required; no delete; sets `is_void = True`, `status = voided` |
| **void → new record** | New active row allowed for same `(company, date, normalized branch)` |

Stale verified records show warning if `sale_count_snapshot` changed (same pattern as EOD).

### 7.5 Z-report display and authority (resolved)

When both `external_total` and `z_report_total` are present on a verified record:

| Aspect | Rule |
|--------|------|
| **Primary authority** | `external_total` — drives `variance_total`, breakdown variances, and primary status messaging |
| **Secondary authority** | `z_report_total` — drives `z_report_variance` only |
| **UI display** | Show **both** variances side by side; never hide Z-report variance when Z total was entered |
| **`within_tolerance`** | `False` if **either** primary or Z-report compare is outside tolerance |
| **`variance_type`** | Reflect the most specific failing category; use `z_report_variance` when Z compare fails but primary external total is within tolerance |
| **Conflict between totals** | If `external_total ≠ z_report_total`, display an informational note that the two external figures differ; **do not** auto-pick Z over external — user chose to enter both |

Z-report-only verification (no `external_total`): UI shows Z total, `z_report_variance`, and
ERP total only; primary “external source” variance row is omitted or shown as “—”.

### 7.6 EOD hook (DSC-P3)

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
| `validate_external_totals` | Draft: partial totals OK; verify: at least one total; Z-only path; negatives rejected |
| `normalize_branch` | `""` and whitespace → `None`; trimmed text preserved |
| **No provider branches** | Service source scan: no `wolvox`, `suitable`, `suitable_pos` identifiers |
| `save_draft` / `verify` / `void` | Draft null ERP/variance columns; upsert active draft; branch uniqueness; material variance ack |
| **Material variance** | `within_tolerance=False` requires `ack_note` on verify; `True` does not |
| `is_verification_stale` / EOD warning | |
| **Posting guard** | No `create_journal_entry` / `post_*` imports |

### 8.2 `tests/test_daily_sales_close_models.py` (~5 tests)

Model create; `company_id` stamp; draft leaves ERP/variance NULL; unique active
`(company, date, normalized branch)`; `""` branch collides with default site.

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
| External total | `amount_input` | Required for external-source basis; optional if Z-only (§3.2.1) |
| Z-report total | `amount_input` | Optional; required for Z-only basis |
| Cash / Card / Online | `amount_input` | Optional breakdown (only when external total entered) |
| ERP totals | read-only metrics | From service; hidden or “—” on draft |
| Variance | read-only | Primary + Z-report rows when both entered (§7.5) |
| Ack note | `st.text_area` | Shown when preview shows material variance |
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

**Resolved (this revision):** Z-report display and authority — see §3.2.1 and §7.5 (show both
variances; `external_total` remains primary when both entered).

---

## 12. Summary

| Question | Answer |
|----------|--------|
| Hardcoded POS systems? | **No** — `source_name` is free text |
| Suitable / Wolvox in code? | **No** — examples in docs only |
| Phase 1 | Manual entry + verification |
| Verification basis | External source, Z report, or both (§3.2.1) |
| Material variance | `not within_tolerance` — ack note required on verify (§7.2) |
| Does it post? | **Never** |
| ERP side | Read-only `Sale` sums; NULL on draft until verify |
| Logic location | `services/daily_sales_close.py` |
| Future imports | Optional adapters in DSC-P4+, same record shape |

*Update [ROADMAP.md](../ROADMAP.md) when DSC-P1 is scheduled.*
