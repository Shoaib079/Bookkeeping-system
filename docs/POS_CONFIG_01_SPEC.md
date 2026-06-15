# POS-CONFIG-01 — Sales Source & Reconciliation Settings

**Status:** 📋 **Approved spec (documentation only)** — no registry keys, no UI, no schema, no `app.py` change from this document alone.  
**Purpose:** Let **each company** configure how sales are imported, verified, and reconciled — without company-wide assumptions.

**Companion docs:** [ROADMAP.md § POS-CONFIG-01](../ROADMAP.md#pos-config-01--sales-source--reconciliation-settings) · [DAILY_SALES_CLOSE_01_SPEC.md](./DAILY_SALES_CLOSE_01_SPEC.md) · [ROADMAP § ROADMAP-UPDATE-02](../ROADMAP.md#roadmap-update-02--ai-learning--posz-report-queue) · [VENDOR-NEUTRAL-01](../ROADMAP.md#vendor-neutral-01--vendor-neutral-architecture-rule)

---

## 1. Problem

Today, sales/POS behaviour is **partially** configurable per company:

| Area | Today | Gap |
|------|--------|-----|
| Card settlement path | `banking.card_settlement_enabled` (Bank vs Card Sales Clearing) | No unified “sales source” model |
| External totals vs ERP | `ExternalSalesVerification` + Closings UI (DSC-P1–P2) | Manual; no workflow mode switch |
| Bank reconciliation | `banking.reconciliation_enabled` + statement import | Not tied to sales verification source |
| POS / Z-report AI | Roadmapped (POS-AI-01..04) | **No settings layer** — AI behaviour undefined per company |

**Rule:** No company-wide assumptions. Every business configures its own workflow. **Settings determine AI behaviour** (suggest vs auto-post gates, duplicate keys, verification source).

---

## 2. Future settings surface

**Navigation (target):** **Settings → Sales & POS Configuration**

Grouped under registry namespace `pos.*` (company-scoped, `CompanySetting` storage — same pattern as `banking.*` in [settings_catalog.py](../registry/settings_catalog.py)).

---

## 3. Configuration options

### 3.1 Sales Source (`pos.sales_source`)

How primary sales data enters the ERP for this company.

| Value | Meaning |
|-------|---------|
| `external_restaurant` | Totals/import from an external restaurant/POS system (DSC / future adapters) |
| `builtin_erp` | Sales recorded in ERP (Add Transaction, staff capture, API) |
| `hybrid` | Both — external verification **and** ERP sales entry |

**Drives:** which closings workflow is default ([DAILY-SALES-CLOSE-01](./DAILY_SALES_CLOSE_01_SPEC.md) vs native sales), SETUP-01 summary fields, POS-AI upload expectations.

### 3.2 Verification Source (`pos.verification_source`)

What document or system the manager uses to **verify** daily sales (read-only compare or pre-post check).

| Value | Meaning |
|-------|---------|
| `pos_z_report` | End-of-day Z-report / fiscal Z |
| `terminal_slips` | Terminal batch slips |
| `system_report` | Exported system sales report (CSV/PDF/manual) |
| `bank_settlement` | Merchant/bank settlement statement |
| `none` | No external verification step required |

**Multi-select in UI later;** Phase 1 registry may store ordered list JSON.

### 3.3 Card Verification Mode (`pos.card_verification_mode`)

How **card** totals are validated before trusting posting or auto-suggest.

| Value | Meaning |
|-------|---------|
| `z_report` | Match card total on Z-report |
| `terminal_slips` | Match terminal slip totals |
| `bank_statement` | Match bank deposit / settlement (ties to `banking.card_settlement_enabled`) |
| `manual_only` | User confirms manually; no automated cross-check |

### 3.4 Cash Source (`pos.cash_source`)

How **cash** sales position is established for the day.

| Value | Meaning |
|-------|---------|
| `system_report` | External system cash total |
| `erp_sales` | Sum of ERP `Sale` rows (`sale_type=Cash`) |
| `manual_cash_count` | Physical count ([Cash Reconciliation](../ROADMAP.md) / till count) |
| `z_report` | Cash line on Z-report |
| `hybrid` | More than one source must agree (e.g. Z-report + till count) |

### 3.5 Duplicate Protection (`pos.duplicate_protection`)

Composite keys used to block double-posting the same POS document (aligns with **POS-AI-04**). Stored as multiselect / JSON list.

| Key | Role |
|-----|------|
| `date` | Business date |
| `terminal_id` | Terminal / device id |
| `report_number` | Z-report / shift report number |
| `batch_number` | Card batch / settlement batch |
| `total` | Stated grand total |
| `hash` | File/content SHA-256 |

**Default (recommended):** `date` + `hash` minimum; restaurants add `terminal_id` + `report_number`.

### 3.6 Auto-post (`pos.auto_post`)

Governs POS-AI and any future sales import posting — **inherits [AI-LEARNING-01](../ROADMAP.md#ai-learning-01--human-first-learning-workflow-shared-rule) gates**.

| Value | Meaning |
|-------|---------|
| `disabled` | Never auto-post; extraction/suggest UI only |
| `suggest_only` | Prefill draft; user must confirm (first release default) |
| `owner_approval_required` | High-confidence suggest still needs owner/manager approval step |
| `trusted_autopost` | Owner-enabled; confidence + approval history + audit + void safety |

**Hard never-auto-post (from POS safety rules):** payroll, taxes, bank transfers, unknown format, unclear date, duplicate report, mismatched totals.

### 3.7 Document Classification (`pos.document_classification`)

User/AI document type labels — shared with Receipt AI ([AI-LEARNING-01](../ROADMAP.md#ai-learning-01--human-first-learning-workflow-shared-rule)).

| Value | Meaning |
|-------|---------|
| `terminal_slip` | Single-terminal slip |
| `z_report` | Z-report / fiscal close |
| `daily_system_report` | POS daily export |
| `shift_report` | Shift-level report |
| `manual_cash_count` | Till / cash count sheet |
| `unknown` | User must classify |

### 3.8 Workflow Mode (`pos.workflow_mode`)

Top-level UX routing (orthogonal to `pos.sales_source` — source = data origin, mode = which UI/workflow is canonical).

| Value | Meaning |
|-------|---------|
| `external_sales` | Closings → External Sales Verification primary |
| `erp_pos` | Add Transaction / built-in sales entry primary |

---

## 4. Proposed registry keys (not implemented)

All **company-scoped**, `storage="company_setting"`, `audit=True`, `planned=True` until POS-CONFIG-01-IMPL slices land.

| Registry key | Type | Default | Notes |
|--------------|------|---------|-------|
| `pos.sales_source` | enum | `hybrid` | §3.1 |
| `pos.verification_source` | json/list | `["system_report"]` | §3.2 |
| `pos.card_verification_mode` | enum | `manual_only` | §3.3 |
| `pos.cash_source` | enum | `erp_sales` | §3.4 |
| `pos.duplicate_protection` | json/list | `["date","hash"]` | §3.5 |
| `pos.auto_post` | enum | `suggest_only` | §3.6 — **not** `trusted_autopost` by default |
| `pos.document_classification_enabled` | bool | `true` | Prompt on unknown uploads |
| `pos.workflow_mode` | enum | `external_sales` | §3.8 |

**Relationship to existing keys (unchanged):**

- `banking.card_settlement_enabled` — still controls GL path (Bank vs 1150 Clearing); `pos.card_verification_mode=bank_statement` requires settlement workflow when verifying against bank.
- `banking.reconciliation_enabled` — statement import; complements `verification_source=bank_settlement`.

---

## 5. How settings drive AI behaviour

```text
Upload / import
    → pos.document_classification (user confirms if unknown)
    → POS-AI-01 extract (injected seam — suggest only)
    → pos.duplicate_protection check
    → pos.card_verification_mode / pos.cash_source cross-checks
    → pos.auto_post policy
         disabled / suggest_only → draft or ESV row only
         owner_approval_required → approval queue
         trusted_autopost → gated post via existing post_* (POS-AI-03)
```

Settings are read in **pure services** (`services/pos_config.py` — future), never in Streamlit business logic.

---

## 6. Implementation slices (future)

| Slice | Scope |
|-------|--------|
| **POS-CONFIG-01-AUDIT** | ✅ This spec + roadmap + contract tests |
| **POS-CONFIG-01-IMPL-1** | Registry `SettingDef` rows (`planned=True` → live) + `get_pos_config(company_id)` DTO |
| **POS-CONFIG-01-IMPL-2** | Settings UI — Sales & POS Configuration page |
| **POS-CONFIG-01-IMPL-3** | Wire DSC + banking gates to read `pos.*` |
| **POS-CONFIG-01-IMPL-4** | POS-AI / POS-AI-04 consume config DTO |

**Sequencing:** POS-CONFIG-01-IMPL-1 **before** POS-AI-01 OCR implementation.

---

## 7. Rules (locked)

1. **No company-wide assumptions** — every field is per `company_id`.
2. **Configurable ERP** — hide/disable workflows, do not delete accounting paths.
3. **Vendor-neutral** — `source_name` free text; no hardcoded POS vendor in core.
4. **Assist-first** — default `pos.auto_post = suggest_only`.
5. **Settings determine AI behaviour** — no parallel hard-coded AI policy in `app.py`.
6. **Service-first** — FastAPI/React-ready DTO; contract tests on config resolver.
7. **No schema change in Phase A** — reuse `CompanySetting` JSON values until volume justifies normalization.

---

## 8. No-change statement

*Documentation only. POS-CONFIG-01 records the approved per-company sales/POS/reconciliation configuration model. Existing `banking.*` toggles and DSC external sales verification remain authoritative until IMPL slices wire `pos.*` keys. No `app.py`, `models.py`, or posting changes from this spec alone.*
