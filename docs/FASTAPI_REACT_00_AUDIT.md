# FASTAPI-REACT-00 — Migration Baseline Audit (FastAPI + React)

**Mode:** Audit only. **No implementation.** Does **not** authorize production FastAPI cutover or React SPA build.

**Date:** 2026-06-05  
**Authority:** Governs planning for slices **FASTAPI-REACT-01+** (future). Consolidates prior audits without replacing them.

**Supersedes for planning gate only:** blocker ordering in [DOCS_MIGRATION_CHECKPOINT_01](./DOCS_MIGRATION_CHECKPOINT_01.md) remains authoritative for register drift; this audit adds a **single React+API readiness snapshot**.

---

## 1. Executive summary

| Layer | Status (2026-06) | Evidence |
|-------|------------------|----------|
| **Service / GL kernel** | ✅ Extracted | `services/posting.py`; app.py shims delegate |
| **Read services (FASTAPI-P0)** | ✅ Shipped | `services/read_*` (reports, ledger, AR/AP, balances, recon readiness, partner statement) |
| **FastAPI foundation** | 🟡 **Partial** | `api/main.py` — P1 reads + P2 writes; JWT + `X-Company-Id`; writes feature-flagged |
| **PostgreSQL runtime** | 🟡 Test-only | SQLite remains production runtime |
| **React SPA** | ⬜ **Not started** | `docs/ERP_DS_05_REACT_ARCHITECTURE.md` spec only; no `package.json` |
| **UI design contracts** | ✅ Frozen | MONO-THEME-01/02 grammar + `ui/react_design_contract.py` + NAV-ARCH-S4 routes |

**Recommendation:** **Proceed with service hardening and API boundary work** (PS-P7, AUTH-SESSION-02, P2-HARDEN-01) **before** React implementation. **Defer React build** until read API spine is stable and token/route contracts are consumed by a thin API client prototype.

---

## 2. What is already FastAPI-ready?

### 2.1 API application (shipped)

- **Entry:** `api/main.py` — `create_app()` mounts auth, reports, ledger, receivables/payables, banking, sales, expenses, purchases, voids, partner/worker movements, bank transactions, reconciliation, closing.
- **Auth:** JWT bearer (`api/bearer_auth.py`, `services/tokens.py`); `X-Company-Id` header for company scope.
- **Guards:** `api/guards.py`, `api/auth_dependencies.py`, `services/permissions.py` — membership + permission resolution per request.
- **Tests:** 38 files `tests/test_fastapi_p0_*.py`, `tests/test_fastapi_p1_*.py`, `tests/test_fastapi_p2_*.py`.

### 2.2 Read services (DTO-oriented)

| Module | Role |
|--------|------|
| `services/read_reports.py` | P&L, balance sheet, cash flow |
| `services/read_ledger.py` | GL page data |
| `services/read_ar_ap.py` | Receivables / payables |
| `services/read_partner_statement.py` | Partner statements |
| `services/read_balances.py` | Balances, liquid position |
| `services/read_reconciliation.py` | Statement readiness |

### 2.3 Write services (partial, flag-gated)

- `services/write_*.py` families behind `ERP_API_WRITE_*=1` env flags (sales, expenses, purchases, banking, voids, reconciliation, etc.).
- Streamlit remains **primary UI**; API writes coexist for integration/testing.

### 2.4 Registry + settings (explicit `company_id`)

- `registry/service.py` — settings/effective config
- `services/user_access.py` — permissions, member views with `to_dict()`

---

## 3. What is already React-ready (contracts only)?

| Contract | Owner | Tests |
|----------|-------|-------|
| Design tokens + grammar | `ui/design_tokens.py`, `ui/react_design_contract.py` | `test_mono_theme_01_s7_react_contract_cleanup.py`, `test_ui_system_02_s5_react_design_contract.py` |
| Route map (42 routes) | `registry/navigation.py` → `react_route` | `test_nav_arch_s4_react_route_contract.py` |
| Component map | `docs/UI_SYSTEM_02_REACT_DESIGN_CONTRACT.md` | S5 react contract tests |
| MONO-THEME visual grammar | MONO-THEME-01/02 CSS + tokens | `test_mono_theme_02_epic_matrix.py` |
| Banking workflow (React) | `registry/banking_workflow_contract.py` | `test_banking_ux_04_s4_react_workflow_contract.py` |
| Architecture spec | `docs/ERP_DS_05_REACT_ARCHITECTURE.md` | Doc reference only |

**React rule:** import `react_token_bundle()` — do not fork hex or color-mix strings in the SPA.

---

## 4. What still blocks React / production API?

| ID | Blocker | Why it matters |
|----|---------|----------------|
| **TD-PS-01** | Posting internal commits | API must own unit-of-work per request |
| **TD-PS-03** | ORM returns at posting boundary | React needs stable JSON DTOs |
| **TD-PS-06/07** | Ambient `company_id` fallback | Cross-tenant leak risk |
| **PS-P6-5** | Reconciliation JE company stamp | Multi-tenant correctness |
| **P2-HARDEN-01** | API `company_id` stamping vs Streamlit `before_flush` | Write path parity |
| **AUTH-SESSION-02** | HttpOnly refresh / idle extension | Production session model |
| **MONEY-DECIMAL-01** | `Float` → `Decimal` | PG + money integrity |
| **BANKING-SERVICE-01** | `reconciliation/match_post.py` lazy `import app` | Service boundary incomplete |
| **REPORTS presentation** | `render_*` formatters in `app.py` | Acceptable for Streamlit; React needs API-only presentation layer |

Historical baseline score **62/100** ([FUTURE-MIGRATION-AUDIT-01](./TECH_DEBT_AND_MIGRATION_CLEANUP.md)) — still useful; extraction since shipped improves service score; **ambient context + write boundaries** remain the main drag.

---

## 5. What must NOT change in FASTAPI-REACT-00

- **Accounting behavior** — no GL rule changes, no posting pair edits, no schema migrations.
- **Streamlit primary UI** — no removal or reroute of `app.py` pages.
- **Frozen contracts** — `react_route` paths, `COMPONENT_GRAMMAR_TOKENS`, MONO-THEME palette.
- **Docker dev setup** — `docker-dev-safe-setup` tag; do not alter container files unless a future slice requires it.
- **No React repo bootstrap** — no `package.json`, no Vite scaffold in this epic slice.

---

## 6. Recommended phased roadmap (FASTAPI-REACT-01+)

| Slice | Scope | Prerequisite |
|-------|--------|--------------|
| **FASTAPI-REACT-01** | PS-P7 posting boundary hardening (commit ownership, `PostingResult` DTO, company_id unification) | Audit only complete |
| **FASTAPI-REACT-02** | AUTH-SESSION-02 production session spine (idle extension → HttpOnly refresh path) | IMPL-3+ |
| **FASTAPI-REACT-03** | P2-HARDEN-01 API write stamp audit + reconciliation `_app()` removal | 01–02 |
| **FASTAPI-REACT-04** | Read API stabilization — OpenAPI consumer smoke, error contract freeze | P0/P1 green |
| **FASTAPI-REACT-05** | React bootstrap — ThemeProvider from `react_token_bundle()`, shell + router from NAV-ARCH-S4 | 04 + MONO-THEME-02 complete |
| **FASTAPI-REACT-06** | First React pages (Home, Ledger read-only) behind feature flag | 05 |
| **FASTAPI-REACT-07** | PostgreSQL runtime cutover (after MONEY-DECIMAL-01 + Alembic authority) | Separate PG epic |

**Sequencing rule:** No React page work before **04**; no production API writes promotion before **01–03**.

---

## 7. Risk matrix

| Risk | Severity | Mitigation |
|------|----------|------------|
| Cross-tenant data via ambient `company_id` | Critical | PS-P7 + P2-HARDEN-01 before write API promotion |
| Money rounding drift on PG | High | MONEY-DECIMAL-01 characterized tests before PG |
| React forks design tokens | Medium | `react_token_bundle()` SSOT + contract tests |
| Streamlit/API behavior divergence | Medium | Shared `services/*` only; no logic in `api/routes` beyond guards/serialization |
| Premature React build | Medium | FASTAPI-REACT-00 gate — contracts frozen, API partial |

---

## 8. Test plan (audit guardrails)

| Guard | File |
|-------|------|
| This audit doc | `tests/test_fastapi_react_00_audit.py` |
| FastAPI inventory | Existing `tests/test_fastapi_p1_api_contract.py`, P0/P2 suites |
| React token bundle | `tests/test_ui_system_02_s5_react_design_contract.py` |
| Route contract | `tests/test_nav_arch_s4_react_route_contract.py` |
| Migration register | `tests/test_docs_migration_checkpoint_01.py` |

---

## 9. Implementation boundaries

| Layer | Owner today | React port rule |
|-------|-------------|-----------------|
| Business logic | `services/*`, `registry/*` | Unchanged — API calls services |
| Streamlit UI | `app.py`, `ui/*` | Retained until FASTAPI-REACT-06+ |
| API routes | `api/routes/*` | Thin — guards + serialization only |
| CSS / theme | `ui/theme.css`, `mobile_*.css` | Streamlit-only selectors per `STREAMLIT_ONLY_SELECTORS` |
| Navigation data | `registry/navigation.py` | Mirror `react_route` in React router |

---

## 10. Cross-references (do not duplicate)

- [FASTAPI_MIGRATION_01_AUDIT.md](./FASTAPI_MIGRATION_01_AUDIT.md) — original service-boundary audit
- [DOCS_MIGRATION_CHECKPOINT_01.md](./DOCS_MIGRATION_CHECKPOINT_01.md) — register drift fix (2026-06)
- [UI_SYSTEM_02_REACT_DESIGN_CONTRACT.md](./UI_SYSTEM_02_REACT_DESIGN_CONTRACT.md) — token + component freeze
- [NAV_ARCH_REACT_ROUTE_CONTRACT.md](./NAV_ARCH_REACT_ROUTE_CONTRACT.md) — 42-route map
- [ERP_DS_05_REACT_ARCHITECTURE.md](./ERP_DS_05_REACT_ARCHITECTURE.md) — SPA architecture spec
- [MONO_THEME_02_VISUAL_CONTRACT.md](./MONO_THEME_02_VISUAL_CONTRACT.md) — live UI refinement complete

---

## 11. Recommendation

**Proceed** with **FASTAPI-REACT-01** (posting boundary hardening) as the next *implementation* slice after this audit. **Revise/defer** any React SPA scaffold until read API stabilization (**FASTAPI-REACT-04**). This audit is **documentation only** — it records the baseline and does not start FastAPI production cutover or React build.

*Frozen 2026-06-05. FASTAPI-REACT-00 audit complete. Next: **FASTAPI-REACT-01** (posting boundary hardening) when approved.*
