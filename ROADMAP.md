# ERP Development Roadmap

**Project:** `streamlit_accounting_erp`  
**Last updated:** 2026-06-10 (UX-03 closed · UX-04 next active)  
**Companion docs:** [ARCHITECTURE_HANDOFF.md](./ARCHITECTURE_HANDOFF.md) · [PHASE_18_DESIGN_REVIEW.md](../PHASE_18_DESIGN_REVIEW.md) · [docs/NAVIGATION_AUDIT.md](./docs/NAVIGATION_AUDIT.md)

This roadmap defines **what is done**, **what is active**, and **what comes next** — in order. Do not skip phases without an explicit architecture decision.

---

## Status at a glance

| Area | Status |
|------|--------|
| Core ERP & accounting engine | ✅ Complete |
| Multi-company isolation | ✅ Complete |
| Company settings isolation (14D-B) | ✅ Complete |
| Settings / module registry (14D-B2a) | ✅ Complete |
| COA & categories per company (14D-C) | ✅ Complete |
| Company creation (14D-D) | ✅ Complete |
| Sidebar uses company role (nav fix) | ✅ Complete |
| Simplified Company Setup UI | ✅ Complete (Expert policies stub) |
| Automated tests | ✅ **818 passing** (run `pytest tests/` on host) |
| Member management (14D-E) | ✅ Complete |
| Member roster polish (14D-F) | ✅ Complete |
| Setup wizard v1 (14D-G) | ✅ Complete — **superseded by SETUP-01** (design approved, not built) |
| SETUP-01 Company Creation Wizard | 🟡 **HIGH** — design approved |
| SETUP-02 Setup Summary | 📋 Medium — planned |
| SETUP-03 Configuration Health Check | 📋 Medium — planned |
| BANK-03 POS Settlement wording | 📋 Low — rename user-facing “Card Settlement” → “POS Settlement” |
| Localization EN/TR (15) | ✅ Complete |
| DEVELOPMENT_MODE | ⚠️ **On** in `app.py` (`DEVELOPMENT_MODE = True`) — set `False` before production |
| Shell / mobile chrome (Phase A) | ✅ Stabilized — fixed header, 968px breakpoint, People hub wired |
| Sidebar / navigation redesign (AD-UI-001) | 🟡 **D1 done** — Financial Statements routes; D2+ gated — see [NAVIGATION_AUDIT.md](./docs/NAVIGATION_AUDIT.md) §16 |
| **MOB-AT-C1** — Concept C Mobile AT UI | ✅ **Accepted** — reference implementation; 747 tests passing |
| **MOBILE-11** — Mobile Design System | ✅ **Approved** — `docs/MOBILE_UI_SYSTEM.md` is the governing document for all future mobile work |
| **MOBILE-12** — Design Governance | ✅ **Approved** — open decisions recorded; phased migration path defined |
| ERP-Wide UI Ownership Principle | ✅ **Approved** — governs all CSS work going forward |
| **CSS-01** — Theme Ownership Consolidation | 🟡 **HIGH** — approved; ownership map for existing CSS |
| **CSS-02** — ERP-Wide UI Ownership Standard | 🟡 **HIGH** — approved; 8 enforceable rules; ongoing standard |
| **MOBILE-14** — Mobile Theme Ownership Cleanup | 🟡 **HIGH** — approved; E1–E13 consolidation steps |
| **LOGIN-01** — Login / Company Picker Modernization | 📋 Medium — planned; blocked on MOBILE-14 |
| **QUICK-ENTRY-01** — Context-Aware Mobile Category Selection | ✅ **DONE** — implemented; 14/14 tests passing (2026-06-10) |
| **ADD-TXN-BR-01** — Sale validation vs bookkeeping rules | ✅ **Closed** — manual + pytest verified (2026-06-10) |
| **AT-LIGHT-01** — Mobile AT Light-Mode Polish (P1–P6) | ✅ **Closed** — manual phone/POS verification complete (2026-06-10) |
| **DATE-01** — Fast Mobile Date Entry | 📋 Medium — future; independent |
| **UX-01** — Session Persistence | 📋 Medium — future; independent |
| **UX-02** — Responsive Viewport & Device Auto-Fit | 🟡 **HIGH** — approved; blocked on MOBILE-14; investigation required |
| **HDR-01** — Combined Header Pass (UX-07 + UX-06) | ✅ **Closed** — responsive selector, ellipsis, toolbar cluster (2026-06-10) |
| **UX-03** — Inline Expense Category Creation | ✅ **Closed** — Expense picker search CTA (2026-06-10) |
| **UX-04** — Selector Interaction Audit (PM chips likely first; date remains picker) | 🟡 **Next active** — approved; gates cleared |
| **Post-Save State Retention** | 📋 **Blocked on UX-04** — not started |
| **Repeat Last Transaction** | 📋 **Blocked on UX-04** — not started |
| **Smart Defaults** | 📋 **Blocked on UX-04** — not started |
| **UX-05** — Universal Outside-Tap Dismiss | 📋 Backlog — last; needs separate infrastructure audit + tests |
| **CHART-01** — Chart Theme Consolidation | 📋 Medium — planned; independent of MOBILE-14 |
| **AUDIT-01** — ERP Ownership Audit | ✅ **Complete** — findings recorded; quick wins identified |
| Future UX / navigation vision | 📋 **Low** — design direction only (MOBILE-07–12, DESIGN-05, DESKTOP-04) — implementation gated on MOBILE-11 system |
| UI architecture stability (UI-STAB) | 📋 **Planned** — Desktop/Mobile audit findings recorded — **not approved for implementation** |
| Operational friction log (OBS-01) | 🟡 **Active** — record real-world UX friction; 3+ occurrences → roadmap candidate |

---

## Current priority

**Use the system daily** — build only what causes friction during real bookkeeping.

**Next build (approved):** **UX-04** — selector interaction audit (Payment Method chips likely first; date remains picker). See [UX-04](#ux-04--selector-interaction-audit).

**Recently closed:** **UX-03** (inline Expense category creation in `More…` picker) · **HDR-01** · **AT-LIGHT-01** · **ADD-TXN-BR-01**. Host pytest: **818/818 passed** (2026-06-10).

**Also active (HIGH):** **SETUP-01** — ensure every new company starts with the correct workflow from day one.

**CSS architecture cleanup (HIGH — approved):** **MOBILE-14** — execute E1–E13 consolidation steps before any further UI redesign. **CSS-01** defines the ownership targets. Neither is a visual redesign.

**Observe during use (do not build yet):** Dashboard quick actions, worker advance mobile parity, BANK-01 reality audit (after weeks of real card/bank activity). Log friction in **[OBS-01](#obs-01--operational-friction-log)** as it happens.

**Deferred:** Inventory expansion, procurement, CRM, BI, PostgreSQL — until real usage demands them.

**Do NOT start (future projects — see [FUTURE UX / NAVIGATION VISION](#future-ux--navigation-vision)):** Banking redesign · Reports redesign · Mobile shell redesign · Navigation redesign · More Hub redesign · Sidebar redesign.

**Current focus stays on:** (1) Accounting stability · (2) Daily-use workflow testing · (3) Banking observation · (4) UX cleanup · (5) Real-world usage feedback.

**Success metric:** Daily sales, expenses, and purchases are easy to enter; banking is understandable; month-end is fast; company switching is reliable — not feature count.

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

### BANK-03 — Wording update 📋 **Low**

Rename user-facing **“Card Settlement”** → **“POS Settlement”**.

Keep **“Card Sales Clearing”** for COA / account names only.

**Purpose:** Reduce confusion with Company Credit Card (KK).

**Status:** Copy spec ready (Banking → Settings + wizard); not shipped.

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

## FUTURE UX / NAVIGATION VISION

**Status:** Planned Future Work  
**Priority:** Low  
**Not approved for implementation.** Design direction only.

Record approved future-direction decisions so they are not forgotten. **No code, no screen redesign, no sprint** until explicitly approved.

**Cross-references (do not duplicate):**

| Existing roadmap item | Relationship |
|----------------------|--------------|
| **AD-UI-001** | D1 statement routes done; D2+ = incremental Reports/sidebar dedup — **not** this vision |
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

**Current findings:**

- Header styling is distributed across `theme.css`, `mobile_shell.css`, and `mobile_header.css`.
- Multiple header-height definitions exist (`--hdr-h` conflicts across files and breakpoints).
- Header behavior has historically been difficult to change consistently.
- Dead toolbar slot branches (`primary` / `mobile_left`) in `_render_hdr_toolbar`; obsolete `hdr_mobile_title` popover CSS after company-switch sheet migration.

**Goals:**

- Single source of truth for header sizing.
- Single source of truth for toolbar spacing.
- Single source of truth for company selector styling.
- Single source of truth for avatar rendering.

**Constraints:** No redesign. Architecture cleanup only.

**Trigger:** Only after current mobile header visuals are approved (see [MOBILE-10](#mobile-10--mobile-header-modernization)).

---

### UI-STAB-02 — Banking Presentation Separation

**Priority:** High

**Current findings:**

- Banking remains largely desktop-first (`render_banking()` — one presentation layer for all viewports).
- Desktop and mobile share one presentation layer (horizontal radio, multi-column forms, dataframes).

**Future direction:**

Separate:

- `render_banking_desktop()`
- `render_banking_mobile()`

while keeping shared:

- Accounting logic
- Posting
- Permissions
- Reconciliation logic

**Goal:** Presentation separation only.

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

**Implementation:** See [MOBILE-14](#mobile-14--mobile-theme-ownership-cleanup) for the ordered execution plan.

---

## MOBILE-14 — Mobile Theme Ownership Cleanup

**Status:** ✅ Approved · **Priority:** High

**Purpose:** Architectural cleanup only. Not a visual redesign. Executes the consolidation order from [CSS-01](#css-01--theme-ownership-consolidation). If any step produces a visible change, a rule was missed from the target file — not intentional.

**Prerequisite:** None — can begin immediately.

**Unlocks:** [LOGIN-01](#login-01--login--company-picker-modernization).

### Consolidation steps (execute in order)

| Step | Action | Files touched | Risk |
|---|---|---|---|
| **E1** | Remove `--hdr-h` from `widgets.css` and `mobile_shell.css`. Keep only in `theme.css` (60px) and `mobile_header.css` (56px/86px). Audit every `var(--hdr-h)` usage after removal. | `widgets.css`, `mobile_shell.css` | Medium |
| **E2** | Remove dead `block-container padding-top` from `mobile_shell.css`. `mobile_header.css` is canonical. | `mobile_shell.css` | Low |
| **E3** | Fix chip override selector bug — `:not([class*="mob_at_save"])` tests the wrong element. Correct selector so the save button is genuinely excluded. Resolves MOBILE-13 save button colour. | `widgets.css` | Medium |
| **E4** | Move AT panel layout grids (`mob_at_amount_row`, `mob_at_tabs`, `mob_at_keypad`, `mob_at_pm2/3`) from `widgets.css @media` block into `mobile_txn.css`. Highest risk step — verify full AT panel after. | `widgets.css`, `mobile_txn.css` | High |
| **E5** | Move report layout grids (`mob_rpt_sel_*`, `mob_rpt_cf_kpi`, `erp_mob_rpt_filters`) from `widgets.css @media` block into `mobile_reports.css`. | `widgets.css`, `mobile_reports.css` | Medium |
| **E6** | Remove dead TXH filter grids (`txh_filter_row1`, `txh_filter_row2`) from `widgets.css` — already live in `mobile_txn_history.css`. | `widgets.css` | Low |
| **E7** | Remove duplicate bottom nav, FAB button, and hub sheet blocks from `widgets.css`. Verify `mobile_shell.css` covers all removed properties before deleting. | `widgets.css` | Low |
| **E8a** | Remove duplicate report active chip rules from `mobile_reports.css` (primary button colour block). `widgets.css` lines 402–423 carry identical selectors and values — removing the `mobile_reports.css` copy is zero-risk. `widgets.css` becomes sole owner of report active chip state. | `mobile_reports.css` | Low |
| **E8b** | Migrate report idle chip rules to `widgets.css` UI-1 block, then remove from `mobile_reports.css`. The idle rule (`--erp-chip-idle-bg/fg/border` on secondary buttons) is not correctly covered by the global secondary rule in `widgets.css` (`--theme-card`); removing without first adding to `widgets.css` causes visual regression. Add to `widgets.css`, verify visual parity, then remove from `mobile_reports.css`. `widgets.css` becomes sole owner of report idle chip state. | `widgets.css`, `mobile_reports.css` | Low–Medium |
| **E9** | Deduplicate `--mob-at-*` token block. Single definition in `mobile_txn.css :root`. Remove copy from `widgets.css`. | `widgets.css`, `mobile_txn.css` | Medium |
| **E10** | Remove internal `.banner.banner-primary` duplicate from `theme.css` — functionally identical to `.banner`. | `theme.css` | Trivial |
| **E11** | Remove dead notification active state from `widgets.css` — `mobile_header.css` loads after it and wins. | `widgets.css` | Trivial |
| **E12** | Fix hardcoded `#9ca3af` in `app.py` login credentials hint — replace with `color:var(--theme-muted)`. Then remove the attribute-selector colour fixers from `theme.css` lines 680–760. | `app.py`, `theme.css` | Low |
| **E13** | Decide ownership of profile sheet and co-switch sheet. Currently only in `widgets.css @media`. Document the decision; consider moving to `mobile_shell.css` or a dedicated `mobile_overlays.css`. | `widgets.css`, possibly `mobile_shell.css` | Low |

### Constraints

- E1 and E2 before all other steps — remove dead `--hdr-h` values first.
- E3 before E4 — chip selector fix may affect AT panel button interactions.
- E4 is the highest-risk step. After moving AT grids, verify the full AT panel on a real mobile viewport before continuing.
- Run `pytest tests/` after E4 and E9 as regression checks.

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

## LOGIN-01 — Login / Company Picker Modernization

**Status:** 📋 Planned · **Priority:** Medium · **Blocked:** Until [MOBILE-14](#mobile-14--mobile-theme-ownership-cleanup) complete.

**Purpose:** Bring the login screen and company picker into the approved Concept C design language so the entire app feels like one product from first load.

**References:** [`docs/MOBILE_UI_SYSTEM.md`](./docs/MOBILE_UI_SYSTEM.md) · Concept C reference implementation ([MOB-AT-C1](#mob-at-c1--concept-c-mobile-add-transaction-ui)) · Login Audit (June 2026).

**Dependency rationale:** MOBILE-14 must run first to establish a stable CSS ownership baseline in `mobile_header.css` (the canonical auth-screen owner) and eliminate cascade conflicts that would make new login CSS unpredictable.

### Scope

| Area | Current state | Target state |
|---|---|---|
| Company banner | `banner banner-primary` with gradient — desktop-first | Concept C surface panel; `erp-auth-banner` classes already defined in `mobile_header.css` |
| User tiles | Unstyled `st.button` with multi-line text; 64–88px height | Avatar-style cards using `erp-mono-avatar` (class already in `theme.css` line 639) |
| Login form | `st.container(border=True)` + `st.form` — generic widget styling | Scoped to auth context via `erp-auth-*` classes; no structural change to login logic |
| Layout | `st.columns([1, 2, 1])` centering hack | `max-width` constraint on content block; no column hack on mobile |
| Credentials hint | Hardcoded `color:#9ca3af` inline style | `color:var(--theme-muted)` — resolved by MOBILE-14 E12 |
| Touch targets | Some interactive elements below 44px | All interactive targets ≥ 44px |

### Constraints

- Use `erp-auth-*` classes already defined in `mobile_header.css` — do not introduce new class families.
- Colour: `--theme-*` tokens only. No Concept C hardcoded hex on auth screens.
- No accounting, schema, or session logic changes.
- Mobile-first. Desktop login is a lower priority.

---

## QUICK-ENTRY-01 — Context-Aware Mobile Category Selection

**Status:** ✅ Implemented & verified (2026-06-10) — `pytest tests/test_quick_entry.py` 14/14 passing on host. · **Priority:** High

**Design philosophy:** FAST ENTRY FIRST — fewer taps, less typing, faster bookkeeping.

**Purpose:** Reduce the number of taps required during daily mobile transaction entry by surfacing common categories directly inside the Add Transaction panel, without requiring the user to open a picker sheet for the majority of transactions.

**Depends on:** MOBILE-14 complete. No accounting engine changes. No database schema changes.

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

**Status:** 📋 Future · **Priority:** Medium · **Independent** — no dependency on MOBILE-14 or other open items.

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

### Behaviour rules

| Element | Behaviour |
|---|---|
| **Today** | Selects today's date, closes sheet immediately — no confirm required |
| **Yesterday** | Selects yesterday's date, closes sheet immediately |
| **This Week** | Sets date to Monday of the current week — closes immediately |
| **Custom Date** | Expands the existing `st.date_input` calendar inline; requires Confirm Date tap (existing behaviour, unchanged) |
| **Recent dates** | Shows up to 3 distinct dates from the current session's prior transactions; tapping selects and closes immediately |
| **Default state** | Today is pre-highlighted on open — matches `at_date` session key |

### Scope

- Mobile only. Desktop AT date field unchanged.
- No new session keys required beyond existing `at_date`.
- Recent dates derived from in-session transaction history — no persistent storage, no new database column.
- No accounting, schema, or posting logic changes.
- The existing Confirm Date flow (for Custom Date only) is unchanged.

### Non-goals

- No multi-date selection.
- No date range picker.
- No changes to how dates are stored, posted, or validated.

**Cross-references:** [MOB-AT-C1](#mob-at-c1--concept-c-mobile-add-transaction-ui) · [QUICK-ENTRY-01](#quick-entry-01--context-aware-mobile-category-selection) · [MOBILE_UI_SYSTEM.md](./docs/MOBILE_UI_SYSTEM.md)

---

## UX-01 — Session Persistence

**Status:** 📋 Future · **Priority:** Medium · **Independent** — no dependency on MOBILE-14 or other open items.

**Purpose:** Users should not need to reconfigure the ERP after login, refresh, company switch, or browser restart. Non-accounting preferences should be remembered automatically so a returning user can open the app and continue working with minimal setup.

### Problem

Currently, every login or refresh resets the user's context — selected company, active page, currency, theme, and sidebar state are all lost. For daily-use bookkeeping, this means repetitive reconfiguration that adds friction before any actual work begins.

### What to remember

| Preference | Notes |
|---|---|
| Last selected company | On next login, open the previously active company automatically |
| Preferred theme (light / dark) | Persist across sessions |
| Sidebar state (open / collapsed) | Restore on reload |
| Last visited page | Return the user to where they left off after login |
| Last used currency | Pre-select on Add Transaction |
| Dashboard filters | Optional — restore date range or filter state if set |
| Desktop / mobile layout preference | If a user manually overrides layout mode in a future feature, remember that preference |

### Examples

| Scenario | Current behaviour | Target behaviour |
|---|---|---|
| Login after yesterday's session | Opens default company and default page | Opens India Gate (last used company) on Banking (last visited page) |
| Refresh mid-session | Resets to defaults | Restores company, page, and currency |
| Company switch | Forgets previous company context | On next login, remembers last active company |
| Currency entry | Defaults to company currency every time | Pre-selects TRY (last used) |

### Constraints

- Must be company-aware — preferences that are company-specific (last page, last currency) must be stored and retrieved per company, not globally.
- Must not affect accounting data, journal entries, balances, or reports.
- Must not affect permissions or role enforcement — persisted preferences do not grant access to anything.
- Must not bypass authentication — preference restoration happens after successful login only.
- Preferences must be stored separately from accounting records (not in transaction tables, not in the COA).

### Non-goals

- No syncing preferences across devices (single-device persistence is sufficient for v1).
- No preference management UI in v1 — preferences are set implicitly through normal use.
- No changes to accounting logic, schema, or posting behaviour.

**Cross-references:** [LOGIN-01](#login-01--login--company-picker-modernization) · [UX-02](#ux-02--responsive-viewport--device-auto-fit)

---

## UX-02 — Responsive Viewport & Device Auto-Fit

**Status:** ✅ Approved · **Priority:** High · **Blocked:** Until [MOBILE-14](#mobile-14--mobile-theme-ownership-cleanup) complete.

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

## UX-04 — Selector Interaction Audit

**Status:** 🟡 **Next active** · **Priority:** Medium · Gates cleared ([UX-03](#ux-03--inline-expense-category-creation) closed 2026-06-10).

**Explicitly not started (blocked under UX-04 umbrella):**

- Post-Save State Retention
- Repeat Last Transaction
- Smart Defaults

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
| `--hdr-h` token — 4-way split | See **CSS-01 C2** | MOBILE-14 E1 |
| `widgets.css` KPI catch-all | See **CSS-01 C1** | MOBILE-14 E3 |
| Mobile ownership drift (layout grids) | See **CSS-01 C4** | MOBILE-14 E4–E9 |
| Sidebar hide — 3 rules in 2 files | `theme.css @media`, `mobile_shell.css @media`, `mobile_shell.css html.erp-mobile` all hide sidebar on mobile | MOBILE-14 — keep `theme.css @media` as primary; document or remove the others |
| Notification active state — duplicated | `widgets.css` line 1025 AND `mobile_header.css` line 117 | MOBILE-14 E11 — remove `widgets.css` copy; `mobile_header.css` is the correct owner |
| Reports internal duplicate | `.erp-mobile-report-filters` visibility set twice inside `theme.css` (lines 1107 and 1354) | Independent quick win — remove line 1107; line 1354 is live |

### Architectural Findings

| Area | Finding |
|---|---|
| Dashboard | Ownership mostly clean — all `erp-dash-*` classes in `theme.css`. Two imported conflicts from `widgets.css` and `mobile_shell.css` (addressed by MOBILE-14). |
| Banking | Ownership mostly clean — no banking-specific CSS file; uses shared `theme.css` classes only. No mobile layout adaptation exists (future `mobile_banking.css`). |
| Mobile Reports | Ownership mostly clean — `mobile_reports.css` is isolated. Desktop reports have no dedicated ownership surface. |
| Company Picker | Almost no styling ownership — emits no `erp-*` classes; tiles are plain `st.button`. This is intentional pending LOGIN-01. |
| Mobile Banking | No dedicated CSS owner. If mobile banking is added, create `ui/mobile_banking.css` scoped to an `erp-banking-mobile-host` sentinel class, following `mobile_reports.css` as a template. |
| Desktop Reports | No dedicated ownership surface. `erp-rpt-sel-desktop-host` class is emitted in `app.py` but has no CSS targeting it. Reserved for a future `ui/desktop_reports.css` (mirrors `desktop_txn_history.css` pattern). |

### Chart Findings

| Finding | Detail | Resolution Path |
|---|---|---|
| Incomplete chart theming | Only 2 of 8 chart instances use `chart_series_color()` / `chart_reference_color()` helpers | CHART-01 |
| Dark mode breakage | 6 `st.bar_chart` / `st.line_chart` instances render on Streamlit default white — breaks in dark mode | CHART-01 — replace with Altair + `chart_theme()` |
| No `chart_theme()` helper | Helper referenced in CHART-01 scope does not yet exist | CHART-01 |

### Login Findings

| Finding | Detail |
|---|---|
| Redesign blocked | Login / Company Picker redesign blocked on MOBILE-14 per LOGIN-01 |
| Hardcoded color | `color:#9ca3af` in credentials hint in `app.py` — tracked under MOBILE-14 E12 |
| No mobile layout | Desktop `st.columns([1, 2, 1])` centering does not adapt to mobile |
| Email-based auth | Remains future **AUTH-01** work — not in scope for LOGIN-01 |

### Quick Wins (Independent — No MOBILE-14 Dependency)

These three items are not tracked in MOBILE-14 and can be executed at any time with minimal risk:

1. **Reports duplicate rule** — remove `theme.css` line 1107 (`.erp-mobile-report-filters` visibility). Line 1354 is the live rule.
2. **Dead desktop report host** — remove or activate `erp-rpt-sel-desktop-host` wrapper in `app.py` line 4158. Either delete the `st.markdown` wrapper or create `ui/desktop_reports.css` to use it as a scoping host (mirrors `desktop_txn_history.css` pattern).
3. **Sidebar ownership decision** — document whether `mobile_shell.css html.erp-mobile` sidebar hide is intentional (JS-cookie guard) or redundant. Either add a comment or remove it.

The following are tracked inside MOBILE-14 and listed here for visibility only — do not execute them as independent tasks:

- **Login hardcoded color** (`color:#9ca3af` → `var(--theme-muted)`) — **MOBILE-14 E12**
- **Header notification duplicate** (`widgets.css` line 1025) — **MOBILE-14 E11**

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
| 2026-06 | Shared DB + `company_id` isolation — do not redesign per-tenant DB yet |
| 2026-06 | Hidden ≠ disabled ≠ locked |
| 2026-06 | 14D-C + 14D-D + nav fix + simplified Company Setup |
| 2026-06 | 14D-B2a shipped read-only; enforcement in B2b / 14D-C |
| 2026-06-06 | Phase 18-MUX approved in principle (mobile calculator New Transaction); backlog only — after mobile nav stabilization |
| 2026-06-09 | **AD-UI-001** sidebar/navigation redesign approved (high priority); implementation gated on NAVIGATION_AUDIT.md |
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
| 2026-06-10 | **UX-03–UX-07 roadmap accepted with adjustment** (post-AT-LIGHT-01 sequencing). Order: (1) **HDR-01** combined header pass (UX-07 + UX-06) — mobile header only: company selector max width, ellipsis for long names, guaranteed spacing between selector/notifications/profile, review of duplicate company switching in Profile. Ownership: `mobile_header.css`; `theme.css` only for desktop and only if audit proves needed; no new header token conflicts; respect AUDIT-01's `--hdr-h` finding. (2) **UX-03** inline Add Expense Category — blocked until header pass complete. (3) **UX-04** selector interaction audit — Payment Method chips likely first; **date remains picker**; Post-Save State Retention · Repeat Last Transaction · Smart Defaults explicitly blocked/not started. (4) **UX-05** universal outside-tap dismiss — backlog/last; requires separate infrastructure audit and dedicated tests. |
| 2026-06-10 | **AT-LIGHT-01 status → code complete, pending final verification.** P1–P6 all implemented (hierarchy/chip grammar, keypad separation, amount card, panel tint, nav-safe spacing, phone/POS keypad order). Host `pytest tests/` — **787/787 passed**. Phone visual verification remains before sign-off. **HDR-01** is the next approved roadmap item after verification. **QUICK-ENTRY-02** deferred; subcategory workflow unchanged. |
| 2026-06-10 | **ADD-TXN-BR-01 closed.** Sale validation aligned with bookkeeping: Cash/Card no longer blocked by category/subcategory; Credit Sale requires named customer (`_at_sale_credit_customer_error`). Expense/Purchase validation unchanged. Manual AT verification + host `pytest tests/` — **800/800 passed**. |
| 2026-06-10 | **AT-LIGHT-01 closed.** P1–P6 complete including phone/POS keypad order (ITU E.161). Manual phone/POS visual verification signed off. Host `pytest tests/` — **800/800 passed**. **HDR-01** is next active item; pre-implementation audit recorded — implementation not started. |
| 2026-06-10 | **HDR-01 closed.** Combined mobile header pass (UX-07 + UX-06): responsive company selector, ellipsis for long names, toolbar cluster (bell + profile, 8px gap), unified spacing tokens, header ownership cleanup. Header company selector remains canonical switch entry point; Profile “Switch Company” opens the same `co_switch` sheet — no duplicate mobile company menu. CSS-only (`mobile_header.css` + `theme.css` mobile block reconciliation). Host `pytest tests/` — **807/807 passed**. **UX-03** is next active item. |
| 2026-06-10 | **UX-03 closed.** Inline Expense category creation in mobile `More…` picker: `_cat_create_or_reactivate` helper shared with desktop dialog; search-zero-match CTA (`txn.mob.add_category_cta`) gated on `manage_categories`; auto-select + last-used memory via `_mob_at_apply_category_pick`. Expense-only; Sale/Purchase/subcategory/AT panel layout unchanged. Host `pytest tests/` — **818/818 passed**. **UX-04** is next active item. |
| 2026-06-09 | **ERP Ownership Audit** complete (**AUDIT-01**). Critical conflicts identified: `--hdr-h` 4-way token split, `widgets.css` KPI catch-all, mobile ownership drift, sidebar triple-hide, notification active state duplication, reports internal duplicate. Architectural finding: Dashboard, Banking, and Mobile Reports are mostly clean; Company Picker and Desktop Reports have no CSS surface (future work). Five quick wins identified that can be executed before MOBILE-14. Decision: all future UI work must follow ownership-first planning; new features must not introduce additional ownership conflicts. |

---

## How to run tests

```bash
cd streamlit_accounting_erp
./venv/bin/python -m pytest tests/ -q
```

Expected: **818 passed**.

---

*Update this file when each phase completes.*
