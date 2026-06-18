# ERP Development Roadmap

**Project:** `streamlit_accounting_erp`  
**Last updated:** 2026-06-05 (UX-STABILIZE-01 — data-entry state cleanup)  
**Companion docs:** [ARCHITECTURE_HANDOFF.md](./ARCHITECTURE_HANDOFF.md) · [PHASE_18_DESIGN_REVIEW.md](../PHASE_18_DESIGN_REVIEW.md) · [docs/NAVIGATION_AUDIT.md](./docs/NAVIGATION_AUDIT.md)

This roadmap defines **what is done**, **what is active**, and **what comes next** — in order. Do not skip phases without an explicit architecture decision.

---

## ERP Core Principles (Locked)

**Status:** Locked architectural principles — learned during Streamlit ERP development (2026).  
**Authority:** Governs all future work (Streamlit, FastAPI, React). Documentation only; no retroactive code mandate beyond what is already shipped.

These ten principles are the official project contract. They extend and consolidate [ARCHITECTURE-PROTECTION-01](#architecture-protection-01--service-first-development-rule), [MIGRATION-READINESS-01](#migration-readiness-01--fastapireact-ready-service-checklist), and related rules below.

### 1. Business Logic First

Always:

```text
Models → Services → Tests → UI
```

Never place business logic in Streamlit UI. Rule remains migration-safe for FastAPI + React.

### 2. Explicit Company Scoping

Services should prefer:

```python
company_id=...
```

Avoid ambient company access inside services. Multi-company isolation is a non-negotiable invariant.

### 3. Accounting Integrity

Never delete accounting records. Use:

```text
Void → Reverse → Audit
```

Audit trail is mandatory.

### 4. State Management Rules

Every form must explicitly define:

- What persists?
- What resets?
- When?
- Why?

Hidden state must never affect save.

### 5. Add Transaction Retention Policy (Locked)

After save:

| Action | Fields |
|--------|--------|
| **KEEP** | Transaction type/section · date |
| **RESET** | Everything else |

Defaults may re-seed safely on rerun. Shipped as **RETENTION-01** / UX-04A evolution.

### 6. Date Ownership Standard

Date is captured at **submit time**. Single resolved date flows through:

```text
UI → Model → Journal Entry → Bank Movement → Reports
```

User-selected date must never be replaced by today's date.

### 7. Desktop/Mobile Unity

Desktop and mobile are **two interfaces of the same ERP** — not separate products. Use:

- Same tokens
- Same components
- Same workflows
- Same permissions
- Same design language

See [ERP-DESIGN-SYSTEM-01](./docs/ERP_DESIGN_SYSTEM_01_ROADMAP.md) and [ERP_DS_04](./docs/ERP_DS_04_MASTER_DESIGN_SYSTEM.md).

### 8. Configurable ERP Philosophy

Prefer **configurable** over opinionated. Examples:

- Inventory optional
- Customer module optional
- Banking workflow configurable ([BANKING-UX-04](#banking-ux-04--configurable-banking-workflow))
- Dashboard density configurable

Hide or organize features instead of deleting them.

### 9. Commit Ownership Principle

Question for every feature: **Who owns commit?**

Target architecture:

```text
UI/API → Unit of Work → Services
```

Boundary commits are the long-term model. Execution plan: [FASTAPI_P0_5D_COMMIT_OWNERSHIP_PLAN.md](./docs/FASTAPI_P0_5D_COMMIT_OWNERSHIP_PLAN.md). Slices shipped: cash sale (S1) · expense (S2).

### 10. Discovery Before Implementation

All future projects should follow:

```text
Discovery → Roadmap → Models → Services → Tests → UI → API → Migration
```

No implementation before roadmap approval.

### Changelog — principles locked (2026-06-14)

| Principle | Streamlit evidence |
|-----------|-------------------|
| Business logic first | `services/posting.py`, `services/audit.py`, registry services |
| Explicit `company_id` | FASTAPI-P0.5b company scoping; service parameter pattern |
| Void/reverse/audit | Kernel + `AuditLog` on every mutation |
| Form state rules | AT widget keys; deferred subcat sync; submit-time capture |
| RETENTION-01 | `_at_clear_post_save_transient_fields()` — type + date only |
| Date ownership | `_at_capture_submit_resolved_date()` pipeline |
| Desktop/mobile unity | `mobile_components.css` + DS-4 parity matrix |
| Configurable ERP | Registry settings; module gates; banking A/B/C (P2.3) |
| Commit ownership | `boundary_commit_scope` + per-family `commit_mode` flags |
| Discovery first | CHAR docs before every extraction phase |

**Cross-references:** [ERP_DS_04](./docs/ERP_DS_04_MASTER_DESIGN_SYSTEM.md) · [ERP_DS_05](./docs/ERP_DS_05_REACT_ARCHITECTURE.md) · [BANKING_UX_03_ROADMAP](./docs/BANKING_UX_03_ROADMAP.md)

---

## Docker Setup (Development)

**Status:** ✅ **Safe local development containerization complete** (2026-06-16)

### Quick Start

```bash
# Build the image (first time only)
docker-compose build

# Start the container (preserves existing erp_data.db)
docker-compose up -d

# Access the app
open http://localhost:8501

# View logs
docker-compose logs -f erp

# Stop the container
docker-compose down
```

### Architecture

- **Dockerfile** — Python 3.11, dependencies, Streamlit on port 8501
- **docker-compose.yml** — Mounts local `erp_data.db`, `uploads/`, `.streamlit/` as volumes
- **.dockerignore** — Excludes `.git`, backups, pycache, tests
- **Database persistence** — SQLite volume mounted at `/app/erp_data.db` (read-write, safe)
- **No data loss** — Existing records appear immediately; container does not create new empty DB

### Safety Guarantees

- Local `erp_data.db` is mounted directly into container
- No automatic schema migrations run (Alembic authority flag unset inside container)
- App reads/writes existing database as-is
- Container can be destroyed without affecting local database
- Backups created before Docker setup (see `backups/` directory)

### Important Notes

- Docker is for **local development only** — not production-ready
- Do **not** run FastAPI routes inside the container yet
- Do **not** use PostgreSQL cutover inside the container
- Business logic and accounting remain unchanged
- Tests run normally on host (outside container)

### Files Added

- `Dockerfile` — image definition
- `docker-compose.yml` — orchestration
- `.dockerignore` — build optimization
- `backups/erp_data_before_docker_*.db` — safety backup

---

## Status at a glance

| Area | Status |
|------|--------|
| Core ERP & accounting engine | ✅ Complete |
| **Docker safe local development** | ✅ **Complete (2026-06-16)** — Dockerfile + docker-compose.yml + persistent SQLite volume |
| Multi-company isolation | ✅ Complete |
| Company settings isolation (14D-B) | ✅ Complete |
| Settings / module registry (14D-B2a) | ✅ Complete |
| COA & categories per company (14D-C) | ✅ Complete |
| Company creation (14D-D) | ✅ Complete |
| Sidebar uses company role (nav fix) | ✅ Complete |
| Simplified Company Setup UI | ✅ Complete (Expert policies stub) |
| Automated tests | ✅ **4654 passing, 11 skipped, 2 xfailed** (run `pytest tests/` on host) |
| Member management (14D-E) | ✅ Complete |
| Member roster polish (14D-F) | ✅ Complete |
| Setup wizard v1 (14D-G) | ✅ Complete — **superseded by SETUP-01** |
| SETUP-01 Company Creation Wizard | ✅ **Built and tested** (reconciled 2026-06-10) — `registry/setup01_wizard.py` + `ui/setup01_wizard.py` (`render_setup01_wizard`) + wizard CSS/locales; tests: `setup01_wizard_b1/b2/b3`, `setup01_i18n`, `setup01_error_messages`, `setup01_entry_regression` |
| SETUP-02 Setup Summary | 📋 Medium — planned |
| SETUP-03 Configuration Health Check | 📋 Medium — planned |
| BANK-03 POS Settlement wording | ✅ **Verified** (2026-06-05 — locales EN/TR; `tests/test_bank03_wording.py`) |
| BANKING-POS-WORKFLOW-01 P1+P2 | ✅ Shipped — Other Income Sales Revenue guardrails + POS Settlement explainer (no posting changes) |
| **BANKING-UX-02** — POS Settlement Transparency | ✅ **Complete** — P1 preview · P1B focused entry · P2 clearing visibility · P3 unsettled list · P4 match check (no posting changes) |
| **BANKING-UX-03** — Reconciliation Cockpit & Queue | ✅ **P1–P2 shipped** · 📋 **P3 future** — see [BANKING_UX_03_ROADMAP](./docs/BANKING_UX_03_ROADMAP.md) |
| **BANKING-UX-04** — Configurable Banking Workflow | ✅ **Complete** — S1–S4; see [§ BANKING-UX-04](#banking-ux-04--configurable-banking-workflow) |
| **ERP Core Principles (Locked)** | ✅ **Approved** — 10 locked principles; see [§ ERP Core Principles](#erp-core-principles-locked) |
| **RETENTION-01** — Add Transaction post-save policy | ✅ **Shipped** — keep type + date; reset all other fields |
| **DATE OWNERSHIP** — Submit-time date capture | ✅ **Shipped** — single resolved date through GL/bank/reports |
| **FASTAPI-P0.5d** — Commit ownership (boundary UoW) | 🟡 **In progress** — S1 cash sale ✅ · S2 expense ✅ · remaining families queued |
| **DATE CONTROL** — Unified React date field | 📋 **Future (React)** — single field + focus-opens calendar; see [§ DATE CONTROL](#date-control--future-react-ux) |
| PARTNER-UX-01 P1–P3 | ✅ Shipped — Partner movement explanations, advance warnings, Summary plain labels (no posting changes) |
| PARTNER-STATEMENT-01 P1 | ✅ Shipped — read-only Partner Statement tab (month/quarter/year/custom); profit by fiscal period end-date; no posting changes |
| PARTNER-STATEMENT-01 P2 | ✅ Shipped — detail lines, running position, Excel export |
| PARTNER-STATEMENT-01 P3 | ✅ Shipped — PDF export + print-friendly report UI |
| PARTNER-STATEMENT-01 P4 | ✅ Shipped — all-partners settlement summary (P1 projection rollup; Excel/CSV/PDF export) |
| Localization EN/TR (15) | ✅ Complete |
| DEVELOPMENT_MODE | ✅ **Resolved by DEV-AUTH-01** — env-gated dev mode: `DEV_MODE = os.getenv("ERP_DEV_MODE", "0") == "1"` (default off). **Production checklist: must not run with `ERP_DEV_MODE=1`** |
| Shell / mobile chrome (Phase A) | ✅ Stabilized — fixed header, 968px breakpoint, People hub wired |
| Sidebar / navigation redesign (AD-UI-001) | 🟡 **D1 + D2-P0 shipped** — Financial Statements routes + promoted daily lookup route (app.py `AD-UI-001 D2-P0` wrapper); D2+ remainder gated — see [NAVIGATION_AUDIT.md](./docs/NAVIGATION_AUDIT.md) §16 |
| **NAV-ARCH** — Navigation single source of truth | ✅ **S4 complete** — registry + React route contract frozen — see [§ NAV-ARCH](#nav-arch--navigation-single-source-of-truth) |
| **UI-SYSTEM-02** — ERP-wide UI & theme modernization | ✅ **S1–S5 complete** — see [§ UI-SYSTEM-02](#ui-system-02--erp-wide-ui--theme-modernization) |
| **MONO-THEME-01** — Option A+ unified mono ERP theme | ✅ **Complete** — S1–S7 — see [§ MONO-THEME-01](#mono-theme-01--option-a-unified-mono-erp-theme) |
| **MONO-THEME-02** — Real UI visual refinement pass | ✅ **Complete** — S0–S5 — see [§ MONO-THEME-02](#mono-theme-02--real-ui-visual-refinement-pass) |
| **MOB-AT-C1** — Concept C Mobile AT UI | ✅ **Accepted** — reference implementation; 747 tests passing |
| **MOBILE-11** — Mobile Design System | ✅ **Approved** — `docs/MOBILE_UI_SYSTEM.md` is the governing document for all future mobile work |
| **MOBILE-12** — Design Governance | ✅ **Approved** — open decisions recorded; phased migration path defined |
| ERP-Wide UI Ownership Principle | ✅ **Approved** — governs all CSS work going forward |
| **CSS-01** — Theme Ownership Consolidation | 🟡 **HIGH** — approved; ownership map for existing CSS |
| **CSS-02** — ERP-Wide UI Ownership Standard | 🟡 **HIGH** — approved; 8 enforceable rules; ongoing standard |
| **MOBILE-14** — Mobile Theme Ownership Cleanup | ✅ **Closed** (M1+M2+M5+M6+TXH) · M3/M4 optional xfails remain |
| **THEME-CONTRAST-01** — Desktop/Theme Contrast (P0+P1) | ✅ **Closed** — primary fill + success/warning text tokens (2026-06-05) |
| **LOGIN-01** — Login / Company Picker Modernization | ✅ **Closed** — flat auth cards; `ui/auth.css` sole owner (2026-06-05) |
| **DASHBOARD-01** — Dashboard Visual Refresh | ✅ **Closed** — D1 flat welcome + micro-text; D2 class system + KPI variant-only API |
| **QUICK-ENTRY-01** — Context-Aware Mobile Category Selection | ✅ **DONE** — implemented; 14/14 tests passing (2026-06-10) |
| **ADD-TXN-BR-01** — Sale validation vs bookkeeping rules | ✅ **Closed** — manual + pytest verified (2026-06-10) |
| **AT-LIGHT-01** — Mobile AT Light-Mode Polish (P1–P6) | ✅ **Closed** — manual phone/POS verification complete (2026-06-10) |
| **DATE-01** — Fast Mobile Date Entry | ✅ **Closed** — mobile date sheet + rollover + backdated marker (2026-06-10) |
| **UX-01** — Session Persistence (v1) | ✅ **Closed** — signed restore token + company revalidation (2026-06-10) |
| **TXH-DETAIL-01** — Transaction Detail JE/Edit History Polish | ✅ **Closed** — semantic classes + readable grid (2026-06-05) |
| **VIEWPORT-SYNC-01** — JS/CSS Mobile Threshold Sync | ✅ **Closed** — align-up to 1366px touch tablets (2026-06-05) |
| **UX-02** — Responsive Viewport & Device Auto-Fit | ✅ **Superseded** — reduced to VIEWPORT-SYNC-01 (HDR-01/MOBILE-14/UX-01 covered rest) |
| **HDR-01** — Combined Header Pass (UX-07 + UX-06) | ✅ **Closed** — responsive selector, ellipsis, toolbar cluster (2026-06-10) |
| **UX-03** — Inline Expense Category Creation | ✅ **Closed** — Expense picker search CTA (2026-06-10) |
| **UX-04** — Selector Interaction Audit | ✅ **Closed** — UX-04A/B/C + Repeat v1 (2026-06-10) |
| **UX-04A** — Post-Save State Retention | ✅ **Closed** — subcategory/customer/worker field fix (2026-06-10) |
| **UX-04B** — Payment Method Chips (mobile) | ✅ **Closed** — inline PM chip row (2026-06-10) |
| **UX-04C** — Safe Smart Defaults | ✅ **Closed** — PM memory + single-bank auto-pick (2026-06-10) |
| **Repeat Last Transaction (v1)** | ✅ **Closed** — TXH row action, Expense/Purchase only (2026-06-10) |
| **UX-STABILIZE-01** — Data-Entry State Cleanup | ✅ **Closed** — worker salary isolation, post-save category reset, nav scroll-to-top (2026-06-05) |
| **UX-05** — Universal Outside-Tap Dismiss | 📋 Backlog — last; needs separate infrastructure audit + tests |
| **CHART-01** — Chart Theme Consolidation | ⚠️ **Needs short verification pass** — `chart_theme_tokens()` exists in `ui/theme.py` but has 0 app.py call sites; 0 native `st.bar_chart`/`st.line_chart` remain (AUDIT-01 counted 6). Charts migrated or removed — verify before trusting status (reconciled 2026-06-10) |
| **AUDIT-01** — ERP Ownership Audit | ✅ **Complete** — findings recorded; quick wins identified |
| Future UX / navigation vision | 📋 **Low** — design direction only (MOBILE-07–12, DESIGN-05, DESKTOP-04) — implementation gated on MOBILE-11 system |
| **PROFILE-PHOTO-01** — Profile photo / avatar upload | 📋 **Proposed** · Low — UX only; no accounting impact |
| **UI-STAB-01** — Shared avatar renderer | ✅ **Complete** — `ui/avatar.py`; header, mobile profile, My Account, login tiles |
| **UI-STAB-02** — Banking presentation separation | ✅ **Complete** — `ui/banking.py`; P1–P4 + P1B presentation; posting stays in `app.py` |
| UI architecture stability (UI-STAB) | 📋 **Planned** — header CSS consolidation remainder; avatar + banking presentation shipped |
| Operational friction log (OBS-01) | 🟡 **Active** — record real-world UX friction; 3+ occurrences → roadmap candidate |
| **ARCHITECTURE-PROTECTION-01** | 🟢 **Active immediately** — service-first, migration-safe development rule |
| **VENDOR-NEUTRAL-01** | 🟢 **Active immediately** — no vendor-specific core architecture; generic external-source pattern |
| **MIGRATION-READINESS-01** | 🟢 **Active immediately** — FastAPI/React-ready service design checklist; exemplars: DSC-P1 · RC-P1 |
| **DAILY-SALES-CLOSE-01** | ✅ **DSC-P1–P2 complete** · 📋 **DSC-P3–P4 pending** — source-neutral external sales verification (no posting); see [docs/DAILY_SALES_CLOSE_01_SPEC.md](./docs/DAILY_SALES_CLOSE_01_SPEC.md) · [TECH_DEBT](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md) |
| **RECIPE-COSTING-01** | ✅ **RC-P1–P2A complete** · 📋 **RC-P2B–P3 pending** · 🔮 **RC-AI-01 optional (future)** — ingredient/recipe costing + menu profitability basics; see [TECH_DEBT](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md) (TD-RC-*) |
| **USER-ACCESS-01** | ✅ **UA-P1 complete** · 📋 **UA-P1b pending** — permission override service + effective resolver; see [docs/USER_ACCESS_STAFF_CAPTURE_SPEC.md](./docs/USER_ACCESS_STAFF_CAPTURE_SPEC.md) · [TECH_DEBT](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md) (TD-UA-*) |
| **STAFF-CAPTURE-01** | ✅ **SC-P1 complete** · ✅ **SC-P1b complete** · 📋 **SC-P2 pending** · 📋 **SC-P3 pending** — expense draft service + thin Streamlit UI (submit · receipts · inbox); see [docs/USER_ACCESS_STAFF_CAPTURE_SPEC.md](./docs/USER_ACCESS_STAFF_CAPTURE_SPEC.md) · [TECH_DEBT](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md) (TD-SC-*) |
| **POSTING-SERVICE-01** | ✅ **Complete** — PS-P0–P6-5 + **FASTAPI-REACT-01** (PS-P7 boundary); TD-PS-01/03 deferred, **not a blocker** · [POSTING_SERVICE_01_STATUS](./docs/POSTING_SERVICE_01_STATUS.md) |
| **REPORTS-SERVICE-01** | 🟡 **Partial** — query/read layer in `services/read_*`; Streamlit presentation (`render_*`, trial balance loop) remains in `app.py` until React |
| **BANKING-SERVICE-01** | 🟡 **Partial** — `write_banking` + `write_reconciliation` + `read_reconciliation` shipped; **BS-02 ✅** · **BS-04 ✅** · `match_post` / `company_card` `_app()` coupling remains · [BANKING_SERVICE_01_AUDIT](./docs/BANKING_SERVICE_01_AUDIT.md) |
| **FastAPI foundation** | 🟡 **Partial (strong)** — P0/P1/P2 routes + 38+ `test_fastapi_*` files; writes feature-flagged; Streamlit primary; **not production-complete** |
| **FASTAPI-REACT-00** | ✅ **Audit complete** — baseline migration snapshot; see [§ FASTAPI-REACT-00](#fastapi-react-00--migration-baseline-audit) |
| **PostgreSQL runtime** | 🟡 **Partial** — **production cutover ✅ (testing)** · flag-gated PG runtime wired · SQLite rollback preserved |
| **React migration** | ⬜ **Not started** — `ERP_DS_05` spec only; no SPA; preceded by [NAV-ARCH](#nav-arch--navigation-single-source-of-truth) |
| **FULL-SERVICE-READINESS-AUDIT** | ✅ **Recorded (2026-06-05)** — whole-repo service-extraction snapshot · [FULL_SERVICE_READINESS_AUDIT](./docs/FULL_SERVICE_READINESS_AUDIT.md) |
| **DOCS-MIGRATION-CHECKPOINT-01** | ✅ **Recorded (2026-06)** — register drift fix after FASTAPI-READINESS-CHECKPOINT · [DOCS_MIGRATION_CHECKPOINT_01](./docs/DOCS_MIGRATION_CHECKPOINT_01.md) |
| **FUTURE-MIGRATION-AUDIT-01** | 📊 **Recorded (2026-06-13 baseline)** — score **62/100**; historical snapshot — blocker list superseded by [DOCS_MIGRATION_CHECKPOINT_01](./docs/DOCS_MIGRATION_CHECKPOINT_01.md) · [TECH_DEBT](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md) |
| **P2-HARDEN-01** — Company Stamp Audit | ✅ **Closed (2026-06-16)** — H-01 matrix ✅ · H-02 fixture fidelity ✅ · H-03 auto-stamp **deferred/rejected** · [closure doc](./docs/P2_HARDEN_01_AUDIT_CLOSURE.md) |
| **DASH-CASH-01** — Split Liquid Funds | ✅ **S1/S2 complete** — `compute_liquid_position` + dashboard UI shipped |
| **AUTH-SESSION-02** — Session hardening | 🟡 **Partial** — audit ✅ · IMPL-1 session policy ✅ · IMPL-2 browser-session policy wiring ✅ · **IMPL-3 idle extension ✅** · remember-device / revocation **open** · [AUTH_SESSION_02_AUDIT](./docs/AUTH_SESSION_02_AUDIT.md) · [IMPL-3](./docs/AUTH_SESSION_02_IMPL_3.md) |
| **RECEIPT-AI-01** | ✅ **Complete** — service seam + adapter + fake extractor (IMPL-1/2/3a/3b/3c) · no real OCR provider |
| **RECEIPT-AI-02** | ✅ **IMPL-1–5 complete** — learning store + prefill loop; **approval/void hooks deferred** · no auto-post |
| **RECEIPT-AI-03 … RECEIPT-AI-08** | 📋 **Future** — vendor detection · item extraction · confidence · trusted auto-post last |
| **POS-CONFIG-01** — Sales Source & Reconciliation Settings | ✅ **Spec/audit complete** — per-company `pos.*` settings; IMPL-1+ pending · [docs/POS_CONFIG_01_SPEC.md](./docs/POS_CONFIG_01_SPEC.md) |
| **POS-AI / POS automation** | ⏸️ **ROADMAP ONLY — paused** — POS AI · Z-report · terminal slips · cash/card reconciliation automation · **do not implement until user explicitly requests** · [§ Paused](#paused--do-not-start-without-user-approval) |
| **BANKING-UX-05** — AI Statement Matching | 📋 **Future** — suggest + learn; user approval first; see [§ ROADMAP-UPDATE-01](#roadmap-update-01--approved-future-work-queue) |
| **DASH-KPI-01 … DASH-KPI-03** — Dashboard KPI extensions | 📋 **Future** — forecast · runway · sales-by-payment-type; see [§ ROADMAP-UPDATE-01](#roadmap-update-01--approved-future-work-queue) |
| **AI-BOOKKEEPER-01** — Business Explanation AI | 📋 **Future** — read-only explanations; see [§ ROADMAP-UPDATE-01](#roadmap-update-01--approved-future-work-queue) |

---

## Current priority

**Use the system daily** — build only what causes friction during real bookkeeping.

**Test baseline:** `pytest tests/` — **4751 passed**, 29 skipped, 2 xfailed.

**MD-05-IMPL-5 (2026-06-16):** Flag-gated `0001→0002` cutover via `ERP_MONEY_NUMERIC_CUTOVER=1` + P3.8 backup/confirmation; post-cutover cache re-sync; production `erp_data.db` blocked. Tag: `money-decimal-05-impl5-cutover-gate`. Doc: [MONEY_DECIMAL_05_IMPL_5.md](./docs/MONEY_DECIMAL_05_IMPL_5.md).

**AUTH-SESSION-02-IMPL-3 (verified 2026-06-16):** Idle session extension — `should_extend_idle` + `_maybe_extend_idle_session()` in `main()`; implementation `ee57dc1`. Tag: `auth-session-02-impl3-idle-extension`. Doc: [AUTH_SESSION_02_IMPL_3.md](./docs/AUTH_SESSION_02_IMPL_3.md).

**P2-HARDEN-01 (verified 2026-06-16):** Company stamp audit closed — H-01/H-02 complete; H-03 auto-stamp deferred/rejected. Tag: `p2-harden-01-company-stamp-audit`. Doc: [P2_HARDEN_01_AUDIT_CLOSURE.md](./docs/P2_HARDEN_01_AUDIT_CLOSURE.md).

**MONEY-DECIMAL-04c+ (verified 2026-06-16):** JE guard / FX native Decimal boundary verified — no runtime changes; float guard preserved (MD-02 locked). Tag: `money-decimal-04c-je-fx-decimal-guard`. Doc: [MONEY_DECIMAL_04C_JE_FX_DECIMAL.md](./docs/MONEY_DECIMAL_04C_JE_FX_DECIMAL.md).

**POSTGRES-PG-BUILD (verified 2026-06-16):** Alembic `upgrade head` PG test build + dual-run parity harness (report fingerprints). Tag: `postgres-pg-build-dual-run-parity`. Doc: [POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md](./docs/POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md).

**POSTGRES-RUNTIME-CUTOVER-PREP (verified 2026-06-16):** Test-only SQLite→PG data copy harness + parse-only runtime gate; production still SQLite. Tag: `postgres-runtime-cutover-prep`. Doc: [POSTGRES_RUNTIME_CUTOVER_PREP.md](./docs/POSTGRES_RUNTIME_CUTOVER_PREP.md).

**POSTGRES-PRODUCTION-CUTOVER (verified 2026-06-16):** Flag-gated PostgreSQL runtime wired; SQLite data migrated to PG; parity verified companies 1–4; backup preserved. Tag: `postgres-production-cutover`. Doc: [POSTGRES_PRODUCTION_CUTOVER.md](./docs/POSTGRES_PRODUCTION_CUTOVER.md).

**POSTGRES-REAL-DRY-RUN (verified 2026-06-16):** Real copy-only SQLite→PG migration dry run; row counts + TB + reports match companies 1–4; `erp_data.db` untouched. Tag: `postgres-real-dry-run-20260616`. Doc: [POSTGRES_REAL_DRY_RUN_20260616.md](./docs/POSTGRES_REAL_DRY_RUN_20260616.md).

**BANKING-SERVICE-01-BS-03 (verified 2026-06-16):**** CC bill payment JE uses `services.posting.create_journal_entry(..., company_id=...)`; implementation `713ac3c`. Tag: `banking-service-01-bs03-company-card-company-scope`. Doc: [BANKING_SERVICE_01_BS03.md](./docs/BANKING_SERVICE_01_BS03.md).

**MD-05 track:** IMPL-1 ✅ · IMPL-2 ✅ · IMPL-3 ✅ · IMPL-4 ✅ · **IMPL-5 ✅** — see [MONEY_DECIMAL track](#money-decimal-01--float--decimal-migration) below.

**External merges (2026-06-16):** **PR #2** — error-handling audit · **PR #3** — +226 coverage tests. *(Pre-sync baseline: **4572 passed**; +6 Sync-02 → **4578 passed**.)*

**Migration gates closed:** **P3.9** series ✅ (A → B-CHAR → B → C) · **ALEMBIC-01** ✅ (Alembic-only schema evolution; `migrate_schema()` no-op stub).

**Register sources:** [FULL_SERVICE_READINESS_AUDIT](./docs/FULL_SERVICE_READINESS_AUDIT.md) · [BANKING_SERVICE_01_AUDIT](./docs/BANKING_SERVICE_01_AUDIT.md) · [FASTAPI_READINESS_CHECKPOINT](./docs/FASTAPI_READINESS_CHECKPOINT.md) · [DOCS_MIGRATION_CHECKPOINT_01](./docs/DOCS_MIGRATION_CHECKPOINT_01.md).

**Current priority (ordered):**

1. **Keep `ROADMAP.md` accurate** after each audit/implementation checkpoint (ROADMAP-SYNC-01/02 hygiene rule).
2. ~~**BANKING-SERVICE-01-BS-03**~~ ✅ — `company_card` CC bill payment JE explicit `company_id` ([BS-03 doc](./docs/BANKING_SERVICE_01_BS03.md); commit `713ac3c`).
3. ~~**AUTH-SESSION-02-IMPL-3**~~ ✅ — idle extension (`should_extend_idle` wired; [IMPL-3 doc](./docs/AUTH_SESSION_02_IMPL_3.md)).
4. ~~**P2-HARDEN-01**~~ ✅ — `company_id` stamping audit closed ([closure doc](./docs/P2_HARDEN_01_AUDIT_CLOSURE.md)).
5. ~~**MONEY-DECIMAL-04c+**~~ ✅ — JE guard / FX native Decimal boundary verified ([MD-04c doc](./docs/MONEY_DECIMAL_04C_JE_FX_DECIMAL.md)).
6. ~~**MONEY-DECIMAL-05 (MD-05)**~~ ✅ — Alembic Numeric migration (**IMPL-1–5 ✅**; flag-gated cutover).
7. ~~**PostgreSQL build + dual-run parity**~~ ✅ — Alembic PG test build + harness ([PG build doc](./docs/POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md)).
8. ~~**PostgreSQL runtime cutover prep**~~ ✅ — test-only SQLite→PG copy + runtime gate parse-only ([prep doc](./docs/POSTGRES_RUNTIME_CUTOVER_PREP.md)).
9. ~~**Real SQLite→PG dry run**~~ ✅ — copy-only migration verified on `erp_pytest` ([dry run doc](./docs/POSTGRES_REAL_DRY_RUN_20260616.md)).
10. ~~**PostgreSQL production runtime cutover**~~ ✅ — flag-gated PG runtime wired; testing cutover verified ([cutover doc](./docs/POSTGRES_PRODUCTION_CUTOVER.md)).
11. **React migration** — Phase D after API/service hardening.

| Task | Status |
|------|--------|
| **POSTING-SERVICE-01** | ✅ Complete — kernel in `services/posting.py`; app shims; FASTAPI-REACT-01 boundary hardening complete |
| **REPORTS-SERVICE-01** | 🟡 Partial — `services/read_*` computes; Streamlit `render_*` until React |
| **BANKING-SERVICE-01** | 🟡 Partial — `write_banking` + `write_reconciliation`; **BS-03 ✅** · **BS-04 ✅**; `match_post`/`company_card` other `_app()` debt |
| **AUTH-SESSION-02** | 🟡 Partial — IMPL-1/2/3 ✅; remember-device/revocation open |
| **RECEIPT-AI-01** | ✅ Complete — service seam; no OCR provider |
| **RECEIPT-AI-02** | ✅ IMPL-1–5 complete — prefill loop; approval/void hooks deferred |
| **FastAPI foundation** | 🟡 Partial (strong) — P0–P2; writes flag-gated; not production-complete |
| **PostgreSQL runtime** | 🟡 Partial — **production cutover ✅ (testing)** · SQLite rollback preserved |
| **React migration** | ⬜ Not started — specs only |

**🚧 BUILD GATE (active):** Do **not** build large new Streamlit UI surfaces before **banking service extraction** and **API hardening** land. Allowed: OBS-01 friction fixes, service-first screen-light phases (RC-P2B/P3 class), thin UI over existing services. Screens are the layer React replaces — invest in services, not chrome.

**⏸️ PAUSED (user gate):** POS AI · Z-report processing · terminal receipt processing · cash/card reconciliation automation · multi-POS automation · POS auto-post · real OCR/AI provider · trusted receipt auto-post — see [§ Paused / Do Not Start](#paused--do-not-start-without-user-approval).

**Approved future queue (docs only — 2026-06-05):** See **[ROADMAP-UPDATE-01](#roadmap-update-01--approved-future-work-queue)** for DASH-KPI · BANKING-UX-05 · AI-BOOKKEEPER backlog. AI receipt **auto-post is not first release** — assist/review mode ships first.

**CSS architecture cleanup:** **MOBILE-14 closed.** Optional follow-up: M3/M4 suppression-rule relocation in `widgets.css` (not blockers). **CSS-01** / **CSS-02** remain the ongoing ownership standard.

**Observe during use (do not build yet):** Dashboard quick actions, worker advance mobile parity, BANK-01 reality audit (after weeks of real card/bank activity). Log friction in **[OBS-01](#obs-01--operational-friction-log)** as it happens.

**Deferred:** Inventory expansion, procurement, CRM, BI — until real usage demands them.

**Do NOT start (future projects — see [FUTURE UX / NAVIGATION VISION](#future-ux--navigation-vision)):** Banking redesign · Reports redesign · Mobile shell redesign · Navigation redesign · More Hub redesign · Sidebar redesign.

**Success metric:** Daily sales, expenses, and purchases are easy to enter; banking is understandable; month-end is fast; company switching is reliable — not feature count.

---

## Paused / Do Not Start Without User Approval

**Status:** Active gate (ROADMAP-SYNC-01, 2026-06-05)

The following are **documented on the roadmap only**. Do **not** implement until the user explicitly requests them:

| Area | Scope |
|------|--------|
| **POS-AI** | Daily POS / Z-report OCR · source learning · trusted POS auto-post |
| **Z-report processing** | Upload · parse · suggest · post automation |
| **Terminal receipt processing** | Slip OCR · terminal-level totals |
| **Cash/card reconciliation automation** | Multi-source auto-match beyond current manual match/post |
| **Multi-POS automation** | Cross-terminal aggregation · auto-post |
| **POS auto-post** | Any autonomous sales posting from POS documents |
| **Real OCR/AI provider integration** | External vision/LLM adapters for receipts or POS |
| **Trusted receipt auto-post** | RECEIPT-AI-07 class owner-gated auto-posting |

**Allowed without this gate:** characterization tests · audits · docs · registry keys · suggest/prefill flows that require user approval.

---

## Completed recent milestones

| Milestone | Status |
|-----------|--------|
| **NAV-UX-02** S1–S6 | ✅ Structural contracts · statements consolidation · Members mobile · Staff Expenses permissions · legacy telemetry |
| **AUTH-SESSION-01** | ✅ Session restore + company revalidation |
| **AUTH-SESSION-02** IMPL-1/2/3 | ✅ `session_policy` + browser-session TTL + idle extension — [IMPL-3](./docs/AUTH_SESSION_02_IMPL_3.md) |
| **DASH-CASH-01** S1/S2 | ✅ `compute_liquid_position` + dashboard UI |
| **RECEIPT-AI-01** IMPL-1/2/3a/3b/3c | ✅ Service seam + adapter + fake extractor |
| **RECEIPT-AI-02** IMPL-1/2/3/4/5 | ✅ Learning store + suggestion capture + prefill (approval/void hooks deferred) |
| **POS-CONFIG-01** audit/spec | ✅ Per-company `pos.*` settings spec |
| **FULL-SERVICE-READINESS-AUDIT** | ✅ Whole-repo extraction snapshot |
| **BANKING-SERVICE-01** audit | ✅ Banking/reconciliation readiness map |
| **BANKING-SERVICE-01-BS-02-CHAR** | ✅ `match_post` account-resolution characterization tests |
| **BANKING-SERVICE-01-BS-04** | ✅ Streamlit manual bank → `write_banking` · [BS-04 note](./docs/BANKING_SERVICE_01_BS04.md) |
| **POSTING-SERVICE-01** | ✅ Complete — PS-P0–P6-5 complete |
| **P3.8-L-EXEC** | ✅ Alembic authority bake-in execution record — [P3_8_L_BAKEIN_EXEC.md](./docs/P3_8_L_BAKEIN_EXEC.md) |
| **P3.8-L-TESTS** | ✅ Alembic authority bake-in characterization gate — [P3_8_L_TESTS.md](./docs/P3_8_L_TESTS.md) |
| **P3.8-N** | ✅ Alembic authority default flip — [P3_8_N_DEFAULT_FLIP.md](./docs/P3_8_N_DEFAULT_FLIP.md) |
| **P3.9-A** | ✅ `migrate_schema()` retirement readiness audit — [P3_9_A_AUDIT.md](./docs/P3_9_A_AUDIT.md) |
| **P3.9-B-CHAR** | ✅ Caller inventory + deprecation contract — [P3_9_B_CHAR_MIGRATE_SCHEMA_CALLERS.md](./docs/P3_9_B_CHAR_MIGRATE_SCHEMA_CALLERS.md) |
| **P3.9-B** | ✅ `migrate_schema()` DeprecationWarning — [P3_9_B_DEPRECATION.md](./docs/P3_9_B_DEPRECATION.md) |
| **P3.9-C** | ✅ `migrate_schema()` implementation removal (no-op stub) — [P3_9_C_REMOVAL.md](./docs/P3_9_C_REMOVAL.md) |
| **ALEMBIC-01** | ✅ Alembic replaces `migrate_schema()` — P3.9-C no-op stub |
| **External PR #2** | ✅ Error-handling improvements (auth/posting/statement_parse/app/theme) |
| **External PR #3** | ✅ +226 coverage tests (6 under-tested modules) |

---

## ROADMAP-SYNC-02 — post P3.9-C + external PR register sync

**Status:** ✅ **Complete** (2026-06-16) — baseline **4578 passed** (4572 post-PR#3 + 6 Sync-02 contract tests); records PR #2/#3 merges; confirms P3.9 + ALEMBIC-01 complete; next critical path **MD-05 Numeric** before PG cutover.

**Contract:** `tests/test_roadmap_sync_01.py` (extended Sync-02 guards)

---

## Roadmap hygiene rule

**Status:** Active (ROADMAP-SYNC-01 · ROADMAP-SYNC-02)

After **every** audit or implementation checkpoint:

1. Update **`ROADMAP.md`** (status at a glance + current priority).
2. Update the **relevant status doc** (e.g. `POSTING_SERVICE_01_STATUS.md`, `BANKING_SERVICE_01_AUDIT.md`).
3. Add or update a **doc contract test** (`tests/test_*_sync_*.py` or checkpoint test).
4. **Commit + tag** the checkpoint (when the user requests a commit).
5. **Never leave stale blockers unmarked** — if code says complete, the roadmap must not still list it as open.

Contract tests: `tests/test_roadmap_sync_01.py` · `tests/test_docs_migration_checkpoint_01.py` · `tests/test_full_service_readiness_audit.py` · `tests/test_banking_service_01_audit.py`.

---

## ARCHITECTURE-PROTECTION-01 — Service-First Development Rule

**Status:** Active immediately

**Rule:** All new modules must be **service-first** and **migration-safe**.

**Required order:**

1. Database models
2. Service / business logic
3. Tests
4. Minimal Streamlit UI only if useful

**Strict rule:**

- Streamlit must **not** own business logic.
- Business rules must live **outside** `app.py`.
- Accounting logic must live in **reusable services**.
- Tests are the authority.

**Reason:** Future target is FastAPI + React ([FUTURE-MIGRATION-01](#future-architecture--long-term-roadmap)). Any logic built correctly now must be reusable later. External systems must stay vendor-neutral ([VENDOR-NEUTRAL-01](#vendor-neutral-01--vendor-neutral-architecture-rule)).

**Warning rule:** If a feature is mainly UI-heavy, multi-user, mobile, login/auth, permissions dashboard, staff portal, uploads, or approval workflow — **pause** before building it deeply in Streamlit.

**Build now:**

- Accounting logic
- Reports logic
- Daily Sales Close service
- Recipe Costing service
- Data models
- Tests

**Defer or keep minimal:**

- Full login system
- Staff portal UI
- Mobile receipt uploads
- Complex permission screens
- Approval inbox UI
- Advanced admin/settings UI

**Future target stack:**

```
React
↓
FastAPI
↓
Services
↓
SQLAlchemy
↓
PostgreSQL
```

**Related:** [ARCHITECTURE-PROTECTION-01](#architecture-protection-01--service-first-development-rule) · [VENDOR-NEUTRAL-01](#vendor-neutral-01--vendor-neutral-architecture-rule) · [MIGRATION-READINESS-01](#migration-readiness-01--fastapireact-ready-service-checklist)

---

## VENDOR-NEUTRAL-01 — Vendor-Neutral Architecture Rule

**Status:** Active immediately

**Rule:** Core architecture must **not** depend on any named POS, restaurant, or external-system vendor. Integrations are **generic first**; vendor-specific code lives only in optional, pluggable adapters outside the core.

**Applies to:** `models.py`, `services/`, `registry/` settings keys, enums, roadmap **requirements**, service function names, module names, and Streamlit dispatch — not user-typed data or documentation examples.

### Required pattern — External Sales Source (and similar)

| Field | Rule |
|-------|------|
| `source_name` | **Free text** — user or operator labels the system (any POS, ERP, or manual source) |
| `source_type` | **Optional generic category** — e.g. `POS`, `ERP`, `MANUAL`, `Z_REPORT`, `EXCEL_UPLOAD`, `OTHER` |
| `branch_location` | Optional text |
| Totals / variance / status | Generic numeric and workflow fields — no vendor columns |

**Do not** hardcode product names (e.g. Suitable, Wolvox, Square) in enums, model fields, service branches, or roadmap implementation requirements.

### Allowed

- **Documentation examples** — vendor names in specs, handoff, or training prose only, clearly as illustrations.
- **User-entered text** — `source_name` may contain any string the operator types.
- **Domain terminology** — “POS Settlement” in banking = card clearing workflow ([BANKING-UX-02](#banking-ux-02--pos-settlement-transparency--complete)), **not** a named POS product integration.
- **Future per-provider adapters** — separate modules (e.g. DSC-P4), registered at runtime; core schema unchanged.

### Forbidden in core (Phase 1 and ongoing)

- `if source == "wolvox"` (or any named vendor) in services or `app.py`
- Enum values or settings keys named after a vendor product
- Service or model names embedding a vendor (`import_wolvox`, `SuitablePosTotals`, etc.)
- Roadmap phases that **require** a specific vendor integration in core
- Provider-specific columns on shared verification/import tables

### Exemplar

[DAILY-SALES-CLOSE-01](./docs/DAILY_SALES_CLOSE_01_SPEC.md) — External Sales Verification: manual entry, `source_name` text, optional `source_type`, no posting. Reference implementation of this rule.

### Enforcement

- New modules: comply with [ARCHITECTURE-PROTECTION-01](#architecture-protection-01--service-first-development-rule) **and** this rule.
- Design reviews: reject vendor-specific core designs; defer adapters.
- Tests (when built): contract scan — no vendor identifiers in `services/` source (see DAILY-SALES-CLOSE-01 test plan).

### Related architecture rules

| Rule | Relationship |
|------|----------------|
| [ARCHITECTURE-PROTECTION-01](#architecture-protection-01--service-first-development-rule) | Services must be reusable; vendor neutrality keeps them portable |
| [MIGRATION-READINESS-01](#migration-readiness-01--fastapireact-ready-service-checklist) | Explicit DTOs and no Streamlit coupling prepare services for FastAPI |
| [FUTURE-MIGRATION-01](#future-architecture--long-term-roadmap) | Generic services + optional adapters support FastAPI/React migration |
| [DAILY-SALES-CLOSE-01](./docs/DAILY_SALES_CLOSE_01_SPEC.md) | First feature spec written under this rule |

---

## MIGRATION-READINESS-01 — FastAPI/React-Ready Service Checklist

**Status:** Active immediately

**Rule:** Every new `services/` module must be designed as if a **FastAPI route will call it next** — even while Streamlit remains the only UI.

**Required properties:**

| # | Property |
|---|----------|
| 1 | Business logic in `services/` (or `registry/` helpers), **not** `app.py` |
| 2 | **No** Streamlit imports, `st.session_state`, `cq()`, or `_current_user()` in services |
| 3 | **Explicit inputs** — `company_id`, `user_id`, dates, and request DTOs passed as parameters |
| 4 | **Serializable outputs** — frozen dataclasses or typed records with `to_dict()` (no ORM rows at the public boundary) |
| 5 | **Pure validation/math** separated from persistence (`validate_*`, `compute_*` with no DB) |
| 6 | **Tests runnable without Streamlit** — in-memory SQLite + explicit `company_id` |
| 7 | **Contract tests** — posting-guard scan; vendor-neutrality scan where applicable |
| 8 | **Known debt logged** in [TECH_DEBT_AND_MIGRATION_CLEANUP.md](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md) |

**UI layers (Streamlit now, React later) may only:**

- Read session/auth context
- Map form state → service DTOs
- Call service functions with explicit `company_id` / `user_id`
- Render service return values (metrics, tables, errors)

**Exemplar:** [DSC-P1](./docs/DAILY_SALES_CLOSE_01_SPEC.md) — `services/daily_sales_close.py` (`ExternalSalesVerification`).

### Implementation report — Migration Cleanup (required)

Every implementation handoff or completion report must end with a **Migration Cleanup** section covering:

1. **Code to keep** during FastAPI/React migration (services, models, tests, DTOs)
2. **Code likely to replace** (Streamlit renderers, `app.py` dispatch, session-key wiring)
3. **Dead code found** (if any)
4. **Temporary Streamlit-only code** (`st.session_state`, `_erp()` lazy imports, widget keys)
5. **Items added to** [TECH_DEBT_AND_MIGRATION_CLEANUP.md](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md)

Template lives in [TECH_DEBT § Implementation report template](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md#implementation-report--migration-cleanup-template).

**Related:** [ARCHITECTURE-PROTECTION-01](#architecture-protection-01--service-first-development-rule) · [VENDOR-NEUTRAL-01](#vendor-neutral-01--vendor-neutral-architecture-rule) · [FUTURE-MIGRATION-01](#future-architecture--long-term-roadmap) · [TECH_DEBT_AND_MIGRATION_CLEANUP.md](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md)

---

## DAILY-SALES-CLOSE-01 — Implementation status

| Phase | Status | Deliverable |
|-------|--------|-------------|
| **DSC-P1** | ✅ **Complete** | `ExternalSalesVerification` model · `services/daily_sales_close.py` · service/model tests · schema indexes |
| **DSC-P2** | ✅ **Complete** | Minimal Streamlit under Closings · `ui/external_sales_verification.py` · UI contract tests |
| **DSC-P3** | 📋 **Pending** | Attachment metadata · EOD warning hook · export |
| **DSC-P4** | 📋 **Pending** | Optional per-provider import adapters (outside core) |

Spec: [docs/DAILY_SALES_CLOSE_01_SPEC.md](./docs/DAILY_SALES_CLOSE_01_SPEC.md). Tech debt: [docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md) (TD-DSC-*).

---

## RECIPE-COSTING-01 — Implementation status

| Phase | Status | Deliverable |
|-------|--------|-------------|
| **RC-P1** | ✅ **Complete** | `Ingredient` · `Recipe` · `RecipeLine` models · `services/recipe_costing.py` · service/model tests · schema indexes |
| **RC-P1b** | ✅ **Complete** | List/read APIs · `ui/recipe_costing.py` (Ingredients · Recipes · Cost Breakdown) · Recipe Costing nav · UI contract tests |
| **RC-P2A** | ✅ **Complete** | `MenuItem` · `MenuPriceHistory` · menu CRUD · price history · profitability math · `render_recipe_menu_items` · Menu Items nav |
| **RC-P2B** | 📋 **Pending** | Advanced analytics — menu engineering matrix · sales volume · dashboard charts (out of RC-P2A scope) |
| **RC-P3** | 📋 **Pending** | Export · purchase integration · `RECIPE_COSTING_01_SPEC.md` |
| **RC-AI-01** | 🔮 **Future / Optional** | AI-assisted recipe suggestions — suggest only; never auto-save; human review required (see below) |

Tech debt: [docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md) (TD-RC-*).

### RC-AI-01 — AI recipe suggestions (future / optional)

**Status:** Future / Optional — not scheduled; no implementation without explicit approval.

**Prerequisites (all required before build):**

| Gate | Requirement |
|------|-------------|
| Foundation | RC-P1 ✅ · RC-P1b ✅ · RC-P2A ✅ |
| Data | Stable ingredient catalog in production use |
| Architecture | Claude architecture review (ARCHITECTURE-PROTECTION-01 · VENDOR-NEUTRAL-01) |
| Governance | Human approval before any save path is wired |

**Allowed:**

- AI may **suggest** recipes (draft lines, quantities, sub-recipes) from the existing ingredient catalog
- Suggestions surfaced in UI as a **review draft** only

**Hard rules:**

- AI may **never** auto-save recipes (`save_recipe`, `create_menu_item`, or any mutation without explicit user confirm)
- User must review, edit, and confirm before `save_recipe` runs
- No bypass of `services/recipe_costing.py` validation · no direct ORM writes from AI layer
- Service layer remains source of truth; AI adapter lives outside core (optional integration, not vendor-named in architecture)

**Out of scope for RC-AI-01:** auto menu pricing · inventory linkage · purchase integration · unattended batch generation.

---

## USER-ACCESS-01 — Implementation status

| Phase | Status | Deliverable |
|-------|--------|-------------|
| **UA-P1** | ✅ **Complete** | `UserPermissionOverride` model · `services/user_access.py` (`PERMISSION_REGISTRY`, `PERMISSION_TEMPLATES`, effective resolver, override CRUD, owner lockout guard) · `_can()` resolver swap · service/model tests · schema indexes |
| **UA-P1b** | 📋 **Pending** | Thin owner permission UI — per-user override checkboxes, effective-permissions viewer, audit trail display |

Spec: [USER_ACCESS_STAFF_CAPTURE_SPEC.md](./docs/USER_ACCESS_STAFF_CAPTURE_SPEC.md). Tech debt: [TECH_DEBT_AND_MIGRATION_CLEANUP.md](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md) (TD-UA-*).

**UA-P1 smoke audit (2026-06-13):**
- Owner compatibility passed
- Manager compatibility passed
- Viewer compatibility passed
- 0 permission regressions
- 0 hidden page regressions
- 0 access regressions
- `manage_permissions` is an intentional owner-only addition (not a regression)

---

## STAFF-CAPTURE-01 — Implementation status

| Phase | Status | Deliverable |
|-------|--------|-------------|
| **SC-P1** | ✅ **Complete** | `ExpenseDraft` · `DraftAttachment` · `services/staff_capture.py` (lifecycle, attachments, DTOs, injected `post_fn` approval) · SC permission keys in `services/user_access.py` · service/model/approval tests · schema indexes |
| **SC-P1b** | ✅ **Complete** | `ui/staff_capture.py` · `NAV_STAFF_EXPENSE_CAPTURE` · expense submit form · receipt upload · my submissions feed · approval inbox (expense only) · return/reject/approve · `app._staff_capture_post_expense_draft` posting seam · UI contract tests · EN/TR `sc.*` locales. **No portal gate.** |
| **SC-P2** | 📋 **Pending** | `sales_total_drafts` · `salary_drafts` · `cash_count_drafts` · inbox grows to three types |
| **SC-P3** | 📋 **Pending** | Returned-flow polish · staff submission feed · retention/archive job · OBS-01 review |

Spec: [USER_ACCESS_STAFF_CAPTURE_SPEC.md](./docs/USER_ACCESS_STAFF_CAPTURE_SPEC.md). Tech debt: [TECH_DEBT_AND_MIGRATION_CLEANUP.md](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md) (TD-SC-*).

Host `pytest tests/` — **1551 passed, 2 xfailed**.

---

## OBS-01 — Operational Friction Log

**Status:** Active (observation only — no implementation from this log alone)

**Purpose:** Every UX change must originate from **repeated real-world friction**, not speculation or audit findings alone. Use this log during daily bookkeeping to capture what actually slows work down.

**Gate:** Only issues experienced **3+ times** become roadmap candidates. Fewer occurrences stay in the log until the pattern repeats or is dismissed.

**How to use:**

1. After each friction moment, add a row (Screen · Task · Issue · Frequency · Impact).
2. Increment **Frequency** on repeat encounters (same screen + task + issue).
3. At **Frequency ≥ 3**, promote to a roadmap item (new `UX-*` / `OBS-*` candidate or elevation of an existing planned item) — still requires explicit approval before build.
4. Architecture-audit items (**UI-STAB**, **FUTURE UX**) inform technical debt but do **not** bypass this gate for user-facing UX changes.

| Screen | Task | Issue | Frequency | Impact |
|--------|------|-------|-----------|--------|
| *(add entries during daily use)* | | | | |

**Impact scale (suggested):** Low = annoyance · Medium = extra steps or errors recoverable · High = blocks daily workflow or risks bad data.

**Cross-references:**

| Related | Relationship |
|---------|--------------|
| **Current priority** | “Use the system daily” — this log is where observations land |
| **UI-STAB** | Technical separation debt — not a substitute for friction evidence |
| **FUTURE UX** | Design vision — requires OBS-01 friction before implementation |

---

## SETUP & Onboarding phase

### SETUP-01 — Company Creation Wizard 🟡 **HIGH** (design approved)

**Goal:** Every new company starts with the correct accounting workflow from day one.

**Runs when:** First company created · additional company created · future branch/location/company created.

**Replaces:** 14D-G 3-step wizard (business type → accounting mode → modules on Company Settings only). SETUP-01 runs at **company creation** and sets banking defaults so owners never need Banking → Settings on day one.

**Tone:** “Help me set up my company correctly” — plain language, no unexplained jargon. Each question includes: simple question, options + explanations, what changes in the ERP, change later (yes/no + where).

| Step | Question (summary) | Maps to |
|------|-------------------|---------|
| **1** | Business type (Restaurant / Retail / Service / Other) | `setup.vertical_template` — defaults & reporting only; no posting change |
| **2** | Customer card sales: know bank immediately vs later from POS/statement | `banking.card_settlement_enabled` OFF vs ON (POS Settlement). **Not** Company Credit Card |
| **3** | Import/reconcile bank statements? | `banking.reconciliation_enabled` |
| **4** | Pay suppliers/expenses with company credit card (KK)? | `banking.company_card_enabled` — not customer POS |
| **5** | Track stock (food, beverages, supplies)? | `module.inventory.enabled` |
| **6** | Multi-currency? | `module.foreign_currency.enabled` / future FX prefs |
| **7** | Daily operations style (Relaxed / Balanced / Strict) | `policy.accounting_mode` + policy bundle |
| **8** | **Summary** — company name + all choices → user confirms → create company |

**Step 2 detail (locked):**

- **Option A — I know immediately** → Card settlement **OFF** → card sales go **directly to Bank**
- **Option B — I know later** → Card settlement **ON** → card sales go to **POS Settlement** first; Bank updated at settlement/match

**Step 8 summary fields:** Company name · Business type · POS Settlement · Statement import · Company credit card · Inventory · Multi-currency · Control level.

**Status:** Design approved · implementation not started.

---

### SETUP-02 — Company Settings Review 📋 **Medium**

**Add:** Settings → Company Profile → **Setup Summary**

Shows wizard choices; read-only review (and link to change paths). Complements SETUP-01.

**Status:** Planned.

---

### SETUP-03 — Configuration Health Check 📋 **Medium**

Advisory warnings only (no forced changes). Examples:

- POS settlement OFF but statement import enabled
- Multi-currency OFF but foreign-currency transactions detected
- Company credit card enabled but no card accounts configured

**Status:** Planned.

---

### BANK-03 — Wording update ✅ **Verified**

Rename user-facing **“Card Settlement”** → **“POS Settlement”** (settings toggle) and **“POS / Card Settlement”** (focused workflow chip).

Keep **“Card Sales Clearing”** for COA / account names only. Retire jargon: **card clearing**, **clearing sales**, **deposit clearing**, **BSI** in user-facing copy.

**Purpose:** Reduce confusion with Company Credit Card (KK).

**Status:** Verified 2026-06-05 after BANKING-UX-02 + UI-STAB-02 — locale sweep EN/TR; Banking page title uses `NAV_BANKING`; contract tests in `tests/test_bank03_wording.py`.

---

### BANKING-POS-WORKFLOW-01 — POS Settlement workflow UX ✅ **P1+P2 shipped**

**P1:** Demote Sales Revenue in Other Income match path; double-count + POS-deposit warnings (no posting block).

**P2:** Card Sale Deposit panel explainer + Banking Settings POS Settlement caption line.

**Not in scope (P3+):** Auto-preselect clearing sales, dashboard clearing balance, posting/matching changes. Deferred to [BANKING-UX-02](#banking-ux-02--pos-settlement-transparency).

---

### BANKING-UX-02 — POS Settlement Transparency ✅ **Complete**

**Status:** Complete  
**Priority:** High (shipped June 2026)

**Completed phases:**

| Phase | Deliverable |
|-------|-------------|
| **P1** | Settlement preview — amounts and warnings before post |
| **P1B** | Focused **POS / Card Settlement** entry on Banking (no import chrome) |
| **P2** | Card Sales Clearing (1150) visibility panel |
| **P3** | Unsettled card sales list with filters |
| **P4** | Match check — plain-language failure explanations |

**Reason (original):** User testing showed Card Sales Clearing works correctly in accounting, but users could not easily locate or understand it during **Banking → Match & Post**. Workflow visibility was weak; the goal was transparency, not accounting redesign.

**Current flow (correct, hard to see):**

```text
Sales Entry → Card Sales Clearing → Bank Deposit → POS Settlement Match → Bank
```

Users cannot easily see the middle stage (**Card Sales Clearing**): outstanding clearing balance, unsettled sales, or why a deposit can or cannot be matched.

**Ordering:** After [BANKING-POS-WORKFLOW-01](#banking-pos-workflow-01--pos-settlement-workflow-ux--p1p2-shipped). Before any new Banking feature development or Banking redesign.

**Unchanged by design:** Revenue recognition · `post_deposit_clearing_match` JE · matching algorithms · Card Sales Clearing account **1150**.

**Tests:** `tests/test_banking_ux02_p1.py` · `p1b` · `p2` · `p3` · `p4` (79 tests). See [docs/COMPLETED_FEATURES.md](./docs/COMPLETED_FEATURES.md).

---

#### Phase P1 — Settlement Match Preview ✅

**Where:** Banking → Statement Import → Match & Post → Card Sale Deposit / POS Settlement

**Show:**

- Number of unsettled card sales
- Gross sales waiting for settlement
- Bank deposit amount
- Estimated / actual POS fee
- Clear explanation: *"This clears Card Sales Clearing and moves money into Bank. It does not create new Sales Revenue."*

**Target outcome:** Users understand exactly what **Confirm & Post** will do before posting.

---

#### Phase P2 — Card Sales Clearing Visibility ✅

Add visible **Card Sales Clearing** balance.

**Possible locations:** Dashboard **or** Banking → Accounts & Transactions

**Show:**

```text
Card Sales Clearing
TRY X waiting settlement
```

**Optional action:** View unsettled card sales

---

#### Phase P3 — Unsettled Card Sales List ✅

Drill-down list:

| Column | |
|--------|---|
| Date | |
| Reference | |
| Amount | |
| Settlement status | |

**Totals:** Waiting Settlement = X

**Purpose:** Users can identify what remains unmatched.

---

#### Phase P4 — Match Failure Explanation ✅

When **Confirm & Post** is unavailable, replace vague messaging with:

- **"No unsettled card sales found."**
- Explain: current Card Sales Clearing balance, candidate count, date-window mismatch if applicable

**Purpose:** Help users understand why settlement matching is unavailable.

---

**Dependencies:** No accounting changes required.

**Do not modify:**

- `post_card_sale`
- `post_deposit_clearing_match`
- Matching algorithms
- Database models

**Scope:** UX and visibility only.

---

### BANKING-UX-03 — Reconciliation Cockpit & Queue

**Status:** P1–P2 shipped · P3 future  
**Plan:** [docs/BANKING_UX_03_ROADMAP.md](./docs/BANKING_UX_03_ROADMAP.md)

Shipped: error UX hardening · confidence chips · fragment-scoped match queue · reconciliation cockpit · batch post · configuration surface (A/B/C) · tie-out/unpost polish.

**Constraints (unchanged):** No accounting changes · no posting kernel changes · `reconciliation/match_post.py` orchestration preserved · batch = N single posts.

**Next:** P3.x mobile oversight · learned match memory · reconciliation audit trail · React-readiness prep (post-FastAPI).

---

### BANKING-UX-04 — Configurable Banking Workflow

**Status:** ✅ **Complete** — S1 audit ✅ · S2 workflow mode + UI routing ✅ · S3 Add Transaction paths ✅ · S4 React contract ✅  
**Priority:** Medium — after BANKING-UX-03 P3 or alongside registry settings expansion  
**Principle:** [Configurable ERP Philosophy](#8-configurable-erp-philosophy) · [BANKING_UX_03 § P2.3](./docs/BANKING_UX_03_ROADMAP.md) · [BANKING_UX_04_AUDIT](./docs/BANKING_UX_04_AUDIT.md)

**Goal:** Let each company choose how bank activity enters the system — without removing any workflow.

**S2 delivered:** `banking.workflow_mode` in `registry/settings_catalog.py`; `banking_workflow_mode()` getter; `render_banking` section order/landing/Advanced panel via `ui/banking.py` helpers. Tests: `tests/test_banking_ux_04_s2_workflow_mode_routing.py`. Tag: `banking-ux-04-s2-workflow-mode-routing`.

**S3 delivered:** Add Transaction bank-path routing via `ui/banking.py` helpers (`at_primary_type_indices`, statement callout, Advanced manual bank type, manual-first landing). Tests: `tests/test_banking_ux_04_s3_add_transaction_bank_paths.py`. Tag: `banking-ux-04-s3-add-transaction-bank-paths`.

**S4 delivered:** React workflow contract frozen in `registry/banking_workflow_contract.py` + `docs/BANKING_UX_04_REACT_WORKFLOW_CONTRACT.md`. Epic matrix: `tests/test_banking_ux_04_epic_matrix.py`. Tag: `banking-ux-04-s4-react-workflow-contract`. **BANKING-UX-04 epic complete.**

#### Modes

| Mode | Workflow | UX emphasis |
|------|----------|-------------|
| **1. Statement-first** (recommended) | Import → Match → Post → Reconcile | Manual bank entry hidden under **Advanced** |
| **2. Hybrid** | Both workflows available | Default landing configurable (registry) |
| **3. Manual-first** | Traditional bookkeeping | Direct bank transaction entry prominent |

#### Rules (locked)

- Do **not** remove manual bank transactions.
- Prevent duplicate posting (existing idempotency guards + UI warnings).
- Imported statements are **preferred**, not mandatory.
- Manual entries remain available in all modes (visibility varies).

**Implementation gate:** Registry setting `banking.workflow_mode` (company-scoped); no schema change required. UI-only visibility routing in `ui/banking.py` + Add Transaction bank paths. Tests: mode switch does not alter posting contracts.

**Do not modify:** `services/posting.py` · `reconciliation/match_post.py` · GL line tuples.

---

### DATE CONTROL — Future React UX

**Status:** 📋 Future (React / DS-6) — spec locked; Streamlit DATE-01 remains interim  
**Principle:** [Date Ownership Standard](#6-date-ownership-standard) · [ERP_DS_04 §12](./docs/ERP_DS_04_MASTER_DESIGN_SYSTEM.md)

**Goal:** One date control pattern across desktop and mobile — no separate calendar button.

| Behavior | Spec |
|----------|------|
| Field | Single editable date text field |
| Open calendar | Click or focus on field opens picker |
| Desktop | Dropdown calendar anchored to field |
| Mobile | Bottom-sheet calendar (same component family) |
| Submit | Date captured at submit time; never overwritten by "today" on rerun |

**Streamlit interim:** DATE-01 mobile date sheet + desktop `at_date` ownership pipeline — behaviorally aligned, visually different until React.

**React component:** `DateField` in DS-4 / DS-5 — maps to `/transactions/new` and all date-bar surfaces.

---

## Phase map (high level)

```mermaid
flowchart LR
    subgraph done [Done]
        P1[Phases 1-13 Core ERP]
        P14[14A-14D-D Multi-company + creation]
        P14E[14D-E Members]
        P14F[14D-F Roster]
        P14G[14D-G Setup wizard]
    end
    subgraph later [Later]
        P15[15 Localization]
        P16[16 UI audit]
        P17[17 Foreign currency]
        P18[18 Bank/CC import]
        P19[19 VAT]
        P20[20 Inventory depth]
        P21[21 PostgreSQL/SaaS]
        P22[22 Billing]
        P23[23 Email invites]
        P24[24 Industry modules]
    end
    done --> P15
```

---

## ✅ Completed phases

### Phases 1–13 — Core ERP

Dashboard, sales, expenses, purchases, customers, vendors, banking, AR/AP, reports, GL, trial balance, P&L, balance sheet, cash flow, attachments, audit log, fiscal/year-end close, partners, profit allocation, cash reconciliation, EOD close, recurring expenses, backup/restore, opening balances.

### Phase 14A — Multi-company foundation

`Company`, `CompanyUser`, `CompanySetting`; `company_id` on business tables; default `company_1`.

### Phase 14B — Company context

Login → company picker; `active_company_id`, `active_company_role`, `active_company_name`.

### Phase 14C — Data isolation

`cq(session, Model)`; auto-stamp on flush; isolation tests.

### Phase 14D-A — Company model

`full_name`, `email`, `phone`, `created_by_user_id`; `CompanyUser.invited_by_id`.

### Phase 14D-B — Company settings isolation

`load_settings()` / `save_settings()` company-scoped; legacy `AppSetting` for global/user prefs only.

### Phase 14D-B2a — Registry foundation ✅ *just completed*

**Delivered:**

| Item | Location |
|------|----------|
| Settings catalog (keys, scope, type, lock metadata) | `registry/settings_catalog.py` |
| Module catalog (ids, nav mapping, planned flags) | `registry/modules_catalog.py` |
| Accounting mode bundles (stub) | `registry/accounting_mode_bundles.py` |
| Loader + validation | `registry/loader.py` |
| Read helpers | `registry/service.py` — `get_setting`, `get_effective_config`, `get_module_state`, `evaluate_lock` |
| Startup validation | `app.py` imports `validate_on_load()` |
| Tests | `tests/test_phase14b2_registry.py` (+16 tests) |

**Explicitly NOT in B2a:**

- Workspace / favorites UI  
- Policy enforcement in posting  
- `set_setting()` writes through registry  
- Industry presets  
- Subscription entitlements  
- `company_module` database tables  

### Phase 14D-B2b — Setting lock enforcement ✅

| Item | Location |
|------|----------|
| Milestones | `get_company_milestones()` — `first_posted_at` from min `JournalEntry.entry_date` |
| Guarded writes | `set_setting(..., check_locks=True)`, `save_company_settings_batch()` |
| Lock errors | `SettingLockError` + EN/TR `registry.lock.*` messages |
| Company Settings UI | `render_company_settings` — batch save; block on currency, warn is advisory only |
| Tests | `tests/test_phase14b2_registry.py` (milestones, block, warn+confirm) |

### Phase 14D-C — COA per company ✅

| Item | Location |
|------|----------|
| Per-company COA seed | `registry/coa_seed.py` |
| Per-company categories | `registry/categories_seed.py` |
| Startup backfill for company_1 | `_ensure_company_1_provisioned()` |
| Tests | `tests/test_phase14c_coa_per_company.py` |

### Phase 14D-D — Company creation ✅

| Item | Location |
|------|----------|
| `create_company()` | `registry/company_provision.py` |
| Picker UI | “Create a new company” expander on company picker (auto-opens when user has no company) |
| Header shortcut | Profile menu → **Create company** (any signed-in user) |
| Zero-membership login | Allowed; picker shows create-first-company flow; new company auto-activates |
| Tests | `tests/test_phase14d_company_creation.py` |

### UX pass ✅

- Sidebar menu uses **company role** (`active_company_role`)  
- **Company Setup** page: Profile + Money & books + Expert stub  

---

## 🔜 Phase 14D — Company management (remaining)

### 14D-E — Member management ✅ **DONE**

**Goal:** Owner manages `CompanyUser` for active company.

**Delivered:** Administration → **👤 Members** (and Company Settings section): add existing user, create user + add, change role, deactivate/reactivate, remove from company; per-company last-owner guard; audit log entries; `registry/company_members.py` helpers.

**Roles:** owner, manager, partner, cashier, viewer.

**Rules:**

- **`CompanyUser.role`** only for access — not `User.role`  
- **Last owner guard** — cannot remove/deactivate/demote last active owner  
- Option A invites only (no email tokens yet)

---

### 14D-F — Member roster polish ✅ **DONE**

**Delivered:** Members page **Roster** tab (search, role/status filters, paginated table, Excel/PDF export); role badge counts in company overview; last login, invited by, member since columns; **Company Setup** and legacy Settings team overview; **Add & manage** tab for 14D-E actions.

### 14D-G — Setup wizard v1 ✅ **DONE** *(legacy — see SETUP-01)*

**Delivered:** 3-step wizard on **Company Setup** — business type → accounting mode → optional modules. Writes registry defaults to `CompanySetting` (vertical, mode, policy bundle, module toggles, `setup.wizard_completed`). Module prefs affect `get_module_state` (e.g. inventory off). Policy enforcement still deferred.

**Gap:** No banking/POS questions at company creation; owners must discover **Banking → Settings** separately — caused inconsistent per-company config (e.g. settlement ON vs OFF). **SETUP-01** (design approved) addresses this.

---

## Phase 15 — Localization (EN / TR) — ✅ **Complete**

**15a — Shell ✅:** Login, picker, header, sidebar nav, Company Setup, Members, wizard.

**15b — Daily ops ✅:** `_st_page_title()` on all `st.title` pages; **Home** dashboard banner/KPIs; **Sales** and **Expenses** forms/filters; **Add Transaction** header. Strings in `registry/locales/transactional.py`.

**15c — CRM slice ✅:** **Vendors**, **Purchases**, **Customers** — forms, filters, void flow, statements, manage rows. Shared `form.*` keys; `PURCHASE_TYPE_I18N` / `PURCHASE_GL_I18N`.

**15d — AR/AP + Banking ✅:** **Payables**, **Receivables**, **Banking** — forms, filters, KPIs, payments, void, CSV import header.

**15e — Reports & GL ✅:** **Reports** hub (exec + management tabs), **General Ledger**, **Trial Balance**, **P&L** / **Today's Summary** banners, sidebar date range, aging buckets, cash recon shell, shared table column headers (`_localize_df`).

**15f — Financial close ✅:** **Balance Sheet**, **Cash Flow**, full **Cash Reconciliation** (4 tabs), **End-of-Day Close**, management-report KPI labels, export popover (Excel/CSV/PDF title).

**15g — Export copy & remaining KPIs ✅:** Export section labels in P&L / BS / CF exports; EOD history detail metrics; fiscal period KPI labels; management-report growth captions and empty-state messages; `_DF_COL_I18N` extended with 8 new column headers.

**15h — Broad coverage ✅:** All major pages localized — Year-End Close, Fiscal Periods, Audit Log, Partners/Equity, Opening Balances, Add Transaction, Transaction History, Journal Entries, Recurring Expenses, Customer Ledger, Inventory, COA, Budget, Categories, Administration, Backup & Restore, My Account. ~185 new EN+TR key pairs across 18 namespaces (`yec`, `fiscal`, `audit`, `partner`, `ob`, `txn`, `je`, `recurring`, `ledger`, `inv`, `coa`, `budget`, `rpt`, `cat`, `admin`, `backup`, `myaccount`, `form` common).

**15i — Cleanup pass ✅:** A follow-up audit found ~70 hardcoded strings still slipping through in less-trafficked code paths (the earlier "0 remaining" claim was premature). Localized: attachment list/upload form, year-end-close validation success/error/warning messages and acknowledgements, Fiscal Periods action buttons & confirm warnings, Equity Movements (new-movement expander, current-account/advance labels & warnings), Add-Transaction inline errors + supplier-payment payable guards + currency/FX/notes/save-button copy, Transaction History row-button tooltips + full detail panel field labels + edit panel, Journal Entries manual-entry section, COA balance summary, Sales/Expense void sections, recurring drafts/notes, bank CSV preview/import, category & subcategory inline help/placeholders, Advanced admin expander titles + migration/flag labels, Backup & cloud-sync copy, My Account password button, and the header search box + notifications popover. **130 new EN+TR key pairs (1221 keys each side, full parity); 0 known hardcoded user-facing strings remaining. 245 tests passing (incl. 2 new 15i tests).**

---

## Phase 16 — UI / theme audit

Complete dark mode, readability, header/sidebar polish, mobile pass.  
**Plan:** [PHASE_16_AUDIT.md](./PHASE_16_AUDIT.md)

### Phase 16A — Foundation ✅

| Item | Location |
|------|----------|
| Global CSS extracted | `ui/theme.css` |
| Tokens + bootstrap | `ui/theme.py` — `bootstrap_theme()`, DB theme on each `main()` |
| Section header helper | `ui/section.py` |
| Streamlit baseline | `.streamlit/config.toml` |
| Page audit matrix | `PHASE_16_AUDIT.md` |
| Tests | `tests/test_phase16a_theme.py` |

### Phase 16B — Native widgets ✅

| Item | Location |
|------|----------|
| Widget dark/light CSS | `ui/widgets.css` (inputs, select, tabs, expander, forms, alerts, metrics, `border=True` containers) |
| Streamlit version pin | `requirements.txt` — `>=1.28,<2` |

### Phase 16C — Page sweep ✅

| Item | Location |
|------|----------|
| Page banners → `section_header_html()` | 18 blocks (audit, txn history, partner, equity, opening balances, advanced, recon, EOD, reports, members, wizard, company setup, settings) |
| Muted/section text → `var(--theme-muted)`; dark text → `var(--theme-text)` | section helpers, captions, txn party names, audit/JE diffs, neutral KPI values |

### Phase 16D — Header + responsive ✅

| Item | Location |
|------|----------|
| Header `📊 Accounting ERP · {company} · {user}` w/ truncation | `render_top_header`, `ui/theme.css` |
| Responsive KPI grid (1 col ≤640px) + mobile sidebar drawer (≤768px overlay) | `ui/theme.css` |

### Phase 16E — Pastel banners + QA ✅

| Item | Location |
|------|----------|
| Aging chips, P&L / cash-flow / balance-sheet headers, badges, Budget Styler → `color-mix` theme tints | `app.py` |
| Tests (responsive, header, no-hardcoded-pastel guards) | `tests/test_phase16a_theme.py` |

**Phase 16 complete.** Full suite green (274 tests). Remaining decorative hex (status dots, white-on-color pills, `#9ca3af` footnotes) intentionally kept. EN/TR × light/dark screenshot pass + a real ≤768px device check recommended before release.

---

## AD-UI-001 — Sidebar & navigation redesign *(Option D — phased)*

**Status:** **Phase D1 complete** (2026-06-05). **Priority: High.** D2+ not started.

**D1 delivered:**

- Top-level **Financial Statements** nav (desktop accordion + mobile Reports/More hubs).
- Thin routes: `render_profit_loss_page`, `render_balance_sheet_page`, `render_cash_flow_page` → unchanged calculators.
- Reports Executive no longer lists P&L / BS / CF.
- Legacy Executive deep-links redirect; date filters on statement pages match Reports.
- Tests: `tests/test_nav_statements_d1.py`.

**D2+ (gated):** Executive rename, TB/GL/Budget dedup, Transaction History sidebar move, Reports tab rework.

**Explicitly out of scope (all phases):** GL posting rules, AD-001–AD-015 accounting behavior, new report renderers.

**Future direction (not D2+ — see below):** Full mobile shell, bottom-nav, More Hub, and compact sidebar modernization are recorded under **[FUTURE UX / NAVIGATION VISION](#future-ux--navigation-vision)**. AD-UI-001 D2+ remains incremental route/tab cleanup; it is **not** a rebuild of mobile chrome or the More menu.

**Reference:** [NAVIGATION_AUDIT.md](./docs/NAVIGATION_AUDIT.md) §16 (D1), §2–6 (pre-audit).

---

## NAV-ARCH — Navigation Single Source of Truth

**Status:** ✅ **Complete — S0–S4**  
**Priority:** After PostgreSQL parity, before React migration  
**Blocker:** None  
**Depends on:**

- **NAV-UX-02** (S1–S7) ✅ structural contracts shipped
- **PostgreSQL build + dual-run parity** ✅

**Purpose:** Eliminate navigation drift by deriving all navigation structures from one registry while preserving current behavior.

**Audit:** [NAV_ARCH_AUDIT.md](./docs/NAV_ARCH_AUDIT.md) · **React contract:** [NAV_ARCH_REACT_ROUTE_CONTRACT.md](./docs/NAV_ARCH_REACT_ROUTE_CONTRACT.md) · **Tests:** `tests/test_nav_arch_audit.py`, `tests/test_nav_arch_s4_react_route_contract.py`

**Problem:** Current navigation uses seven parallel structures:

- `registry/nav_keys.py`
- `_NAV_ACCORDION`
- `_NAV_DIRECT_PAGES`
- `_NAV_ROLE_PAGES`
- `_MOBILE_BOTTOM_NAV`
- `_MOBILE_HUB_CONFIG`
- `_PAGE_DISPATCH`

Current parity tests mitigate drift, but architecture still relies on hand-synced lists.

**Hard rules:**

- No duplicate fixes.
- Build on **NAV-UX-02**; do not re-open completed slices.
- No business logic in navigation.
- Navigation remains UI-independent and FastAPI/React-ready.
- Render functions stay thin.
- React routes become the long-term contract.
- **Navigation must eventually derive from one registry** (`registry/navigation.py`).

**Slices:**

| Slice | Scope | Status |
|-------|--------|--------|
| **NAV-ARCH-S0 — Guardrails** | No new navigation structures without registry plan | ✅ Active |
| **NAV-ARCH-S1 — Audit + parity guardrails** | `docs/NAV_ARCH_AUDIT.md` + `tests/test_nav_arch_audit.py`; `KNOWN_HIDDEN` allow-list; no runtime change | ✅ **Complete** |
| **NAV-ARCH-S2 — Introduce `registry/navigation.py`** | Per-page metadata; **derive `_PAGE_DISPATCH` only** | ✅ **Complete** |
| **NAV-ARCH-S3A — Desktop derived** | Derive `_NAV_ACCORDION` + `_NAV_DIRECT_PAGES` from registry | ✅ **Complete** |
| **NAV-ARCH-S3B — Role derived** | Derive `_NAV_ROLE_PAGES` from registry | ✅ **Complete** |
| **NAV-ARCH-S3C — Mobile derived** | Derive `_MOBILE_BOTTOM_NAV` + `_MOBILE_HUB_CONFIG` from registry | ✅ **Complete** |
| **NAV-ARCH-S4 — Freeze React route contract** | `docs/NAV_ARCH_REACT_ROUTE_CONTRACT.md`; `react_route` migration contract | ✅ **Complete** |

**Success criteria:**

- Single source of truth for navigation.
- No route drift.
- No duplicate route definitions.
- React migration consumes the same registry.

**Note:** This is **not** a PostgreSQL blocker and should not delay production cutover. It is a **pre-React** architecture improvement.

---

## UI-SYSTEM-02 — ERP-Wide UI & Theme Modernization

**Status:** 🟡 **In progress — S3 complete**  
**Priority:** High — after NAV-ARCH, before Banking UX  
**Blocker:** None  
**Depends on:**

- **NAV-ARCH** ✅ S0–S4 complete
- **MOBILE-14** ✅ closed (ownership baseline)
- **CSS-01 / CSS-02** approved ownership standard

**Purpose:** Prepare a unified professional SaaS look across desktop and mobile; one ERP feel; React migration-ready design contract. **No rainbow accents**; restrained slate + blue primary.

**Audit:** [UI_SYSTEM_02_AUDIT.md](./docs/UI_SYSTEM_02_AUDIT.md) · **Tests:** `tests/test_ui_system_02_audit.py` (+ existing UI/theme/nav contract tests)

**Hard rules:**

- No accounting, database, or business-logic changes.
- No navigation route changes in S1–S2.
- No sidebar visual redesign until **S3**.
- No broad CSS rewrite without a scoped slice.
- Audit first; implement in S2–S5 only.
- CSS-02 remains the ongoing ownership law.

**Slices:**

| Slice | Scope | Status |
|-------|--------|--------|
| **UI-SYSTEM-02-S0 — Guardrails** | Audit-only; CSS-02; no parallel theme systems | ✅ Active |
| **UI-SYSTEM-02-S1 — Audit + guardrails** | `docs/UI_SYSTEM_02_AUDIT.md` + `tests/test_ui_system_02_audit.py`; no runtime change | ✅ **Complete** |
| **UI-SYSTEM-02-S2 — Design token registry** | Centralize colour/spacing/radius/shadow/typography; resolve `--hdr-h` mobile conflict; deprecate stale role hues | ✅ **Complete** |
| **UI-SYSTEM-02-S3 — Sidebar modernization** | Visual grouping/spacing/icons only; derive presentation from registry; **no route moves** | ✅ **Complete** |
| **UI-SYSTEM-02-S4 — Unified shell/component pass** | Dead report-filters CSS; expense-bar inline width; KPI grid single owner (`mobile_components.css`); mob-space aliases | ✅ **Complete** |
| **UI-SYSTEM-02-S5 — Theme governance / React design contract** | `docs/UI_SYSTEM_02_REACT_DESIGN_CONTRACT.md` + `ui/react_design_contract.py`; component prop map; Streamlit selector retirement | ✅ **Complete** |

**Success criteria:**

- Single token registry consumed by CSS and charts.
- Desktop and mobile share one component language.
- Sidebar visually modern without route drift.
- React team can port `AppShell`, `SidebarNav`, `KpiGrid`, `ChipSelector` from documented contract.

**Next slice:** MONO-THEME-01 epic **complete** — DS-6 React build or next prioritized epic.

---

## MONO-THEME-01 — Option A+ Unified Mono ERP Theme

**Status:** ✅ **Complete** — S1–S7 (shared grammar + React contract export)  
**Priority:** High — after UI-SYSTEM-02 token foundation; before React DS-6 build  
**Depends on:** UI-SYSTEM-02-S2 (`ui/design_tokens.py`) · MOBILE-UX-02 theme audits · UI-SYSTEM-02-S5 React contract

**User-approved direction (Option A+ Final Blend):** accounting-first shadcn-style spine · mono/neutral by default · one blue accent · dense accounting tables · rich dashboard only where meaningful · desktop and mobile feel like one ERP · no rainbow UI · color only when it carries meaning.

**Audit:** [MONO_THEME_01_AUDIT.md](./docs/MONO_THEME_01_AUDIT.md) · **Tests:** `tests/test_mono_theme_01_audit.py`, `tests/test_mono_theme_01_s2_shared_grammar_tokens.py`, `tests/test_mono_theme_01_s3_nav_active_grammar.py`, `tests/test_mono_theme_01_s4_desktop_card_grammar.py`, `tests/test_mono_theme_01_s5_mobile_card_grammar.py`, `tests/test_mono_theme_01_s6_table_status_grammar.py`, `tests/test_mono_theme_01_s7_react_contract_cleanup.py`

**Core finding:** Token foundation already matches Option A+. Problem is **duplicated component grammar** — desktop and mobile CSS style cards/nav/chips separately despite shared tokens.

**Hard rules:** No accounting/PostgreSQL/schema/routing/nav/posting changes · no new color system · no template copying · shadcn inspiration only · all semantic colors preserved (success/warning/danger/info, P&L, recon matched/review/mismatch, void).

| Slice | Scope | Status |
|-------|--------|--------|
| **MONO-THEME-01-S1** | Audit + design spec (this doc) | ✅ **Complete** |
| **MONO-THEME-01-S2** | Shared component-grammar tokens (`--erp-nav-*`, `--erp-card-*`, `--erp-chip-*`, `--erp-table-*`) | ✅ **Complete** |
| **MONO-THEME-01-S3** | Sidebar + mobile nav active grammar | ✅ **Complete** |
| **MONO-THEME-01-S4** | Desktop cards, dashboard, forms, buttons | ✅ **Complete** |
| **MONO-THEME-01-S5** | Mobile shell, cards, forms, lists | ✅ **Complete** |
| **MONO-THEME-01-S6** | Reports, tables, banking statuses | ✅ **Complete** |
| **MONO-THEME-01-S7** | Cleanup + React contract update | ✅ **Complete** |

**Next slice:** MONO-THEME-02 epic **complete** — **FASTAPI-REACT-00** baseline audit (see [§ FASTAPI-REACT-00](#fastapi-react-00--migration-baseline-audit)).

---

## MONO-THEME-02 — Real UI Visual Refinement Pass

**Status:** ✅ **Complete** — S0 visual contract ✅ · S1 sidebar ✅ · S2 top bar ✅ · S3 dashboard/cards ✅ · S4 tables ✅ · S5 mobile parity ✅  
**Priority:** High — closes the gap between MONO-THEME-01 grammar tokens and live screenshot quality  
**Depends on:** MONO-THEME-01 complete · UI-SYSTEM-02 token foundation · user-approved screenshots

**Goal:** Make the actual desktop/mobile app match the approved Option A+ direction — **refined, denser, stronger hierarchy** — without redesign, new colors, or business-logic changes.

**Contract:** [MONO_THEME_02_VISUAL_CONTRACT.md](./docs/MONO_THEME_02_VISUAL_CONTRACT.md) · **Tests:** `tests/test_mono_theme_02_visual_contract.py`, `tests/test_mono_theme_02_epic_matrix.py`, slice tests S1–S5

**Hard rules:** No accounting/PostgreSQL/nav-route/business-logic changes · no new palette · existing `--erp-*` grammar tokens only · semantic colors immutable · CSS/layout only per slice.

| Slice | Scope | Status |
|-------|--------|--------|
| **MONO-THEME-02-S0** | Option A+ visual contract (audit only) | ✅ **Complete** |
| **MONO-THEME-02-S1** | Desktop sidebar only — active tint + accent bar, spacing rhythm | ✅ **Complete** |
| **MONO-THEME-02-S2** | Top bar — compact desktop header, search prominence | ✅ **Complete** |
| **MONO-THEME-02-S3** | Dashboard + cards — density, KPI grid, activity hierarchy | ✅ **Complete** |
| **MONO-THEME-02-S4** | Tables + lists — row density, hover, money alignment | ✅ **Complete** |
| **MONO-THEME-02-S5** | Mobile parity — bottom nav, KPI chips, hub sheets | ✅ **Complete** |

**Next slice:** MONO-THEME-02 epic **complete**.

---

## FASTAPI-REACT-00 — Migration Baseline Audit

**Status:** ✅ **Complete (audit only)** — baseline snapshot for FastAPI + React planning  
**Priority:** High — gates FASTAPI-REACT-01+ implementation slices  
**Depends on:** POSTING-SERVICE-01 extracted · FASTAPI-P0/P1/P2 partial · MONO-THEME-02 complete · UI/NAV React contracts frozen

**Goal:** Single authoritative audit of FastAPI foundation state, frozen React contracts, blockers, and phased slice plan — **no implementation**.

**Audit:** [FASTAPI_REACT_00_AUDIT.md](./docs/FASTAPI_REACT_00_AUDIT.md) · **Tests:** `tests/test_fastapi_react_00_audit.py`

**Hard rules:** No accounting changes · Streamlit remains primary · no React `package.json` bootstrap · no Docker file edits unless required · does **not** authorize production API cutover.

| Slice | Scope | Status |
|-------|--------|--------|
| **FASTAPI-REACT-00** | Baseline audit — FastAPI partial, React not started, contracts inventory | ✅ **Complete** |
| **FASTAPI-REACT-01** | PS-P7 posting boundary hardening | ✅ **Complete** |
| **FASTAPI-REACT-02** | API write hardening / explicit `company_id` | ✅ **Complete** |
| **FASTAPI-REACT-03** | Recon `_app()` removal + boundary readiness | ✅ **Complete** |
| **FASTAPI-REACT-04** | Read API stabilization + TD-PS-01 characterization | ✅ **Complete** |
| **FASTAPI-REACT-05** | React bootstrap (ThemeProvider + router shell) | ✅ **Complete** |
| **FASTAPI-REACT-06** | First React pages (Home + Ledger read-only) | ✅ **Complete** |
| **FASTAPI-REACT-07** | PG boundary matrix / TD-PS-01 characterization | ✅ **Complete** |
| **FASTAPI-REACT-08** | First React write page (cash sale) | ✅ **Complete** |
| **FASTAPI-REACT-09** | Expense write tab (New Transaction) | ✅ **Complete** |
| **FASTAPI-REACT-10** | Card/credit sale + bank expense | ✅ **Complete** |
| **FASTAPI-REACT-11** | Void write tab (New Transaction) | ✅ **Complete** |
| **FASTAPI-REACT-12** | Purchase write tab (New Transaction) | ✅ **Complete** |
| **FASTAPI-REACT-17** | Read expansion (balance sheet + AR/AP) | ✅ **Complete** |
| **FASTAPI-REACT-18** | Partner statement + banking readiness | ✅ **Complete** |
| **FASTAPI-REACT-19** | Reports hub + profit & loss read pages | ✅ **Complete** |
| **FASTAPI-REACT-20** | Cash flow + transaction ledger read pages | ✅ **Complete** |
| **FASTAPI-REACT-21** | COA + partner pickers | ✅ **Complete** |
| **FASTAPI-REACT-22** | Bank/worker/partner write pickers | ✅ **Complete** |
| **FASTAPI-REACT-23** | Reconcile/closing pickers + match-type forms | ✅ **Complete** |
| **FASTAPI-REACT-24** | Receivable sale + allocation pickers | ✅ **Complete** |
| **FASTAPI-REACT-25** | Chart of accounts + vendors read pages | ✅ **Complete** |
| **FASTAPI-REACT-26** | Sales + expenses read pages | ✅ **Complete** |
| **FASTAPI-REACT-27** | Workers read page | ✅ **Complete** |
| **FASTAPI-REACT-28** | Customers read page | ✅ **Complete** |
| **FASTAPI-REACT-29** | Purchases read page | ✅ **Complete** |
| **FASTAPI-REACT-30** | Bank accounts read page | ✅ **Complete** |
| **FASTAPI-REACT-31** | Fiscal periods read page | ✅ **Complete** |
| **FASTAPI-REACT-32** | Journal entries read page | ✅ **Complete** |
| **FASTAPI-REACT-33** | Trial balance read page | ✅ **Complete** |
| **FASTAPI-REACT-34** | Recon health read page | ✅ **Complete** |
| **FASTAPI-REACT-35** | Opening balances read page | ✅ **Complete** |
| **FASTAPI-REACT-36** | Audit log read page | ✅ **Complete** |
| **FASTAPI-REACT-37** | Company members read page | ✅ **Complete** |
| **FASTAPI-REACT-38** | Inventory read page | ✅ **Complete** |
| **FASTAPI-REACT-39** | Budget vs actual read page | ✅ **Complete** |
| **FASTAPI-REACT-40** | Permissions read page | ✅ **Complete** |
| **FASTAPI-REACT-41** | Company settings read page | ✅ **Complete** |
| **FASTAPI-REACT-42** | Backup & restore read page | ✅ **Complete** |
| **FASTAPI-REACT-43+** | React read page expansion or ops slices | 📋 Planned |

**Audit:** [FASTAPI_REACT_42_REACT_READ_BACKUP_RESTORE_AUDIT.md](./docs/FASTAPI_REACT_42_REACT_READ_BACKUP_RESTORE_AUDIT.md) · **Tests:** `tests/test_fastapi_react_42_react_read_backup_restore.py` · **Tag:** `fastapi-react-42-react-read-backup-restore`

**Next slice:** **FASTAPI-REACT-43** — production `COMMIT_MODE_*` flip or next NAV read placeholder; see FR-42 audit §7.

---

## FUTURE UX / NAVIGATION VISION

**Status:** Planned Future Work  
**Priority:** Low  
**Not approved for implementation.** Design direction only.

Record approved future-direction decisions so they are not forgotten. **No code, no screen redesign, no sprint** until explicitly approved.

**Cross-references (do not duplicate):**

| Existing roadmap item | Relationship |
|----------------------|--------------|
| **AD-UI-001** | D1 statement routes done; D2+ = incremental Reports/sidebar dedup — **not** this vision |
| **NAV-ARCH** | Pre-React navigation registry — deferred until PG parity; see [§ NAV-ARCH](#nav-arch--navigation-single-source-of-truth) |
| **Phase 18-MUX** | Mobile Add Transaction shipped; **current bottom nav unchanged** |
| **Phase 16D** | Header foundation (truncation, responsive) — **not** MOBILE-10 compact SaaS header |
| **SETUP-01 / SETUP-02 / SETUP-03** | Onboarding at company creation — separate from **DESIGN-05** progressive disclosure |
| **Module state vocabulary** | `Hidden` = nav preference — aligns with **MOBILE-07** (see below) |

### FUTURE UX PRINCIPLE

> The ERP should prioritize **speed of daily operation** over feature visibility. Frequently used functions should be immediately accessible. Advanced or rarely-used functions should remain available but not dominate the interface.

---

### MOBILE-07 — Customizable More Hub

**Status:** Planned

**Goal:** Allow each company to choose which modules appear inside the **More** section.

This hides navigation only. It does **not** disable functionality. Users can restore hidden modules later.

**Examples:**

| Company | Visible in More | Hidden (restorable) |
|---------|-----------------|---------------------|
| Restaurant A | Banking, Reports, Receivables, Payables | Inventory, Assets, CRM, Projects |
| Restaurant B | Inventory, Purchasing, Banking | Receivables, CRM |

**Requirements:**

- Company-specific  
- Permission-aware  
- Reversible  
- Navigation visibility only  
- No accounting impact  

**Explicitly:** This is **not** user-role security. This is **UI simplification** (same idea as registry `Hidden` module state — see [Module state vocabulary](#module-state-vocabulary-frozen)).

---

### MOBILE-08 — Organized More Hub

**Status:** Planned

**Goal:** Replace long flat menu lists with **grouped sections**.

**Future structure example (illustrative only):**

| Section | Items |
|---------|--------|
| **Banking** | *(section header)* |
| **Inventory** | Products · Stock · Adjustments |
| **Accounting** | Receivables · Payables · Ledger · Journal |
| **Reports** | P&L · Balance Sheet · Cash Flow |
| **Administration** | Users · Roles · Settings |

**Do not implement now.** Future navigation cleanup project.

---

### DESIGN-05 — Progressive Disclosure

**Status:** Planned

**Principle:** New users should only see functionality required for **daily operation**. Advanced features appear when needed or enabled.

**Example — new restaurant owner (illustrative):**

| Primary chrome | Under More |
|----------------|------------|
| Home · Add · Cashflow · Ledger · More | Banking · Reports · Settings |

**Advanced areas remain hidden until enabled or required:** Inventory · Assets · Projects · CRM · Advanced analytics

**Goal:** Reduce overwhelm; keep first-day experience simple.

*Complements SETUP-01 (correct defaults at create) but applies ongoing nav/module visibility — not a replacement for onboarding wizard.*

---

### MOBILE-09 — Future Mobile Navigation Vision

**Status:** Concept approved · **not approved for implementation**

**Current navigation remains unchanged.**

**Future evaluation candidates (do not choose one yet):**

| Option A | Option B |
|----------|----------|
| Home · Add · Cashflow · Ledger · More | Home · Banking · Add · Reports · More |

**Reason:** Daily-use functions belong in primary navigation; rarely-used functions belong under More.

---

### MOBILE-10 — Mobile Header Modernization

**Status:** Planned · user preference recorded

**Future direction:** Replace oversized profile blocks and large identity cards. Move toward a **compact professional header**.

**Desired characteristics:**

- Compact company switcher  
- Compact notification button  
- Real profile avatar / photo / icon  
- Avoid large single-letter profile circles  
- Reduce vertical space usage  
- Maximize workspace  

**Reference style:** Modern SaaS mobile applications.

**Not implementation-ready.** Design direction only. *(Phase 16D delivered truncation/responsive foundation; this is a later polish pass.)*

**Prerequisite (architecture, not redesign):** **[UI-STAB-01](#ui-stab-01--header-architecture-consolidation)** — header CSS/sizing consolidation. Trigger only after compact mobile header visuals are approved.

---

### PROFILE-PHOTO-01 — Profile Photo / Avatar

**Status:** Proposed  
**Priority:** Low  
**Not approved for implementation.**

**Purpose:** Allow users to upload and display a profile photo/avatar instead of initials.

**Requirements:**

- Upload profile image (My Account → Profile tab)
- Store avatar path/reference on `User` (e.g. `avatar_path` column + file under company/user-scoped storage)
- Show avatar in header profile popover/sheet and My Account profile card
- Fallback to initials when no image exists (`erp-mono-avatar`, `erp-hdr-profile-avatar`)
- EN/TR labels (`account.profile_photo`, upload/remove/success/error keys)
- Permissions: self-service only (current user edits own avatar; no owner directory management)
- Desktop + mobile: `_render_hdr_profile_panel_content`, mobile profile sheet, login user tiles

**Non-goals:**

- Social-login avatars
- External image URLs
- User directory / admin avatar management

**Current state (June 2026):**

- `User` model has no `avatar_path` field
- `render_my_account` shows initials + `account.photo_coming` (“Upload coming in a future release”)
- Header/mobile profile use initials HTML in three places (not a single helper yet)
- [UI-STAB-01](#ui-stab-01--header-architecture-consolidation) calls for single avatar renderer — implement together or immediately before

**Suggested implementation sketch (when approved):**

1. Schema: `users.avatar_path` via `migrate_schema()`; store files under e.g. `data/avatars/{user_id}/`
2. `registry/avatar.py`: save/delete/resolve URL, validate MIME/size, initials fallback HTML helper
3. My Account Profile: `st.file_uploader` + remove button; audit log optional
4. Replace inline initials in header, mobile sheet, login tiles with shared `_user_avatar_html(user)`
5. Tests: upload round-trip, fallback, permission (cannot set another user's path), no posting changes

**Reason:** UX enhancement only. No accounting impact.

**Cross-reference:** [AUDIT_HISTORY.md](./docs/AUDIT_HISTORY.md) (mono-sweep-3 — photo was never implemented; not a regression).

---

### DESKTOP-04 — Sidebar Modernization

**Status:** Planned · user preference recorded

**Future direction:** Compact **icon-first** navigation.

**Characteristics:**

- Smaller visual footprint  
- Clear active state  
- Better hierarchy  
- Reduced clutter  
- Modern SaaS appearance  

**Important:** This is **not** a rebuild request. Preserve design intent for future UX work. *(AD-UI-001 D2+ may adjust routes/labels; DESKTOP-04 is visual/IA modernization.)*

---

### Do NOT start (explicit)

Until a separate architecture / UX approval:

- Banking redesign  
- Reports redesign  
- Mobile shell redesign  
- Navigation redesign  
- More Hub redesign  
- Sidebar redesign  

These remain **future projects**. Current focus stays on accounting stability, daily-use testing, banking observation, UX cleanup (e.g. i18n/trust fixes), and real-world usage feedback.

**Related (stability, not redesign):** **[UI-STAB](#ui-stab--ui-architecture-stability)** records audit findings for presentation separation and CSS cleanup — distinct from MOBILE-10 / DESKTOP-04 visual modernization.

---

## UI-STAB — UI Architecture Stability

**Status:** Planned  
**Not approved for implementation.**

**Purpose:** Preserve findings from the Desktop/Mobile Architecture Audit so future UI work is based on known technical debt rather than rediscovery.

**Cross-references (do not duplicate):**

| Existing item | Relationship |
|---------------|--------------|
| **Phase 16D** | Header foundation — **UI-STAB-01** consolidates distributed CSS on top of it |
| **MOBILE-10** | Compact mobile header polish — **UI-STAB-01** runs only after those visuals are approved |
| **18-MUX** | Add Transaction dual-host pattern — reference model for **UI-STAB-02** banking split |
| **AD-UI-001** | Route/sidebar dedup (D2+) — **UI-STAB-03** is nav *renderer* consolidation, not route redesign |
| **FUTURE UX** | MOBILE-07–10, DESIGN-05, DESKTOP-04 — redesign vision; UI-STAB is stability/separation first |

**Audit summary (June 2026):** Business logic separation is healthy (`_at_save`, posting, permissions, queries shared correctly). Presentation separation is partial — strongest on Transaction Ledger and Add Transaction; weakest on Banking and Notifications. CSS is globally injected with cascade conflicts (`--hdr-h` 60 / 120 / 56 / 86px) and unscoped rules leaking across viewports.

**Theme ownership follow-up (June 2026):** A complete Theme Ownership Audit was completed and recorded as **[CSS-01](#css-01--theme-ownership-consolidation)**. Finding: CSS conflicts are concentrated in `widgets.css`, `mobile_shell.css`, and `mobile_header.css` — not globally fragmented. **[MOBILE-14](#mobile-14--mobile-theme-ownership-cleanup)** is the approved execution plan. UI-STAB-05 findings are fully superseded by CSS-01 for the mobile CSS domain.

---

### UI-STAB-01 — Header Architecture Consolidation

**Priority:** High

**Avatar renderer (June 2026):** ✅ **Complete** — `ui/avatar.py` (`user_initials`, `render_user_avatar`, sizes sm/md/lg). All initials avatars (header profile, mobile sheet, My Account, login tiles) use one renderer and `.erp-user-avatar--*` CSS. Prepares for [PROFILE-PHOTO-01](#profile-photo-01--profile-photo--avatar) without schema changes.

**Remaining (header CSS — not started):**

- Header styling is distributed across `theme.css`, `mobile_shell.css`, and `mobile_header.css`.
- Multiple header-height definitions exist (`--hdr-h` conflicts across files and breakpoints).
- Header behavior has historically been difficult to change consistently.
- Dead toolbar slot branches (`primary` / `mobile_left`) in `_render_hdr_toolbar`; obsolete `hdr_mobile_title` popover CSS after company-switch sheet migration.

**Goals (remainder):**

- Single source of truth for header sizing.
- Single source of truth for toolbar spacing.
- Single source of truth for company selector styling.

**Constraints:** No redesign. Architecture cleanup only.

**Trigger:** Only after current mobile header visuals are approved (see [MOBILE-10](#mobile-10--mobile-header-modernization)).

---

### UI-STAB-02 — Banking Presentation Separation

**Status:** ✅ **Complete** (2026-06-05)

**Delivered:** `ui/banking.py` — chip selector, P1 settlement preview, P2 clearing visibility, P3 unsettled sales list, P4 match failure panel, P1B POS settlement entry + focused section. `app.py` keeps orchestration (`render_banking`, `_render_bsi_deposit_clearing`, statement import) and all posting.

**Unchanged:** Posting logic · settlement math · journal entries · account **1150** · BANKING-UX-02 behavior.

**Tests:** `tests/test_ui_stab02_banking.py` (contract tests) + existing `test_banking_ux02_*` / `test_banking_desktop_b1b2.py`.

**Future direction (not started):** Optional `render_banking_desktop()` / `render_banking_mobile()` dual-host presenters — same pattern as Transaction Ledger; business logic already separated.

---

### UI-STAB-03 — Navigation Architecture Consolidation

**Priority:** Medium

**Current findings:**

- Desktop and mobile use different navigation renderers (`_render_navigation_tree` in sidebar vs `_render_mobile_hub_sheet` + bottom bar) but share state (`nav_selection`) and duplicate navigation definitions.
- Sidebar nav tree still renders on mobile (widgets hidden via CSS).

**Future direction:**

- One navigation definition.
- Separate presenters: desktop presenter · mobile presenter.
- Shared navigation metadata.

**Goal:** Reduce duplication and maintenance cost.

---

### UI-STAB-04 — Notification Interaction Unification

**Priority:** Medium

**Current findings:**

- Mobile uses sheets for profile and company switch.
- Notifications still use `st.popover` on both mobile and desktop (`_render_hdr_toolbar`).

**Future direction:** Consistent mobile interaction model (e.g. notification sheet mirroring profile/co-switch pattern).

**Goal:** Reduce special cases.

---

### UI-STAB-05 — CSS Scope & Leakage Cleanup

**Priority:** Medium

**Current findings:**

- Mobile CSS affecting desktop (e.g. global `.erp-txh-pill` in `mobile_txn_history.css` styles desktop ledger rows).
- Desktop CSS affecting mobile (e.g. `theme.css` `@media (max-width:968px)` `--hdr-h: 120px` vs `mobile_header.css` `56px`).
- Global selectors influencing multiple screens; all stylesheets concatenated in `load_theme_css()` on every viewport.

**Future direction:**

- Host-scoped CSS (`:has(.erp-*-host)` pattern from TXH/AT).
- Viewport-scoped CSS (`html.erp-mobile` / `@media` used consistently with Python `_is_mobile_ui()`).
- Reduced global selector usage.

**Goal:** Predictable UI changes.

---

## Phase 17 — Foreign currency

Base currency + optional multi-currency; FX accounts; original amount + rate + base amount; exchange transactions; FX gain/loss. Do not hardcode TRY.

---

## Phase 18 — Bank / credit card statement reconciliation

Full design: [PHASE_18_DESIGN_REVIEW.md](../PHASE_18_DESIGN_REVIEW.md) (APPROVED blueprint — CSV/Excel first, zero auto-post, Needs Review queue, Card Sales Clearing architecture, 6 new tables, rule engine, sub-phases 18A–18G).

**Decisions locked (June 4, 2026):**

- **Confirm everything.** Nothing posts to the GL without an explicit per-line user confirmation. Suggestions are advisory only; a "confirm all suggested" shortcut still requires a deliberate click. (Reinforces the doc's zero-auto-post policy.)
- **Full provenance / 6-month traceability.** Imported statements land in a staging layer that keeps the **raw line forever** (statement file name, account, import date, who imported), linked forward to the `BankTransaction` / `JournalEntry` / `Payable` / `ExpenseRecord` it produced, plus who confirmed and when. From any posted transaction you can walk back to the originating statement line; every confirm/assign/fee action writes an `AuditLog` entry.
- **Outflows allow ad-hoc.** Assigning a statement debit to a vendor can either settle an existing open `Payable` **or** create an ad-hoc expense / supplier payment on the spot (for unexpected, non-routine costs) posted to that vendor's account.
- **Single "Bank Charges" expense account** (supersedes the doc's split "Card Processing Fees" vs "Bank Charges"). Both outgoing-transfer charges and card-deposit/settlement fees post to one Bank Charges account; when a matched total doesn't tie out, the shortfall is proposed as a Bank Charges line for confirmation.
- **Feature toggles — all OFF by default, so behaviour is identical to today until enabled:**
  - `banking.reconciliation_enabled` — the whole reconciliation/matching workspace.
  - `banking.company_card_enabled` — company-owned credit card as a payment source (purchases credit a Credit Card Payable liability; paying the bill = bank→card transfer).
  - `banking.bank_charges_enabled` — the fee/charge step (country-dependent; some countries have no such charges).
  - `banking.card_settlement_enabled` — **POS settlement** (user-facing label per BANK-03; GL account remains **Card Sales Clearing** 1150) + merchant settlement statement import; when off, card sales post directly to Bank as today. **SETUP-01** Step 2 sets this at company creation.

**Known drift to resolve during 18A/18E:** current code posts a Card sale **directly to Bank** (the doc's *rejected* alternative) via `post_card_sale` + an immediate `BankTransaction`. The approved architecture routes card sales through a **Card Sales Clearing** account and only moves to Bank at settlement — that change is what makes batched, net-of-fee settlement matching possible.

**Three import types (settlement statement added June 4, 2026):**

1. **Bank statement** — debits/credits; shows only the *net* deposit and usually hides fees.
2. **Credit card statement** — company-card charges (liability); gated by `banking.company_card_enabled`.
3. **Merchant settlement statement** *(preferred input for card-settlement recon; gated by `banking.card_settlement_enabled`)* — itemized per batch: **gross sales, processor fee, net deposited**. The fee is read directly from this statement (exact, not inferred), it reconciles the Card Sales Clearing account, and its net figure cross-checks against the bank statement's deposit line. Fallback when a processor provides no settlement statement: infer the fee as the clearing-vs-deposit difference for user confirmation. *(Capture real column layout from a user-provided sample before building — formats vary by processor.)*

**MVP build order (trimmed from the 18A–18G blueprint — deterministic, no ML/rules yet):**

- **18-MVP-1 — Clearing migration + toggles. ✅ (June 5, 2026)** Added `banking.*` settings (all OFF = today's behaviour); added **Card Sales Clearing** (1150) + **Bank Charges** (5800) accounts and an idempotent `ensure_phase18_accounts` startup backfill; when `banking.card_settlement_enabled` is on, card-sale posting routes to clearing (`DR Card Sales Clearing / CR Sales Revenue`, no bank deposit yet) — when off, card sales post directly to Bank as today; added `is_reconciled` / `statement_ref` / `charge_subtype` to `BankTransaction`. **Deviation from the doc's automatic one-time backfill:** historical card-sale treatment is now an explicit, user-chosen setting (`banking.card_sales_clearing_backfill` = `none` | `reclassify_to_clearing`) applied only via an owner/manager "Apply migration now" button — never automatic, guarded by a per-company `MigrationFlag`, idempotent, posting through `create_journal_entry`. Settlement → Bank + Bank Charges ← clearing lands in 18-MVP-4.
- **18-MVP-2 — Import to staging + provenance. ✅ (June 5, 2026)** `BankStatementImport` + `BankStatementRow` tables; raw file on disk under `uploads/statements/` + SHA-256; `raw_line_text` per row; CSV/Excel parse with column mapping UI in Advanced → Bank Statement Import (gated by `banking.reconciliation_enabled`); soft duplicate flags on composite key (date + amount + normalized description + balance); permissions `import_bank_statement` / `view_bank_statement_import`. **No GL posting** — matching/posting is MVP-3. CC/settlement import pipelines deferred.
- **18-MVP-3 — Manual match & post (deterministic). ✅ (June 5, 2026)** Step **③ Match & post** on Bank Statement Import; deposits match card sales in clearing (multi-select, amounts must tie); other deposits post DR Bank / CR user-selected account; withdrawals assign vendor + open `Payable` **or** ad-hoc expense; confirm-everything; posts via `create_journal_entry`; `BankTransaction.statement_ref=bsr:{row_id}`; row status → `posted`; `AuditLog` on each post. Bank charges / fee shortfalls deferred to 18-MVP-4.
- **18-MVP-4 — Bank charges + settlement statement. ✅ (June 5, 2026)** Merchant settlement import (`SettlementStatementImport` / `SettlementStatementRow`) with gross/fee/net column mapping under Upload expander (gated by `banking.card_settlement_enabled`); clearing match books **Bank Charges** when deposit &lt; clearing — exact fee from linked settlement batch or inferred difference with user confirmation (gated by `banking.bank_charges_enabled`); cross-check settlement gross↔clearing and net↔deposit; `BankTransaction.charge_subtype=card_settlement_fee`; provenance link `bank_statement_rows.settlement_row_id`.
- **18-MVP-5 — Company credit card (optional). ✅ (June 5, 2026)** `BankAccount.kind="credit_card"` for bank-like UX; **Credit Card Payable** (2110) GL; expenses/purchases/payable payments by card credit the liability when `banking.company_card_enabled`; bank-statement **KK ödeme** posts DR CC Payable / CR Bank via Match & post with card-account picker.
- **Deferred to post-MVP:** rule engine, fuzzy/ML suggestions, receipt auto-matching, PDF/OCR import, advanced report suite, multi-currency conversion (store original amount/currency now, leave base = original until Phase 17 FX).

**Engineering guardrails (accepted June 4, 2026):**

- **Clearing migration is the keystone** — do it first (18-MVP-1); without it, batched settlement matching is impossible. Includes a one-time backfill of card sales currently posted straight to Bank.
- **Deterministic matching only at MVP** — group unsettled clearing entries inside the deposit's date window and let the user multi-select; no fuzzy/ML matching yet.
- **Handle refunds / chargebacks** — settlement and statement lines can be negative; the matcher and sum-checks must not assume positive-only amounts.
- **Single Bank Charges GL account, with a charge-subtype tag** (`transfer_fee` / `card_settlement_fee` / `monthly_fee`) for reporting without extra accounts.
- **Duplicate detection is soft, not a hard constraint** — composite key (date + amount + normalized description + running balance) with a "possible duplicate, confirm?" review, so legitimate repeated payments (e.g. identical monthly rent) aren't rejected. Don't depend on `bank_reference` (many CSVs lack it).
- **Provenance = real file, not just metadata** — store uploaded file bytes + SHA-256, keep every raw statement line forever, and surface a **"Source"** link on each transaction's detail panel back to its originating line.
- **Add `is_reconciled` / `statement_ref` to `BankTransaction`** so *existing* rows (e.g. card-sale deposits) can be matched, not only newly imported ones.
- **Company credit card = bank-like account (`kind="credit_card"`)** for UX reuse, but GL posts to a Credit Card Payable liability; mind the existing `BankAccount.balance` cache sign.
- **All posting routes through `create_journal_entry`** so the closed-period guard and balanced-entry enforcement always apply; never write `JournalEntry` rows directly.
- **Currency:** capture `original_amount` + `currency` from day one, but leave base = original (no conversion) until Phase 17 FX.
- **Permissions:** import + approve/post = owner/manager; cashier may review only; partner read-only reports (per design doc Part 12).

---

## Phase 18-MUX — Mobile Transaction UX *(partially shipped — stabilize only; no expansion)*

**Status:** Complete (18-MUX-1 … 18-MUX-5). **Prerequisite:** mobile navigation shell — **met** (header/shell fixes Jun 6, 2026). Dual-host calculator, searchable pickers, edge-case fields, fragment keypad, and per-bank ledger tracking shipped — **no new posting types**.

**Goal:** Calculator / POS-style **New Transaction** screen on mobile (≤768px) for fast daily entry with minimal phone keyboard use. Desktop Add Transaction form stays unchanged.

**Decisions locked (June 6, 2026):**

| # | Decision |
|---|----------|
| 1 | **Mobile only** — calculator UI hidden on desktop (≥769px). |
| 2 | **Desktop form unchanged** — existing two-column `render_add_transaction` layout. |
| 3 | **New Transaction remains primary entry** — top action bar + Quick Create on Home; Sales/Expenses/Purchases list pages stay under More as history/review only. |
| 4 | **No accounting logic changes** — presentation layer only. |
| 5 | **`_at_save` remains the single save path** — mobile collects inputs, then calls existing `_at_save()`. |
| 6 | **Salary = visible chip** — maps internally to Expense → Worker → Salary (no new posting type). |
| 7 | **Categories** — searchable **bottom sheet** when lists are long; avoid a full-screen card wall at scale. |
| 8 | **Foreign currency** — keypad/display design must allow multi-currency later; FX implementation can defer (aligns with Phase 17). |
| 9 | **Do not implement until mobile nav is stable** — hubs, padding, roles, module gating verified in production use. |

**Preferred UX (summary):**

- Read-only amount display + in-app keypad (`st.button` grid, `session_state` buffer) — **no** `st.text_input` for amount on mobile (avoids OS keyboard).
- Large type chips: Sale, Expense, Purchase, Customer Payment, Supplier Payment, Salary (+ Bank Transaction optional/advanced).
- Payment method chips filtered per type (reuse existing method sets).
- Step flow: type → amount → payment → category/context → optional notes/receipt → save.
- Save button sticky above bottom nav; label shows type + formatted amount.

**Technical approach (when started):**

- Dual-host pattern: `.erp-at-mobile-host` / `.erp-at-desktop-host`; separate widget keys (`mob_at_*` vs `at_*`); CSS `@media` shows one host.
- Consider `st.fragment` for keypad to reduce rerun scope (Streamlit ≥1.33).
- Reuse `_parse_amount_str`, `_allowed`, `_can("create_transaction")`, existing conditional fields per type.

**Suggested build order (post-prerequisite):**

| Sub-phase | Scope |
|-----------|--------|
| **18-MUX-1** | Keypad + display + mobile host CSS; Sale + Cash MVP → `_at_save` |
| **18-MUX-2** | All type chips + filtered payment chips; Salary → worker Expense mapping |
| **18-MUX-3** | Searchable category bottom sheet; customer/vendor/payable context |
| **18-MUX-4** | Edge cases: Card bank account, supplier payable, worker salary sub-fields, FX display hooks |
| **18-MUX-5** | `st.fragment` polish, i18n, `UI_SHELL.md`, Playwright + unit tests for buffer/formatting |

**Explicitly deferred:** multi-line `*` entry, changes to `_at_save` / posting functions, desktop calculator UI, Phase 17 FX conversion logic.

**Reference:** Mobile nav contract in [UI_SHELL.md](./UI_SHELL.md) (mobile chrome section). Calculator mockup review in project canvases (`mobile-nav-mockups.canvas.tsx`).

**Future nav (not 18-MUX):** Bottom-tab structure and More Hub organization are **unchanged** for now. Evaluation options and hub customization are under **[MOBILE-09](#mobile-09--future-mobile-navigation-vision)**, **[MOBILE-07](#mobile-07--customizable-more-hub)**, **[MOBILE-08](#mobile-08--organized-more-hub)**.

---

## MOBILE-11 — Mobile Design System

**Status:** ✅ Approved 2026-06-09.

**Reference:** [`docs/MOBILE_UI_SYSTEM.md`](./docs/MOBILE_UI_SYSTEM.md)

The mobile design system is now the authoritative source for future mobile UX decisions.

**Concept C Mobile Add Transaction is accepted as the reference implementation for:**

- Progressive disclosure
- Sheet picker interactions
- Trigger row pattern
- Mobile transaction entry workflow
- Mobile spacing philosophy
- Mobile colour token philosophy

Future mobile screens should gradually migrate toward this design system. No full-app rewrite is approved. Migration remains phased and observation-driven.

**Phased migration sequence (not approved for implementation yet — observation-driven):**

1. Add Transaction — ✅ complete (Concept C)
2. Home page
3. Banking page
4. Reports / Cashflow
5. More Hub
6. Transaction History / Ledger

Each phase is visual rendering only. No accounting, posting, or schema changes in any phase.

**Cross-references:** [OBS-01](#obs-01--operational-friction-log) · [FUTURE UX / NAVIGATION VISION](#future-ux--navigation-vision) · [MOB-AT-C1](#mob-at-c1--concept-c-mobile-add-transaction-ui) · [MOBILE-12](#mobile-12--design-governance)

---

## MOBILE-12 — Design Governance

**Status:** ✅ Approved 2026-06-09.

**Purpose:** Prevent repeated redesigns, conflicting UI patterns, duplicate CSS, and one-off implementations.

**Rules:**

- Follow [`docs/MOBILE_UI_SYSTEM.md`](./docs/MOBILE_UI_SYSTEM.md)
- Reuse existing mobile components before creating new ones
- Use the sheet picker standard
- Use the trigger row standard
- Use progressive disclosure
- Hide invalid options instead of disabling them
- Avoid desktop patterns on mobile
- Do not place HTML inside Streamlit widget labels
- Do not introduce new mobile visual patterns without updating the design system document
- **No UI redesign work should begin until ownership conflicts for that area are understood.** Perform a CSS ownership audit for the target area first. Examples: login redesign requires login ownership audit (done — see CSS-01); banking redesign requires banking ownership audit; reports redesign requires reports ownership audit.

Any future mobile UX proposal should explain why existing patterns cannot be reused before introducing a new pattern.

### Future Observation Decisions

**Status:** Not approved for implementation. Decision method: [OBS-01](#obs-01--operational-friction-log) operational usage observations. No implementation until repeated real-world usage identifies the better option.

**1. Banking naming**

| Option | Notes |
|--------|-------|
| Banking | Current label — familiar, conventional |
| Cashflow | Broader framing — covers inflows and outflows |
| Alternative | To be proposed via OBS-01 |

**2. Bottom navigation placement**

| Option | Notes |
|--------|-------|
| Ledger | Historical records focus |
| Reports | Summary and analysis focus |
| Banking | Account and balance focus |

Current placement and labels are unchanged until resolved.

**3. More naming**

| Option | Notes |
|--------|-------|
| More | Current label — conventional, widely understood |
| Hub | Suggests a central place for secondary tools |
| Operations | More descriptive for restaurant operations context |
| Alternative | To be proposed via OBS-01 |

**Cross-references:** [OBS-01](#obs-01--operational-friction-log) · [`docs/MOBILE_UI_SYSTEM.md`](./docs/MOBILE_UI_SYSTEM.md) · [FUTURE UX / NAVIGATION VISION](#future-ux--navigation-vision) · [MOB-AT-C1](#mob-at-c1--concept-c-mobile-add-transaction-ui)

---

## ERP-Wide UI Ownership Principle

**Status:** ✅ Approved · **Applies to:** All future CSS and UI work.

**Goal:** The ERP must no longer have scattered UI rules where multiple files style the same component and override each other silently. This is not about merging everything into one CSS file. It is about assigning one clear owner per UI area.

### Core principle

| Rule | Statement |
|---|---|
| One component | One owner file |
| One token | One source of truth |
| One pattern | Reused everywhere |
| Duplicate selectors | Only if intentionally documented |
| Silent overrides | Not permitted from `widgets.css` or `theme.css` |
| New UI work | Ownership must be clear before implementation begins |

### What we do NOT want

- One giant `theme.css` that owns everything
- One giant `mobile.css` that owns everything
- More global override layers added on top of existing conflicts

### What we DO want

| File | Owns |
|---|---|
| `theme.css` | Global tokens (`--theme-*`, `--erp-chip-*`) · desktop/shared base styles · sidebar · dashboard · header desktop |
| `widgets.css` | Truly generic Streamlit widget behaviour only (inputs, selects, border containers, primary button base) |
| `mobile_header.css` | Mobile header only — height, compact toolbar, auth screen |
| `mobile_shell.css` | Mobile shell / bottom nav / hub sheet only |
| `mobile_txn.css` | Mobile Add Transaction only — AT panel, pickers, `--mob-at-*` tokens |
| `mobile_reports.css` | Mobile reports only — report layout grids, spacing, density, scroll behaviour; chip colour grammar owned by `widgets.css` |
| `mobile_txn_history.css` | Mobile transaction history only |
| `desktop_txn_history.css` | Desktop transaction history only |
| `desktop_reports.css` | Desktop reports — canonical chip selector layout (`mob_rpt_sel_*`; REPORTS-DESKTOP-02) |
| `setup01_wizard.css` | Setup wizard only |
| `mobile_banking.css` | Mobile banking only — **does not exist yet; create when banking redesign begins** |

**Cross-references:** [CSS-01](#css-01--theme-ownership-consolidation) · [CSS-02](#css-02--erp-wide-ui-ownership-standard) · [MOBILE-14](#mobile-14--mobile-theme-ownership-cleanup) · [MOBILE-12](#mobile-12--design-governance)

---

## CSS-01 — Theme Ownership Consolidation

**Status:** ✅ Approved · **Priority:** High

**Purpose:** Establish single ownership for each CSS domain so future UI work does not produce MOBILE-13-style cascade conflicts. This is architecture documentation and the authority that MOBILE-14 executes against.

**Reference:** Theme Ownership Audit (June 2026). Cross-reference: [UI-STAB-05](#ui-stab-05--css-scope--leakage-cleanup) (audit findings — CSS-01 is the approved execution).

### Target ownership map

| Domain | Canonical owner after CSS-01 |
|---|---|
| `--theme-*` and `--erp-chip-*` tokens | `theme.css :root` |
| `--hdr-h` — desktop 60px | `theme.css :root` |
| `--hdr-h` — mobile 56px / 86px search | `mobile_header.css` only |
| Header column layout (desktop) | `theme.css` |
| Header column layout (mobile compact) | `mobile_header.css` |
| Bottom nav + FAB + hub sheet | `mobile_shell.css` only |
| AT panel visual CSS | `mobile_txn.css` |
| AT panel layout grids | `mobile_txn.css` (moved from `widgets.css`) |
| `--mob-at-*` tokens | `mobile_txn.css` only |
| Report visual CSS | `mobile_reports.css` |
| Report layout grids | `mobile_reports.css` (moved from `widgets.css`) |
| Chip button active state (AT + report) | `widgets.css` only |
| Chip button idle state (AT + report) | `widgets.css` only (report idle migrated from `mobile_reports.css` by E8b) |
| TXH layout grids | `mobile_txn_history.css` only |
| Auth screen / login (`erp-auth-*`) | `mobile_header.css` |
| Setup Wizard | `setup01_wizard.css` (no changes needed) |
| Desktop TXH table | `desktop_txn_history.css` (no changes needed) |
| `block-container` padding-top (mobile) | `mobile_header.css` only |

### Blocking issues this resolves

| ID | Issue | Severity |
|---|---|---|
| C1 | `stVerticalBlockBorderWrapper` global catch-all forces `--theme-card` on all border containers | High — documented; partial mitigation via targeted overrides |
| C2 | `--hdr-h` defined in 4 files with conflicting values | High — removed from `widgets.css` and `mobile_shell.css` by E1 |
| C3 | Chip override `:not` selector tests wrong element — save button always caught | Medium — fixed by E3 |
| C4 | Layout grids for 3 components owned by `widgets.css` instead of their component files | Medium — resolved by E4/E5/E6 |
| C5 | `html.erp-mobile` vs `@media` dual detection asymmetry | Medium — documented; no single fix |
| C6 | `block-container padding-top` defined in 4 files | Low — dead copies removed by E2 |

**Implementation:** See [MOBILE-14](#mobile-14--mobile-theme-ownership-cleanup) for the re-baselined M1–M6 execution plan (E1–E13 superseded).

---

## MOBILE-14 — Mobile Theme Ownership Cleanup

**Status:** ✅ **Closed** (2026-06-10) · **Priority:** High · All required steps complete

**Purpose:** Architectural cleanup only — **zero visible UI change** expected. Executes the reduced scope from [CSS-01](#css-01--theme-ownership-consolidation) after prior UI work (HDR-01, AT-LIGHT-01, UI-1 chip grammar, QUICK-ENTRY, UX-04B, etc.) already closed many original E-steps.

**Original plan:** E1–E13 consolidation (**superseded** — do not execute). See [supersession table](#mobile-14--e1e13-superseded) below.

**Prerequisite:** Ownership contract tests in `tests/test_mobile14_ownership_contract.py` (see [TEST_COVERAGE_MAP.md](./docs/TEST_COVERAGE_MAP.md)).

**Unblocked:** [LOGIN-01](#login-01--login--company-picker-modernization) and [UX-02](#ux-02--responsive-viewport--device-auto-fit) — M1+M2 minimum complete (not started yet).

### Re-baselined steps (M1–M6)

| Step | Action | Owner file(s) | Status |
|---|---|---|---|
| **M1** | **Header height/token dedupe** — dedupe `--hdr-h` definitions **within** `theme.css` and `mobile_header.css`. No new tokens. | `theme.css`, `mobile_header.css` | ✅ **Closed** — dedup complete; M1 dedup tests promoted (suite: **914 passed, 5 xfailed** at M1 close) |
| **M2** | **Verify/remove dead mobile `block-container padding-top`** in `mobile_shell.css` (old E2). | `mobile_shell.css` | ✅ **Closed / verified no-op** — rule already removed during M1 session; canonical top inset in `mobile_header.css`; M2 tombstone comments + contract test added |
| **M3** | **Optional:** relocate bottom-nav / FAB / hub **suppression** references from `widgets.css` → `mobile_shell.css`. Shell already owns styling; xfail contract documents non-owner suppression refs (allowed). | `widgets.css`, `mobile_shell.css` | 📋 **Optional / low** — not a blocker |
| **M4** | **Optional:** relocate profile / co-switch **suppression** references from `widgets.css` → `mobile_shell.css`. E13 sheet chrome already in shell; suppression refs in widgets are live. | `widgets.css`, `mobile_shell.css` | 📋 **Optional / low** — not a blocker |
| **M5** | **Move KPI / dashboard rules** out of `widgets.css` → `theme.css` — `.erp-kpi-section`, `.kpi-grid`. Real styling move. | `widgets.css`, `theme.css` | ✅ **Closed** |
| **M6** | Sidebar single-owner + notification two-owner exception. | `widgets.css`, `mobile_header.css`, `mobile_shell.css`, `theme.css` | ✅ **Closed** |
| **TXH** | Move `txh_actions_` grid from `widgets.css` → `mobile_txn_history.css`. | `widgets.css`, `mobile_txn_history.css` | ✅ **Closed** — duplicate removed; canonical owner already in `mobile_txn_history.css` |

### Already complete — do not redo

| Original step | Closed by |
|---|---|
| **E4** — AT layout grids → `mobile_txn.css` | Prior MOBILE / AT work + layout contract tests |
| **E5** — Report layout grids → `mobile_reports.css` | Prior mobile reports work |
| **E6** — Dead TXH filter grids in `widgets.css` | `mobile_txn_history.css` ownership |
| **E8a/b** — Report chip colour grammar | UI-1 / `widgets.css` chip grammar |
| **E9** — `--mob-at-*` token dedupe | AT-LIGHT-01 + `mobile_txn.css` ownership |
| **E12** — Login credentials hint colour | Theme-token fix (if present in codebase) |
| **UI-1** — Chip colour grammar in `widgets.css` | Closed — do not move or rewrite |
| **AT-LIGHT-01** — Mobile AT token / panel polish | Closed 2026-06-10 |
| **HDR-01** — Mobile header pass | Closed 2026-06-10 |

### Explicit non-goals (M1–M6)

- Do **not** touch AT picker z-index stack.
- Do **not** touch AT-LIGHT wrapper-strip block.
- Do **not** touch `--mob-at-*` token ownership (`mobile_txn.css`).
- Do **not** touch UI-1 chip grammar in `widgets.css`.
- Do **not** visually redesign anything.

### Ownership contract tests (`tests/test_mobile14_ownership_contract.py`)

**Current:** **14 passed, 2 xfailed** (16 tests total). Required contracts all pass; remaining xfails are optional M3/M4 only.

| Contract | Purpose | State |
|---|---|---|
| `--hdr-h` ownership + within-file dedup | M1 pin | ✅ Pass |
| `mobile_shell.css` has no `block-container padding-top` | M2 pin | ✅ Pass |
| Bottom-nav / FAB / hub styling owned by `mobile_shell.css` | Regression lock | ✅ Pass |
| No bottom-chrome selectors in `widgets.css` | M3 optional relocation target | xfail (suppression refs allowed) |
| Profile / co-switch sheets owned by `mobile_shell.css` | E13 regression lock | ✅ Pass |
| No sheet selectors in `widgets.css` | M4 optional relocation target | xfail (suppression refs allowed) |
| No KPI / dashboard rules in `widgets.css` | M5 pin | ✅ Pass |
| Sidebar hide ownership contract | M6 pin | ✅ Pass |
| No `mob_at_`/`mob_rpt_` layout grids in `widgets.css` | E4–E5 regression lock | ✅ Pass |
| No `txh_` layout grids in `widgets.css` | TXH micro-step | ✅ Pass |
| Notification rule liveness pin | Permanent two-owner contract | ✅ Pass |

**Rule:** Non-owner files may reference owned selectors for **state suppression** only. M3/M4 xfails are optional — not required for MOBILE-14 closure.

### MOBILE-14 — E1–E13 superseded

| Old step | Disposition |
|---|---|
| E1 | → **M1** (narrowed: dedupe within `theme.css` / `mobile_header.css` only) |
| E2 | → **M2** |
| E3 | Chip selector bug — **out of M1–M6**; address only if regression found |
| E4, E5, E6, E9 | **Complete** — do not redo |
| E7 | → **M3** |
| E8a, E8b | **Complete** (UI-1) — do not redo |
| E10 | Banner duplicate — **deferred**; not in M1–M6 |
| E11 | → **M6** (re-audit; do not blind-delete) |
| E12 | **Complete** — do not redo |
| E13 | → **M4** |

### Constraints

- **Tests before cleanup** — ownership contract tests exist; promote xfails with each M-step.
- M1+M2 complete — LOGIN-01 and UX-02 unblocked (not started).
- M3/M4 optional suppression relocations may be done later — not blockers.
- Run `pytest tests/` after each M-step; any visible change indicates a missed rule — not intentional.

---

## CSS-02 — ERP-Wide UI Ownership Standard

**Status:** ✅ Approved · **Priority:** High

**Purpose:** Prevent future UI regressions caused by scattered styling, duplicate selectors, and unclear CSS ownership across the full ERP — not just the mobile Add Transaction area. Formalises the [ERP-Wide UI Ownership Principle](#erp-wide-ui-ownership-principle) as enforceable rules for all future work.

**Cross-references:** [ERP-Wide UI Ownership Principle](#erp-wide-ui-ownership-principle) · [CSS-01](#css-01--theme-ownership-consolidation) · [MOBILE-14](#mobile-14--mobile-theme-ownership-cleanup) · [MOBILE-11](#mobile-11--mobile-design-system) · [MOBILE-12](#mobile-12--design-governance) · Theme Ownership Audit (June 2026).

### Rules

| # | Rule |
|---|---|
| 1 | Every UI surface must have one declared owner file. |
| 2 | Generic widget styling may live in `widgets.css` only if it is truly global (applies to all Streamlit widgets app-wide with no component-specific logic). |
| 3 | Component-specific layout grids must live in that component's CSS file — not in `widgets.css`. |
| 4 | Component-specific colours must use approved `--theme-*` tokens or documented component-level tokens (e.g. `--mob-at-*`). Hardcoded hex is not permitted in component CSS. |
| 5 | No CSS selector may be duplicated across files unless there is a written reason recorded in that section's comment or in the roadmap. |
| 6 | New UI work must include an ownership check before implementation begins. If the target area has unresolved ownership conflicts, those must be resolved first. |
| 7 | If a selector is overridden only by higher specificity or `!important` stacking, it must be documented or consolidated — not left as a silent win. |
| 8 | Existing duplicate rules must be removed in planned cleanup phases (e.g. MOBILE-14). Do not remove them randomly during unrelated feature work. |

### Scope

CSS-02 applies to all CSS files in `ui/`. It is not time-boxed — it is the ongoing standard for all CSS added or modified after June 2026. Violations found during feature work should be logged as future cleanup candidates, not silently worked around.

### Relationship to CSS-01 and MOBILE-14

CSS-01 maps the current ownership state and identifies the gaps. MOBILE-14 fixes those gaps for the mobile layer. CSS-02 is the rule set that prevents the gaps from reappearing.

---

## THEME-CONTRAST-01 — Desktop/Theme Contrast (P0 + P1)

**Status:** ✅ **Closed** (2026-06-05) · Token/CSS only — no layout, no chip redesign, no hover pass.

**P0 — Primary filled button contrast:** Added `--erp-primary-fill` / `--erp-primary-fill-hover` (`#2563eb` / `#1d4ed8`). Filled primary buttons (main, mobile FAB/save/hub, AT picker confirm) use the fill token; `--theme-info` unchanged for links/tints. Dark mode buttons shift slightly deeper blue; white text ≥ 4.5:1.

**P1 — Success/warning text contrast:** Added `--theme-success-text` (`#15803d`) and `--theme-warning-text` (`#b45309`) for light-mode foreground text on card/bg. Applied to KPI amounts, txn tips, `.amt-pos`, TXH status/amount text. Fill/icon `--theme-success` / `--theme-warning` unchanged.

**Tests:** `tests/test_theme_contrast.py` (15 WCAG contrast contracts).

---

## LOGIN-01 — Login / Company Picker Modernization

**Status:** ✅ **Closed** (2026-06-05) · **Priority:** Medium · Visual/UI only — auth logic unchanged.

**Purpose:** Bring the login screen and company picker into the approved flat card design language so the entire app feels like one product from first load.

**References:** [`docs/MOBILE_UI_SYSTEM.md`](./docs/MOBILE_UI_SYSTEM.md) · Concept C reference implementation ([MOB-AT-C1](#mob-at-c1--concept-c-mobile-add-transaction-ui)) · Login Audit (June 2026).

### Delivered

| Area | Before | After |
|---|---|---|
| Header | Gradient `banner banner-primary` + emoji | Flat `erp-auth-header-card` in `ui/auth.css` |
| User tiles | Multi-line `st.button` text | Avatar cards (`erp-mono-avatar`, role chip) + `login.select` button |
| Login form | Inline `style=` headings/hint | `erp-auth-password-heading`, `erp-auth-hint`; errors tinted via CSS |
| Company picker | Bordered container + separate Enter button | Full-width tappable rows (`pick_co_{id}`) with chevron affordance |
| Create company | Expander + primary button | Quiet secondary full-width `picker_start_setup01` |
| Sign out | Primary button with emoji | Quiet text-style `picker_signout` |
| CSS ownership | `erp-auth-*` in `mobile_header.css` | Sole owner: `ui/auth.css`; registered in `load_theme_css()` |

### Constraints honored

- Widget keys frozen (`select_user_{id}`, `login_*`, `pick_co_{id}`, `picker_signout`, `picker_start_setup01`).
- No auth logic, DEV-AUTH-01, UX-01 restore, password validation, or membership validation changes.
- `--theme-*` and `--role-*` tokens only; no new color tokens.

---

## QUICK-ENTRY-01 — Context-Aware Mobile Category Selection

**Status:** ✅ Implemented & verified (2026-06-10) — `pytest tests/test_quick_entry.py` 14/14 passing on host. · **Priority:** High

**Design philosophy:** FAST ENTRY FIRST — fewer taps, less typing, faster bookkeeping.

**Purpose:** Reduce the number of taps required during daily mobile transaction entry by surfacing common categories directly inside the Add Transaction panel, without requiring the user to open a picker sheet for the majority of transactions.

**Depends on:** MOBILE-14 M1 + M2 minimum. No accounting engine changes. No database schema changes.

### Problem

The current mobile flow requires opening a category picker for most transactions:

```
Type → Payment Method → Category Picker → Category → Amount → Save
```

For a high-frequency user logging 20–50 transactions a day, this extra picker interaction is the single most repeated friction point in the app.

### Goal

For common transaction types, show categories directly inside the AT panel. The picker remains fully available as a fallback — this is a shortcut layer only.

```
Type → Category Chip → Amount → Save
```

### Desired behaviour by transaction type

| Type | Inline behaviour | Picker fallback |
|---|---|---|
| **Sale** | If only one active sales category exists: auto-select it, no chips shown. If multiple: show category chips inline. | "More…" chip opens picker |
| **Expense** | Show the most common expense categories as chips directly below Row 1. Example: `Cleaning · Utilities · Maintenance · Payroll · Office · More…` | "More…" chip opens picker |
| **Purchase** | Show purchase categories inline. | "More…" chip opens picker |
| **Supplier Payment** | Vendor is the primary selector — no category chips required. | Picker unchanged |
| **Customer Payment** | Customer / invoice is primary — no category chips required. | Picker unchanged |
| **Bank Transaction** | Bank account is primary — no category chips required. | Picker unchanged |

### "More…" behaviour

When category chips are shown, a final `More…` chip is always included:

```
Cleaning  Utilities  Maintenance  Payroll  More…
```

Tapping `More…` opens the existing category picker sheet. The picker is unchanged. The user can always reach any category regardless of what appears inline.

### UX rules

- Mobile only. Desktop AT panel unchanged.
- Maximum 4–5 visible category chips (excluding `More…`).
- Must respect active / inactive category status — inactive categories never appear as chips.
- Chip selection must call the same category-apply logic as the picker (`_mob_at_apply_category_pick`). No new posting path.
- Must work with the current category architecture — no new category fields, no frequency tracking required for initial implementation.
- Must not alter `_at_save()` or any accounting logic.

### Non-goals

This section does not change or remove:

- Category picker sheet — remains fully functional
- Category management (add / rename / activate / deactivate)
- Existing accounting or posting logic
- Desktop AT form
- Any other picker (payment, type, vendor, bank, invoice, payable)

### Success metric

| Metric | Current | Target |
|---|---|---|
| Taps for a common expense transaction | 6 (Type → PM → Open picker → Select category → Amount → Save) | 5 (Type → PM → Category chip → Amount → Save) |
| Picker required for majority of transactions | Yes | No — picker is a fallback, not the default path |

**Cross-references:** [MOB-AT-C1](#mob-at-c1--concept-c-mobile-add-transaction-ui) · [MOBILE-14](#mobile-14--mobile-theme-ownership-cleanup) · [MOBILE_UI_SYSTEM.md](./docs/MOBILE_UI_SYSTEM.md)

**Deferred:** **QUICK-ENTRY-02** (subcategory quick-entry workflow) — not approved; subcategory flow unchanged.

---

## ADD-TXN-BR-01 — Sale Validation vs Bookkeeping Rules

**Status:** ✅ **Closed** (2026-06-10).  
**Priority:** Urgent regression fix — completed.  
**Scope:** Add Transaction Sale validation only. Expense and Purchase rules unchanged.

### Business rule (implemented)

| Field | Cash / Card Sale | Credit Sale |
|-------|------------------|-------------|
| Amount | Required | Required |
| Date | Required (defaulted) | Required |
| Payment method | Required | Required |
| Customer | Optional (walk-in default) | **Required** (named customer; not blank / not walk-in default) |
| Category / Subcategory | **Optional** — must not block save | Optional |

### Record

- Sale Cash/Card record without category/subcategory (matches legacy `render_sales` posting path).
- Credit Sale blocks empty or `"Walk-in Customer"`; named customer saves and posts to AR.
- `_at_save` / GL posting unchanged — category stored when present, not required for journal.
- Tests: `tests/test_at_sale_submit.py` (+3 BR-01 cases); host **800/800 passed**.

**Cross-references:** [docs/AUDIT_HISTORY.md](./docs/AUDIT_HISTORY.md) §2026-06-10 ADD-TXN-BR-01 · [QUICK-ENTRY-01](#quick-entry-01--context-aware-mobile-category-selection)

---

## AT-LIGHT-01 — Mobile AT Light-Mode Polish

**Status:** ✅ **Closed** (2026-06-10).  
**Priority:** High (was prerequisite for HDR-01).  
**Scope:** Mobile Add Transaction panel only — CSS + keypad layout. No accounting, schema, or posting changes.

### Completed scope (P1–P6)

| Phase | Deliverable |
|-------|-------------|
| **P1 — Hierarchy & separation** | Row 1 selectors vs category chip grammar; selected chip state (UI-1 solid accent on quick chips) |
| **P2 — Keypad separation** | White (`--theme-card`) keys; border treatment; `:active` pressed state |
| **P3 — Amount card cleanup** | Wrapper band removed; clean border on inner card surface |
| **P4 — Panel refinement** | Stronger panel tint (22%/10% info mix); Page → Panel → Card hierarchy |
| **P5 — Nav-safe keypad spacing** | Bottom row visible above bottom nav (`--mob-at-panel-h` 380px; keypad padding) |
| **P6 — Mobile keypad ordering** | Phone/POS order: `1 2 3` / `4 5 6` / `7 8 9` / `. 0 ⌫` (ITU E.161 / ISO 9564) |

### Verification

| Check | Status |
|-------|--------|
| Host `pytest tests/` | ✅ **800 passed** (2026-06-10) |
| Phone / POS visual verification | ✅ Manual sign-off (2026-06-10) — light + dark; Row 1 vs chips; keypad order; nav clearance |

### Ownership

- Tokens + panel surface: `ui/mobile_txn.css` (`:root` `--mob-at-*`, AT-LIGHT-01 blocks)
- Chip colour grammar: `ui/widgets.css` (UI-1; MOBILE-14 E8 ruling)
- Keypad tuple: `app.py` `_mob_at_render_amount_keypad_fragment` (P6 only)

**Next:** [UX-04](#ux-04--selector-interaction-audit) (UX-03 closed 2026-06-10).

**Cross-references:** [QUICK-ENTRY-01](#quick-entry-01--context-aware-mobile-category-selection) · [docs/AUDIT_HISTORY.md](./docs/AUDIT_HISTORY.md) §2026-06-10 AT-LIGHT-01

---

## DATE-01 — Fast Mobile Date Entry

**Status:** ✅ **Closed** (2026-06-10) · **Priority:** Medium · Mobile Add Transaction date sheet only.

**Design philosophy:** FAST ENTRY FIRST — for bookkeeping users, the date is nearly always today or yesterday. The current date picker opens a full sheet with a native `st.date_input`, which is reliable but requires more interaction than the common case demands.

**Purpose:** Reduce date-entry taps for the majority of mobile transactions by surfacing the most common date choices directly inside the date picker sheet, before the calendar input.

### Proposed picker sheet layout

```
┌─────────────────────────────────────────┐
│  ── grab handle ──                      │
│  Date                               ×   │
├─────────────────────────────────────────┤
│  [ Today      ]  [ Yesterday ]          │  ← quick-select row 1
│  [ This Week  ]  [ Custom Date ]        │  ← quick-select row 2
├─────────────────────────────────────────┤
│  Recent                                 │
│  9 Jun 2026                             │
│  8 Jun 2026                             │
│  7 Jun 2026                             │
├─────────────────────────────────────────┤
│  (calendar / YYYY-MM-DD input —         │
│   shown only when Custom Date tapped)   │
└─────────────────────────────────────────┘
```

### Completed (2026-06-10)

- Date sheet quick choices: **Today · weekday+date**, **Yesterday · weekday+date**, **Custom date...**
- `at_date_follows_today` rollover guard (company-scoped); Today/default sets True; Yesterday/Custom clears.
- Backdated Row 1 date pill accent border + dot when `at_date != today`.
- Closed-period courtesy check via shared `_entry_date_posting_blocked` helper (posting engine final authority).
- Repeat Transaction sets date to today + `at_date_follows_today = True`.

**Tests:** `tests/test_date01_fast_mobile_date.py` (15 tests). Host `pytest tests/` — **887/887 passed**.

### Scope delivered

- Mobile date sheet only. Desktop `st.date_input` unchanged.
- No schema or posting logic changes (shared period guard extracted, not altered).

**Cross-references:** [MOB-AT-C1](#mob-at-c1--concept-c-mobile-add-transaction-ui) · [QUICK-ENTRY-01](#quick-entry-01--context-aware-mobile-category-selection) · [MOBILE_UI_SYSTEM.md](./docs/MOBILE_UI_SYSTEM.md)

---

## UX-01 — Session Persistence (v1 — narrow restore)

**Status:** ✅ **Closed** (2026-06-10) · **Priority:** Medium.

### Completed (v1)

- HMAC-signed restore cookie (`erp_session_restore`) — user identity + optional `active_company_id`.
- Payload: `user_id`, `iat`, `exp` (8h), password-hash fragment; company id revalidated via `_activate_company_in_session`.
- Disabled when `ERP_SESSION_RESTORE_SECRET` unset; **DEV_MODE** path untouched.
- JS-set cookie (`SameSite=Lax`, `Secure` on HTTPS). **Not HttpOnly** (JS limitation — document before production).
- Does **not** persist AT state, navigation, locale, PM/category memory, or report filters.

**Pre-production:** set `ERP_SESSION_RESTORE_SECRET` to a long random string (≥32 bytes).

**Tests:** `tests/test_ux01_session_restore.py` (17 tests). Host `pytest tests/` — **904/904 passed**.

### Deferred (broader UX-01)

- Page restore, locale restore, PM/category memory, registry/user preference persistence, theme/sidebar/filters.

**Cross-references:** [LOGIN-01](#login-01--login--company-picker-modernization) · [UX-02](#ux-02--responsive-viewport--device-auto-fit)

---

## TXH-DETAIL-01 — Transaction Detail JE / Edit History Polish

**Status:** ✅ **Closed** (2026-06-05) · Visual/readability only — no accounting or action changes.

**Problem:** Expanded Transaction History view panel rendered Journal Entries and Edit History as 11px inline-styled debug-like text.

**Delivered:** `_txh_render_view_je_block` + `_txh_render_view_edit_history_block` with semantic `erp-txh-je-*` / `erp-txh-edit-*` classes; JE account/Dr/Cr grid (13px, tabular nums, right-aligned amounts); edit diffs use `--theme-danger-text` / `--theme-success-text`. CSS owner: `desktop_txn_history.css` (+ mobile panel tweaks in `mobile_txn_history.css`).

**Tests:** `tests/test_txh_detail01.py` (6 contracts).

---

## VIEWPORT-SYNC-01 — JS/CSS Mobile Threshold Sync

**Status:** ✅ **Closed** (2026-06-05) · Replaces/reduces **UX-02** · **Align-up** decision approved.

**Problem:** JS `inject_mobile_viewport_detector()` tagged touch tablets up to **1366px** as `html.erp-mobile`, but CSS `@media` fallback arms only reached **1024px** coarse pointer — 1025–1366px tablets got mobile widgets without full mobile layout CSS.

**Fix:** Canonical mobile `@media` header (narrow ≤968 | touch tablet ≤1366 coarse | phone landscape ≤520 coarse) applied uniformly in `mobile_shell.css`, `mobile_txn.css`, `mobile_header.css`, `mobile_reports.css`, `mobile_txn_history.css`, `widgets.css`. Constants pinned in `ui/theme.py`.

**Tests:** `tests/test_viewport_sync01.py` (5 contracts).

**Caveat:** Fine-pointer laptops at 1024–1200px remain desktop unless width ≤968; coarse touch devices up to 1366px receive POS/mobile UI.

---

## UX-02 — Responsive Viewport & Device Auto-Fit

**Status:** ✅ **Superseded by VIEWPORT-SYNC-01** (2026-06-05). Original scope mostly solved by **HDR-01**, **MOBILE-14**, **UX-01**; remaining gap was JS/CSS threshold mismatch.

**Purpose:** Users should never need to manually adjust browser zoom, viewport size, or scaling after login. Viewport adaptation is a core usability requirement — the ERP must automatically fit the device it is opened on.

### Problem

Some users currently need to manually adjust browser zoom or viewport scaling to make the ERP render correctly. This creates friction on every session and is especially problematic on:

- Mobile phones — layout may not switch to mobile mode automatically
- Tablets — available width may not be used correctly
- Shared / multi-user devices — each user may see a different zoom state
- Any device where the JS mobile-detection cookie has not yet fired

### Goal

The ERP detects the device and viewport automatically and delivers the correct layout without any manual adjustment by the user. The correct layout must be stable after login, refresh, and company switch.

### Requirements by device class

| Device | Required behaviour |
|---|---|
| **Phone** | Mobile layout activates automatically; bottom navigation visible; AT panel fits viewport; no manual zoom needed |
| **Tablet** | Tablet-optimised layout; available screen width used correctly; no manual zoom needed |
| **Desktop** | Desktop layout with sidebar and header scaling correctly; no manual zoom needed |

### Rules

- ERP must respond to actual viewport size — not assumed or hardcoded dimensions.
- ERP must not depend on the browser zoom level being set to 100%.
- Users must not need to refresh to receive the correct layout.
- Layout mode (mobile / desktop) must be determined automatically on first load.
- Responsive behaviour must be consistent across: initial load, page refresh, and company switch.

### Investigation required

Before implementation, determine which layer(s) are causing the current mis-fit. Candidates:

| Candidate | What to check |
|---|---|
| Viewport meta tag | Is `<meta name="viewport" content="width=device-width, initial-scale=1">` present and correct? Streamlit injects its own — verify it is not overridden or absent. |
| Browser zoom assumptions | Does any CSS use fixed `px` widths that assume 100% zoom? |
| Responsive breakpoint logic | Is the 968px breakpoint correctly matching the physical device class on all tested devices? |
| Streamlit container sizing | Does `st.set_page_config(layout="wide")` interact with mobile viewports in ways that break the layout? |
| Mobile detection timing | The JS cookie → Python flag path (`_sync_mobile_ui_flag_from_cookie`) fires after first render. Does the first render show desktop layout briefly before switching? |
| CSS width constraints | Are any `max-width` or `min-width` constraints in `theme.css` or `mobile_shell.css` preventing correct scaling? |

The investigation output should identify the root cause(s) before any CSS or Python changes are made.

### Success metric

A user opens the ERP on any device and immediately receives the correct layout — no browser zoom change, no window resize, no refresh required.

**Cross-references:** [CSS-01](#css-01--theme-ownership-consolidation) · [MOBILE-14](#mobile-14--mobile-theme-ownership-cleanup) · [MOBILE_UI_SYSTEM.md](./docs/MOBILE_UI_SYSTEM.md)

---

## HDR-01 — Combined Header Pass (UX-07 + UX-06)

**Status:** ✅ **Closed** (2026-06-10). **Priority:** High.

### Completed

- Responsive company selector (replaced fixed 220px cap with token-based side reserve)
- Ellipsis for long company names (multi-company Streamlit button `p` + single-company `.erp-hdr-mobile-co`)
- Toolbar cluster — bell + profile as one right-side group (32×32 controls, 8px gap)
- Unified spacing via layout tokens (`--hdr-toolbar-cluster-w`, `--hdr-toolbar-edge`, `--hdr-toolbar-gap`)
- Header ownership cleanup — `mobile_header.css` owns mobile header; `theme.css` mobile block reconciled for padding/gap conflicts only
- Company switch parity verified — header `hdr_mobile_co_switch_btn` is canonical; Profile “Switch Company” opens the same `co_switch` sheet
- No duplicate mobile company switch menu (`show_co_switch_link=True`; no inline `_render_company_switch_menu()` on mobile profile)

**Tests:** `tests/test_mobile_header_compact.py` extended (7 HDR-01 contract tests). Host `pytest tests/` — **807/807 passed**.

**Decision:** Header company selector remains the canonical company switch entry point. Profile “Switch Company” remains available but opens the same `co_switch` sheet. No company-switch logic duplication.

### Implementation notes

- `ui/mobile_header.css` remains owner of mobile header styling.
- `ui/mobile_shell.css` still contains a fixed `84px` title reserve; it currently matches active token values (`--hdr-title-side-reserve` = 72px + 12px). Future header spacing changes must be audited before modifying the shell reserve.
- No new `--hdr-h` definitions added. No `app.py` changes required — switch wiring was already correct.

Full audit + closure: [docs/AUDIT_HISTORY.md](./docs/AUDIT_HISTORY.md) §2026-06-10 HDR-01.

---

## UX-03 — Inline Expense Category Creation

**Status:** ✅ **Closed** (2026-06-10). **Priority:** High.

### Completed

- Shared helper `_cat_create_or_reactivate(session, txn_type, name)` — strip/normalize, case-insensitive dedup, company-scoped, reactivate inactive duplicate, create otherwise; `_cat_add_dialog` refactored to call it.
- Expense-only CTA in mobile category list picker (`expense_cat`): search with zero matches shows `+ Add "{name}"` when `_can("manage_categories")`.
- On CTA tap: create/reactivate → `_mob_at_apply_category_pick(..., txn_type="Expense")` → close picker → rerun; last-used category memory updated; outside-top-5 promotion via existing quick-chip logic.
- Locale: `txn.mob.add_category_cta` (EN/TR).
- Sale/Purchase workflows, subcategory workflow, and main AT panel layout unchanged. QUICK-ENTRY-02 remains deferred.

**Tests:** `tests/test_ux03_inline_category.py` (11 tests). Host `pytest tests/` — **818/818 passed**.

**Ownership:** `app.py` picker-sheet helpers · `registry/locales/transactional.py` · no `mobile_txn.css` changes required.

---

## UX-04A — Post-Save State Retention

**Status:** ✅ **Closed** (2026-06-10). **Priority:** Medium (UX-04 sub-item).

### Completed

- `_at_clear_post_save_transient_fields()` — post-save reset in `_at_process_submit` (desktop + mobile).
- **Clear after save:** `at_amount_display`, `at_notes_field`, `at_cust`, `at_cust_sel`, `at_payable_id`, `at_last_vendor`, worker gross/deduction/advance fields (desktop + mobile keys).
- **Retain after save:** `at_last_cat_id` (fixes desktop subcategory clearing), transaction type, payment method, category, subcategory, vendor, date, currency, bank account, quick-entry memory.
- No changes to `_at_save`, `_COMPANY_SCOPED_AT_KEYS`, or accounting/posting logic.

**Tests:** `tests/test_ux04a_post_save_retention.py` (8 tests). Host `pytest tests/` — **826/826 passed**.

---

## Repeat Last Transaction (v1)

**Status:** ✅ **Closed** (2026-06-10). **Priority:** Medium (UX-04 sub-item).

### Completed

- Transaction History row action **Repeat** (🔁) for eligible non-void **Expense** (non-salary) and **Purchase** rows only.
- Prefills Add Transaction and navigates there; user must press Save manually (no auto-save).
- Explicit allowlist copy: type, active category/subcategory, coerced payment method, currency, active vendor (Purchase), amount, notes; date → today.
- Guards: void, company scope, inactive category/vendor drop, PM coercion, forbidden fields never copied.

**Tests:** `tests/test_ux04_repeat_transaction.py` (20 tests). Host `pytest tests/` — **872/872 passed**.

**Not in v1:** Sale, Credit Sale, Salary/Worker Expense, Customer/Supplier Payment, Bank Transaction, post-save flash Repeat button.

---

## UX-04C — Safe Smart Defaults

**Status:** ✅ **Closed** (2026-06-10). **Priority:** Medium (UX-04 sub-item).

### Completed

- Per-type PM memory (`mob_at_last_pm_sale` / `expense` / `purchase`) — remembered on PM chip tap.
- Default chain: memory → `_AT_DEFAULT_PM` → first allowed; invalid memory falls back safely.
- Type switch restores valid remembered PM via `_mob_at_coerce_pm_type` tracking.
- Memory keys in `_COMPANY_SCOPED_AT_KEYS` (cleared on company switch).
- Single-bank auto-pick when PM requires Bank and exactly one active account (`_at_apply_single_bank_auto_pick`).
- No inference for customer, vendor, worker, subcategory, amount, payable/invoice, or multi-bank/CC.

**Tests:** `tests/test_ux04c_smart_defaults.py` (12 tests). Host `pytest tests/` — **852/852 passed**.

---

## UX-STABILIZE-01 — Data-Entry State Cleanup

**Status:** ✅ **Closed** (2026-06-05). **Priority:** Medium (operational friction / OBS-01 follow-up).

### Completed

- **`_at_is_worker_expense_entry()`** — single gate for mobile Salary chip + desktop worker expense radio.
- **Worker salary isolation** — clear category session keys when entering worker mode; `_mob_at_c_apply_type(Salary)` sets worker state; `_at_gather_submit_fields` skips category resolution in worker mode; desktop/mobile render branches call `_at_clear_category_session_state()`.
- **Post-save category reset** — `_at_clear_post_save_transient_fields()` reuses `_at_clear_category_session_state()` (RETENTION-01: keep section + date only).
- **Navigation scroll** — `_scroll_main_to_top()` on `_current_page` change (same zero-height `components.html` pattern as session-restore cookie).
- **Submit type** — desktop/mobile submit uses `_at_effective_txn_type()` consistently (Salary idx 6 → Expense worker path).

**Docs:** [docs/UX_STABILIZE_01_DATA_ENTRY_STATE.md](./docs/UX_STABILIZE_01_DATA_ENTRY_STATE.md)

**Tests:** `tests/test_ux_stabilize_01_data_entry_state.py` + existing `test_ux04a_post_save_retention.py`, `test_add_txn_fix01.py`, `test_add_txn_fix01::test_worker_salary_cash_posting_succeeds`.

**Regression fix (2026-06-05):** Desktop branch used `expense_mode == "worker"` while mobile Salary tab flags could set `_at_is_worker_expense_entry()` without syncing `at_expense_mode`; shared `_at_render_worker_expense_panel()` + presync/transition helpers. Tag: `ux-stabilize-01-worker-form-regression-fix`.

**Out of scope:** posting/accounting logic, PostgreSQL migration, NAV_ARCH untracked files.

---

## UX-04B — Payment Method Chips (mobile)

**Status:** ✅ **Closed** (2026-06-10). **Priority:** Medium (UX-04 sub-item).

### Completed

- Row 1 reduced to **Type | Date | Currency** (PM removed from picker trigger).
- New `_mob_at_render_pm_chip_row` between Row 1 and category chips — uses `_at_sale_pay_methods`, `_at_expense_pay_methods`, `_at_purchase_pay_methods` (no duplicated method lists).
- Active PM = solid selected chip; tap sets `at_pm` + `_at_clear_stale_payment_account_keys`.
- Mobile `"payment"` picker branch and `_mob_at_render_payment_picker_sheet` retired.
- Bank Transaction skips PM row; `mob_at_pm2` subtype row unchanged.
- Company CC chip gated by existing `_company_cc_charge_ready`; short label `txn.pm.company_cc_short`.
- CSS: `mob_at_pm_row` in `mobile_txn.css` + AT-LIGHT-01 wrapper strip; selected chip rule extended in `widgets.css`.
- Desktop AT unchanged; post-save retains `at_pm`.

**Tests:** `tests/test_ux04b_payment_method_chips.py` (14 tests). Host `pytest tests/` — **840/840 passed**.

---

## UX-04 — Selector Interaction Audit

**Status:** ✅ **Closed** (2026-06-10) · **Priority:** Medium · UX-04A/B/C + Repeat v1 delivered.

**Decision heuristic:** cardinality × frequency. Few options used every transaction → chips; long or searchable lists → picker sheets.

| Selector | Decision |
|---|---|
| Payment method | Likely first action — convert to chips (3–4 options, own row, last-used preselected) |
| Date | **Remains picker** — no change in this item |
| Currency | Keep picker; seed last-used per company |
| Transaction type | Keep picker (Concept C Row 1) |
| Vendor / customer / bank / invoice / payable | Keep pickers (searchable lists) |

**Constraint:** Chip active/idle colour grammar lives in `widgets.css` per the MOBILE-14 E8 ruling; layout in `mobile_txn.css`. Do not recreate the pre-Concept-C Row 1 crowding.

---

## UX-05 — Universal Outside-Tap Dismiss

**Status:** 📋 Backlog · **Priority:** Low · **Sequenced last.** Requires a separate infrastructure audit and its own CSS contract tests before approval.

**Concept:** One reusable scrim-button dismissal pattern (`_render_scrim_dismiss(surface)`) anchored on the existing `_mobile_open_surface()` / `_mobile_close_app_surfaces()` lifecycle. Desktop popovers already dismiss natively — mobile session-state surfaces (hub sheets, AT picker, profile, notifications) are the gap.

**Known constraints (recorded, not yet audited):**

- Streamlit has no native outside-tap event for session-state surfaces; a transparent full-viewport scrim button is the only clean mechanism.
- Company-switch confirm must never outside-dismiss (destructive decision).
- AT picker dismiss must provably preserve in-progress entry state (needs a test).
- Z-index / pointer-events regression history (popover click-trap guards in TEST_COVERAGE_MAP).
- Must land after MOBILE-14 — do not build a universal overlay layer on unresolved ownership conflicts.

---

## CHART-01 — Chart Theme Consolidation

**Status:** 📋 Planned · **Priority:** Medium · **Independent** of MOBILE-14 and MOBILE-13. Can be executed in any order relative to other roadmap items.

**Purpose:** Make all charts (Plotly, Altair) inherit ERP theme tokens — eliminating hardcoded chart backgrounds, text colours, and grid colours that break in dark mode or during theme switches.

### Scope

| Item | Action |
|---|---|
| `chart_theme()` helper in `ui/theme.py` | New function returning a Plotly layout dict populated with `var(--theme-*)` values (bg, paper_bg, font colour, gridcolor, zerolinecolor) |
| 7 chart / plot call sites in `app.py` | Wrap each with `chart_theme()` — visual only, no data change |
| `ui/widgets.css` | Scoped background override so chart containers inherit `--theme-card` rather than Streamlit's default white |

**Constraint:** Visual only. No data, calculation, or schema changes.

---

## AUDIT-01 — ERP Ownership Audit Findings

**Status:** ✅ Complete — June 2026
**Purpose:** Record the final ownership audit results for all UI areas and establish priorities for consolidation work. This section is a reference document — no implementation is included here.

### Critical Ownership Conflicts

Conflicts shared with CSS-01 are referenced rather than restated — see CSS-01 blocking issues table for full detail. Conflicts found only during the full-ERP audit are stated in full below.

| Conflict | Detail | Resolution Path |
|---|---|---|
| `--hdr-h` token — 4-way split | See **CSS-01 C2** | MOBILE-14 **M1** |
| `widgets.css` KPI catch-all | See **CSS-01 C1** | MOBILE-14 **M5** |
| Mobile ownership drift (layout grids) | See **CSS-01 C4** | **Complete** (E4–E6, E9) — contract tests only |
| Sidebar hide — 3 rules in 2 files | `theme.css @media`, `mobile_shell.css @media`, `mobile_shell.css html.erp-mobile` all hide sidebar on mobile | MOBILE-14 **M6** — single owner only if safe |
| Notification active state — duplicated | `widgets.css` AND `mobile_header.css` | MOBILE-14 **M6** — `hdr_toolbar_row` rules in `widgets.css` are **live for legacy desktop**; do not delete blindly; likely permanent two-owner exception or liveness contract |
| Reports internal duplicate | `.erp-mobile-report-filters` visibility set twice inside `theme.css` (lines 1107 and 1354) | Independent quick win — remove line 1107; line 1354 is live |

### Architectural Findings

| Area | Finding |
|---|---|
| Dashboard | Ownership mostly clean — all `erp-dash-*` classes in `theme.css`. KPI catch-all in `widgets.css` addressed by MOBILE-14 **M5**. |
| Banking | Ownership mostly clean — no banking-specific CSS file; uses shared `theme.css` classes only. No mobile layout adaptation exists (future `mobile_banking.css`). |
| Mobile Reports | Ownership mostly clean — `mobile_reports.css` is isolated. Desktop reports have no dedicated ownership surface. |
| Company Picker | Almost no styling ownership — emits no `erp-*` classes; tiles are plain `st.button`. This is intentional pending LOGIN-01. |
| Mobile Banking | No dedicated CSS owner. If mobile banking is added, create `ui/mobile_banking.css` scoped to an `erp-banking-mobile-host` sentinel class, following `mobile_reports.css` as a template. |
| Desktop Reports | ✅ **R2 shipped** — chips-only selector desktop + mobile; `desktop_reports.css` chip layout; selectbox removed |

### Chart Findings

| Finding | Detail | Resolution Path |
|---|---|---|
| Incomplete chart theming | Only 2 of 8 chart instances use `chart_series_color()` / `chart_reference_color()` helpers | CHART-01 |
| Dark mode breakage | 6 `st.bar_chart` / `st.line_chart` instances render on Streamlit default white — breaks in dark mode | CHART-01 — replace with Altair + `chart_theme()` |
| No `chart_theme()` helper | Helper referenced in CHART-01 scope does not yet exist | CHART-01 |

### Login Findings

| Finding | Detail |
|---|---|
| Redesign unblocked | Login / Company Picker redesign unblocked after MOBILE-14 M1+M2; not started |
| Hardcoded color | `color:#9ca3af` in credentials hint — closed (formerly E12); verify in codebase before LOGIN-01 |
| No mobile layout | Desktop `st.columns([1, 2, 1])` centering does not adapt to mobile |
| Email-based auth | Remains future **AUTH-01** work — not in scope for LOGIN-01 |

### Quick Wins (Independent — No MOBILE-14 Dependency)

These three items are not tracked in MOBILE-14 and can be executed at any time with minimal risk:

1. **Reports duplicate rule** — remove `theme.css` line 1107 (`.erp-mobile-report-filters` visibility). Line 1354 is the live rule.
2. ~~**Dead desktop report host**~~ — **R2 closed:** desktop selectbox removed; chips canonical. Spacing polish deferred.
3. **Sidebar ownership decision** — document whether `mobile_shell.css html.erp-mobile` sidebar hide is intentional (JS-cookie guard) or redundant. Either add a comment or remove it.

The following are tracked inside MOBILE-14 — do not execute as independent tasks outside that plan:

- **Header notification duplicate** — **MOBILE-14 M6** (re-audit only; widgets.css desktop rules likely permanent)
- **Bottom nav / FAB / hub suppression in widgets.css** — **MOBILE-14 M3** (optional low-priority relocation)
- **Profile / co-switch suppression in widgets.css** — **MOBILE-14 M4** (optional low-priority relocation)
- **TXH `txh_actions_` grid in widgets.css** — independent micro-step; target owner `mobile_txn_history.css` (not `mobile_shell.css`)

**Cross-references:** CSS-01 · CSS-02 · MOBILE-14 · CHART-01 · LOGIN-01 · AUTH-01

---

## MOB-AT-C1 — Concept C Mobile Add Transaction UI

**Status:** ✅ Accepted as reference implementation — 2026-06-09.

**Design references:** [`docs/MOBILE_AT_CONCEPT_C.md`](./docs/MOBILE_AT_CONCEPT_C.md) (component detail) · [`docs/MOBILE_UI_SYSTEM.md`](./docs/MOBILE_UI_SYSTEM.md) (governing system)

**Scope (locked):**

| Item | Decision |
|------|----------|
| Mobile AT panel | ✅ Rewritten — Concept C "Full Pad" layout |
| Desktop AT form | 🚫 Unchanged |
| Posting / accounting logic | 🚫 Unchanged — `_at_save()` not touched |
| Database schema | 🚫 Unchanged |
| Banking, Reports, More, Header, Bottom Nav | 🚫 Unchanged |
| App-wide Concept C theme rollout | 📋 Deferred — mobile AT only for now |

**What changes:**

- 4-tab row + separate PM chips + date row → single compact **Row 1** (`[Type | Payment | Date | Currency]`) — each cell opens a bottom-sheet picker
- Category shown with type-coloured dot below Row 1 as full-width button
- Amount display → full-width **Save** button → 3×4 keypad (Save moved out of side column)
- Existing pickers (vendor, bank, payable, category sheets) reused unchanged
- New picker modes added: `"txn_type"`, `"payment"`, `"date"`, `"currency"`
- New session key `"at_picker_mode"` added to `_COMPANY_SCOPED_AT_KEYS`

**Colour tokens:** see `docs/MOBILE_AT_CONCEPT_C.md §Colour tokens`

**Files changed:** `app.py`, `ui/mobile_txn.css`, `docs/MOBILE_AT_CONCEPT_C.md`

---

## Phase 19 — VAT / tax

VAT enable, rates, inclusive/exclusive pricing, liability accounts, VAT reports, lock after first tax invoice.

---

## Phase 20 — Inventory integrity

Stock movements, valuation, COGS, counts, negative stock control, adjustments. Enable/disable/lock — not hide-only.

---

## Phase 21 — PostgreSQL / SaaS readiness

Review shared schema + `company_id` + RLS vs alternatives; tenant isolation tests; concurrency; impersonation audit. **Keep shared schema during dev** (frozen decision).

---

## Phase 22 — Subscription / billing

**Status:** Planned (after Phase 21 PostgreSQL / SaaS). **Will implement** — not optional.

| Area | Plan |
|------|------|
| **Trial (per company)** | On `create_company()`, start `trial` status; default **14 days** (configurable via `billing.trial_days`, e.g. 30). Store `trial_started_at`, `trial_ends_at` on `Company`. |
| **Extend trial** | Platform/owner admin sets new `trial_ends_at` or adds days; log to `AuditLog` (manual until payment gateway exists). |
| **Enforcement** | After company gate in `main()`: if `now > trial_ends_at` and status is `trial` → block with message (read-only export optional later). |
| **Paid plans** | Plans, entitlements, gateway, usage limits, `active` / `expired` / `suspended`; tie to registry `ModuleDef.entitlement` and `get_module_state`. |

**Explicitly NOT in earlier phases:** subscription tables, Stripe, trial gate (deferred here).

---

## Phase 23 — Email / invitation infrastructure

Password reset, verification, invite tokens, SMTP.

---

## Phase 24 — Advanced industry modules

Restaurant (POS, recipes), retail (barcode), services (projects), tourism (bookings). **Future only.**

---

## ROADMAP-UPDATE-01 — Approved Future Work Queue

**Status:** Approved (documentation only — 2026-06-05)  
**Scope:** Record approved future epics. **No runtime implementation** from this update alone.

### Architectural rules (all items below)

- **Service-first:** Models → Services → Tests → thin UI → FastAPI → React. No Streamlit business logic.
- **Explicit `company_id`** in services; serializable DTOs; contract tests.
- **Accounting integrity:** void → reverse → audit; no silent deletes.
- **Migration-safe:** FastAPI-ready reads/writes; React consumes same service layer later.
- **AI assist mode first:** suggestion + human review before any auto-post or auto-match.
- **Trusted auto-post / auto-match (when shipped):** requires learning history, confidence thresholds, **owner enablement**, full audit trail, and void/reversal safety. Never auto-post payroll, taxes, bank transfers, large expenses, unknown vendors, or multi-category uncertain receipts.

### Priority order (execution sequence)

| # | Epic | Notes |
|---|------|--------|
| 1 | **DASH-CASH-01** | Split liquid funds on Home dashboard |
| 2 | **RECEIPT-AI-01** | Audit / discovery before build |
| 3 | **RECEIPT-AI-02 / 03 / 04** | Learning · vendor detection · item extraction |
| 4 | **RECEIPT-AI-05 / 06 / 08** | Learning engine · confidence · correction feedback |
| 5 | **RECEIPT-AI-07** | Trusted vendor auto-post (owner-controlled; last in RECEIPT-AI chain) |
| 6 | **BANKING-UX-05** | AI statement matching (approval-first) |
| 7 | **AUTH-SESSION-02** | Remember device + session hardening |
| 8 | **DASH-KPI-01 … 03** | Forecast · runway · sales-by-payment-type |
| 9 | **AI-BOOKKEEPER-01** | Business explanation AI (read-only) |
| 10 | **FastAPI foundation** | [FUTURE-MIGRATION-01](#future-architecture--long-term-roadmap) Phase B |
| 10a | **NAV-ARCH** | Navigation single source of truth — after PG parity, before React · [§ NAV-ARCH](#nav-arch--navigation-single-source-of-truth) |
| 11 | **React migration** | [FUTURE-MIGRATION-01](#future-architecture--long-term-roadmap) Phase D — consumes NAV-ARCH `react_route` contract |

---

### DASH-CASH-01 — Split Liquid Funds

**Status:** 🟡 Audited · **S1 read helper shipped** (`services/read_balances.compute_liquid_position`) · **S2+ UI pending**

**Goal:** Show **Cash in Hand** separately from **Bank Balance** on Home dashboard + mobile chips — without changing posting or sub-ledger behavior.

| Rule | Detail |
|------|--------|
| Cash in Hand | GL **1000–1003** (Cash family) |
| Bank Balance | GL **1010–1013** (Bank family) |
| Exclude | **1150** Card Sales Clearing · **2110** Credit Card Payable |
| Source | GL journal-derived balances only (`calculate_account_balance` / `_for_period`) |
| Scope | Company-scoped · as-of date aware · multi-currency buckets |
| UI (pending) | Replace combined “Cash & Bank” sub-ledger column; desktop + mobile KPI chips |

**Slices:** S1 read DTO ✅ · S2 Home UI · S3 mobile chips · S4 i18n · S5 contract tests · S6 optional GL vs sub-ledger hint.

---

### AUTH-SESSION-02 — Remember Device / Session Hardening

**Status:** 🟡 **Partial** — IMPL-1 ✅ · IMPL-2 ✅ · **IMPL-3 idle extension ✅** · remember-device / revocation **open** — see [AUTH_SESSION_02_AUDIT.md](./docs/AUTH_SESSION_02_AUDIT.md) · [AUTH_SESSION_02_IMPL_3.md](./docs/AUTH_SESSION_02_IMPL_3.md).

**Scope (future):**

- Optional **remember-this-device** toggle (per login; default off) — IMPL-4+
- ~~Split **idle timeout** vs **absolute session expiry**~~ ✅ (IMPL-1/3)
- Future **FastAPI HttpOnly cookie** + JWT refresh integration (unify with `services/tokens.py`)
- Server revocation (`token_version`, optional `user_sessions` table)
- Aligns with AUTH-SESSION-01-IMPL-3 / IMPL-4 backlog in [AUTH_SESSION_01_IMPLEMENTATION.md](./docs/AUTH_SESSION_01_IMPLEMENTATION.md)

**Not in scope now:** weakening restore secret requirements or removing void/audit session rules.

---

### RECEIPT-AI — Receipt Intelligence Pipeline

**Status:** 📋 Future — **first release = assist/review only**; trusted auto-post is a later gated mode.

| ID | Name | Summary |
|----|------|---------|
| **RECEIPT-AI-01** | Receipt OCR Pipeline | Upload receipt → OCR/extract vendor, date, amount, line items → suggest category/subcategory/vendor/items → **expense draft** → user approves before posting. **Never auto-post unknown receipts.** |
| **RECEIPT-AI-02** | Supplier Learning | Learn vendor/category behavior from approvals (e.g. BİM → Grocery); store mappings + correction history. |
| **RECEIPT-AI-03** | Vendor Auto Detection | Detect known retail vendors (BİM, Metro, Migros, Getir, Carrefour, …); suggest creating vendor if missing. **Vendor-neutral core** — detection adapters, not hard-coded vendor logic in posting ([VENDOR-NEUTRAL-01](#vendor-neutral-01--vendor-neutral-architecture-rule)). |
| **RECEIPT-AI-04** | Item Extraction | Extract purchased line items; suggest inventory/item creation when missing; **item tracking optional/configurable**. |
| **RECEIPT-AI-05** | Learning Engine | Track approval counts + correction history; vendor/category/item mapping tables; confidence from repeated approvals. |
| **RECEIPT-AI-06** | Confidence Engine | **&lt;80%** → manual review · **80–95%** → prefill + confirm · **&gt;95% + 20 approvals** → eligible for auto-post · **&gt;99% + 100 approvals** → trusted vendor tier. |
| **RECEIPT-AI-07** | Trusted Vendor Auto-Post | Owner-controlled rules; auto-post **only** for trusted vendors/categories. **Never** auto-post: payroll, taxes, bank transfers, large expenses, unknown vendors, multi-category uncertain receipts. Must remain auditable + voidable. |
| **RECEIPT-AI-08** | Correction Feedback Loop | Persist AI suggestion vs user-approved values; feed corrections back into learning (RECEIPT-AI-05). |

**Integration note:** Builds on [STAFF-CAPTURE-01](#staff-capture-01--expense-draft--approval-pipeline) draft/approval patterns where applicable; OCR/ML adapters live outside `services/posting.py`.

---

### BANKING-UX-05 — AI Statement Matching

**Status:** 📋 Future — after RECEIPT-AI learning patterns mature; **user approval first**.

**Scope:**

- Import bank statement → AI-suggested matches to expenses/sales/transfers
- Learn recurring vendor/payment mappings from approved matches
- Future **trusted auto-match** rules (owner-enabled, auditable, reversible) — same confidence/approval gates as RECEIPT-AI

**Constraints:** No change to GL posting rules without explicit match confirmation in v1; extends [BANKING-UX-03](./docs/BANKING_UX_03_ROADMAP.md) reconciliation cockpit — does not replace it.

---

### DASH-KPI — Dashboard KPI Extensions

**Status:** 📋 Future — after DASH-CASH-01; read-only analytics over existing GL/txn data.

| ID | Name | Summary |
|----|------|---------|
| **DASH-KPI-01** | Daily Cash Forecast | Expected cash position next 7 days (scheduled inflows/outflows heuristic). |
| **DASH-KPI-02** | Cash Runway | Days of cash remaining from current liquidity ÷ average daily expenses. |
| **DASH-KPI-03** | Sales by Payment Type | Dashboard KPI: Cash / Card / Credit sales (period-aware; company-scoped). |

**Rules:** Service-layer compute DTOs; no new posting types; optional mobile chips mirroring DASH-CASH-01 pattern.

---

### AI-BOOKKEEPER-01 — Business Explanation AI

**Status:** 📋 Future — read-only advisory layer.

**Scope:**

- Explain profit changes month-over-month
- Explain expense/vendor trends
- Natural-language Q&A (“Why is profit lower this month?”) over **computed report DTOs** — not raw JE mutation

**Rules:** No autonomous posting; citations to P&L/BS/GL aggregates; FastAPI/React-ready explanation service; optional LLM adapter behind interface ([VENDOR-NEUTRAL-01](#vendor-neutral-01--vendor-neutral-architecture-rule)).

---

## ROADMAP-UPDATE-02 — AI Learning + POS/Z-Report Queue

**Status:** Approved (documentation only — 2026-06). **No implementation, no schema change, no `app.py` change** from this update alone. Inherits all [ROADMAP-UPDATE-01 architectural rules](#roadmap-update-01--approved-future-work-queue) (service-first, explicit `company_id`, void→reverse→audit, migration-safe, assist-mode-first, owner-gated trusted auto-post).

### AI-LEARNING-01 — Human-first learning workflow (shared rule)

The single learning contract shared by **Receipt AI** and **POS AI** (and any future document AI):

- **Unknown documents must ask the user what they are** — never guess a document's type.
- **User classifies the document:** `expense receipt` · `POS/Z-report sales receipt` · `bank/card slip` · `other`.
- **User confirms** vendor/source, category, payment method, and **posting destination** before anything is stored.
- **System stores the approved pattern** (document type + source signature + confirmed mapping).
- **Future similar documents are prefilled** from the stored pattern (suggestion only).
- **Trusted auto-post is allowed only after** repeated approvals **and** high confidence **and** owner enablement **and** audit-log capture **and** void/reversal safety. Absent any one of these → fall back to review.

This rule governs the shared learning engine ([RECEIPT-AI-05](#receipt-ai--receipt-intelligence-pipeline)); POS AI reuses it rather than inventing a parallel learner.

### POS-AI — Daily POS / Z-Report Intelligence

**Status:** 📋 Future — **first release = suggest/review only**; trusted auto-post is a later gated mode. Reuses the Receipt-AI document-understanding + learning pattern.

| ID | Name | Summary |
|----|------|---------|
| **POS-AI-01** | Daily POS/Z-Report OCR | Upload POS daily report / Z-report / system sales receipt → extract date, cash sales, card sales, credit sales (if present), refunds, voids, tax, totals. **First phase: suggest only; user approves.** |
| **POS-AI-02** | POS Source Learning | After user approval, learn the POS **format/source**, **where cash/card totals appear**, and whether the report is a **daily total**, **shift total**, or **terminal total**. |
| **POS-AI-03** | Trusted POS Auto-Post | Owner-controlled; only after enough approvals + high confidence. Posts via **existing sales/posting logic**: Cash sales → **Cash**; Card sales → **Card Sales Clearing**; Credit sales → **Receivables** (if supported). Must be **audit-logged** and **void/reversal safe**. |
| **POS-AI-04** | Duplicate Z-Report Protection | Prevent posting the same POS daily report twice via **date / source / terminal / total / hash** matching. |

### POS auto-post safety rules (hard gates)

- **Never auto-post an unknown format.**
- **Never auto-post unclear dates.**
- **Never auto-post a duplicate daily report.**
- **Never auto-post mismatched totals** (line/section sums must reconcile to the stated total).
- **Always fall back to review** when any gate is not satisfied.

### Priority queue note

- **Receipt AI and POS AI share the same learning engine** (AI-LEARNING-01 / RECEIPT-AI-05) — one document-understanding + pattern-store, two document families.
- **Receipt AI goes first** to build document understanding (classification, source signature, confirm-then-store, confidence).
- **POS AI reuses that pattern later** — it sequences **after the RECEIPT-AI learning/confidence chain** (after RECEIPT-AI-05/06) and before/alongside BANKING-UX-05, sharing the same confidence + owner-enablement + audit + void gates. No separate learner is built for POS.
- **POS-CONFIG-01** (per-company `pos.*` settings) **precedes POS-AI implementation** — settings determine verification source, duplicate keys, and auto-post policy ([§ POS-CONFIG-01](#pos-config-01--sales-source--reconciliation-settings)).

---

## POS-CONFIG-01 — Sales Source & Reconciliation Settings

**Status:** 📋 **Spec approved (documentation only — 2026-06-15)** — no registry/UI/schema change from this section alone.

**Purpose:** Allow **each company** to configure how sales are imported, verified, and reconciled. **No company-wide assumptions.** **Settings determine AI behaviour.**

**Future UI:** **Settings → Sales & POS Configuration**

**Spec:** [docs/POS_CONFIG_01_SPEC.md](./docs/POS_CONFIG_01_SPEC.md)

### Configuration domains

| Domain | Options (summary) |
|--------|-------------------|
| **Sales Source** | External restaurant system · Built-in ERP/POS · Hybrid |
| **Verification Source** | POS Z-report · Terminal slips · System report · Bank settlement · None |
| **Card Verification Mode** | Z-report · Terminal slips · Bank statement · Manual only |
| **Cash Source** | System report · ERP sales · Manual cash count · Z-report · Hybrid |
| **Duplicate Protection** | Date · Terminal ID · Report number · Batch number · Total · Hash |
| **Auto-post** | Disabled · Suggest only · Owner approval required · Trusted auto-post |
| **Document Classification** | Terminal slip · Z-report · Daily system report · Shift report · Manual cash count · Unknown |
| **Workflow Mode** | External sales workflow · ERP/POS workflow |

### Rules (locked)

- Per-`company_id` only — explicit `company_id` in config services.
- Default auto-post = **suggest only**; trusted auto-post requires owner enablement + learning history + audit + void safety (inherits AI-LEARNING-01).
- Vendor-neutral core — free-text `source_name`; no named POS in posting paths ([VENDOR-NEUTRAL-01](#vendor-neutral-01--vendor-neutral-architecture-rule)).
- Complements existing `banking.card_settlement_enabled` and [DAILY-SALES-CLOSE-01](#daily-sales-close-01--external-sales-verification-dsc) — does not replace them in Phase A.

### Implementation slices

| Slice | Scope |
|-------|--------|
| **POS-CONFIG-01-AUDIT** | ✅ Spec + roadmap + contract tests |
| **POS-CONFIG-01-IMPL-1** | Registry `pos.*` keys + `get_pos_config(company_id)` DTO |
| **POS-CONFIG-01-IMPL-2** | Settings UI page |
| **POS-CONFIG-01-IMPL-3** | Wire DSC + banking to read `pos.*` |
| **POS-CONFIG-01-IMPL-4** | POS-AI consumes config DTO |

---

## Future Architecture / Long-Term Roadmap

Design direction and future-state targets only. **Does not change current development priorities.** Streamlit remains the primary application until migration readiness is achieved.

### FUTURE-MIGRATION-01

**Status:** Approved Long-Term Direction

**Target Architecture:**

```
React Frontend
↓
FastAPI Backend
↓
Service Layer (business/accounting logic)
↓
SQLAlchemy
↓
PostgreSQL
```

**Rationale:**

- Preserve existing accounting engine.
- Preserve SQLAlchemy models.
- Preserve reporting logic.
- Preserve automated test suite.
- Support future mobile applications.
- Support staff portal.
- Support API integrations.
- Support multi-user deployment.
- Provide enterprise-grade UI/UX.

**Migration Principles:**

1. No rewrite while Streamlit ERP is under active feature development.
2. Streamlit remains the primary application until migration readiness is achieved.
3. Accounting logic must be extracted into reusable service modules.
4. Business rules must never depend on UI implementation.
5. Existing tests must remain authoritative.
6. Migration will be incremental, not big-bang.
7. PostgreSQL becomes the target production database.
8. Streamlit and FastAPI may coexist during transition.

**Pre-Migration Requirements:**

- Daily Sales Close complete
- Recipe Costing complete
- User Access complete
- Staff Capture complete
- Date System stabilization complete
- Service-layer extraction roadmap approved

**Architecture Preparation Phase:**

| Phase | Scope |
|-------|--------|
| **A** | Move business logic from `app.py` into `services/` |
| **B** | Introduce FastAPI alongside Streamlit |
| **C** | Expose accounting services through API endpoints |
| **D** | Build React frontend module-by-module |
| **E** | Retire Streamlit UI only after feature parity |

**Decision Gate:**

Before starting implementation of FastAPI + React migration:

- Obtain independent architectural review from Claude.
- Compare FastAPI + React versus any alternative architecture at that time.
- Reconfirm migration strategy against current project size and requirements.

**Notes:**

Current platform remains:

- Python
- Streamlit
- SQLite
- SQLAlchemy

Migration target is future-state only and does not change current development priorities.

**Related:** [ARCHITECTURE-PROTECTION-01](#architecture-protection-01--service-first-development-rule) · [VENDOR-NEUTRAL-01](#vendor-neutral-01--vendor-neutral-architecture-rule) · [MIGRATION-READINESS-01](#migration-readiness-01--fastapireact-ready-service-checklist) · [FUTURE-MIGRATION-AUDIT-01](#future-migration-audit-01--fastapi-readiness-audit)

### FUTURE-MIGRATION-AUDIT-01 — FastAPI Readiness Audit

**Status:** Recorded (independent architectural review — Claude, 2026-06-13). **Superseded for blocker/keystone truth by** [DOCS-MIGRATION-CHECKPOINT-01](./docs/DOCS_MIGRATION_CHECKPOINT_01.md) (2026-06).

**Migration readiness score:** **62 / 100** (historical baseline — not re-scored here)

Does **not** authorize FastAPI/React implementation start. Baseline assessment only — satisfies the *readiness review* input to [FUTURE-MIGRATION-01](#future-migration-01) decision gate; full gate still requires strategy reconfirmation at implementation time.

| Dimension | Assessment (2026-06-13 baseline) | Updated (DOCS-MIGRATION-CHECKPOINT-01) |
|-----------|-----------------------------------|----------------------------------------|
| **Strength** | New `services/` modules FastAPI-ready — explicit IDs, DTOs, contract tests | Unchanged |
| **Main blocker (historical)** | `app.py` posting engine | **Resolved** — POSTING-SERVICE-01 complete |
| **Current focus** | — | Banking extraction, API hardening, session idle, decimal/PG |

**Also tracked (migration prep — status per DOCS-MIGRATION-CHECKPOINT-01):**

| ID | Scope | Status |
|----|--------|--------|
| [POSTING-SERVICE-01](#posting-service-01--keystone-migration-task) | GL posting engine | ✅ Complete |
| [MONEY-DECIMAL-01](#money-decimal-01) | `Float` → `Decimal` audit | ✅ Audit |
| [MONEY-DECIMAL-02](#money-decimal-02) | Golden posting vectors (Float baseline) | ✅ Complete |
| [MONEY-DECIMAL-03](#money-decimal-03) | `services/money.py` Decimal helpers | ✅ Complete |
| [MONEY-DECIMAL-04-CHAR](#money-decimal-04-char) | Posting kernel money math characterization | ✅ Complete |
| [MONEY-DECIMAL-04a](#money-decimal-04a) | Wire `services.money` at posting boundaries | ✅ Complete |
| [MONEY-DECIMAL-04b-CHAR](#money-decimal-04b-char) | Profit allocation rounding characterization | ✅ Complete |
| [MONEY-DECIMAL-04b](#money-decimal-04b) | Allocation `money_to_float` wiring | ✅ Complete |
| [MONEY-DECIMAL-04c+](#money-decimal-04c) | JE guard & FX native Decimal boundary verification | ✅ Complete |
| [MONEY-DECIMAL-05-IMPL-1](#money-decimal-05-impl-1) | Alembic `0002_money_numeric` revision | ✅ Complete |
| [P3.8-L-EXEC](#p38-l-exec) | Alembic authority bake-in execution | ✅ Complete |
| [P3.8-L-TESTS](#p38-l-tests) | Alembic authority bake-in characterization gate | ✅ Complete |
| [P3.8-N](#p38-n) | Alembic authority default flip | ✅ Complete |
| [P3.9-A](#p39-a) | migrate_schema() retirement readiness audit | ✅ Complete |
| [P3.9-B-CHAR](#p39-b-char) | migrate_schema() caller inventory | ✅ Complete |
| [P3.9-B](#p39-b) | migrate_schema() deprecation warning | ✅ Complete |
| [P3.9-C](#p39-c) | migrate_schema() implementation removal | ✅ Complete |
| [ALEMBIC-01](#alembic-01) | Alembic replaces `migrate_schema()` | ✅ Complete — P3.9-C no-op stub; Alembic-only evolution |
| [BANKING-SERVICE-01](#banking-service-01) | Banking subledger logic | 🟡 Partial |
| [REPORTS-SERVICE-01](#reports-service-01) | Report query/aggregation | 🟡 Partial (query layer) |
| [CONTEXT-AUDIT-01](#context-audit-01) | Streamlit `_erp()` / session coupling | Open |

Register: [TECH_DEBT_AND_MIGRATION_CLEANUP.md § FUTURE-MIGRATION-AUDIT-01](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md#future-migration-audit-01-2026-06-13).

**🚧 Build gate (owner decision, 2026-06-13, updated 2026-06):** no large new Streamlit UI surfaces before **banking extraction** and **API hardening** land. Allowed meanwhile: OBS-01 friction fixes, service-first screen-light phases, thin UI over existing services. See [§ Current priority](#current-priority).

#### POSTING-SERVICE-01 — Keystone migration task

**Priority:** Critical (migration prep) — **complete**  
**Status:** ✅ **Complete** (PS-P0 through PS-P6-5; FASTAPI-REACT-01 boundary hardening). Source of truth: [POSTING_SERVICE_01_STATUS.md](./docs/POSTING_SERVICE_01_STATUS.md).

Extract the accounting posting engine from `app.py` into a reusable service (`services/posting.py`):

- `create_journal_entry` + balance rules (normal/contra) — **shipped**
- Fiscal-period close guard — **shipped**
- Void/reversal via `create_reversing_journal_entry` — **shipped**
- Convenience wrappers (`post_cash_sale`, `post_purchase`, `post_expense`, …) — **shipped**
- Streamlit and FastAPI both call the same module; Staff Capture `post_fn` wires here (TD-SC-01) — **shipped**

**Deferred (post-boundary):** TD-PS-01 commit ownership, TD-PS-03 DTO route adapters, TD-POSTING-06 reconciliation `_app()` imports — see [FASTAPI_REACT_01_POSTING_BOUNDARY_AUDIT.md](./docs/FASTAPI_REACT_01_POSTING_BOUNDARY_AUDIT.md).

**Gate:** Contract tests against existing posting tests; zero GL behaviour change — **met** (`tests/test_posting_service01_*.py`).

#### MONEY-DECIMAL-01

**Priority:** High (migration prep)  
**Status:** ✅ **Audit complete** (2026-06-16) — 99 Float columns inventoried; PG **production** blocked until Numeric migration characterized

Replace `Float` money columns and arithmetic with `Decimal`/`Numeric` across models and services before PostgreSQL **production** runtime cutover. SQLite remains runtime; PG is test-only. Float engine swap is safe ([P3.1](./docs/P3_1_POSTGRES_COMPATIBILITY_AUDIT.md)); **Numeric semantics change** is the blocker.

**Audit:** [MONEY_DECIMAL_01_AUDIT.md](./docs/MONEY_DECIMAL_01_AUDIT.md) · contract: `tests/test_money_decimal_01_audit.py`

**Next slices:** ~~PG build + dual-run parity~~ ✅ · ~~runtime cutover prep~~ ✅ · ~~real SQLite→PG dry run~~ ✅ · ~~production runtime cutover~~ ✅ → **React migration**

Aligns with [TD-MIG-04](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md#global-migration-td-mig).

#### MONEY-DECIMAL-02

**Priority:** High (migration prep)  
**Status:** ✅ **Complete** (2026-06-16) — golden Float posting vectors pinned before Decimal conversion

Tests-only slice: captures current JE balance guard, basic posting at **100.01**, profit-allocation penny absorption, multi-line accumulation, void/reversal symmetry, report/GL parity, and TRY/USD/EUR `amount_native` rounding.

**Doc:** [MONEY_DECIMAL_02_GOLDEN_VECTORS.md](./docs/MONEY_DECIMAL_02_GOLDEN_VECTORS.md) · contract: `tests/test_money_decimal_02_golden_posting_vectors.py`

**Rules honored:** no production code, schema, Alembic, or Decimal changes.

#### MONEY-DECIMAL-03

**Priority:** High (migration prep)  
**Status:** ✅ **Complete** (2026-06-16) — pure `services/money.py` parse/quantize helpers; not wired into posting

Centralizes `Decimal` boundary parsing and `ROUND_HALF_UP` quantization (2/4/8 dp) for future MD-04 posting-kernel migration. No schema, model, Alembic, or posting changes.

**Doc:** [MONEY_DECIMAL_03_HELPERS.md](./docs/MONEY_DECIMAL_03_HELPERS.md) · contract: `tests/test_money_decimal_03_money_helpers.py`

#### MONEY-DECIMAL-04-CHAR

**Priority:** High (migration prep)  
**Status:** ✅ **Complete** (2026-06-16) — posting kernel Float money math characterized before Decimal wiring

Tests-only slice: source-level audit of `services/posting.py` (no `services.money` / no `decimal` import), JE balance guard, post_* amount passthrough, allocation rounding, void symmetry, report dependency chain, and MD-02 manifest alignment.

**Doc:** [MONEY_DECIMAL_04_POSTING_MATH_CHAR.md](./docs/MONEY_DECIMAL_04_POSTING_MATH_CHAR.md) · contract: `tests/test_money_decimal_04_char_posting_math.py`

**Rules honored:** no posting, model, schema, Alembic, or Decimal wiring changes.

#### MONEY-DECIMAL-04a

**Priority:** High (migration prep)  
**Status:** ✅ **Complete** (2026-06-16) — `services.money` wired at safe posting amount boundaries

Posting-only slice: `_normalize_money_amount` (`money_to_float`) on sale/expense/purchase/bank post paths; `_je_line_money` (`parse_money` → float) on JE line debit/credit. Balance guard, allocation, FX native, reports, and Float columns unchanged.

**Doc:** [MONEY_DECIMAL_04A_POSTING_HELPERS.md](./docs/MONEY_DECIMAL_04A_POSTING_HELPERS.md) · parity: MD-02 + MD-04-CHAR + `test_posting_service01_*`

#### MONEY-DECIMAL-04b-CHAR

**Priority:** High (migration prep)  
**Status:** ✅ **Complete** (2026-06-16) — profit/loss allocation float rounding characterized before Decimal changes

Tests-only slice: pins Python `round` share loop, last-partner remainder absorption, profit/loss JE orientation, void reversal, 0.01 edge cases, share validation messages, and no `services.money` in allocation kernel.

**Doc:** [MONEY_DECIMAL_04B_PROFIT_ALLOCATION_CHAR.md](./docs/MONEY_DECIMAL_04B_PROFIT_ALLOCATION_CHAR.md) · contract: `tests/test_money_decimal_04b_char_profit_allocation_rounding.py`

**Rules honored:** no posting, model, schema, Alembic, or Decimal wiring changes.

#### MONEY-DECIMAL-04b

**Priority:** High (migration prep)  
**Status:** ✅ **Complete** (2026-06-16) — allocation share loop uses `_allocation_share_float` → `money_to_float`

Replaces built-in `round(..., 2)` in `allocate_profit_to_partners` with `services.money` while preserving MD-04b-CHAR + MD-02 golden vectors (last-partner absorption, penny splits, JE orientation, void symmetry).

**Doc:** [MONEY_DECIMAL_04B_PROFIT_ALLOCATION_HELPERS.md](./docs/MONEY_DECIMAL_04B_PROFIT_ALLOCATION_HELPERS.md) · contracts: `test_money_decimal_04b_char_profit_allocation_rounding.py` + MD-02 allocation vectors

#### MONEY-DECIMAL-04c+

**Priority:** High (migration prep)  
**Risk:** Low  
**Behavior changes:** None  
**Status:** ✅ **Closed by verification** (2026-06-16) — JE guard float tolerance preserved (MD-02 locked); FX native via `persist_fx`; all posting money through `services/money.py`

Audit confirms MD-04a/04b/05-IMPL-3 already wired safe boundaries. Decimal JE balance guard **deferred** — would alter MD-02 accept/reject semantics.

**Doc:** [MONEY_DECIMAL_04C_JE_FX_DECIMAL.md](./docs/MONEY_DECIMAL_04C_JE_FX_DECIMAL.md) · contract: `tests/test_money_decimal_04c_je_fx_decimal.py` · tag: `money-decimal-04c-je-fx-decimal-guard`

#### POSTGRES-PG-BUILD — Alembic Build + Dual-Run Parity

**Priority:** High (migration prep)  
**Risk:** Low  
**Behavior changes:** None (test infrastructure only)  
**Status:** ✅ **Closed** (2026-06-16)

Wires PostgreSQL test databases through **`alembic upgrade head`** (revision `0002`, Numeric money). Extends P3.2 dual-run harness with **report fingerprints** (P&L / balance sheet). SQLite CI path unchanged (in-memory ORM).

**Doc:** [POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md](./docs/POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md) · contracts: `tests/test_pg_build_dual_run_parity.py` · `tests/test_p3_2_dual_run_parity.py` · tag: `postgres-pg-build-dual-run-parity`

**Not in scope:** production `DATABASE_URL` switch · applying `0002` to production `erp_data.db`

#### POSTGRES-RUNTIME-CUTOVER-PREP — SQLite→PG Data Migration Prep

**Priority:** High (migration prep)  
**Risk:** Low  
**Behavior changes:** None (test harness + parse-only gate)  
**Status:** ✅ **Closed** (2026-06-16)

Test-only SQLite file → PostgreSQL row copy on Alembic `0002` schemas; money snapshot parity on smoke tenant. Runtime cutover gate **wired** via `paths.get_database_url()`.

**Doc:** [POSTGRES_RUNTIME_CUTOVER_PREP.md](./docs/POSTGRES_RUNTIME_CUTOVER_PREP.md) · contracts: `tests/test_postgres_runtime_cutover_prep.py` · `tests/test_postgres_runtime_cutover_gate.py` · tag: `postgres-runtime-cutover-prep`

**Remaining:** ~~production-shaped migration~~ ✅ · ~~runtime wiring~~ ✅ · ~~operator backup/approval~~ ✅

#### POSTGRES-REAL-DRY-RUN — Copy-Only Migration Verified (2026-06-16)

**Priority:** High (migration prep)  
**Risk:** Low  
**Behavior changes:** None  
**Status:** ✅ **Verified** (operator dry run)

Real production-shaped SQLite copy migrated to disposable PostgreSQL (`ERP_TEST_POSTGRES_URL` → `erp_pytest`); Alembic `0002` PG build; row counts + trial balance + reports match for companies **1–4**. Production `erp_data.db` **not touched**.

**Doc:** [POSTGRES_REAL_DRY_RUN_20260616.md](./docs/POSTGRES_REAL_DRY_RUN_20260616.md) · contract: `tests/test_postgres_real_dry_run_20260616.py` · tag: `postgres-real-dry-run-20260616`

#### POSTGRES-PRODUCTION-CUTOVER — Runtime Wired (2026-06-16)

**Priority:** High (migration)  
**Risk:** Medium (operator-gated)  
**Behavior changes:** Runtime resolves to PostgreSQL when cutover env gates pass  
**Status:** ✅ **Verified** (testing environment)

Flag-gated PostgreSQL runtime; operator migration script; full parity + smoke verified. SQLite backup + rollback preserved.

**Doc:** [POSTGRES_PRODUCTION_CUTOVER.md](./docs/POSTGRES_PRODUCTION_CUTOVER.md) · contracts: `tests/test_postgres_production_cutover.py` · `tests/test_postgres_production_cutover_smoke.py` · tag: `postgres-production-cutover`

**Not decommissioned:** SQLite `erp_data.db` (rollback target)

#### MONEY-DECIMAL-05-IMPL-1

**Priority:** High (migration prep)  
**Status:** ✅ **Complete** (2026-06-05) — Alembic revision **`0002_money_numeric`** authored; **`money_numeric_columns.py`** pins 2/4/8-dp tiers (88 columns upgraded; 11 quantity/percentage/confidence stay Float); ephemeral SQLite `0001→0002` smoke; **`0001_baseline` untouched**; **`models.py` still Float**

Schema-only slice per [MONEY_DECIMAL_05_NUMERIC_MIGRATION_PLAN.md](./docs/MONEY_DECIMAL_05_NUMERIC_MIGRATION_PLAN.md). PG `ALTER … TYPE NUMERIC USING`; SQLite `batch_alter_table`. Quantization (ROUND_HALF_UP) deferred to **MD-05-IMPL-3**. Model `Numeric(asdecimal=True)` deferred to **MD-05-IMPL-2**. Not applied to production DB.

**Contract:** `tests/test_money_decimal_05_impl1_numeric_revision.py` · Alembic head now **`0002`**

#### MONEY-DECIMAL-05-IMPL-2

**Priority:** High (migration prep)  
**Status:** ✅ **Complete** (2026-06-16) — `models.py` uses `NUMERIC_MONEY` / `NUMERIC_FX` / `NUMERIC_RATE` (`asdecimal=True`); 88 money columns Numeric, 11 quantity/percentage/confidence remain Float; posting/read/write services + `app.py` route through `services/money.py`; MD-02 golden vectors unchanged; **`0002` not applied to production DB**

**Contract:** updated MD-01/MD-03/MD-05 tests · baseline **4611 passed** (+2 vs IMPL-1). Tag: `money-decimal-05-impl2-model-numeric`

#### MONEY-DECIMAL-05-IMPL-3

**Priority:** High (migration prep)  
**Status:** ✅ **Complete** (2026-06-16) — ROUND_HALF_UP consolidation through `services/money.py`; stale `BankAccount.balance` / payable writes fixed; `sync_account_balances` + `sync_bank_account_balances`; Alembic `0002` PG `ROUND(col::numeric, scale)` USING; `ingredients.cost_per_base_unit` in `NUMERIC_19_4`; removed `_normalize_money_amount` / `_allocation_share_float`; **`0002` not applied to production DB**

**Contract:** `test_money_decimal_05_impl3_*` · extended MD-03 · baseline **4625 passed** (+14 vs IMPL-2). Tag: `money-decimal-05-impl3-quantization-cache`. Doc: [MONEY_DECIMAL_05_IMPL_3.md](./docs/MONEY_DECIMAL_05_IMPL_3.md)

#### MONEY-DECIMAL-05-IMPL-4

**Priority:** High (migration prep)  
**Status:** ✅ **Complete** (2026-06-16) — Populated SQLite `0001→0002` smoke (index/FK/table integrity, money snapshot parity, post-migration posting); optional PG `@pytest.mark.optional_postgres` NUMERIC scale + `0.1+0.2=0.30` exactness; **`0002` SQLite supplemental index re-apply** after batch rebuild; **`0002` not applied to production DB**

**Contract:** `test_money_decimal_05_impl4_*` · `md05_migration_smoke_utils.py` · baseline **4633 passed** (+8 vs IMPL-3). Tag: `money-decimal-05-impl4-migration-smoke`. Doc: [MONEY_DECIMAL_05_IMPL_4.md](./docs/MONEY_DECIMAL_05_IMPL_4.md)

#### MONEY-DECIMAL-05-IMPL-5

**Priority:** High (migration prep)  
**Status:** ✅ **Complete** (2026-06-16) — `ERP_MONEY_NUMERIC_CUTOVER=1` + P3.8 backup/confirmation arms populated `0001→0002` startup upgrade; post-cutover GL + bank cache re-sync; `alembic_runner` passes `DATABASE_URL` + prefers `alembic` on PATH; **production `erp_data.db` still blocked**

**Contract:** `test_money_decimal_05_impl5_cutover_gate.py` · baseline **4651 passed** (+18 vs IMPL-4). Tag: `money-decimal-05-impl5-cutover-gate`. Doc: [MONEY_DECIMAL_05_IMPL_5.md](./docs/MONEY_DECIMAL_05_IMPL_5.md)

#### ALEMBIC-01

**Priority:** Medium (migration prep)  
**Status:** ✅ **Complete** — P3.8-K2 wired · **P3.8-L-EXEC ✅** · **P3.8-L-TESTS ✅** · **P3.8-N ✅** · **P3.9-A/B-CHAR/B/C ✅**; production `migrate_schema()` is **no-op stub**; schema evolution **Alembic-only**

Introduce Alembic revision chain; retire silent `ALTER TABLE` / `CREATE INDEX IF NOT EXISTS` pattern in `migrate_schema()` for schema evolution audibility. Required before multi-environment FastAPI deployment and PostgreSQL production cutover (P4.2 blocker #1).

**Completed slices:** P3.8-K2 startup wiring · P3.8-L bake-in review plan · P3.8-M local smoke · **P3.8-L-EXEC** · **P3.8-L-TESTS** · **P3.8-N** default flip · **P3.9-A** retirement readiness audit · **P3.9-B-CHAR** caller inventory · **P3.9-B** deprecation warning · **P3.9-C** implementation removal.

**Docs:** [P3_8_L_BAKEIN_AUDIT.md](./docs/P3_8_L_BAKEIN_AUDIT.md) · [P3_8_L_BAKEIN_EXEC.md](./docs/P3_8_L_BAKEIN_EXEC.md) · [P3_8_L_TESTS.md](./docs/P3_8_L_TESTS.md) · [P3_8_N_DEFAULT_FLIP.md](./docs/P3_8_N_DEFAULT_FLIP.md) · [P3_9_A_AUDIT.md](./docs/P3_9_A_AUDIT.md) · [P3_9_B_CHAR_MIGRATE_SCHEMA_CALLERS.md](./docs/P3_9_B_CHAR_MIGRATE_SCHEMA_CALLERS.md) · [P3_9_B_DEPRECATION.md](./docs/P3_9_B_DEPRECATION.md) · [P3_9_C_REMOVAL.md](./docs/P3_9_C_REMOVAL.md) · contracts: `test_p3_8_k2_startup_wiring.py` · `test_p3_8_l_exec_bakein_execution.py` · `test_p3_8_l_tests_bakein_characterization.py` · `test_p3_8_n_default_flip.py` · `test_p3_9_a_audit.py` · `test_p3_9_b_char_migrate_schema_callers.py` · `test_p3_9_b_deprecation.py` · `test_p3_9_c_removal.py`

#### P3.8-L-EXEC

**Priority:** Medium (migration prep)  
**Status:** ✅ **Complete** (2026-06-16) — automated throwaway-DB bake-in matrix + execution record; prior P3.8-M manual smoke referenced

Ran flag-on/off scenarios across real temporary SQLite DB states (at_head verify_only, unstamped block, ahead/unknown fail-closed, strict-new upgrade, populated behind_head block even with gate, rollback). No flag default change, no production DB mutation, no `migrate_schema()` retirement.

**Doc:** [P3_8_L_BAKEIN_EXEC.md](./docs/P3_8_L_BAKEIN_EXEC.md) · contract: `tests/test_p3_8_l_exec_bakein_execution.py`

#### P3.8-L-TESTS

**Priority:** Medium (migration prep)  
**Status:** ✅ **Complete** (2026-06-16) — §6 bake-in characterization gate (schema equivalence, single-caller guard, never-on-PG, lock-safety, flag-off parity)

Tests-only slice: pins retirement-prep invariants from [P3_8_L_BAKEIN_AUDIT.md](./docs/P3_8_L_BAKEIN_AUDIT.md) §6; complements P3.8-L-EXEC e2e scenarios and P3.4-D equivalence harness. No production code change, no flag default change, no `migrate_schema()` retirement.

**Doc:** [P3_8_L_TESTS.md](./docs/P3_8_L_TESTS.md) · contract: `tests/test_p3_8_l_tests_bakein_characterization.py`

#### P3.8-N

**Priority:** Medium (migration prep)  
**Status:** ✅ **Complete** (2026-06-16) — `ERP_ALEMBIC_AUTHORITATIVE` default-on; explicit `=0`/`false`/`off` opts out to legacy `migrate_schema()` path

Default flip slice: unset/empty env → Alembic authoritative startup; explicit opt-out restores `migrate_schema()` with no schema change. **`migrate_schema()` not removed** — P3.9 retirement remains separate.

**Doc:** [P3_8_N_DEFAULT_FLIP.md](./docs/P3_8_N_DEFAULT_FLIP.md) · contract: `tests/test_p3_8_n_default_flip.py`

#### P3.9-A

**Priority:** Medium (migration prep)  
**Status:** ✅ **Complete** (2026-06-05) — retirement readiness audit; Phase A done via P3.8-N; Phases B/C not started

Audit-only slice: prerequisite checklist, caller inventory, gap analysis vs Phases B/C, PostgreSQL implications. Verdict: **NOT READY to remove `migrate_schema()`** — next **P3.9-B-CHAR** → P3.9-B → P3.9-C.

**Doc:** [P3_9_A_AUDIT.md](./docs/P3_9_A_AUDIT.md) · contract: `tests/test_p3_9_a_audit.py`

#### P3.9-B-CHAR

**Priority:** Medium (migration prep)  
**Status:** ✅ **Complete** (2026-06-05) — caller inventory + P3.9-B deprecation warning contract pinned

Characterization-only slice: inventories production wiring, test harness direct/mock callers, and pins zero `DeprecationWarning` pre-B plus the exact warning message/`stacklevel=2` contract for P3.9-B. No production behavior change.

**Doc:** [P3_9_B_CHAR_MIGRATE_SCHEMA_CALLERS.md](./docs/P3_9_B_CHAR_MIGRATE_SCHEMA_CALLERS.md) · contract: `tests/test_p3_9_b_char_migrate_schema_callers.py`

#### P3.9-B

**Priority:** Medium (migration prep)  
**Status:** ✅ **Complete** (2026-06-05) — `DeprecationWarning` on every `migrate_schema()` call; body retained

Phase B slice: `MIGRATE_SCHEMA_DEPRECATION_MESSAGE` + `warnings.warn(..., DeprecationWarning, stacklevel=2)` at `migrate_schema` entry. Test harness callers updated; legacy `ERP_ALEMBIC_AUTHORITATIVE=0` path unchanged. **Not removed** — P3.9-C gated on warning-clean window.

**Doc:** [P3_9_B_DEPRECATION.md](./docs/P3_9_B_DEPRECATION.md) · contract: `tests/test_p3_9_b_deprecation.py`

#### P3.9-C

**Priority:** Medium (migration prep)  
**Status:** ✅ **Complete** (2026-06-05) — production DDL body removed; no-op stub + archived `tests/legacy_migrate_schema.py`

Phase C slice: `migrate_schema()` warns and returns without DDL; equivalence harness uses archived legacy body; flag-off path no longer evolves schema. **Alembic-only** production evolution.

**Doc:** [P3_9_C_REMOVAL.md](./docs/P3_9_C_REMOVAL.md) · contract: `tests/test_p3_9_c_removal.py`

#### BANKING-SERVICE-01

**Priority:** High (migration prep)  
**Status:** 🟡 **Partial** — `services/write_banking.py` (manual deposit/withdrawal/transfer) + `services/write_reconciliation.py` (match/unmatch API) + `services/read_reconciliation.py` shipped. **Open:** `reconciliation/match_post.py` and `reconciliation/company_card.py` `_app()` coupling (8 + 3 sites); Streamlit `render_banking` duplicate manual path; balance ownership asymmetry (TD-PS-08). **BS-02-CHAR ✅** — account-resolution characterization before `_app()` removal. Audit: [BANKING_SERVICE_01_AUDIT.md](./docs/BANKING_SERVICE_01_AUDIT.md).

#### REPORTS-SERVICE-01

**Priority:** Medium (migration prep)  
**Status:** 🟡 **Partial** — core read computations extracted via FASTAPI-P0 `services/read_*` (`read_reports`, `read_ledger`, `read_ar_ap`, `read_partner_statement`, `read_balances`, `read_reconciliation`). Streamlit **presentation** (`render_*` in `app.py`) remains by design until React Phase D.

#### CONTEXT-AUDIT-01

**Priority:** Medium (migration prep)  
**Status:** Open

Inventory and reduce Streamlit-only context coupling — `_erp()` lazy `import app`, `st.session_state`, `cq()` in `ui/` renderers. Related: TD-DSC-08, TD-UA-04, TD-SC-03/04. Output: shared `ui/context.py` or injected context protocol for FastAPI Phase D.

#### P2-HARDEN-01 — Company Stamp Audit

**Priority:** High  
**Risk:** Low  
**Behavior changes:** None  
**Status:** ✅ **Closed (2026-06-16)** — audit + H-01/H-02 complete; H-03 auto-stamp **deferred/rejected**

**Completed:**

- **H-01** — `tests/test_p2_harden_01_company_stamp_matrix.py` (parametrized write-family matrix; no fixture hook)
- **H-02** — P2 fixture fidelity; removed misleading `before_flush` from `test_fastapi_p2_*` db fixtures
- **H-03** — Systemic hook audit: **DEFER**; silent auto-stamp **rejected** — [P2_HARDEN_01_H03_AUDIT.md](./docs/P2_HARDEN_01_H03_AUDIT.md)

**Closure:** [P2_HARDEN_01_AUDIT_CLOSURE.md](./docs/P2_HARDEN_01_AUDIT_CLOSURE.md) · tag `p2-harden-01-company-stamp-audit`

**Standing rule:** explicit service-layer `company_id` stamping; no API `before_flush` auto-stamp.

**Optional follow-ups (non-blocking):** reconciliation match stamp asserts; fail-loud NULL guard at FastAPI runtime cutover only.

Register: [TECH_DEBT_AND_MIGRATION_CLEANUP.md § P2-HARDEN-01](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md#p2-harden-01-2026-06-14).

---

## Module state vocabulary (frozen)

| State | Meaning |
|-------|---------|
| **Hidden** | Navigation preference — module still exists (future: per-company More Hub customization — **MOBILE-07**) |
| **Disabled** | Functionality blocked (plan, safety, misconfiguration) |
| **Locked** | Setting/module frozen after use (e.g. base currency after first post) |

---

## Registry key quick reference

### Live today (backed by DB)

| Registry key | Legacy / storage |
|--------------|------------------|
| `company.display_name` | `Company.name` |
| `company.legal_name` | `Company.full_name` |
| `company.email` | `Company.email` |
| `company.phone` | `Company.phone` |
| `company.address` | `CompanySetting.company_address` |
| `company.tax_number` | `CompanySetting.company_tax_number` |
| `company.logo_url` | `CompanySetting.company_logo_url` |
| `accounting.base_currency` | `CompanySetting.currency` |
| `accounting.default_tax_rate` | `CompanySetting.tax_rate` |
| `accounting.fiscal_year_label` | `CompanySetting.financial_year` |

### Metadata only (defaults until later phases)

`company.timezone`, `accounting.fiscal_year_start_month`, `accounting.multi_currency_enabled`, `accounting.coa_template`, all `policy.*`, most `user.*`.

---

## Decision log

| Date | Decision |
|------|----------|
| 2026-06-05 | **FASTAPI-REACT-42 (closure)** — Backup & restore read page: thin `GET /api/v1/backup-status` + `BackupRestorePage` at `/settings/backup-restore` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-42-react-read-backup-restore`. Next: **FASTAPI-REACT-43**. |
| 2026-06-05 | **FASTAPI-REACT-41 (closure)** — Company settings read page: thin `GET /api/v1/company-settings` + `CompanySettingsPage` at `/settings/company` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-41-react-read-company-settings`. Next: **FASTAPI-REACT-42**. |
| 2026-06-05 | **FASTAPI-REACT-40 (closure)** — Permissions read page: thin `GET /api/v1/permissions/members` + `GET /api/v1/permissions/effective` + `PermissionsPage` at `/settings/permissions` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-40-react-read-permissions`. Next: **FASTAPI-REACT-41**. |
| 2026-06-05 | **FASTAPI-REACT-39 (closure)** — Budget read page: thin `GET /api/v1/reports/budget-vs-actual` + `BudgetPage` at `/books/budget` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-39-react-read-budget`. Next: **FASTAPI-REACT-40**. |
| 2026-06-05 | **FASTAPI-REACT-38 (closure)** — Inventory read page: thin `GET /api/v1/products` + `InventoryPage` at `/inventory` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-38-react-read-inventory`. Next: **FASTAPI-REACT-39**. |
| 2026-06-05 | **FASTAPI-REACT-37 (closure)** — Company members read page: thin `GET /api/v1/members` + `MembersPage` at `/settings/members` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-37-react-read-members`. Next: **FASTAPI-REACT-38**. |
| 2026-06-05 | **FASTAPI-REACT-36 (closure)** — Audit log read page: thin `GET /api/v1/audit-log` + `AuditLogPage` at `/settings/audit-log` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-36-react-read-audit-log`. Next: **FASTAPI-REACT-37**. |
| 2026-06-05 | **FASTAPI-REACT-35 (closure)** — Opening balances read page: thin `GET /api/v1/opening-balances` + `OpeningBalancesPage` at `/books/opening-balances` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-35-react-read-opening-balances`. Next: **FASTAPI-REACT-36**. |
| 2026-06-05 | **FASTAPI-REACT-34 (closure)** — Recon health read page: thin `GET /api/v1/reconciliation/health` + `ReconHealthPage` at `/books/recon-health` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-34-react-read-recon-health`. Next: **FASTAPI-REACT-35**. |
| 2026-06-05 | **FASTAPI-REACT-33 (closure)** — Trial balance read page: thin `GET /api/v1/reports/trial-balance` + `TrialBalancePage` at `/books/trial-balance` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-33-react-read-trial-balance`. Next: **FASTAPI-REACT-34**. |
| 2026-06-05 | **FASTAPI-REACT-32 (closure)** — Journal entries read page: thin `GET /api/v1/journal-entries` + `JournalEntriesPage` at `/books/journal-entries` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-32-react-read-journal-entries`. Next: **FASTAPI-REACT-33**. |
| 2026-06-05 | **FASTAPI-REACT-31 (closure)** — Fiscal periods read page: `FiscalPeriodsPage` wired to existing `GET /api/v1/fiscal-periods` at `/books/fiscal-periods` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-31-react-read-fiscal-periods`. Next: **FASTAPI-REACT-32**. |
| 2026-06-05 | **FASTAPI-REACT-30 (closure)** — Bank accounts read page: `BankAccountsPage` wired to existing `GET /api/v1/bank-accounts` at `/banking/accounts` (hidden NAV route) behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-30-react-read-bank-accounts`. Next: **FASTAPI-REACT-31**. |
| 2026-06-05 | **FASTAPI-REACT-29 (closure)** — Purchases read page: thin P1 list API (`GET /api/v1/purchases`) + `PurchasesPage` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-29-react-read-purchases`. Next: **FASTAPI-REACT-30**. |
| 2026-06-05 | **FASTAPI-REACT-28 (closure)** — Customers read page: thin P1 list API (`GET /api/v1/customers`) + `CustomersPage` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-28-react-read-customers`. Next: **FASTAPI-REACT-29**. |
| 2026-06-05 | **FASTAPI-REACT-27 (closure)** — Workers read page: `WorkersPage` wired to existing `GET /api/v1/workers` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-27-react-read-workers`. Next: **FASTAPI-REACT-28**. |
| 2026-06-05 | **FASTAPI-REACT-26 (closure)** — Sales + expenses read pages: thin P1 list APIs (`GET /api/v1/sales`, `GET /api/v1/expenses`) + `SalesPage`, `ExpensesPage` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-26-react-read-sales-expenses`. Next: **FASTAPI-REACT-27**. |
| 2026-06-05 | **FASTAPI-REACT-25 (closure)** — Chart of accounts + vendors read pages: `ChartOfAccountsPage`, `VendorsPage` wired to existing P1 list APIs behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-25-react-read-coa-vendors`. Next: **FASTAPI-REACT-26**. |
| 2026-06-05 | **FASTAPI-REACT-24 (closure)** — Receivable sale + allocation pickers: thin P1 list APIs (`/api/v1/receivable-sales`, `/api/v1/profit-allocations`) + `ReceivableSalePicker` / `ProfitAllocationPicker` on `NewTransactionPage`. Write picker track complete. Tag: `fastapi-react-24-react-write-final-pickers`. Next: **FASTAPI-REACT-25**. |
| 2026-06-05 | **FASTAPI-REACT-23 (closure)** — Reconcile/closing pickers + match-type forms: thin P1 list APIs (`/api/v1/bank-statement-rows`, `/api/v1/fiscal-periods`, `/api/v1/vendors`) + `StatementRowPicker`, `FiscalPeriodPicker`, `VendorPicker`, and per-match-type payload fields on `NewTransactionPage`. Tag: `fastapi-react-23-react-write-recon-forms`. Next: **FASTAPI-REACT-24**. |
| 2026-06-05 | **FASTAPI-REACT-22 (closure)** — Bank/worker/partner write pickers: thin P1 list APIs (`/api/v1/bank-accounts`, `/api/v1/workers`) + `BankAccountPicker` / `WorkerPicker` / reused `PartnerPicker` on `NewTransactionPage` write tabs. Tag: `fastapi-react-22-react-write-pickers`. Next: **FASTAPI-REACT-23**. |
| 2026-06-05 | **FASTAPI-REACT-21 (closure)** — COA + partner pickers: thin P1 list APIs (`/api/v1/chart-of-accounts`, `/api/v1/partners`) + `CoaAccountPicker` / `PartnerPicker` on Ledger and Partner Statement pages behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-21-react-read-pickers`. Next: **FASTAPI-REACT-22**. |
| 2026-06-05 | **FASTAPI-REACT-20 (closure)** — Cash flow + transaction ledger: thin P1 APIs (`/api/v1/reports/cash-flow`, `/api/v1/transactions`) + `services/read_transaction_history.py`; `CashFlowPage`, `TransactionLedgerPage` behind `VITE_ERP_REACT_PAGES=1`. Tag: `fastapi-react-20-react-read-cashflow-txn-ledger`. Next: **FASTAPI-REACT-21**. |
| 2026-06-05 | **FASTAPI-REACT-19 (closure)** — Reports hub + P&L read pages: `ReportsPage`, `ProfitLossPage` wired to `/api/v1/reports/profit-loss` behind `VITE_ERP_REACT_PAGES=1`; transaction ledger deferred (no P1 read endpoint). `docs/FASTAPI_REACT_19_REACT_READ_REPORTS_HUB_AUDIT.md` + `tests/test_fastapi_react_19_react_read_reports_hub.py`. Tag: `fastapi-react-19-react-read-reports-hub`. Next: **FASTAPI-REACT-20**. |
| 2026-06-05 | **FASTAPI-REACT-18 (closure)** — Partner statement + banking readiness read pages: `PartnerStatementPage`, `BankingReadinessPage` wired to P1 read APIs behind `VITE_ERP_REACT_PAGES=1`; `docs/FASTAPI_REACT_18_REACT_READ_PARTNER_BANKING_AUDIT.md` + `tests/test_fastapi_react_18_react_read_partner_banking.py`. Streamlit primary unchanged. Tag: `fastapi-react-18-react-read-partner-banking`. Next: **FASTAPI-REACT-19**. |
| 2026-06-05 | **FASTAPI-REACT-17 (closure)** — Read page expansion: `BalanceSheetPage`, `ReceivablesPage`, `PayablesPage` wired to P1 read APIs behind `VITE_ERP_REACT_PAGES=1`; `docs/FASTAPI_REACT_17_REACT_READ_EXPANSION_AUDIT.md` + `tests/test_fastapi_react_17_react_read_expansion.py`. Streamlit primary unchanged. Tag: `fastapi-react-17-react-read-expansion`. Next: **FASTAPI-REACT-18**. |
| 2026-06-05 | **FASTAPI-REACT-16 (closure)** — Reconciliation + Closing write tabs on `/transactions/new` via P2.8/P2.9 APIs behind `VITE_ERP_REACT_WRITE_RECONCILIATION` / `VITE_ERP_REACT_WRITE_CLOSING`; `docs/FASTAPI_REACT_16_REACT_WRITE_RECON_CLOSING_AUDIT.md` + `tests/test_fastapi_react_16_react_write_recon_closing.py`. Completes P2 write UI coverage. Tag: `fastapi-react-16-react-write-recon-closing`. Next: **FASTAPI-REACT-17**. |
| 2026-06-05 | **FASTAPI-REACT-15 (closure)** — Partner + Worker write tabs on `/transactions/new` via `POST /api/v1/partner-movements` and `POST /api/v1/worker-payments` behind `VITE_ERP_REACT_WRITE_PARTNER_WORKER=1`; `docs/FASTAPI_REACT_15_REACT_WRITE_PARTNER_WORKER_AUDIT.md` + `tests/test_fastapi_react_15_react_write_partner_worker.py`. Streamlit primary unchanged. Tag: `fastapi-react-15-react-write-partner-worker`. Next: **FASTAPI-REACT-16**. |
| 2026-06-05 | **FASTAPI-REACT-14 (closure)** — Bank transaction write tab on `/transactions/new` via `POST /api/v1/bank-transactions` behind `VITE_ERP_REACT_WRITE_BANKING=1`; `docs/FASTAPI_REACT_14_REACT_WRITE_BANKING_AUDIT.md` + `tests/test_fastapi_react_14_react_write_banking.py`. Streamlit primary unchanged. Tag: `fastapi-react-14-react-write-banking`. Next: **FASTAPI-REACT-15**. |
| 2026-06-05 | **FASTAPI-REACT-13 (closure)** — Receivable payment write tab on `/transactions/new` via `POST /api/v1/receivable-payments` behind `VITE_ERP_REACT_WRITE_RECEIVABLE_PAYMENTS=1`; `docs/FASTAPI_REACT_13_REACT_WRITE_RECEIVABLE_PAYMENT_AUDIT.md` + `tests/test_fastapi_react_13_react_write_receivable_payment.py`. Streamlit primary unchanged. Tag: `fastapi-react-13-react-write-receivable-payment`. Next: **FASTAPI-REACT-14**. |
| 2026-06-05 | **FASTAPI-REACT-12 (closure)** — Purchase write tab on `/transactions/new` via `POST /api/v1/purchases` behind `VITE_ERP_REACT_WRITE_PURCHASES=1`; `docs/FASTAPI_REACT_12_REACT_WRITE_PURCHASE_AUDIT.md` + `tests/test_fastapi_react_12_react_write_purchase.py`. Streamlit primary unchanged. Tag: `fastapi-react-12-react-write-purchase`. Next: **FASTAPI-REACT-13**. |
| 2026-06-05 | **FASTAPI-REACT-11 (closure)** — Void write tab on `/transactions/new` via `POST /api/v1/voids` behind `VITE_ERP_REACT_WRITE_VOIDS=1`; `docs/FASTAPI_REACT_11_REACT_WRITE_VOID_AUDIT.md` + `tests/test_fastapi_react_11_react_write_void.py`. Streamlit primary unchanged. Tag: `fastapi-react-11-react-write-void`. Next: **FASTAPI-REACT-12**. |
| 2026-06-05 | **FASTAPI-REACT-10 (closure)** — Payment method expansion: Card/Credit sale fields + Bank expense on `/transactions/new`; `docs/FASTAPI_REACT_10_REACT_WRITE_PAYMENT_METHODS_AUDIT.md` + `tests/test_fastapi_react_10_react_write_payment_methods.py`. Streamlit primary unchanged. Tag: `fastapi-react-10-react-write-payment-methods`. Next: **FASTAPI-REACT-11**. |
| 2026-06-05 | **FASTAPI-REACT-09 (closure)** — Expense write tab on `/transactions/new` via `POST /api/v1/expenses` behind `VITE_ERP_REACT_WRITE_EXPENSES=1`; tabbed UI with FR-08 cash sale; `docs/FASTAPI_REACT_09_REACT_WRITE_EXPENSE_AUDIT.md` + `tests/test_fastapi_react_09_react_write_expense.py`. Streamlit primary unchanged. Tag: `fastapi-react-09-react-write-expense`. Next: **FASTAPI-REACT-10**. |
| 2026-06-05 | **FASTAPI-REACT-08 (closure)** — First React write page: cash sale form on `/transactions/new` via `POST /api/v1/sales` behind `VITE_ERP_REACT_WRITE_SALES=1` + `VITE_ERP_REACT_PAGES=1` + `ERP_API_WRITE_SALES=1`; `registry/react_write_contract.py` + `docs/FASTAPI_REACT_08_REACT_WRITE_AUDIT.md` + `tests/test_fastapi_react_08_react_write.py`. Streamlit primary unchanged. Tag: `fastapi-react-08-react-write`. Next: **FASTAPI-REACT-09**. |
| 2026-06-05 | **FASTAPI-REACT-07 (closure)** — PG boundary matrix / TD-PS-01: API write-path dual-run (cash sale, expense, void) + failure rollback; optional PostgreSQL parity when `ERP_TEST_POSTGRES_URL` set; `registry/pg_boundary_contract.py` + `docs/FASTAPI_REACT_07_PG_BOUNDARY_MATRIX_AUDIT.md` + matrix tests. Default `internal` unchanged. Tag: `fastapi-react-07-pg-boundary-matrix`. Next: **FASTAPI-REACT-08**. |
| 2026-06-05 | **FASTAPI-REACT-06 (closure)** — First React pages: `HomePage` (P&L MTD) + `LedgerPage` (GL read-only) wired to P1 read API behind `VITE_ERP_REACT_PAGES=1`; `registry/react_pages_contract.py` + `docs/FASTAPI_REACT_06_REACT_PAGES_AUDIT.md` + `tests/test_fastapi_react_06_react_pages.py`. Streamlit primary unchanged. Tag: `fastapi-react-06-react-pages`. Next: **FASTAPI-REACT-07**. |
| 2026-06-05 | **FASTAPI-REACT-05 (closure)** — React bootstrap: `frontend/` Vite+React shell, `ThemeProvider` from `react_token_bundle()`, NAV-ARCH-S4 router (42 placeholder routes), `scripts/export_react_bootstrap_assets.py`; `docs/FASTAPI_REACT_05_REACT_BOOTSTRAP_AUDIT.md` + `tests/test_fastapi_react_05_react_bootstrap.py`. Streamlit primary unchanged. Tag: `fastapi-react-05-react-bootstrap`. Next: **FASTAPI-REACT-06**. |
| 2026-06-05 | **FASTAPI-REACT-04 (closure)** — Read API stabilization + TD-PS-01 characterization inventory: frozen read paths/error contract, commit-family dual-run test map; `registry/api_read_contract.py` + `registry/commit_boundary_contract.py` + `docs/FASTAPI_REACT_04_READ_API_BOUNDARY_AUDIT.md` + `tests/test_fastapi_react_04_read_api_boundary.py`. Default `internal` unchanged. Tag: `fastapi-react-04-read-api-boundary-commit`. Next: **FASTAPI-REACT-05**. |
| 2026-06-05 | **FASTAPI-REACT-03 (closure)** — Reconciliation `_app()` removal: `match_post.py` + `company_card.py` call `services.posting` / `read_balances` / `banking_balance` directly; TD-PS-01 boundary readiness documented (default `internal` unchanged). `docs/FASTAPI_REACT_03_RECON_BOUNDARY_AUDIT.md` + `tests/test_fastapi_react_03_recon_boundary.py`. Tag: `fastapi-react-03-recon-boundary-commit`. Next: **FASTAPI-REACT-04**. |
| 2026-06-05 | **FASTAPI-REACT-02 (closure)** — API write hardening verification: explicit `company_id` on all 13 P2 write routes closed via P2-HARDEN-01; `registry/api_write_contract.py` + `docs/FASTAPI_REACT_02_API_WRITE_HARDENING_AUDIT.md` + `tests/test_fastapi_react_02_api_write_hardening.py`. No accounting behavior change. Tag: `fastapi-react-02-api-write-hardening`. Next: **FASTAPI-REACT-03**. |
| 2026-06-05 | **FASTAPI-REACT-01 (closure)** — PS-P7 posting boundary hardening: `services/posting_boundary.py`, additive DTO helpers, app shim dedup; `docs/FASTAPI_REACT_01_POSTING_BOUNDARY_AUDIT.md` + `tests/test_fastapi_react_01_posting_boundary.py`. No accounting behavior change. Tag: `fastapi-react-01-posting-boundary-hardening`. Next: **FASTAPI-REACT-02**. |
| 2026-06-05 | **FASTAPI-REACT-00 (closure)** — Migration baseline audit: FastAPI partial, React not started, frozen contracts inventory, blocker matrix, FASTAPI-REACT-01+ slice plan; `docs/FASTAPI_REACT_00_AUDIT.md` + `tests/test_fastapi_react_00_audit.py`. Audit only. Next: **FASTAPI-REACT-01** (posting boundary hardening). |
| 2026-06-05 | **MONO-THEME-02 (epic closure)** — S0–S5 complete; epic matrix `tests/test_mono_theme_02_epic_matrix.py`; implementation audit updated. Tags: `mono-theme-02-s0` through `mono-theme-02-s5`. |
| 2026-06-05 | **MONO-THEME-02-S5 (closure)** — Mobile parity: removed widgets mob_bar/hub override drift, mobile KPI chips + tables use `--erp-card-*`/`--erp-table-*`, hub sheet card radius; `tests/test_mono_theme_02_s5_mobile_parity.py`. Tag: `mono-theme-02-s5-mobile-parity`. **MONO-THEME-02 epic complete.** |
| 2026-06-05 | **MONO-THEME-02-S4 (closure)** — Desktop table density: tighter `.erp-fin-table`/`.erp-data-table` padding, sticky fin headers, stTable row hover + tabular-nums; `tests/test_mono_theme_02_s4_table_refinement.py`. Tag: `mono-theme-02-s4-table-refinement`. Next: **MONO-THEME-02-S5** (mobile parity). |
| 2026-06-05 | **MONO-THEME-02-S3 (closure)** — Desktop dashboard density: tighter KPI grid/cards, card-shell insight rows, activity hover focal point, bordered Streamlit panels; `tests/test_mono_theme_02_s3_dashboard_refinement.py`. Tag: `mono-theme-02-s3-dashboard-refinement`. Next: **MONO-THEME-02-S4** (tables). |
| 2026-06-05 | **MONO-THEME-02-S2 (closure)** — Desktop top bar: compact `--hdr-h` 52px, search card prominence, softer toolbar controls; `tests/test_mono_theme_02_s2_topbar_refinement.py`. Tag: `mono-theme-02-s2-topbar-refinement`. Next: **MONO-THEME-02-S3** (dashboard/cards). |
| 2026-06-05 | **MONO-THEME-02-S1 (closure)** — Desktop sidebar polish: quiet active row (tint + 3px accent bar, no filled button), section header rhythm, item padding; `tests/test_mono_theme_02_s1_sidebar_polish.py`. Tag: `mono-theme-02-s1-sidebar-refinement`. Next: **MONO-THEME-02-S2** (top bar). |
| 2026-06-05 | **MONO-THEME-02-S0 (closure)** — Option A+ visual contract frozen: `docs/MONO_THEME_02_VISUAL_CONTRACT.md` + `tests/test_mono_theme_02_visual_contract.py`. Audit only; screenshots = source of truth; S1–S5 slice plan. Next: **MONO-THEME-02-S1** (sidebar polish). |
| 2026-06-05 | **MONO-THEME-01-S7 (closure)** — Epic complete: `react_token_bundle()` exports `componentGrammar` + grammar key families; `auth.css` mono role chips (no `--role-*`); `tests/test_mono_theme_01_s7_react_contract_cleanup.py`. Tag: `mono-theme-01-s7-react-contract-cleanup`. Next: **DS-6 React build** or next ROADMAP epic. |
| 2026-06-05 | **MONO-THEME-01-S6 (closure)** — Table/status grammar: `--erp-table-*` on fin/data/stTable/txn-ledger surfaces; chip extensions on status pills + banking/report selectors; `tests/test_mono_theme_01_s6_table_status_grammar.py`. Tag: `mono-theme-01-s6-table-status-grammar`. Next: **MONO-THEME-01-S7** (React contract + cleanup). |
| 2026-06-05 | **MONO-THEME-01-S5 (closure)** — Mobile card grammar: KPI/list/sheet/form surfaces route through `--erp-card-*` (`mobile_components.css`, `mobile_shell.css`, `mobile_txn.css`, `mobile_reports.css`); `tests/test_mono_theme_01_s5_mobile_card_grammar.py`. Tag: `mono-theme-01-s5-mobile-card-grammar`. Next: **MONO-THEME-01-S6** (tables/statuses). |
| 2026-06-05 | **MONO-THEME-01-S4 (closure)** — Desktop card grammar: KPI/dashboard/banner/activity cards + form containers route through `--erp-card-*` tokens (`theme.css`, `widgets.css`); `tests/test_mono_theme_01_s4_desktop_card_grammar.py`. Tag: `mono-theme-01-s4-desktop-card-grammar`. Next: **MONO-THEME-01-S5** (mobile card parity). |
| 2026-06-05 | **MONO-THEME-01-S3 (closure)** — Nav active grammar: desktop sidebar + mobile bottom-nav/hub route through `--erp-nav-*` tokens (`theme.css`, `mobile_shell.css`, `icons.css`); `tests/test_mono_theme_01_s3_nav_active_grammar.py`. Tag: `mono-theme-01-s3-nav-active-grammar`. Next: **MONO-THEME-01-S4** (desktop cards/forms). |
| 2026-06-05 | **MONO-THEME-01-S2 (closure)** — Shared component grammar tokens: `COMPONENT_GRAMMAR_TOKENS` in `ui/design_tokens.py` mirrored in `ui/theme.css` (`--erp-nav-*`, `--erp-card-*`, `--erp-chip-*` ext, `--erp-table-*`); `tests/test_mono_theme_01_s2_shared_grammar_tokens.py`. Token definitions only; no component migration. Tag: `mono-theme-01-s2-shared-grammar-tokens`. Next: **MONO-THEME-01-S3** (sidebar + mobile nav active). |
| 2026-06-17 | **MONO-THEME-01-S1 (closure)** — Option A+ unified mono theme audit: `docs/MONO_THEME_01_AUDIT.md` + `tests/test_mono_theme_01_audit.py`. Verdict PROCEED (revise-light): shared grammar tokens on existing foundation; no new colors. Tag: `mono-theme-01-s1-audit-design-spec`. Next: **MONO-THEME-01-S2** (shared grammar tokens). |
| 2026-06-05 | **BANKING-UX-04-S4 (closure)** — React workflow contract frozen: `registry/banking_workflow_contract.py` + `docs/BANKING_UX_04_REACT_WORKFLOW_CONTRACT.md`; epic matrix `tests/test_banking_ux_04_epic_matrix.py`. Tag: `banking-ux-04-s4-react-workflow-contract`. **BANKING-UX-04 epic complete.** |
| 2026-06-05 | **BANKING-UX-04-S3 (closure)** — Add Transaction bank-path workflow routing: type order/landing, statement callout, Advanced manual bank type via `ui/banking.py`. No posting/recon/GL changes. Tests: `tests/test_banking_ux_04_s3_add_transaction_bank_paths.py`. Tag: `banking-ux-04-s3-add-transaction-bank-paths`. Next: **BANKING-UX-04-S4** (tests/React-readiness). |
| 2026-06-05 | **BANKING-UX-04-S2 (closure)** — Workflow mode setting (`banking.workflow_mode`, default `statement_first`) + Banking UI routing: section order, landing, Advanced manual panel via `ui/banking.py`. No posting/recon/GL changes. Tests: `tests/test_banking_ux_04_s2_workflow_mode_routing.py`. Tag: `banking-ux-04-s2-workflow-mode-routing`. Next: **BANKING-UX-04-S3** (Add Transaction bank paths). |
| 2026-06-05 | **BANKING-UX-04-S1 (closure)** — Configurable banking workflow architecture audit: `docs/BANKING_UX_04_AUDIT.md` + `tests/test_banking_ux_04_audit.py`. Recommendation: PROCEED (UI-only). Tag: `banking-ux-04-s1-audit`. |
| 2026-06-05 | **UI-SYSTEM-02-S5 (closure)** — React design contract: `docs/UI_SYSTEM_02_REACT_DESIGN_CONTRACT.md` + `ui/react_design_contract.py`; frozen component prop map, `react_token_bundle()`, Streamlit-only selector retirement list. Tests: `tests/test_ui_system_02_s5_react_design_contract.py`. Tag: `ui-system-02-s5-react-design-contract`. **UI-SYSTEM-02 epic S1–S5 complete.** |
| 2026-06-05 | **UI-SYSTEM-02-S4 (closure)** — Unified shell/component pass: removed dead `.erp-mobile-report-filters` mobile block rule; 96× expense-bar `[data-pct]` ladder → inline `width:%`; KPI grid owned by `mobile_components.css` with `--reports-cf` modifier; `--mob-space-*` alias `--erp-space-*`. Tests: `tests/test_ui_system_02_s4_shell_component_pass.py`. Tag: `ui-system-02-s4-unified-shell-component-pass`. Next: **UI-SYSTEM-02-S5** (React design contract). |
| 2026-06-05 | **UI-SYSTEM-02-S3 (closure)** — Sidebar modernization: `registry/sidebar_layout.py` drives desktop render tree; `_NAV_GROUP_KEYS` derived; tokenized section headers + CSS chevrons. Tests: `tests/test_ui_system_02_s3_sidebar_modernization.py`. Tag: `ui-system-02-s3-sidebar-modernization`. Next: **UI-SYSTEM-02-S4** (unified shell/component pass). |
| 2026-06-05 | **UI-SYSTEM-02-S2 (closure)** — Design token registry: `ui/design_tokens.py` derives `LIGHT_ROOT_VARS`/`DARK_ROOT_VARS`; spacing/radius/shadow/typography scales in `theme.css`; resolved mobile `--hdr-h` conflict (removed stale 120px). Tests: `tests/test_ui_system_02_s2_design_token_registry.py`. Tag: `ui-system-02-s2-design-token-registry`. Next: **UI-SYSTEM-02-S3** (sidebar modernization). |
| 2026-06-05 | **UI-SYSTEM-02-S1 (closure)** — ERP-wide UI & theme audit: `docs/UI_SYSTEM_02_AUDIT.md` + `tests/test_ui_system_02_audit.py`; 14 CSS files / 7,379 lines inventoried; sidebar visual readiness documented; no runtime change. Tag: `ui-system-02-s1-ui-theme-audit`. Next: **UI-SYSTEM-02-S2** (design token registry). |
| 2026-06-17 | **NAV-ARCH-S4 (closure)** — React route contract frozen: `docs/NAV_ARCH_REACT_ROUTE_CONTRACT.md` + `validate_react_route_contract()`; 42 routes 1:1; legacy aliases canonical only. Tag: `nav-arch-s4-react-route-contract`. **NAV-ARCH epic S0–S4 complete.** |
| 2026-06-17 | **NAV-ARCH-S3C (closure)** — Mobile nav derived: `_MOBILE_BOTTOM_NAV` + `_MOBILE_HUB_CONFIG` from `registry/navigation.py`; five bottom slots + money/reports/people/more hubs preserved. Tests: `tests/test_nav_arch_s3c_mobile_derived.py`. Tag: `nav-arch-s3c-mobile-derived`. Next: **NAV-ARCH-S4** (React route contract). |
| 2026-06-17 | **NAV-ARCH-S3B (closure)** — Static role gates derived: `_NAV_ROLE_PAGES` from `registry/navigation.py`; permission override for Staff Expenses unchanged in `app.py`. Tests: `tests/test_nav_arch_s3b_role_derived.py`. Tag: `nav-arch-s3b-role-derived`. Next: **NAV-ARCH-S3C** (derive mobile nav). |
| 2026-06-17 | **NAV-ARCH-S3A (closure)** — Desktop nav derived: `_NAV_ACCORDION` + `_NAV_DIRECT_PAGES` from `registry/navigation.py`; sidebar render order unchanged. Tests: `tests/test_nav_arch_s3a_desktop_derived.py`. Tag: `nav-arch-s3a-desktop-derived`. Next: **NAV-ARCH-S3B** (derive role gates). |
| 2026-06-17 | **NAV-ARCH-S2 (closure)** — `registry/navigation.py` derives `_PAGE_DISPATCH` (42 routes); accordion/direct/role/mobile unchanged. Tests: `tests/test_nav_arch_s2_registry_dispatch.py`. Tag: `nav-arch-s2-registry-dispatch`. Next: **NAV-ARCH-S3A** (derive desktop nav). |
| 2026-06-17 | **NAV-ARCH-S1 (closure)** — Navigation audit + live parity guardrails: `docs/NAV_ARCH_AUDIT.md`, `tests/test_nav_arch_audit.py`; no runtime change; `registry/navigation.py` deferred to S2. Tag: `nav-arch-s1-audit-guardrails`. Next: **NAV-ARCH-S2** (registry + derive dispatch). |
| 2026-06-16 | **POSTGRES-PRODUCTION-CUTOVER** — Flag-gated PostgreSQL runtime wired; SQLite→PG migration + parity verified (companies 1–4); smoke flows pass; backup preserved. Doc: [POSTGRES_PRODUCTION_CUTOVER.md](./docs/POSTGRES_PRODUCTION_CUTOVER.md). Tag: `postgres-production-cutover`. |
| 2026-06-16 | **POSTGRES-REAL-DRY-RUN** — Real copy-only SQLite→PG dry run verified: row counts + TB + reports match (companies 1–4); `erp_data.db` untouched; `safe_for_production_cutover: true` (data parity only). Doc: [POSTGRES_REAL_DRY_RUN_20260616.md](./docs/POSTGRES_REAL_DRY_RUN_20260616.md). Tag: `postgres-real-dry-run-20260616`. |
| 2026-06-16 | **POSTGRES-RUNTIME-CUTOVER-PREP (closure)** — Test-only SQLite→PG data copy harness + parse-only runtime gate; money snapshot parity on smoke tenant; production still SQLite. Doc: [POSTGRES_RUNTIME_CUTOVER_PREP.md](./docs/POSTGRES_RUNTIME_CUTOVER_PREP.md). Tag: `postgres-runtime-cutover-prep`. Next: **real SQLite→PG dry run**. |
| 2026-06-16 | **POSTGRES-PG-BUILD (closure)** — PG test DBs built via Alembic `upgrade head` (0002); dual-run harness compares SQLite vs PG posting + report fingerprints; `bootstrap_postgres_via_alembic` in `tests/postgres_utils.py`. No production runtime switch. Doc: [POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md](./docs/POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md). Tag: `postgres-pg-build-dual-run-parity`. Next: **PostgreSQL runtime cutover prep**. |
| 2026-06-16 | **MONEY-DECIMAL-04c+ (closure)** — JE guard / FX native Decimal boundary verified; float guard preserved (MD-02 locked); `persist_fx` + `services/money.py` boundaries confirmed; no runtime changes. Doc: [MONEY_DECIMAL_04C_JE_FX_DECIMAL.md](./docs/MONEY_DECIMAL_04C_JE_FX_DECIMAL.md). Tag: `money-decimal-04c-je-fx-decimal-guard`. Next: **PostgreSQL build + dual-run parity**. |
| 2026-06-16 | **P2-HARDEN-01 (closure)** — Company stamp audit closed: H-01/H-02 verified green; H-03 silent auto-stamp deferred/rejected; explicit service-layer stamping remains standard. Doc: [P2_HARDEN_01_AUDIT_CLOSURE.md](./docs/P2_HARDEN_01_AUDIT_CLOSURE.md). Tag: `p2-harden-01-company-stamp-audit`. Next: **MONEY-DECIMAL-04c+**. |
| 2026-06-16 | **NAV-ARCH** — Record planned navigation single-source-of-truth epic (S0–S4): derive dispatch/accordion/role/mobile from `registry/navigation.py` after PG parity, before React; not a PG blocker. Docs only. |
| 2026-06-16 | **BANKING-SERVICE-01-BS-03 (closure)** — Verified CC bill payment JE already uses explicit `company_id` via `services.posting` (`713ac3c`); doc [BANKING_SERVICE_01_BS03.md](./docs/BANKING_SERVICE_01_BS03.md). Tag: `banking-service-01-bs03-company-card-company-scope`. Next: **P2-HARDEN-01**. |
| 2026-06-16 | **AUTH-SESSION-02-IMPL-3 (closure)** — Verified idle extension already shipped (`ee57dc1`); ROADMAP/TECH_DEBT sync; doc [AUTH_SESSION_02_IMPL_3.md](./docs/AUTH_SESSION_02_IMPL_3.md). Tag: `auth-session-02-impl3-idle-extension`. Next: **BANKING-SERVICE-01-BS-03**. |
| 2026-06-16 | **MONEY-DECIMAL-05-IMPL-5** — Flag-gated `0001→0002` cutover wiring (`ERP_MONEY_NUMERIC_CUTOVER` + P3.8 gate); post-cutover cache re-sync; Alembic runner `DATABASE_URL` + PATH fix. Baseline **4651 passed** (+18). Tag: `money-decimal-05-impl5-cutover-gate`. Next: PG build + dual-run parity. |
| 2026-06-16 | **MONEY-DECIMAL-05-IMPL-4** — Populated SQLite `0001→0002` migration smoke + optional PG NUMERIC tests; fix `0002` SQLite supplemental index re-apply after batch rebuild. Baseline **4633 passed** (+8). Tag: `money-decimal-05-impl4-migration-smoke`. Next: **MD-05-IMPL-5**. |
| 2026-06-16 | **MONEY-DECIMAL-05-IMPL-3** — ROUND_HALF_UP via `services/money.py`; fix stale bank/payable cache paths; GL + bank cache re-sync; Alembic `0002` explicit PG ROUND USING; `ingredients.cost_per_base_unit` → NUMERIC(19,4). Baseline **4625 passed** (+14). Tag: `money-decimal-05-impl3-quantization-cache`. Next: **MD-05-IMPL-4**. |
| 2026-06-16 | **MONEY-DECIMAL-05-IMPL-2** — Switch `models.py` to `Numeric(asdecimal=True)`; route posting/read/write/`app.py` through `services/money.py`; preserve MD-02 golden vectors; no PG production cutover. Baseline **4611 passed** (+2). Tag: `money-decimal-05-impl2-model-numeric`. Next: **MD-05-IMPL-3**. |
| 2026-06-05 | **MONEY-DECIMAL-05-IMPL-1** — Author Alembic `0002_money_numeric` + `money_numeric_columns.py` (2/4/8-dp classification); ephemeral SQLite upgrade smoke; Alembic head **0002**; `0001_baseline` untouched; models still Float. Baseline **4609 passed** (+31). Tag: `money-decimal-05-impl1-numeric-revision`. |
| 2026-06-16 | **ROADMAP-SYNC-02** — Register sync after P3.9-C + external PR #2 (error-handling) + PR #3 (+226 coverage tests): baseline **4578 passed** (4572 post-PR#3 + 6 Sync-02 contract tests); P3.9 + ALEMBIC-01 complete; next critical path **MD-05 Numeric** before PostgreSQL runtime cutover. Docs/tests only. |
| 2026-06-05 | **P3.9-C** — `migrate_schema()` implementation removed: production no-op stub + `tests/legacy_migrate_schema.py` archive; Alembic-only evolution; flag-off no longer applies DDL. **ALEMBIC-01 ✅** Test baseline: **4346 passed**. |
| 2026-06-05 | **P3.9-B** — `migrate_schema()` DeprecationWarning on every call (`MIGRATE_SCHEMA_DEPRECATION_MESSAGE` + `test_p3_9_b_deprecation.py`); harness callers updated; body retained. Next P3.9-C. Test baseline: **4331 passed**. |
| 2026-06-05 | **P3.9-B-CHAR** — `migrate_schema()` caller inventory + P3.9-B deprecation contract pinned (`docs/P3_9_B_CHAR_MIGRATE_SCHEMA_CALLERS.md` + `test_p3_9_b_char_migrate_schema_callers.py`). Pre-B: zero DeprecationWarning. Next P3.9-B. Test baseline: **4318 passed**. Tests/docs only. |
| 2026-06-05 | **P3.9-A** — `migrate_schema()` retirement readiness audit: Phase A done via P3.8-N; Phases B/C not started; verdict NOT READY to remove (`docs/P3_9_A_AUDIT.md` + `test_p3_9_a_audit.py`). Next P3.9-B-CHAR. Test baseline: **4293 passed**. Audit/docs/tests only. |
| 2026-06-16 | **P3.8-N** — Alembic authority default flip: unset/empty → flag-on; explicit `ERP_ALEMBIC_AUTHORITATIVE=0` → legacy `migrate_schema()` path (`parse_alembic_authoritative_flag` + `test_p3_8_n_default_flip.py`). **`migrate_schema()` retained.** Production requires stamped DB at head. Test baseline: **4275 passed**. |
| 2026-06-16 | **P3.8-L-TESTS** — Alembic authority bake-in characterization gate: schema equivalence, single-caller guard, never-on-PG, lock-safety, flag-off parity (`test_p3_8_l_tests_bakein_characterization.py`) + [P3_8_L_TESTS.md](./docs/P3_8_L_TESTS.md). **Not ready to retire `migrate_schema()`** — P3.8-N next. Test baseline: **4250 passed**. Tests/docs only. |
| 2026-06-16 | **P3.8-L-EXEC** — Alembic authority bake-in execution record: automated throwaway-DB scenario matrix (`test_p3_8_l_exec_bakein_execution.py`) + [P3_8_L_BAKEIN_EXEC.md](./docs/P3_8_L_BAKEIN_EXEC.md). Flag off/on/at_head/unstamped/ahead/strict-new/behind_head/rollback all **PASS**; references prior P3.8-M manual smoke. **Not ready to retire `migrate_schema()`** — P3.8-L-TESTS next. Test baseline: **4231 passed**. No flag default change, no production DB mutation. |
| 2026-06-16 | **BANKING-SERVICE-01-BS-04** — `render_banking` manual Add Transaction form delegates to `services.write_banking.create_manual_bank_transaction`; inline balance/post removed. **Improvement:** manual path now writes `AuditLog` (previously Streamlit-only gap). Guard: `test_banking_service01_char_manual_bank_parity.py`. Doc: [BANKING_SERVICE_01_BS04](./docs/BANKING_SERVICE_01_BS04.md). |
| 2026-06-05 | **ROADMAP-SYNC-01** — Register sync from [FULL_SERVICE_READINESS_AUDIT](./docs/FULL_SERVICE_READINESS_AUDIT.md) + [BANKING_SERVICE_01_AUDIT](./docs/BANKING_SERVICE_01_AUDIT.md): POSTING complete; REPORTS/BANKING/AUTH-SESSION/FastAPI/PG partial; RECEIPT-AI-01 + RECEIPT-AI-02 IMPL-1–5 complete; POS-AI/Z-report/cash-card automation **paused until user explicitly requests**; current priority reordered (BS-02 → BS-04 char → AUTH-SESSION-IMPL-3 → P2-HARDEN-01 → MONEY-DECIMAL-01 → PG → React); roadmap hygiene rule + `test_roadmap_sync_01.py`. Test baseline: **3883 passed**. Docs only. |
| 2026-06-15 | **POS-CONFIG-01** — Sales Source & Reconciliation Settings spec approved (docs only): per-company `pos.*` configuration for sales source, verification source, card/cash verification modes, duplicate protection keys, auto-post policy, document classification, and workflow mode. **Rules:** no company-wide assumptions; settings determine AI behaviour; default suggest-only; complements `banking.*` + DSC. **Sequencing:** POS-CONFIG-01-IMPL-1 before POS-AI-01. Spec: [docs/POS_CONFIG_01_SPEC.md](./docs/POS_CONFIG_01_SPEC.md). No `app.py`/schema change. |
| 2026-06-05 | **ROADMAP-UPDATE-01** — Approved future work queue recorded (docs only): **DASH-CASH-01** (audited; S1 `compute_liquid_position` shipped; UI pending) · **AUTH-SESSION-02** (remember device + session hardening after AUTH-SESSION-01) · **RECEIPT-AI-01–08** (OCR → learning → confidence → owner-gated trusted auto-post last) · **BANKING-UX-05** (AI statement matching; approval-first) · **DASH-KPI-01–03** (forecast, runway, sales-by-payment-type) · **AI-BOOKKEEPER-01** (read-only business explanations). **Rules locked:** first AI release = assist/review; auto-post requires learning history + confidence + owner enablement + audit + void safety; service-first / FastAPI-ready / no Streamlit business logic. **Priority order:** DASH-CASH-01 → RECEIPT-AI audit → RECEIPT-AI 02/03/04 → 05/06/08 → 07 trusted auto-post → BANKING-UX-05 → AUTH-SESSION-02 → DASH-KPI → AI-BOOKKEEPER → FastAPI → React. No runtime code from this update. |
| 2026-06-14 | **P2-HARDEN-01 recorded** — Company Stamp Audit: audit API `company_id` stamping across P2 write paths; Priority High, Risk Low, no intended behavior changes. Triggered by P2.9 `PartnerProfitAllocation` finding ([P2_AUDIT_01_LEDGER](./docs/P2_AUDIT_01_LEDGER.md)). Register: [TECH_DEBT](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md). |
| 2026-06-14 | **ROADMAP-PRINCIPLES-01** — **ERP Core Principles (Locked)** recorded: 10 architectural principles learned during Streamlit ERP development (business logic first · explicit `company_id` · void/reverse/audit · form state rules · RETENTION-01 · date ownership · desktop/mobile unity · configurable ERP · commit ownership · discovery before implementation). **BANKING-UX-04** Configurable Banking Workflow added (statement-first / hybrid / manual-first). **DATE CONTROL** future React UX spec locked (single field, focus-opens calendar). Docs only — no code. Cross-links: [ERP_DS_04](./docs/ERP_DS_04_MASTER_DESIGN_SYSTEM.md) · [ERP_DS_05](./docs/ERP_DS_05_REACT_ARCHITECTURE.md) · [FASTAPI_P0_5D](./docs/FASTAPI_P0_5D_COMMIT_OWNERSHIP_PLAN.md). |
| 2026-06 | Shared DB + `company_id` isolation — do not redesign per-tenant DB yet |
| 2026-06 | Hidden ≠ disabled ≠ locked |
| 2026-06 | 14D-C + 14D-D + nav fix + simplified Company Setup |
| 2026-06 | 14D-B2a shipped read-only; enforcement in B2b / 14D-C |
| 2026-06-06 | Phase 18-MUX approved in principle (mobile calculator New Transaction); backlog only — after mobile nav stabilization |
| 2026-06-09 | **AD-UI-001** sidebar/navigation redesign approved (high priority); implementation gated on NAVIGATION_AUDIT.md |
| 2026-06-11 | **ROADMAP-UPDATE-01** — **BANKING-UX-02** POS Settlement Transparency proposed (High). User testing: clearing logic correct but Card Sales Clearing / unsettled sales not visible in Match & Post. P1–P4 are UX-only; ordered after BANKING-POS-WORKFLOW-01, before new Banking features. |
| 2026-06 | **SETUP-01** Company Creation Wizard design approved (8 steps + summary at create); SETUP-02/03 planned; BANK-03 POS Settlement wording |
| 2026-06 | P0 complete: multi-company switch + persistence, mobile surfaces, AT safety, Transaction Ledger; daily-use priority over new features |
| 2026-06 | **Future UX / Navigation vision** recorded (MOBILE-07–10, DESIGN-05, DESKTOP-04) — low priority, design direction only; explicit deferral of banking/reports/mobile shell/nav/More/sidebar redesigns |
| 2026-06-09 | **MOB-AT-C1** Concept C Mobile AT UI approved for implementation — mobile panel only; desktop AT / accounting / schema / Banking / Reports / More / Header / Bottom Nav all unchanged; app-wide theme rollout deferred |
| 2026-06-09 | **MOB-AT-C1** accepted as reference implementation — 747 tests passing; HTML-in-button bug fixed (st.button escapes HTML — use st.markdown for decorative elements); picker overlay fixed (keypad suppressed when picker open); date picker test updated to reflect new picker-sheet architecture |
| 2026-06-09 | **MOBILE-11** Mobile Design System approved — `docs/MOBILE_UI_SYSTEM.md` is the governing document for all future mobile work; Concept C is the reference implementation |
| 2026-06-09 | **MOBILE-12** Design Governance approved — forbidden patterns codified; phased migration sequence defined; three open naming decisions recorded (Banking label / Reports-or-Cashflow / More label) — do not rename until resolved via OBS-01 or explicit instruction |
| 2026-06-09 | **Concept C** accepted as the reference implementation for future mobile UX. Reason: aligns with the ERP philosophy — *"The tool disappears and the work appears."* Concept C successfully establishes: Row 1 meta-strip, progressive disclosure, context-sensitive fields, sheet picker workflow, keypad-first transaction entry. Future mobile pages should follow these principles. |
| 2026-06 | **Desktop/Mobile Architecture Audit** completed. Business logic separation is healthy. Presentation separation is partially complete. Future UI work should prioritize stability and separation before major redesign projects. Findings recorded as **UI-STAB** (not approved for implementation). |
| 2026-06 | **OBS-01** Operational Friction Log added. UX changes must originate from repeated real-world friction (3+ occurrences) before becoming roadmap candidates. |
| 2026-06-09 | **Theme Ownership Audit** completed. Finding: ERP is not globally fragmented — most CSS conflicts are concentrated in `widgets.css`, `mobile_shell.css`, and `mobile_header.css`. Decision: ownership cleanup (**MOBILE-14**) takes priority over further UI redesign. **CSS-01** establishes the target ownership map. **LOGIN-01** (login redesign) is blocked until MOBILE-14 is complete. **CHART-01** (chart theming) is independent and can proceed at any time. Design Governance rule added to MOBILE-12: no UI redesign work begins until ownership conflicts for that area are understood. |
| 2026-06-09 | **ERP-Wide UI Ownership Principle** approved. Decision: the ERP will keep modular CSS files, but each UI area must have a single owner. `theme.css` for global tokens and desktop base; `widgets.css` for truly generic Streamlit widget behaviour only; each feature area owns its own CSS file. Future work must consolidate ownership rather than adding new override layers. **CSS-02** formalises this as 8 enforceable rules applying to all CSS added or modified after June 2026. |
| 2026-06-09 | **MOBILE-14 E8 revised** (E8a + E8b). Audit finding: the report active chip rules in `mobile_reports.css` are true duplicates of `widgets.css` and safe to remove (E8a). The report idle chip rules are not — `--erp-chip-idle-bg` ≠ `--theme-card`; removing without first relocating to `widgets.css` causes visual regression. Decision: chip active/idle grammar for all contexts (AT and reports) belongs in `widgets.css` UI-1 block. `mobile_reports.css` owns layout, spacing, grids, and density only — not chip colours. E8b requires add-then-remove sequencing with visual parity verification. |
| 2026-06-09 | **UX-01** recorded. Decision: the ERP should remember non-accounting user preferences (last company, last page, theme, sidebar state, last used currency, dashboard filters) to reduce repetitive setup after login, refresh, and company switch. Preferences must be stored separately from accounting records and must not affect accounting behaviour, permissions, or authentication. Session persistence is a productivity feature. |
| 2026-06-09 | **UX-02** approved. Decision: viewport adaptation is a core usability requirement. The ERP must automatically fit the user's device and viewport without requiring manual zoom or window resizing. Root cause investigation required before implementation — candidates include viewport meta handling, CSS breakpoint assumptions, Streamlit container sizing, and mobile detection timing. Blocked on MOBILE-14. |
| 2026-06-09 | **DATE-01** recorded. Decision: mobile date picker should surface Today, Yesterday, This Week, and up to 3 recent session dates as immediate one-tap selections before the calendar input. Custom Date expands the existing calendar inline. Reduces date-entry taps for the majority of transactions. Independent — no blocking dependencies. |
| 2026-06-09 | **QUICK-ENTRY-01** approved. Decision: for common mobile transactions, direct inline category selection is preferred over opening additional picker sheets. Maximum 4–5 chips inline; a "More…" chip always provides picker fallback. The category picker is unchanged and remains fully reachable. Blocked on MOBILE-14. No accounting, schema, or posting logic changes. |
| 2026-06-10 | **QUICK-ENTRY-01** implemented and verified. Quick chips wired for Sale/Expense/Purchase; per-type last-category memory (company-scoped, cleared on switch); seeding via last-used or sole active category; subcategory reset on every pick; `More…` opens the unchanged picker. CSS lives in `mobile_txn.css` per CSS-02 ownership. Host audit: `tests/test_quick_entry.py` 14/14 passing. Accounting, schema, and posting logic untouched. |
| 2026-06-10 | **AT-LIGHT-01 final polish (P1–P5) implemented** per approved design review: chip grammar split (tinted Row 1 selectors vs white bordered category chips), solid-accent selected chip (widgets.css UI-1, AT-scoped), white keypad keys with border + pressed state, amount hero card cleanup (wrapper band removed), panel tint 22%/10%, nav-safe bottom padding. CSS-only; tokens stay in `mobile_txn.css` :root per E9; chip colours in `widgets.css` per E8. Static contracts green (UI-1 20/20, layout contract 4/4, quick-entry CSS contract). Closure pending host `pytest tests/` + visual verification; then HDR-01 begins. |
| 2026-06-10 | **AT-LIGHT-01 P6 — Mobile keypad ordering** approved and implemented. Keypad reordered from calculator layout to phone/POS layout (`1 2 3` top; ITU E.161 / ISO 9564, matches mobile OS decimal pads). Single tuple change in `_mob_at_render_amount_keypad_fragment`; no CSS/logic/schema changes; no test impact. Final AT-LIGHT-01 item — close after host pytest + phone visual verification, then HDR-01. |
| 2026-06-10 | **Roadmap reconciliation applied** (docs only, no code/test changes). Corrections: **SETUP-01** "design approved, not built" → **built and tested** (wizard modules, CSS, locales, 6 dedicated test files). **DEVELOPMENT_MODE** blocker → resolved by DEV-AUTH-01 env gating (`ERP_DEV_MODE`); production checklist retained. **AD-UI-001** → D1 + D2-P0 shipped (promoted daily lookup route). **BANK-03** and **CHART-01** → flagged "needs short verification pass" (mixed evidence). **MOBILE-14** confirmed closed (M1+M2+M5+M6+TXH; M3/M4 = optional backlog xfails). **LOGIN-01**/**UX-02** unblocked, not started; next recommended item = LOGIN-01/UX-02 modernization **audit** (implementation not approved). |
| 2026-06-10 | **UX-03–UX-07 roadmap accepted with adjustment** (post-AT-LIGHT-01 sequencing). Order: (1) **HDR-01** combined header pass (UX-07 + UX-06) — mobile header only: company selector max width, ellipsis for long names, guaranteed spacing between selector/notifications/profile, review of duplicate company switching in Profile. Ownership: `mobile_header.css`; `theme.css` only for desktop and only if audit proves needed; no new header token conflicts; respect AUDIT-01's `--hdr-h` finding. (2) **UX-03** inline Add Expense Category — blocked until header pass complete. (3) **UX-04** selector interaction audit — Payment Method chips likely first; **date remains picker**; Post-Save State Retention · Repeat Last Transaction · Smart Defaults explicitly blocked/not started. (4) **UX-05** universal outside-tap dismiss — backlog/last; requires separate infrastructure audit and dedicated tests. |
| 2026-06-10 | **AT-LIGHT-01 status → code complete, pending final verification.** P1–P6 all implemented (hierarchy/chip grammar, keypad separation, amount card, panel tint, nav-safe spacing, phone/POS keypad order). Host `pytest tests/` — **787/787 passed**. Phone visual verification remains before sign-off. **HDR-01** is the next approved roadmap item after verification. **QUICK-ENTRY-02** deferred; subcategory workflow unchanged. |
| 2026-06-10 | **ADD-TXN-BR-01 closed.** Sale validation aligned with bookkeeping: Cash/Card no longer blocked by category/subcategory; Credit Sale requires named customer (`_at_sale_credit_customer_error`). Expense/Purchase validation unchanged. Manual AT verification + host `pytest tests/` — **800/800 passed**. |
| 2026-06-10 | **AT-LIGHT-01 closed.** P1–P6 complete including phone/POS keypad order (ITU E.161). Manual phone/POS visual verification signed off. Host `pytest tests/` — **800/800 passed**. **HDR-01** is next active item; pre-implementation audit recorded — implementation not started. |
| 2026-06-10 | **HDR-01 closed.** Combined mobile header pass (UX-07 + UX-06): responsive company selector, ellipsis for long names, toolbar cluster (bell + profile, 8px gap), unified spacing tokens, header ownership cleanup. Header company selector remains canonical switch entry point; Profile “Switch Company” opens the same `co_switch` sheet — no duplicate mobile company menu. CSS-only (`mobile_header.css` + `theme.css` mobile block reconciliation). Host `pytest tests/` — **807/807 passed**. **UX-03** is next active item. |
| 2026-06-10 | **UX-03 closed.** Inline Expense category creation in mobile `More…` picker: `_cat_create_or_reactivate` helper shared with desktop dialog; search-zero-match CTA (`txn.mob.add_category_cta`) gated on `manage_categories`; auto-select + last-used memory via `_mob_at_apply_category_pick`. Expense-only; Sale/Purchase/subcategory/AT panel layout unchanged. Host `pytest tests/` — **818/818 passed**. **UX-04** is next active item. |
| 2026-06-10 | **UX-04A closed.** Post-save state retention fix in Add Transaction: stop clearing `at_last_cat_id` (desktop subcategory retained); clear `at_cust_sel` and worker salary amount fields; amount/notes still clear. `_at_clear_post_save_transient_fields()` in `app.py` only. Host `pytest tests/` — **826/826 passed**. **UX-04** Payment Method chips remains next — not implemented. |
| 2026-06-10 | **UX-04B closed.** Mobile PM chips replace payment-method bottom sheet: Row 1 → Type/Date/Currency; `_mob_at_render_pm_chip_row` uses shared pay-method helpers; payment picker retired; `mob_at_pm2` untouched. CSS in `mobile_txn.css` + `widgets.css`. Host `pytest tests/` — **840/840 passed**. UX-04 remainder: Repeat Last · Smart Defaults. |
| 2026-06-10 | **UX-04C closed.** Safe smart defaults: per-type PM memory on chip tap, default chain memory→static→allowed, type-switch restore, single-bank auto-pick only. `app.py` only. Host `pytest tests/` — **852/852 passed**. UX-04 remainder: Repeat Last Transaction. |
| 2026-06-10 | **Repeat Last Transaction v1 closed.** TXH row action for Expense (non-salary) + Purchase: explicit allowlist prefill, navigate to Add Transaction, no auto-save. `app.py` + locale. Host `pytest tests/` — **872/872 passed**. UX-04 umbrella complete. |
| 2026-06-10 | **DATE-01 closed.** Mobile date sheet: Today/Yesterday weekday labels, `at_date_follows_today` rollover, backdated Row 1 marker, closed-period courtesy check. `app.py` + `mobile_txn.css` + locale. Host `pytest tests/` — **887/887 passed**. |
| 2026-06-10 | **UX-01 v1 closed.** Narrow session restore: HMAC cookie `erp_session_restore`, user + company revalidation, no AT/nav persistence. Requires `ERP_SESSION_RESTORE_SECRET` in production. Host `pytest tests/` — **904/904 passed**. |
| 2026-06-10 | **MOBILE-14 re-baselined.** Original E1–E13 plan superseded by smaller **M1–M6** scope (many E-steps already closed by HDR-01, AT-LIGHT-01, UI-1, E4–E6, E9). Documentation + test-plan only — no CSS movement yet. LOGIN-01 and UX-02 blocked on **M1+M2** minimum. Zero visible UI change expected. |
| 2026-06-10 | **MOBILE-14 M1 closed.** `--hdr-h` dedupe within `theme.css` + `mobile_header.css`; M1 dedup tests promoted. Suite: **914 passed, 5 xfailed**. |
| 2026-06-10 | **MOBILE-14 M2 closed (verified no-op).** Dead `mobile_shell.css` `block-container padding-top` already removed during M1 session; canonical rule in `mobile_header.css`; tombstone comments + M2 contract test. Suite: **915 passed, 5 xfailed**. |
| 2026-06-10 | **MOBILE-14 roadmap correction.** M3/M4 downgraded to optional suppression-rule relocation (not blockers). M5 next active CSS step (`.erp-kpi-section`, `.kpi-grid` → `theme.css`). M6 open (sidebar + notification liveness). TXH xfail relabeled independent micro-step → `mobile_txn_history.css`. LOGIN-01 + UX-02 unblocked, not started. |
| 2026-06-10 | **MOBILE-14 M5 closed.** KPI/dashboard spacing rules moved `widgets.css` → `theme.css`. Suite: **916 passed, 4 xfailed**. |
| 2026-06-10 | **MOBILE-14 TXH micro-step closed.** Duplicate `txh_actions_` grid removed from `widgets.css`; canonical owner `mobile_txn_history.css`. **MOBILE-14 closed.** Suite: **918 passed, 2 xfailed** (M3/M4 optional xfails only). |
| 2026-06-09 | **ERP Ownership Audit** complete (**AUDIT-01**). Critical conflicts identified: `--hdr-h` 4-way token split, `widgets.css` KPI catch-all, mobile ownership drift, sidebar triple-hide, notification active state duplication, reports internal duplicate. Architectural finding: Dashboard, Banking, and Mobile Reports are mostly clean; Company Picker and Desktop Reports have no CSS surface (future work). Five quick wins identified that can be executed before MOBILE-14. Decision: all future UI work must follow ownership-first planning; new features must not introduce additional ownership conflicts. |
| 2026-06-05 | **FUTURE-MIGRATION-01** approved as long-term direction only — React + FastAPI + service layer + PostgreSQL target stack. Streamlit remains primary until pre-migration requirements and decision gate are met. No change to active module priorities. |
| 2026-06-05 | **ARCHITECTURE-PROTECTION-01** active immediately — all new modules service-first (models → services → tests → minimal UI). Streamlit must not own business logic; pause before deep UI for auth, staff portal, uploads, approval workflows. |
| 2026-06-13 | **VENDOR-NEUTRAL-01** active immediately — core architecture must not depend on named POS/vendor products; generic External Sales Source pattern (`source_name` free text, optional `source_type` category). Vendor names allowed in documentation examples only; future adapters live outside core. Cross-links ARCHITECTURE-PROTECTION-01 and FUTURE-MIGRATION-01. Audit (2026-06-13): no vendor leakage in production code. |
| 2026-06-05 | **DOCS-MIGRATION-CHECKPOINT-01** — register drift fix after FASTAPI-READINESS-CHECKPOINT: **POSTING-SERVICE-01 ✅ complete**; **REPORTS-SERVICE-01 / BANKING-SERVICE-01 🟡 partial**; FastAPI foundation partial (not complete); PostgreSQL test-only; React not started. Critical path: AUTH-SESSION-02-IMPL-3 → BANKING-SERVICE-01 → P2-HARDEN-01 → MONEY-DECIMAL-01 → PG cutover → React. Doc: [DOCS_MIGRATION_CHECKPOINT_01](./docs/DOCS_MIGRATION_CHECKPOINT_01.md). Contract: `test_docs_migration_checkpoint_01.py`. No runtime code. |
| 2026-06-13 | **FUTURE-MIGRATION-AUDIT-01 recorded** — independent FastAPI readiness audit (Claude): score **62/100**; new service modules FastAPI-ready; main blocker `app.py` posting engine; keystone **POSTING-SERVICE-01**; also track MONEY-DECIMAL-01, ALEMBIC-01, BANKING-SERVICE-01, REPORTS-SERVICE-01, CONTEXT-AUDIT-01. Register: [TECH_DEBT](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md). Does not start FastAPI/React implementation. *(Blocker list superseded 2026-06 by DOCS-MIGRATION-CHECKPOINT-01.)* |
| 2026-06-05 | **POSTING-SERVICE-01 PS-P2a complete** — `get_account_by_name`, sales `post_*` trio, `card_settlement_on` → `services/posting.py`; app.py shims unchanged signatures. `test_posting_service01_p2a.py` (18). PS-P2b (expense/purchase/payable) pending. Host `pytest tests/` — **1595 passed, 2 xfailed**. |
| 2026-06-13 | **STAFF-CAPTURE-01 SC-P1b complete** — `ui/staff_capture.py` (submit · my submissions · approval inbox), `NAV_STAFF_EXPENSE_CAPTURE`, `app._staff_capture_post_expense_draft` posting seam, EN/TR `sc.*` locales, `test_staff_capture01_ui_contract.py` (11). SC-P2 · SC-P3 pending. Host `pytest tests/` — **1551 passed, 2 xfailed**. |
| 2026-06-13 | **STAFF-CAPTURE-01 SC-P1 complete** — `ExpenseDraft` / `DraftAttachment` models, `services/staff_capture.py` (lifecycle, attachments, DTOs, injected `post_fn` approval, separation of duties), SC permission keys in `services/user_access.py`, tests (`test_staff_capture01_models.py`, `test_staff_capture01_drafts.py`, `test_staff_capture01_approval.py`). SC-P1b · SC-P2 · SC-P3 pending. Host `pytest tests/` — **1540 passed, 2 xfailed**. |
| 2026-06-13 | **USER-ACCESS-01 UA-P1 complete** — `UserPermissionOverride` model, `services/user_access.py` (registry, templates, effective resolver, override CRUD, owner lockout guard), `_can()` resolver swap, tests (`test_user_access01_permissions.py`, `test_user_access01_models.py`). UA-P1b · UA-P2 pending. **Smoke audit:** Owner/Manager/Viewer compatibility passed; 0 permission/hidden-page/access regressions; `manage_permissions` intentional owner-only addition. Host `pytest tests/` — **1502 passed, 2 xfailed**. |
| 2026-06-05 | **MIGRATION-READINESS-01** active immediately — FastAPI/React-ready service checklist (explicit `company_id`, serializable DTOs, no Streamlit in `services/`, contract tests, tech-debt register). Exemplar: DSC-P1 (`services/daily_sales_close.py`). Register: [TECH_DEBT_AND_MIGRATION_CLEANUP.md](./docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md). |
| 2026-06-05 | **RECIPE-COSTING-01 RC-P2A complete** — `MenuItem` / `MenuPriceHistory` models, menu profitability service APIs, `render_recipe_menu_items`, Menu Items nav, EN/TR `rc.menu.*` locales, tests (`test_recipe_costing_menu_models.py`, `test_recipe_costing_menu_service.py`). RC-P2B–P3 pending. Host `pytest tests/` — **1465 passed, 2 xfailed**. |
| 2026-06-05 | **RECIPE-COSTING-01 RC-P1b complete** — `ui/recipe_costing.py` (Ingredients · Recipes · Cost Breakdown), Recipe Costing nav, list/read/update APIs, EN/TR `rc.*` locales, UI contract tests (`test_recipe_costing_ui_contract.py`). RC-P2–P3 pending. Host `pytest tests/` — **1447 passed, 2 xfailed**. |
| 2026-06-05 | **RECIPE-COSTING-01 RC-P1 complete** — `Ingredient` / `Recipe` / `RecipeLine` models, `services/recipe_costing.py`, service/model tests. |
| 2026-06-05 | **DAILY-SALES-CLOSE-01 DSC-P2 complete** — `ui/external_sales_verification.py`, Closings nav, permissions, EN/TR `esv.*` locales, UI contract tests (`test_daily_sales_close_ui_contract.py`). Thin `app.py` dispatch only. DSC-P3–P4 pending. Host `pytest tests/` — **1403 passed, 2 xfailed**. |
| 2026-06-05 | **DAILY-SALES-CLOSE-01 DSC-P1 complete** — `ExternalSalesVerification` model, `services/daily_sales_close.py`, service/model tests. |

---

## How to run tests

```bash
cd streamlit_accounting_erp
./venv/bin/python -m pytest tests/ -q
```

Expected: **1502 passed, 2 xfailed**.

---

*Update this file when each phase completes.*
