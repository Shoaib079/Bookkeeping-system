# Audit History

Chronological record of read-only audits and accounting fixes for banking, reconciliation, and company credit card. Future sessions should **append** here rather than re-audit from scratch.

## Documentation maintenance (required)

After every completed feature, bug fix, accounting change, audit, migration, or major test addition — append a dated entry here and update the other project memory docs as needed. See [BANKING_RECON_CC_STATUS.md](./BANKING_RECON_CC_STATUS.md#documentation-maintenance-required).

---

## 2026-06-13 — USER-ACCESS-01 UA-P1 (Permission Override Service)

**Task:** Service-first effective permissions — `user_permission_overrides` model, registry/templates, override CRUD, owner lockout guard, `_can()` resolver swap. No permission management UI (UA-P1b deferred).

**UA-P1 delivered:**
- Model: `UserPermissionOverride` — unique `(company_id, user_id, permission_key)`
- Service: `services/user_access.py` — `PERMISSION_REGISTRY`, `PERMISSION_TEMPLATES`, `LEGACY_PERMISSION_MATRIX`, `effective_permissions`, `has_permission`, `set_override`, `clear_override`, `reset_to_template`, owner lockout guard, audit logging
- App: `_can(action)` signature unchanged; session cache; `_PERMISSIONS` re-export from service seed
- Tests: `test_user_access01_permissions.py` (23), `test_user_access01_models.py` (1)
- Docs: UA-P1 migration cleanup in `TECH_DEBT_AND_MIGRATION_CLEANUP.md` (TD-UA-*)

**Smoke audit (2026-06-13):**
- Owner/Manager/Viewer compatibility **passed**
- **0 permission regressions** (legacy matrix parity for owner/manager/cashier/partner)
- **0 hidden-page regressions** · **0 access regressions** on audit pages (Dashboard, Add Transaction, Banking, Reports, Partner Accounts, External Sales Verification, Recipe Costing)
- `manage_permissions` is an **intentional owner-only addition** (not a regression)

**Pending:** UA-P1b (permission UI) · UA-P2 (Staff Capture SC-P1).

**Tests:** Full suite **1502 passed, 2 xfailed**.

**Files changed:** `models.py`, `app.py`, `services/user_access.py`, `tests/test_user_access01_permissions.py`, `tests/test_user_access01_models.py`, `tests/test_daily_sales_close_ui_contract.py`, `tests/test_recipe_costing_ui_contract.py`, `docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md`.

---

## 2026-06-05 — RECIPE-COSTING-01 RC-P2A (Menu Profitability Basics)

**Task:** Menu item linkage to recipes, selling price history, and on-demand profitability (recipe cost · gross/net price · food cost % · markup · suggested price). No menu engineering matrix, sales volume, inventory, or posting.

**RC-P2A delivered:**
- Models: `MenuItem`, `MenuPriceHistory` (append-only gross price history)
- Service: `create_menu_item`, `update_menu_item`, `deactivate_menu_item`, `set_menu_price`, `get_current_menu_price`, `compute_menu_profitability`, `list_menu_profitability`
- DTOs: `MenuItemView`, `MenuPriceView`, `MenuProfitabilityView`
- UI: `render_recipe_menu_items` — Menu Items nav under Recipe Costing
- Locales: `rc.menu.*`, `nav.rc_menu_items` EN/TR
- Tests: `test_recipe_costing_menu_models.py` (3), `test_recipe_costing_menu_service.py` (15); UI contract extended (+0 count, menu assertions)

**Deferred (RC-P2B–P3):** Menu engineering matrix · Stars/Puzzles/Plowhorses/Dogs · sales volume analytics · dashboard charts · export · purchase integration · design spec.

**Unchanged:** Inventory · posting paths · automatic repricing · API endpoints.

**Tests:** Full suite **1465 passed, 2 xfailed**.

---

## 2026-06-05 — RECIPE-COSTING-01 RC-P1b (Recipe Costing UI)

**Task:** Daily-use Streamlit UI for recipe costing — Ingredients, Recipes (tree editor), Cost Breakdown. Service-only writes; no costing math in UI.

**RC-P1b delivered:**
- `ui/recipe_costing.py` — `render_recipe_ingredients`, `render_recipe_recipes`, `render_recipe_cost_breakdown`
- Recipe Costing nav accordion (Ingredients · Recipes · Cost Breakdown)
- Service read APIs: `list_ingredients`, `get_ingredient`, `update_ingredient`, `activate_ingredient`, `list_recipes`, `get_recipe`
- Permissions: `view_recipe_costing`, `manage_recipe_costing` (owner + manager)
- Locales: `rc.*`, `nav.rc_*`, `nav.group.recipe_costing` EN/TR
- Tests: `test_recipe_costing_ui_contract.py` (9); service read API tests (+3)

**Deferred (RC-P2B–P3 at time of P1b):** Advanced menu analytics · dashboard · charts · export · purchase integration · design spec — see RC-P2A entry for menu profitability basics.

**Unchanged:** Inventory · posting paths · menu modules · mobile-specific UI.

**Tests:** Full suite **1447 passed, 2 xfailed**.

---

## 2026-06-05 — RECIPE-COSTING-01 RC-P1 (Ingredient & Recipe Costing)

**Task:** Service-first recipe costing foundation — ingredients, recipes, sub-recipes via `RecipeLine.sub_recipe_id`, on-demand cost rollup. No inventory, menu, export, dashboard, or Streamlit UI in RC-P1.

**RC-P1 delivered:**
- Models: `Ingredient`, `Recipe`, `RecipeLine` (no `SubRecipe` table)
- `services/recipe_costing.py` — unit conversion (weight/volume/count), validation, `compute_recipe_cost`, `where_used`, ingredient/recipe CRUD mutations
- Schema indexes in `migrate_schema()`
- Tests: `test_recipe_costing_service.py` (29), `test_recipe_costing_models.py` (3)

**Deferred (RC-P1b–P3 at time of P1):** Streamlit UI · analytics · export — see RC-P1b entry for UI completion.

**Unchanged:** Inventory tables · product stock · `create_journal_entry` / posting paths · menu modules.

**Tests:** Full suite **1435 passed, 2 xfailed**.

---

## 2026-06-05 — DAILY-SALES-CLOSE-01 DSC-P1 + DSC-P2 (External Sales Verification)

**Task:** Source-neutral daily external-vs-ERP sales verification — service-first (P1), minimal Streamlit UI (P2). Verification only; no JE/GL/bank posting.

**DSC-P1 delivered:**
- `ExternalSalesVerification` model (`external_sales_verifications`)
- `services/daily_sales_close.py` — explicit `company_id`, serializable DTOs, no Streamlit
- Tests: `test_daily_sales_close_service.py`, `test_daily_sales_close_models.py`
- Schema indexes in `migrate_schema()`

**DSC-P2 delivered:**
- `ui/external_sales_verification.py` — verify + history tabs; calls service only
- Closings nav: `NAV_EXTERNAL_SALES_VERIFICATION`
- Permissions: `view_external_sales_verification`, `verify_external_sales`, `void_external_sales_verification` (owner + manager)
- Locales: `esv.*`, `nav.external_sales_verification` EN/TR
- Tests: `test_daily_sales_close_ui_contract.py` (9 contract tests)

**Deferred (DSC-P3–P4):** Attachments · EOD warning hook · export · per-provider import adapters.

**Unchanged:** `create_journal_entry` / posting paths · EOD close posting behavior · cash reconciliation.

**Tests:** Full suite **1403 passed, 2 xfailed**.

---

## 2026-06-05 — PARTNER-STATEMENT-01 P4 (all-partners settlement summary)

**Task:** Period-scoped all-partners settlement board so owners can review every partner’s opening position, activity, closing position, settlement status, outstanding advances, and warnings in one view.

**P4 deliverables:**
- `build_all_partners_settlement_summary()` — one `build_partner_statement()` call per partner; no parallel accounting math.
- `AllPartnersSettlementRow` / `Footer` / `Summary` dataclasses; net change uses P1 semantics (AdvanceOffset excluded from net change).
- UI: All Partners Settlement Summary section **above** single-partner P1–P3 panel on Partner Statement tab; shared period controls; KPI cards; filters (hide inactive / hide settled); “View statement” row action.
- Exports: Excel, CSV, PDF via `all_partners_settlement_to_export_df()` + `generate_all_partners_settlement_pdf()`; filename stem `all_partners_settlement_{from}_{to}`.
- Caption distinguishes P4 from Tab 4 Summary (period position vs point-in-time balances without advances netted).
- Locales: `partner.stmt.all_*` keys EN/TR.

**Unchanged:** `post_partner_movement`, `allocate_profit_to_partners`, JE logic, account structure, Balance Sheet, P1/P2/P3 formulas, profit allocation inclusion rule.

**Files:** `registry/partner_statement.py`, `registry/partner_statement_pdf.py`, `app.py`, `registry/locales/transactional.py`, `tests/test_partner_statement_p4.py`.

**Tests:** 27 new tests; full suite **1217 passed, 2 xfailed**.

---

## 2026-06-05 — BANKING-UX-02 completed (POS Settlement Transparency P1–P4)

**Status:** Complete — all phases shipped.

**Summary:**

- Focused POS / Card Settlement workflow (P1B entry + P1 preview on deposit clearing panel)
- Card Sales Clearing (1150) balance visibility (P2)
- Unsettled card sales drill-down list (P3)
- Match failure explanations before post (P4)

**Unchanged:** Revenue recognition · `post_deposit_clearing_match` posting logic · matching algorithms · Card Sales Clearing account **1150**.

**Key files:** `reconciliation/pos_settlement_preview.py`, `reconciliation/clearing_visibility.py`, `reconciliation/unsettled_card_sales_list.py`, `reconciliation/pos_match_failure.py`, `app.py`, `registry/locales/transactional.py`, `tests/test_banking_ux02_p1.py` through `p4.py`.

**Docs:** `ROADMAP.md`, `docs/TEST_COVERAGE_MAP.md`, `docs/COMPLETED_FEATURES.md`.

---

## 2026-06-05 — BANK-03 verification pass (Banking wording)

**Task:** Verify Banking navigation labels, section titles, and POS Settlement wording after BANKING-UX-02 + UI-STAB-02.

**Findings fixed:** Retired user-facing jargon (`card clearing sales`, `clearing sales`, generic `takas` labels) in import match copy EN/TR; aligned P2 visibility labels with **Card Sales Clearing** account name; Banking page title now uses `NAV_BANKING` for localized header; TR chip title aligned to **POS / Kart Mutabakatı**.

**Unchanged:** Posting logic · routes · account **1150** · internal session keys (`bsi_*`).

**Tests:** `tests/test_bank03_wording.py`; strengthened stale-wording patterns in `tests/test_banking_desktop_b1b2.py`.

---

## 2026-06-05 — UI-STAB-02 (Banking presentation separation)

**Task:** Stabilize Banking UI by separating presentation from business logic so future Banking work does not accidentally break layout, routing, or accounting behavior.

**Delivered:** `ui/banking.py` — `banking_section_select`, P1 preview, P2 clearing visibility, P3 unsettled sales list, P4 match failure panel, P1B route keys + entry + focused POS settlement section. `app.py` re-exports as `_render_*` / `_banking_*` aliases; orchestration and posting remain in `app.py` + `reconciliation/*`.

**Unchanged:** Posting logic · `post_deposit_clearing_match` · settlement math · journal entries · account **1150** · BANKING-UX-02 panel order and locale keys.

**Tests:** `tests/test_ui_stab02_banking.py`; existing `test_banking_ux02_*` and `test_banking_desktop_b1b2.py` updated for `ui/banking` source paths.

---

## 2026-06-05 — UI-STAB-01 (Shared avatar renderer)

**Task:** Stabilize initials avatars across header, mobile profile, My Account, and login tiles before PROFILE-PHOTO-01.

**Delivered:** `ui/avatar.py` (`user_initials`, `render_user_avatar`, sizes sm/md/lg); `.erp-user-avatar--*` in `ui/theme.css`; all call sites in `app.py` use shared helper; design contract tests in `tests/test_ui_stab01_avatar.py`.

**Unchanged:** Initials-only behavior; no `users.avatar_path`; no upload/storage; no auth or posting changes.

**Next:** PROFILE-PHOTO-01 can extend `render_user_avatar` with optional photo URL when implemented.

---

## 2026-06-05 — BANKING-UX-02 P1 (POS Settlement preview)

**Task:** Show settlement preview before posting POS settlement on Statement Import → Card Sale Deposit.

**Preview shows:** Card Sales Clearing balance, settlement amount, bank charges, expected bank deposit, remaining clearing; warnings for exceed/fee/negative/zero balance.

**Unchanged:** `post_deposit_clearing_match` JE (Dr Bank, Dr Bank Charges, Cr Clearing); sales revenue recognition; Sales Revenue in Advanced only.

**Files:** `reconciliation/pos_settlement_preview.py`, `app.py`, `registry/locales/transactional.py`, `tests/test_banking_ux02_p1.py`.

---

## 2026-06-05 — PARTNER-STATEMENT-01 P3 (PDF + print polish)

**Task:** PDF export and print-friendly Partner Statement presentation.

**P3 deliverables:**
- `partner_statement_pdf_payload()` + `generate_partner_statement_pdf()` (adapter on existing statement PDF patterns).
- PDF includes summary, status, warnings, and P2 detail lines; totals match screen/Excel.
- UI: `page_report_banner_html`, `financial_section_header_html`, `financial_statement_table_html` (no inline flex styles); print CSS hides filters/export.

**Unchanged:** posting, allocation posting, models, JEs, P1/P2 formulas.

**Files:** `exports.py`, `registry/partner_statement.py`, `app.py`, `ui/theme.css`, `registry/locales/transactional.py`, `tests/test_partner_statement_p3.py`.

---

## 2026-06-05 — PARTNER-STATEMENT-01 P2 (detail lines + Excel export)

**Task:** Detail-line support, running position, and export polish for Partner Statement.

**P2 deliverables:**
- `build_partner_statement_detail_lines()` — date, section, type, description, reference, inflow/outflow, net effect, running position.
- All movement types + profit/loss allocation lines (allocations still keyed to fiscal period `end_date`).
- UI expander “Show detail lines” below summary; Excel export via `partner_statement_to_export_df()` (`pdf=False`).

**Unchanged:** posting, allocation posting, models, JEs, Balance Sheet.

**Files:** `registry/partner_statement.py`, `app.py`, `registry/locales/transactional.py`, `tests/test_partner_statement_p2.py`.

---

## 2026-06-05 — PARTNER-STATEMENT-01 P1 (read-only Partner Statement)

**Task:** Monthly/quarterly/yearly/custom partner settlement review report.

**Location:** Partner Accounts page — new tab **Partner Statement** (tab 5 when partnership mode active).

**Formulas:**
- Position = Capital + Current − Advances (Equity Cr−Dr; Advances Dr−Cr).
- Profit/loss allocations included by **fiscal period `end_date`** in range; uses stored `PartnerProfitAllocationLine.amount`.
- AdvanceOffset shown under Settlements (zero net position effect).

**Warnings:** Outstanding advance; closed period without allocation; reconciliation mismatch (opening + activity ≠ closing within 0.01).

**Unchanged:** `post_partner_movement`, `allocate_profit_to_partners`, year-end close, models, JEs, account structure, Balance Sheet logic.

**Files:** `registry/partner_statement.py`, `app.py`, `registry/locales/transactional.py`, `tests/test_partner_statement_p1.py`, docs.

**Tests:** 20 new in `test_partner_statement_p1.py`; full suite **1044 passed, 2 xfailed**.

---

## 2026-06-11 — PARTNER-UX-01 i18n fix (Summary plain labels)

**Bug:** Partner Summary showed raw keys (`partner.summary_plain.capital`, etc.).

**Root cause:** Keys used dotted form `partner.summary_plain.*` inconsistent with catalog convention (`partner.summary_plain_adv_owes`); entries were only in `transactional.py` working tree, not duplicated in `messages.py` for MESSAGES fallback.

**Fix:** Renamed to `partner.summary_plain_capital|current|advances`; duplicated all six Summary keys in `messages.py` EN/TR; regression tests assert `t()` never returns raw keys.

---

## 2026-06-11 — PARTNER-UX-01 P1–P3 (Partner Accounts plain-language UX)

**Task:** Make Partner Accounts understandable for non-accountants without changing posting logic.

**P1:** Movement-type plain-language captions (EN/TR) on New Movement form.

**P2:** Outstanding advance from partner 15XX GL via `get_partner_advance_balance()`; warnings for no advance / exceeds outstanding on Repayment & AdvanceOffset.

**P3:** Summary tab plain-language labels (capital, current, advances) + direction captions for current account and advance owing.

**Unchanged:** `post_partner_movement`, JE lines, models, allocation, year-end close.

**Files:** `app.py`, `registry/locales/transactional.py`, `tests/test_partner_ux_p1p2p3.py`, docs.

---

## 2026-06-11 — BANKING-POS-WORKFLOW-01 P1+P2 (POS Settlement guardrails + explanation)

**Task:** UX guardrails for Other Income double-count risk; explain POS Settlement / Card Sale Deposit workflow.

**P1 — Guardrails:**
- Sales Revenue removed from main Other Income selectbox; moved to **Advanced / unusual** expander.
- Double-count warning when Sales Revenue selected; escalated POS warning when `card_deposit_style` matches.
- Posting not blocked (warning only).

**P2 — Explanation:**
- `st.info` explainer at top of Card Sale Deposit (`_render_bsi_deposit_clearing`).
- Banking Settings caption: **POS Settlement** = matching bank deposits to waiting card sales.

**Unchanged:** `post_generic_deposit`, `post_deposit_clearing_match`, matching math, models, GL names.

**Files:** `app.py`, `registry/locales/transactional.py`, `tests/test_banking_pos_workflow_p1p2.py`, docs.

---

## 2026-06-11 — BANKING-DESKTOP-01 B1+B2 (chip switchers + POS Settlement wording)

**Task:** Replace Banking desktop `st.radio` section switchers with chip grid; unify POS Settlement user-facing wording (BANK-03).

**B1 — Chip switchers:**
- Added `_banking_section_select()` — mirrors Reports chip grammar (`bank_sec_sel_*`, `erp-bank-sel-chip-host`).
- `render_banking`: Accounts / Import / Settings chips; state key `banking_section` unchanged.
- `render_bank_statement_import`: Upload / Review / Match / History chips; state key `bsi_section` unchanged.
- New `ui/banking.css` (chip grid layout); registered in `load_theme_css()`.

**B2 — Wording:**
- User-facing workflow labels → **POS Settlement** (EN) / **POS Mutabakatı** (TR).
- GL account name **Card Sales Clearing** retained in captions/help where referring to the 1150 account.

**Risks:** None for accounting/recon — UI-only. Staged import session keys (`bsi_file_bytes`, etc.) not touched by chip navigation.

**Files:** `app.py`, `ui/banking.css`, `ui/theme.py`, `registry/locales/transactional.py`, `registry/locales/messages.py`, `tests/test_banking_desktop_b1b2.py`, docs.

---

## 2026-06-11 — REPORTS-DESKTOP-02 (chips-only report selector)

**Task:** Remove redundant desktop report selectbox; chips canonical on desktop + mobile.

**Audit:** `erp_rpt_sel_desktop_*` only referenced in `_mgmt_report_select`, CSS hide rules, and R1 tests. Session state already keyed via chip clicks (`widget_key`). No accounting/chart dependencies.

**Removed:**
- `st.selectbox` + `erp_rpt_sel_desktop_*` container from `_mgmt_report_select`.
- Dual-host CSS: hide desktop select on mobile, hide chips on desktop.

**Kept:** Chip grid (`mob_rpt_sel_*`), routing via `st.session_state[widget_key]`, active styling in `widgets.css`.

**Chip layout:** Moved from `mobile_reports.css` @media block → `desktop_reports.css` (all viewports).

**Files:** `app.py`, `ui/desktop_reports.css`, `ui/mobile_reports.css`, `tests/test_desktop_reports_r1.py`, docs.

---

## 2026-06-11 — REPORTS-DESKTOP-01 R1 (desktop Reports CSS ownership)

**Task:** Create `ui/desktop_reports.css`; move desktop dual-host visibility rules out of `mobile_reports.css`.

**Moved to `desktop_reports.css`:**
- `@media (min-width: 969px)` — hide `st-key-mob_rpt_sel_*` (mobile chip selectors on desktop).

**Remains in `mobile_reports.css`:**
- `@media (max-width: 968px)` (+ touch arms) — hide `st-key-erp_rpt_sel_desktop_*`.
- `html.erp-mobile` — hide desktop selectbox (JS viewport fallback).
- All mobile chip layout, tabs, filters, CF KPI grids.

**Registered:** `load_theme_css()` via `_DESKTOP_REPORTS_CSS_PATH`.

**Files:** `ui/desktop_reports.css`, `ui/mobile_reports.css`, `ui/theme.py`, `tests/test_desktop_reports_r1.py`, docs.

---

## 2026-06-11 — DASHBOARD-01 D2 (class system + KPI variant-only)

**Task:** Structural cleanup — `render_dashboard()` first fully standardized desktop surface.

**Delivered:**
- Removed all inline `style=` from `render_dashboard()` (~35 replacements) → semantic `erp-dash-*` classes in `ui/theme.css`.
- Alert strip: `erp-dash-alert-card` (+ count/text/separator modifiers); no bare `.card` + inline `border-left`.
- Recent activity, insights, cash rows, status badges, expense bars — class-based layout.
- `render_kpi_grid`: removed `color=` / hex escape hatch; `variant` only (`muted` added for report secondary KPIs).
- Migrated 10 report `color: var(--theme-muted)` callers → `variant: "muted"`.

**Files:** `app.py`, `ui/theme.css`, `tests/test_dashboard01_d1.py`, docs.

---

## 2026-06-11 — DASHBOARD-01 D1 (flat welcome card + micro-text)

**Task:** Dashboard visible pass — replace legacy gradient welcome banner with flat card; bump dashboard micro-text from 10px to 11px.

**Delivered:**
- `render_dashboard` welcome: `banner banner-primary` → `erp-dash-welcome-card` (greeting, company overview, date, FY unchanged).
- `theme.css`: flat card uses `--theme-card`, `--theme-border`, `--theme-text`, `--theme-muted`, info left accent — no gradient.
- Micro-text: KPI `%` deltas, alert strip (already 11/12px), insight `_irow` captions, cash account lines, recent-activity meta — all `font-size:10px` → `11px` in `render_dashboard` only.
- D2 deferred: inline-style removal, KPI builder API, desktop quick actions unchanged.

**Files:** `app.py`, `ui/theme.css`, `tests/test_dashboard01_d1.py`, docs.

**Tests:** `test_dashboard01_d1.py` (5 contracts) + full `pytest tests/`.

---

## 2026-06-09 — MOB-AT-C1 Concept C minimal repair (HTML fix + picker overlay)

**Task:** Fix four bugs discovered from real phone screenshots after Concept C implementation.

**Root causes fixed:**
1. `_mob_at_render_c_cat_row` — HTML `<span>` passed as `st.button()` label. `st.button` escapes HTML by design; raw `<span style="...` appeared as literal text. Fixed by Option B: `st.markdown` dot column + plain-text `st.button`.
2. `_mob_at_render_txn_type_picker_sheet` — same HTML-in-button bug. Fixed by removing HTML from label, using `st.markdown` dot + plain-text label in 2-column layout.
3. Picker overlay — `_mob_at_render_amount_keypad_fragment` was rendered unconditionally inside `erp_mob_at_panel` even when a picker sheet was open. Picker floats above panel (position:fixed) but keypad was visible below/behind. Fixed by guarding with `if not st.session_state.get("mob_at_picker")`.
4. CSS for cat row / picker grid dot columns — `mob_at_c_cat_row` grid updated from `1fr` to `22px 1fr`; `.erp-mob-at-cat-dot` rule added; `mob_at_picker_grid` stHorizontalBlock updated to `22px 1fr` for each type row.

**Files changed:**
- `app.py` — `_mob_at_render_c_cat_row`, `_mob_at_render_txn_type_picker_sheet`, keypad guard at line ~12864
- `ui/mobile_txn.css` — cat row grid, picker grid row grid, `.erp-mob-at-cat-dot` styles

**Not changed:** Desktop, accounting/posting, Banking/Reports/More, CSS file structure.

**Tests:** Static contract checks (6/6 pass). Full `pytest tests/` must be run on host Mac (Python 3.13 venv required).

---

## 2026-06-05 — AD-UI-001 Pre-D2 navigation cleanup (SAFE TO REMOVE)

**Task:** Remove orphan nav renderers and dead mobile/i18n artifacts identified in Post-D1 Navigation Debt Verification.

**Removed from `app.py`:**

- `render_advanced()`, `render_customer_ledger()`, `render_settings()` (unreachable)
- `advanced_subpage` session usage
- `report_exec` mobile hub handler + visibility helpers
- Unused `close_more_on_nav` parameter on `_render_navigation_tree`
- Stale `_NAV_SECTIONS` comment

**Removed i18n:**

- `nav.group.daily`, `nav.group.crm` (messages.py)
- `reports.exec.pnl`, `reports.exec.balance_sheet`, `reports.exec.cash_flow` (transactional.py)

**Not touched:** `_PAGE_DISPATCH`, Financial Statements routes, D1 structure, legacy redirects (`_LEGACY_RPT_EXEC_TO_STATEMENT`, `_LEGACY_BSI`), accounting, banking, permissions.

**Docs:** `UI_SHELL.md`, `NAVIGATION_AUDIT.md`, `CLAUDE.md`.

---

## 2026-06-05 — AD-UI-001 Option D Phase D1 (Financial Statements navigation)

**Task:** Improve discoverability of P&L, Balance Sheet, and Cash Flow without changing report calculations, posting, or permissions.

**Changes:**

- Desktop: new **Financial Statements** accordion before Reports; thin page wrappers dispatch to existing renderers.
- Reports Executive picker: removed P&L / BS / CF; retains Budget, TB, GL, Transaction Ledger, Today's Summary.
- Mobile: Reports hub + More hub statement sections; shortcuts open dedicated routes.
- Legacy `rpt_exec_sel` (`pnl`, `balance_sheet`, `cash_flow`) redirects to new pages.
- Registry: `profit_loss`, `balance_sheet`, `cash_flow` modules; i18n keys EN/TR.
- Tests: `tests/test_nav_statements_d1.py`; `tests/test_mobile_nav.py` updated.

**Not touched:** accounting logic, report math, Banking, reconciliation, Executive rename, TB/GL dedup, Transaction History move.

**Docs:** [NAVIGATION_AUDIT.md](./NAVIGATION_AUDIT.md) §16, [UI_SHELL.md](../UI_SHELL.md), [ROADMAP.md](../ROADMAP.md).

---

## 2026-06-09 — AD-UI-001 Navigation Audit Phase 1 (read-only)

**Task:** Complete navigation and workflow audit after Banking Stabilization, UI Sweeps 1–3, and Legacy UI Cleanup. No code or navigation changes.

**Deliverables:** Full page inventory (31 sidebar/mobile routes + embedded reports), daily/weekly/monthly classifications, discoverability and duplicate-path analysis, nine workflow traces (sale → monthly reporting), financial reporting audit, mobile vs desktop parity, top 10 problems, IA options A–D evaluation, restaurant-owner preliminary recommendation.

**Key findings:**

- Balance Sheet / P&L / Cash Flow reachable only via `📊 Reports` → Executive tab → 8-way picker (not in Books sidebar).
- TB / GL / Budget duplicated in Books accordion and Reports Executive.
- Transaction History only via Reports → Transaction Ledger; `📅 Today's Summary` in dispatch but not sidebar.
- Orphan renderers: `render_advanced`, `render_customer_ledger`, `render_settings` (unreachable).
- Cashier/viewer lack Books sidebar but can open financial reports via Reports Executive.
- Mobile: Members has no hub path; operational pages often 3 taps via More.

**Docs updated:** [NAVIGATION_AUDIT.md](./NAVIGATION_AUDIT.md) (Phase 1 complete).

**Not touched:** accounting, banking, reconciliation, navigation code, workflows.

**Next:** Stakeholder selects IA option (A–D) before AD-UI-001 implementation.

---

## 2026-06-09 — Legacy UI cleanup Phase 3 (SAFE TO REMOVE)

**Task:** Remove orphan CSS classes and dead Streamlit key selectors from Legacy UI Audit Final Pass (36 items; zero runtime usage).

**Removed CSS classes (26):**

- `ui/theme.css` — `.app-body`, `.table-row`, `.muted`, `.erp-hdr-app-tag`, `.erp-hdr-co-primary`, `.erp-hdr-desktop-brand`, `.erp-hdr-divider`, `.erp-hdr-greeting-mobile`, `.erp-hdr-mark`, `.erp-hdr-meta`, `.erp-hdr-profile-trigger`, `.erp-hdr-role-pill`, `.erp-hdr-search-wrap`, `.erp-hdr-sep`, `.erp-hdr-toolbar-mark`, legacy header aliases (`.erp-hdr-brand`, `.erp-hdr-co`, `.erp-hdr-user-name`, `.erp-hdr-hide-sm`, `.erp-hdr-hide-md`), `.erp-hdr-mobile-page`
- `ui/widgets.css` — `.erp-mobile-chrome-footer`
- `ui/mobile_txn.css` — `.erp-mob-at-cat-section-title`
- `ui/mobile_shell.css` — `.erp-mob-bar-fab-col`
- `ui/mobile_txn_history.css` — `.erp-txh-pill--purple`, `.erp-section-header`

**Removed dead Streamlit key selectors (10):**

- `st-key-hdr_toolbar_mobile_left`, `st-key-hdr_toolbar_primary` (`widgets.css`)
- `st-key-hdr_desktop_tools`, `st-key-hdr_mobile_search_btn`, `st-key-hdr_mobile_tools` (`theme.css`, `mobile_shell.css`)
- `st-key-mob_at_cat_rows`, `st-key-mob_at_vendor_row`, `st-key-mob_rpt_date_` (`widgets.css`, `mobile_reports.css`)
- `st-key-mob_grp_btn`, `st-key-mob_nav_btn` (`widgets.css` desktop-hide rule)

**Tests/docs:** `test_header_identity_classes_present` now asserts active header classes; `UI_SHELL.md` amount-class and toolbar docs updated.

**Not touched:** accounting, banking, reconciliation, navigation, table rendering, mobile shell architecture, KPI system, or any ACTIVE / REFACTOR LATER items.

**Remaining SAFE TO REMOVE count:** 0 (audit list exhausted).

---

## 2026-06-09 — Legacy UI cleanup Phase 1 + Phase 2

**Task:** Remove dead UI artifacts identified in Legacy UI/Theme Audit (approved items only).

**Phase 1 — files removed (zero runtime references):**

- `app.py.bak`, `models.py.bak` (gitignored backups)
- `assets/mobile_at_calculator_before.png`, `assets/mobile_at_calculator_after.png` (dev screenshots)
- `scripts/browser_mobile_at_keypad.py`, `browser_mobile_fix.py`, `browser_mobile_search.py`, `browser_sidebar_pass.py` (Playwright smoke scripts; not imported by app)

**Phase 2 — unreachable CSS removed:**

- Glide / `stDataFrame` / `--gdg-*` rules in `ui/widgets.css`, `ui/theme.css`
- `_DARK_DATAFRAME_CSS` injection in `ui/theme.py`
- Orphan host markers `erp-bottom-nav-host`, `erp-mobile-top-nav-host` in `ui/widgets.css` (layout uses `st-key-erp_mob_bottom_bar` in `mobile_shell.css`)

**Tests:** `test_glide_dataframe_css_removed` replaces `_DARK_DATAFRAME_CSS` contract; `test_dark_mode_metric_and_alert_rules_in_widgets` updated.

**Not touched:** accounting, banking, reconciliation, navigation, readable table system, mobile txn history CSS, active theme helpers.

---

## 2026-06-09 — New Transaction selectbox focus-trap fix

**Task:** New Transaction — selecting Bank or Customer left UI stuck; refresh required.

**Root cause (combined):**

1. **CSS overlay** — Dropdown visibility fix set `z-index: 10050` on all `div[data-baseweb="popover"]` shells without `pointer-events: none`. Stale popover portals after a virtual-dropdown pick intercepted clicks (regression from 2026-06-09 dropdown visibility work).
2. **Dual host** — Mobile AT host always rendered (hidden via CSS on desktop), still running picker/bank-pay helpers that wrote `at_bank_pay_acct` before desktop `st.selectbox` instantiated.

**Actions taken (UI/session only):**

- `ui/widgets.css` — popover shell click-through; tooltip `pointer-events: none`.
- `ui/mobile_txn.css` — desktop hidden mobile host `pointer-events: none`.
- `app.py` — render mobile host only when `_erp_mobile_ui`; `_at_clear_stale_mobile_overlay_state()` on desktop; guard mobile bank-pay session write; shared `_mob_at_ensure_defaults()` before host branch.
- Tests: `test_selectbox_popover_click_through_css_contract`, `test_desktop_skips_mobile_at_host`, `TestNewTransactionTypeState` bank/customer/sync cases.

**Likely regression source:** Dropdown visibility CSS (popover z-index) + always-on mobile host (pre-existing, exposed by Streamlit 1.58 virtual dropdown).

**No accounting, workflow, navigation, or schema changes.**

---

## 2026-06-09 — Form controls light-mode visibility fix

**Task:** Banking Add Account/Transaction, Expenses attach/upload/Record Expense, Recon Closing Cash Count — black or poorly styled text in light mode.

**Root cause:** `st.form_submit_button()` uses `button[kind="secondaryFormSubmit"]` (not `secondary`). File uploader and number input use separate Streamlit 1.58 components not covered by existing `stButton` / `stTextInput` CSS.

**Actions taken (UI/CSS only):**

- Extended `ui/widgets.css` — `stFormSubmitButton`, `primaryFormSubmit`, file uploader dropzone/chips, number input container/steppers, progress bar track.
- `docs/UI_STYLE_GUIDE.md` — Form Controls and Widget Visibility Rules.
- Tests: `test_form_widget_visibility_css_contract`.

**No accounting, workflow, or form option changes.**

---

## 2026-06-09 — Selectbox / dropdown option visibility fix

**Task:** Banking → Add Account → Account Type (and app-wide `st.selectbox`) — selected value visible but dropdown option list hard to read.

**Root cause:** Streamlit 1.58+ `st.selectbox` uses `ul[data-testid="stSelectboxVirtualDropdown"]` (virtual list), not BaseWeb `div[data-baseweb="menu"] li`. Existing CSS only styled the latter; option text kept Streamlit inline theme colors (poor contrast in dark mode).

**Actions taken (UI/CSS only):**

- Expanded global dropdown rules in `ui/widgets.css` — virtual dropdown, BaseWeb `[role="option"]`, popover shell, disabled options, hover highlight.
- Sidebar closed select value text in `ui/theme.css`.
- `docs/UI_STYLE_GUIDE.md` — Dropdown and Selectbox Visibility Rules.
- Tests: `test_dropdown_visibility_css_contract` in `test_ui1_design_language.py`.

**No accounting, workflow, navigation, or form option changes.**

---

## 2026-06-09 — UI Mono Sweep 3 (colorful UI removal)

**Task:** Remove remaining pre-existing rainbow / per-module colors after Sweeps 1–2 — aging buckets, report KPI hex, P&L/Budget gradient banners, recon charts, opening-balance section accents, member role pills.

**Actions taken (UI/CSS only):**

- New helpers: `page_report_banner_html()`, `aging_buckets_html()`, `mono_role_pill_html()` in `ui/section.py`.
- `chart_series_color()` / `chart_reference_color()` in `ui/theme.py` for Altair charts.
- `.banner.banner-primary` / `.banner-info` → mono card + left info accent (no gradients).
- KPI value classes forced to `--theme-text` in all modes.
- AR/AP aging, member roles, advanced hub groups, OB/partner sections, dashboard expense bars converted to mono.
- `docs/UI_STYLE_GUIDE.md` — Mono Design Enforcement section.
- Tests: `test_mono_sweep3_*` in `test_ui1_design_language.py`.

**Intentional exceptions:** Semantic status pills (Paid/Open/Overdue); signed amount colors; header logo brand gradient; P&L income/expense section accent borders.

**Checkpoint base:** `7f32800`.

---

## 2026-06-09 — UI readability Sweep 2 (operational tables)

**Task:** Remaining weak spots — Reports management tabs, Banking ledger, Budget, COA summary, AR/AP lists, paginated tables, and other Glide `st.dataframe` clip points.

**Actions taken (UI only):**

- `readable_dataframe_table_html()` + `infer_column_kind()` in `ui/section.py`; `_render_readable_df()` in `app.py`.
- **All `st.dataframe` display calls removed from `app.py`** (~70 sites) → `_render_readable_df()`.
- Reports Sales/Expenses/Customers/Vendors/Banking/EOD management tables converted.
- Banking transaction history, statement import previews, Budget (status row tint), COA summary, Customers/Vendors/Purchases/Payables/Receivables export tables converted.
- `render_paginated_table()` page slice uses readable HTML; sort/page UI preserved.
- CSS: `.erp-fin-row-over|ok|warn` for status rows.
- `docs/UI_STYLE_GUIDE.md` — Operational Table Readability Rules.
- Tests: +3 in `test_phase16a_theme.py` (infer_column_kind, status rows, `_render_readable_df`).

**Intentional exceptions:** Charts (bar/line/Altair); interactive per-row AR/AP manage UI (not tabular).

**Related tests:** `pytest tests/test_phase16a_theme.py tests/test_ui1_design_language.py` — 35 passed.

---

## 2026-06-09 — Global UI readability fix (financial tables + tokens)

**Task:** Important information hard to see across app (light and dark) — clipped amounts, weak muted text, Glide dataframe contrast, financial statement rows.

**Root cause:** Phase 15+ reports used `st.dataframe` (Glide) for BS/P&L/TB/GL; Glide columns clip long account names and amounts. Muted labels used `--theme-muted` without a stronger caption token; some mobile KPI chips used `text-overflow: ellipsis`.

**Actions taken (UI/CSS only — no accounting logic):**

- New `--theme-caption` token (light/dark); captions, KPI labels, fin headers use it.
- `financial_statement_table_html()` + `financial_section_header_html()` in `ui/section.py`; `.erp-fin-*` CSS in `ui/theme.css`.
- Balance Sheet, P&L, Trial Balance, General Ledger, Chart of Accounts → themed fin tables (code, name, amount visible).
- Cash Flow activity rows → `.erp-fin-cf-row` layout.
- `widgets.css`: dataframe gridcell min-height, wrap, caption readability.
- Mobile KPI values: no ellipsis clipping (`theme.css`, `mobile_txn.css`).
- `docs/UI_STYLE_GUIDE.md` — “Global Readability and Financial Statement Rules”.
- Tests: `test_phase16a_theme.py` fin table + CSS class checks.

**Related tests:** `pytest tests/test_phase16a_theme.py`.

---

## 2026-06-09 — AD-UI-001 approved (sidebar / navigation redesign — future work)

**Audit / task:** User could not find Balance Sheet; read-only navigation investigation confirmed report exists under `📊 Reports` → Executive → Balance Sheet, not under Books. Discoverability and workflow efficiency prioritized over further accounting changes.

**Decision:** **AD-UI-001** — sidebar and navigation redesign **approved** for future work. **Priority: High.** **No implementation in this pass.**

**Prerequisite:** Complete [NAVIGATION_AUDIT.md](./NAVIGATION_AUDIT.md) (inventory, workflows, mobile parity, role gates, IA options) before any nav code changes.

**Known symptoms (pre-audit):** Financial statements (BS, P&L, CF) only under Reports → Executive; TB/GL also in Books accordion; legacy top-level statement items removed in Phase 15 hub consolidation.

**Docs:** `docs/NAVIGATION_AUDIT.md` created; `ROADMAP.md` updated with AD-UI-001 gate.

---

## 2026-06-09 — Opening Balance credit card fix (AD-015)

**Audit / task:** Opening Balances page posted DR Bank/Cash / CR OBE for all `BankAccount` rows, including `kind=credit_card` — wrong GL (treated liability as asset).

**Root cause:** `render_opening_balances` banking tab used one code path: deposit txn + Bank/Cash GL debit. Banking → Add account already had correct CC path (DR OBE / CR 2110) but logic was duplicated and OB page diverged.

**Actions taken:**

- `_post_opening_balance_bank_account()` — shared posting for bank vs credit_card; duplicate `OBBank` guard.
- Opening Balances UI: Kind column, CC labels/help, feature-disabled message, account picker with kind.
- Banking add-account refactored to same helper (balance via `apply_account_balance_delta` for CC).
- AD-015 in `ACCOUNTING_DECISIONS.md`.
- Tests: `tests/test_opening_balance_cc.py` (6 scenarios).

**Related tests:** banking bundle +6 (181 total with new file).

---

## 2026-06-09 — Card spacing / KPI grid layout polish (theme/CSS only)

**Task:** Metric cards too close vertically; overlap with tables/containers on Reports Sales and similar pages.

**Actions taken:**

- `.erp-kpi-section` wrapper on all `render_kpi_grid()` output; grid gap 16px, card min-height 76px, section margin 12px/20px.
- Bordered `st.container` padding/margin/gap; KPI-in-container spacing overrides.
- Main vertical block gap 0.875rem; dataframe/chart/export popover margins.
- Empty `kpi-sub` omitted to reduce card height jitter.

**Pages:** Dashboard, Reports (Sales/Expenses/all KPI tabs), Recon Health, Banking, EOD, Cash Reconciliation, AR detail, New Transaction summaries.

**Related tests:** `test_phase16a_theme.py`.

---

## 2026-06-09 — Targeted dark mode fix (remaining high-confidence UI)

**Task:** Fix Glide table contrast, remaining `st.metric` clipping, and hardcoded faint gray text — theme/CSS only.

**Actions taken:**

- `render_kpi_grid()` on Cash Reconciliation history, Banking statement match summary, AR invoice detail, EOD historical close.
- Recon Health Banking + COA Cache drift → `_render_theme_df_table()` (read-only; no sort/filter change elsewhere).
- Glide `--gdg-*` CSS vars in `widgets.css` + dark `inject_theme_css`; `[theme.dark]` dataframe colors in `.streamlit/config.toml`.
- Replaced `#9ca3af` with `var(--theme-muted)` / `.erp-filter-date-hdr` on Audit Log, Mobile TX History, P&L, Cash Flow footnotes.
- Multiselect tag styling for table filter chips.

**Related tests:** `test_phase16a_theme.py`, `test_ui1_design_language.py`, `test_cc_recon_health.py`.

---

## 2026-06-09 — Dark mode visibility & layout polish (theme/CSS only)

**Audit / task:** Full dark-mode visual audit — clipped Recon Health metrics, weak contrast on tables/cards/alerts, inconsistent section accents.

**Root causes:**

1. Recon Health used `st.columns(4)` + `st.metric` — Streamlit metric labels/values ellipsized in narrow columns (`TRY 5,0…`).
2. `.kpi-value` had `white-space: nowrap; text-overflow: ellipsis` — same clipping on dashboard KPI grids in dark mode.
3. Dark tokens (`--theme-muted`, `--theme-card`, `--theme-border`) were too close to page background — labels and card edges faded.
4. Glide `st.dataframe` headers ignored `th` CSS — light header flash on dark pages (CC card breakdown).
5. No `stMetric` / `stAlert` / `stVerticalBlockBorderWrapper` dark overrides in `widgets.css`.

**Actions taken (UI only — no accounting logic changed):**

- Recon Health AR/AP/CC: `render_kpi_grid()` + `_render_rh_metrics()`; CC breakdown → `theme_table_html()`.
- `ui/theme.py` / `theme.css`: brighter dark muted text, card, border tokens; KPI values wrap with `clamp()` font size.
- `ui/widgets.css`: `stMetric` (no ellipsis), bordered containers, mono alert cards, dataframe/table token headers.
- Dark mode refined to **mono** (no KPI metric tinting, no tinted alert backgrounds; status colors reserved for danger/void actions).
- `ui/section.py`: `theme_table_html()` helper; `.rh-section-hdr` single-accent subsection labels.
- `docs/UI_STYLE_GUIDE.md`: dark-mode manual regression checklist.

**Related tests:** `test_phase16a_theme.py`, `test_ui1_design_language.py` (existing theme contracts).

---

## 2026-06-09 — New Transaction type reset to Sales after CC expense submit

**Root cause:** `_render_add_transaction_mobile()` always called `_mob_at_sync_type_from_tab()`, which overwrote `at_type_idx` from stale `mob_at_tab` (default 0 = Sale) even on desktop. Desktop type buttons only set `at_type_idx`, not `mob_at_tab`. Submit then used corrupted `at_type_idx`; success `st.rerun()` also showed Sale. Flash messages did not survive rerun.

**Fix:** `_at_sync_desktop_type_to_mobile_tabs()` on desktop; `_mob_at_sync_type_from_tab()` no-op unless `_erp_mobile_ui`; persistent `_at_set_flash` / `_at_render_flash`; desktop type buttons sync mobile tabs.

**Tests:** +4 in `test_cc_expense_form.py` (type state + flash).

---

## 2026-06-09 — Company CC expense save fix (desktop New Transaction + Expenses)

**Audit / task:** Fix silent reset when saving Company Credit Card expenses from desktop New Transaction and Expenses page.

**Root cause:**

1. `ExpenseRecord` rows created without `company_id` — `_sync_company_cc_subledger` raised after GL posted, failing the save.
2. `_at_process_submit` always called `st.rerun()` after `_at_save`, even on failure — cleared validation/posting errors and reset the form.

**Actions taken (fixed, not hidden):**

- `_company_cc_charge_ready` — show Company CC only when toggle on, company context set, and at least one active `credit_card` account.
- `_save_and_post_expense_record` — shared save path sets `company_id`, resolves card id, posts GL 2110 + sub-ledger atomically, rolls back on failure.
- `_resolve_submit_company_cc_card_id` — auto-pick single card at submit time.
- `_at_process_submit` — rerun only when `_at_save_succeeded` flag set; errors remain visible.
- Expenses page uses same helper and resolved card id.

**Tests:** `tests/test_cc_expense_form.py` (9 scenarios); updated `test_company_cc_safety.py`.

**Related tests:** 171 passed in banking bundle (161 prior + 10 expense form).

---

## 2026-06-09 — AD-014 Void/unpost BankStmtCCBillPay (shipped)

**Audit / task:** Implement atomic void/unpost for posted credit card bill payments from bank statement reconciliation.

**Findings:** `post_credit_card_bill_payment` posted correctly (DR 2110 / CR Bank + dual sub-ledger) but had no safe undo. Direct `void_bank_transaction` on the bank leg left GL and CC sub-ledger broken.

**Actions taken:**

- `void_credit_card_bill_payment` in `reconciliation/company_card.py` — reverses JE, voids both `bsr:{row_id}` and `bsr:{row_id}:cc` transactions, restores balances, sets `row.status=voided`.
- `void_bank_transaction` blocks `statement_ref` starting with `bsr:`.
- Banking → Statement import → Review: unpost control for posted `cc_bill_payment` rows.
- AD-014 decision recorded.
- Tests: `tests/test_cc_bill_payment_void.py` (8 scenarios).

**Related tests:** 161 passed in banking bundle (153 prior + 8 void bill pay).

---

## 2026-06-09 — Credit Card Payable Recon Health (shipped)

**Audit / task:** Add read-only Recon Health section comparing GL 2110 to sum of active `credit_card` `BankAccount.balance` with per-card breakdown.

**Findings:** After AD-011, synced flows align; manual CC withdrawals without GL remain a drift source with no UI visibility.

**Actions taken:**

- `compute_cc_payable_recon_health` in `reconciliation/company_card.py`.
- Recon Health page section (gated by `banking.company_card_enabled`): GL, sub-ledger total, difference, OK/warning, card breakdown with last activity.
- AD-013 decision for tolerance and comparison rule.
- Tests: `tests/test_cc_recon_health.py` (7 scenarios).

**Related tests:** 153 passed in banking bundle (146 prior + 7 recon health).

---

## 2026-06-08 — AD-011 Company credit card sub-ledger sync (shipped)

**Audit / task:** Implement AD-011 — sync `credit_card` `BankAccount.balance` with GL 2110 on company CC charges (expense, purchase, payable payment).

**Findings:** Pre-AD-011, charges credited 2110 only; card sub-ledger drifted until bill pay.

**Actions taken:**

- Added `credit_card_account_id` on `ExpenseRecord`, `Purchase`, `Payable` + `migrate_schema` columns.
- `reconciliation/company_card.py`: `resolve_company_credit_card_account_id`, `post_cc_subledger_charge`, `reverse_cc_subledgers_for_gl_reference`.
- `app.py`: `_sync_company_cc_subledger`, void/edit symmetry, card pickers on Expenses/Purchases/Payables/New Transaction (desktop + mobile).
- AD-012 decision: linkage via FK + `ccc:{type}:{id}` statement_ref.
- Tests: `tests/test_cc_subledger_sync.py` (11 scenarios); updated CC regression tests for one-card auto-select.

**Related tests:** 146 passed in documented banking bundle (`test_cc_subledger_sync` + mvp1–5 + CC safety + CardPurchase + payable lifecycle + cash recon + EOD).

---

## 2026-06-07 — Decision Log Index added to ACCOUNTING_DECISIONS.md

**Audit / task:** Documentation-only — add Decision Log Index (AD-001 through AD-011) for fast reference without rereading full audits.

**Findings:** Accounting rules were documented in narrative sections only; no numbered decision IDs for cross-session citation.

**Actions taken:**

- Added **Decision Log Index** table and AD-reference rule near top of `docs/ACCOUNTING_DECISIONS.md`.
- Mapped AD-001–AD-011 to existing frozen rules, shipped fixes, deferred scope, and next approved task.

**Related tests:** N/A (documentation only; no code or test changes).

---

## 2026-06-07 — Documentation gate reinforced (retry)

**Audit / task:** Re-apply documentation update rule after prior session may not have loaded Cursor rule from repo root.

**Findings:** Cursor workspace root is `registry/`; rule at parent `.cursor/rules/` alone may not apply to all sessions.

**Actions taken:**

- Added `registry/.cursor/rules/erp-project-memory.mdc` (always-apply).
- Added documentation gate section to `CLAUDE.md`.
- Verified maintenance sections in all four `docs/` memory files.

**Related tests:** N/A (process only).

---

## 2026-06-05 — Project memory system & documentation gate (process)

**Audit / task:** Establish persistent ERP project memory (`docs/BANKING_RECON_CC_STATUS.md`, `AUDIT_HISTORY.md`, `ACCOUNTING_DECISIONS.md`, `TEST_COVERAGE_MAP.md`) and a rule that no task is complete until docs are updated.

**Findings:** Prior sessions repeated full roadmap/CC drift audits; knowledge was not centralized.

**Actions taken:**

- Created four `docs/` memory files (2026-06-05).
- Added `.cursor/rules/erp-project-memory.mdc` (always-apply documentation gate).
- Cross-linked maintenance rule in all memory docs.

**Related tests:** N/A (process only).

---

## 2026-06-05 — Roadmap vs actual code (read-only)

**Audit:** Compare `ROADMAP.md`, `PHASE_18_DESIGN_REVIEW.md`, registry, tests, and implementation for Banking / Reconciliation / Phase 18 / Company CC.

**Findings:**

- Phase 18 MVP-1 through MVP-5 marked ✅ in ROADMAP match shipped code in `reconciliation/` and `app.py`.
- Credit card **issuer statement import** documented in design but **not implemented** (deferred at MVP-2).
- `registry/modules_catalog.py` still lists `bank_statement_import` and `credit_cards` as `planned` while features live under **Banking** page.
- `ARCHITECTURE_HANDOFF.md` stale (pre–Phase 18, wrong test count).
- ROADMAP claimed 360 tests; suite had grown (434+ collected at time of audit).
- Legacy CSV bank import still exists when `banking.reconciliation_enabled` is OFF.

**Actions taken:** Documentation only (this memory system). No code changes.

**Related tests:** `test_phase18_mvp1`–`mvp5` (verify MVP claims).

---

## 2026-06-05 — Company credit card implementation review (read-only)

**Audit:** Whether ERP has full CC management vs basic 2110 payable accounting.

**Findings:**

- GL pattern works: DR Expense/Inventory, CR 2110 on charges; DR 2110, CR Bank on bill pay.
- Single GL 2110; multiple `BankAccount` (`kind=credit_card`) for UX only.
- No CC statement import, reports, limits, due dates, or dashboard widgets.
- Bill payment supports partial amounts and card picker; charges do not pick a card.

**Actions taken:** None (read-only).

**Related tests:** `test_phase18_mvp5.py`, `test_company_cc_safety.py`.

---

## 2026-06-05 — Company CC safety & mobile parity (implementation)

**Audit / task:** Gate company CC behind `banking.company_card_enabled`; block silent Cash/Bank fallback; desktop/mobile parity.

**Findings (before):** `_resolve_payment_credit_account` could mis-route; mobile/desktop payment lists inconsistent; `void_purchase`/`edit_purchase` used wrong ref type for Credit Card purchases.

**Actions taken:**

- `_business_pay_methods`, `_at_*_pay_methods`, `_validate_company_cc_payment`, `_coerce_at_payment_method`
- Fixed `_resolve_payment_credit_account` (only `"credit card"`, not `"Card"`)
- Mobile uses same helpers as desktop New Transaction
- Added `tests/test_company_cc_safety.py`

**Related tests:** `test_company_cc_safety.py` (10), `test_phase18_mvp5.py`.

---

## 2026-06-05 — CardPurchase void/edit accounting fix (implementation)

**Audit:** Credit Card purchases post `CardPurchase` JE; void/edit reversed `Purchase` instead.

**Actions taken:**

- `_purchase_ref_type()` helper
- `void_purchase` and `edit_purchase` use correct reference types
- Added `tests/test_card_purchase_void_edit.py`

**Related tests:** `test_card_purchase_void_edit.py` (8); regression: `test_phase18_mvp5.py`.

---

## 2026-06-05 — Purchase payable lifecycle on type change (implementation)

**Audit:** `edit_purchase` updated payable amount only; did not create/void payables when switching Credit ↔ Cash/Bank/Credit Card.

**Actions taken:**

- `_sync_purchase_payable_lifecycle`, `_create_purchase_payable`, `_void_purchase_linked_payable`, `_update_purchase_payable`
- `void_purchase` delegates to `_void_purchase_linked_payable`
- Added `tests/test_purchase_payable_lifecycle.py`

**Related tests:** `test_purchase_payable_lifecycle.py` (11).

---

## 2026-06-05 — GL 2110 vs credit_card sub-ledger drift (read-only)

**Audit:** Exact mechanics of 2110 updates vs `BankAccount.balance` for `kind=credit_card`.

**Findings:**

- **2110** updated via `create_journal_entry` on all CC charges and bill payments; truth = `calculate_account_balance()`.
- **Card balance** updated on bill pay, manual CC withdrawal, opening balance setup — **not** on expense/purchase/payable CC charges.
- No `credit_card_account_id` on `ExpenseRecord`, `Purchase`, or `Payable`.
- `at_card_bank_acct` is for **customer Card sales**, not company CC.
- Drift scenarios documented (charge then bill pay → negative card balance).

**Actions taken:** Identified **next approved task** (sub-ledger sync). No code changes.

**Related tests:** Gap documented in [TEST_COVERAGE_MAP.md](./TEST_COVERAGE_MAP.md) — drift tests not yet written.

---

## 2026-06-09 — Concept C Mobile AT UI (MOB-AT-C1) implementation

**Scope:** Mobile Add Transaction panel only. No accounting/posting changes. No schema changes. No desktop changes.

**Changes made:**

- `app.py`: Added `"at_picker_mode"` to `_COMPANY_SCOPED_AT_KEYS`. Added `at_picker_mode` default in `_mob_at_ensure_defaults()`. Added `_MOB_AT_C_TYPE_ROWS` constant and `_MOB_AT_C_TYPE_COLOUR` dict. Added new Concept C helpers: `_mob_at_c_current_type_key`, `_mob_at_c_type_label`, `_mob_at_c_apply_type`, `_mob_at_render_txn_type_picker_sheet`, `_mob_at_render_payment_picker_sheet`, `_mob_at_render_date_picker_sheet`, `_mob_at_render_currency_picker_sheet`, `_mob_at_c_row1_date_label`, `_mob_at_render_c_row1`, `_mob_at_render_c_cat_row`. Added new picker branches (`"txn_type"`, `"payment"`, `"date"`, `"currency"`) to `_mob_at_render_picker_sheet`. Rewrote AT panel section of `_render_add_transaction_mobile()`: removed 4-tab row, date row, More type radio, per-type PM chips, currency chips; added Concept C Row 1 + category row. Restructured `_mob_at_render_amount_keypad_fragment`: amount display is now full-width (no side column), Save is full-width button below amount, currency read from session state.
- `ui/mobile_txn.css`: Added CSS for `mob_at_row1` (4-col grid), `mob_at_c_cat_row` (full-width with dot alignment), `mob_at_save_row` (full-width primary Save), date picker confirm button.
- `docs/MOBILE_AT_CONCEPT_C.md`: Created — colour tokens, layout rules, implementation reference.
- `ROADMAP.md`: Added MOB-AT-C1 section + decision log entry.
- `tests/test_mobile_layout_contract.py`: Updated contract — removed `mob_at_tabs`, `mob_at_pm3`; added `mob_at_row1`, `mob_at_c_cat_row`, `mob_at_save_row`.
- `tests/test_mob_at_tab_labels.py`: Replaced old tab-button source check with Concept C Row 1 and `_MOB_AT_C_TYPE_ROWS` checks.

**Accounting unchanged:** `_at_save()`, all posting functions, journal entry logic, schema — untouched.

**Tests:** All static contract checks pass (verified via Python). Full `pytest tests/` must be run on host (requires Python 3.13 venv). Expected: 663+ passing.

---

## 2026-06-10 — QUICK-ENTRY-01 quick category chips — implementation verified

**Scope:** Mobile Add Transaction panel only. No accounting/posting changes. No schema changes. No desktop changes.

**Feature (as implemented):**

- `_mob_at_quick_chips(session, txn_type)` — pure helper; returns top 5 active categories alphabetically; if the currently selected category falls outside the top 5, it replaces the 5th slot so the selection is always visible.
- `_mob_at_render_quick_cat_chips(session, txn_type, picker_kind=...)` — renders wrapped chips + a `More…` chip that opens the existing category picker (`_mob_at_open_picker`); wired for Sale, Expense, and Purchase only.
- `_mob_at_seed_visible_category()` — visible preselection: last-used category per txn type (`mob_at_last_cat_sale` / `_expense` / `_purchase`), or auto-select when exactly one active category exists. Stale selections dropped via `_mob_at_coerce_visible_category()`.
- `_mob_at_apply_category_pick()` — single apply path shared by chips and picker; resets subcategory on every pick; records per-type last-category memory.
- Last-category keys added to `_COMPANY_SCOPED_AT_KEYS` — cleared on company switch.
- `ui/mobile_txn.css` — QUICK-ENTRY-01 chip block (wrap, no horizontal scroll; `--mob-at-chip-idle-*` tokens), placed in the AT-owned file per CSS-02 ownership rules.

**Audit (host run, 2026-06-10):** `pytest tests/test_quick_entry.py` — **14/14 passed** in 1.28s. Covers: top-5 alphabetical selection, selected-outside-top-5 retention, pure-helper guarantee, subcategory reset on pick, per-type last-category memory, seeding (last-used + single-category), company-scoped key registration + clearing, Sale/Expense/Purchase wiring, picker fallback intact (`_mob_at_render_c_cat_row` still available, `More…` opens existing picker), non-category txn types unchanged, CSS contract.

**Accounting unchanged:** `_at_save()`, all posting functions, journal entry logic, schema — untouched. The picker remains fully reachable; chips are a shortcut layer only.

**Related docs:** [TEST_COVERAGE_MAP.md](./TEST_COVERAGE_MAP.md) — `tests/test_quick_entry.py` section added. `ROADMAP.md` — QUICK-ENTRY-01 status moved to implemented.

---

## 2026-06-10 — UX-03–UX-07 UX audit + roadmap acceptance (no code changes)

**Scope:** Opinion/UX audit only — no implementation, no patches.

**Audited:** UX-03 (inline expense category creation), UX-04 (selector interaction), UX-05 (universal outside-tap dismiss), UX-06 (company switching duplication), UX-07 (header responsive behaviour).

**Key findings:**

- Desktop already has inline category creation (`_cat_add_dialog`: dedup, reactivation, permission-gated) — UX-03 is a mobile-only gap; create belongs inside the `More…` picker sheet.
- Header pill and profile sheet both render the same `_render_company_switch_menu()` — UX-06 duplication is UI-level only, logic is shared.
- `mobile_header.css` caps the company pill at fixed 220px but has no ellipsis rule or guaranteed toolbar gap — UX-07 risk is real on narrow devices with long names.
- Mobile surfaces are session-state driven with a CSS-only (non-clickable) scrim; outside-tap dismiss requires a scrim-button pattern and must land after MOBILE-14.

**Decision (recorded in ROADMAP decision log):** Roadmap accepted with adjustment. After AT-LIGHT-01 is fully approved: **HDR-01** (combined UX-07 + UX-06 header pass, mobile only) → **UX-03** → **UX-04** (PM chips likely first; date remains picker) → **UX-05** backlog/last pending its own infrastructure audit and tests.

**Code changes:** None. `ROADMAP.md` updated only (HDR-01/UX-03/UX-04/UX-05 sections, summary table rows, decision log entry).

---

## 2026-06-10 — AT-LIGHT-01 final polish (P1–P5) implemented

**Scope:** Mobile AT panel visual polish only. CSS-only — no app.py, accounting, posting, or schema changes.

**Changes (per approved priorities):**

- **P1 — chip grammar split:** `--mob-at-chip-idle-bg` → `var(--theme-card)` with info-mixed border (chips = white bordered pills); new `--mob-at-selector-bg/-border` tokens (info 12%/30% mixes) applied to Row 1 buttons and the category fallback row (selectors = tinted pills). Selected quick chip: new UI-1 rule in `widgets.css` — solid `var(--theme-info)` fill + white text, scoped to `mob_at_quick_cat_chips`/`mob_at_qc_*` only (the tinted generic active-chip treatment was invisible on the tinted panel). Specificity (0,6,1) ties the generic UI-1 rule; later cascade position wins.
- **P2 — keypad keys:** `--mob-at-key-bg` → `var(--theme-card)`; explicit 1px border + `--mob-at-key-shadow`; new `:active` pressed state (hover-bg fill, shadow removed).
- **P3 — amount card:** outer `mob_at_amount_row` container → transparent (wrapper band removed); inner border wrapper → card surface, 1px `--mob-at-surface-border`, 12px radius, surface shadow.
- **P4 — panel tint:** gradient strengthened 16%/6% → 22%/10% info mix. Light-mode direction preserved; all values theme-token-derived (dark mode unaffected structurally).
- **P5 — nav clearance:** panel bottom padding 10px → 16px (+safe-area); new keypad container `padding-bottom` rule at (0,3,1) beating the wrapper padding-strip at (0,3,0); `--mob-at-panel-h` 340px → 380px.

**Ownership:** All tokens remain in `mobile_txn.css` :root (CSS-01/E9). Chip colour grammar addition in `widgets.css` UI-1 block (MOBILE-14 E8 ruling). No changes to `mobile_reports.css`, `theme.css`, or token aliases pinned by contract (`--mob-at-chip-active-bg: var(--erp-chip-active-bg)` untouched).

**Verification (host, 2026-06-10):** `pytest tests/` — **800/800 passed**. Includes `test_ui1_design_language.py`, `test_mobile_layout_contract.py`, `test_quick_entry.py` (14/14), `test_at_sale_submit.py` (ADD-TXN-BR-01).

**Closure (2026-06-10):** Manual phone/POS visual verification signed off. **AT-LIGHT-01 → Closed.** P1–P6 complete (phone/POS keypad order verified on device). HDR-01 was next active item (now closed — see §2026-06-10 HDR-01 closed).

**Out of scope (intentionally untouched):** FAB glyph (bottom nav, not AT panel — not in approved priorities).

### AT-LIGHT-01 P6 — Mobile keypad ordering (approved addendum, 2026-06-10)

Keypad rows reordered from calculator layout (`7 8 9 / 4 5 6 / 1 2 3`) to phone/POS layout (`1 2 3 / 4 5 6 / 7 8 9`), matching ITU E.161 / ISO 9564 and the iOS/Android decimal pads. `. 0 ⌫` row unchanged. One tuple in `_mob_at_render_amount_keypad_fragment` (app.py) — no CSS, logic, or schema changes; button keys (`mob_at_key_*`) and container key unchanged, so no test impact (verified: no test pins digit order). Explicitly approved as P6 — not silent scope expansion.

**Roadmap status (2026-06-10):** AT-LIGHT-01 → **Closed**. HDR-01 → **Closed**. UX-03 next active item. QUICK-ENTRY-02 deferred; subcategory workflow unchanged. See `ROADMAP.md` decision log.

---

## 2026-06-10 — ADD-TXN-BR-01 Sale validation vs bookkeeping (closed)

**Trigger:** Sale Cash/Card blocked at Add Transaction by category/subcategory validation despite GL posting not requiring them (legacy `render_sales` never asked).

**Audit conclusion:** Category/subcategory on Sale are reporting metadata only — `post_cash_sale` / `post_card_sale` / `post_credit_sale` always credit **Sales Revenue**. Hard-blocking Sale on category was a validation/bookkeeping mismatch.

**Implemented rules:**

| Sale type | Required | Optional (no block) |
|-----------|----------|---------------------|
| Cash / Card | Amount, date, payment method | Category, subcategory, notes, currency, customer (walk-in default) |
| Credit | Above + **named customer** (not blank, not walk-in default) | Category, subcategory, notes, currency |

**Code:** `_at_process_submit` — Sale removed from category/subcategory gate; `_at_sale_credit_customer_error` for Credit; `_at_save` / posting unchanged. Expense and Purchase validation unchanged.

**Verification:** Manual AT sign-off (Cash/Card without category; Credit customer gate). `pytest tests/` — **800/800 passed** (`test_sale_cash_without_category_records`, `test_sale_card_without_category_records`, `test_sale_credit_requires_customer`).

**Status:** ✅ **Closed**

---

## 2026-06-10 — HDR-01 pre-implementation audit (no code changes)

**Status:** ✅ **Superseded by implementation closure** (see §2026-06-10 HDR-01 closed below). Audit findings were accurate; patch delivered per approved mockup.

**Scope:** Combined mobile header pass — **UX-07** (responsive company selector) + **UX-06** (duplicate company-switch surfaces). Mobile header only; desktop unchanged unless audit proves otherwise.

### UX-07 — Responsive company selector

| Item | Current state | Risk | Proposed fix |
|------|---------------|------|--------------|
| Pill max width | `mobile_header.css` L50: `max-width: min(100%, 220px)` | Long company names truncate abruptly or overflow on narrow phones | Replace fixed cap with responsive `clamp()`; add `overflow: hidden; text-overflow: ellipsis; white-space: nowrap` on `.erp-hdr-mobile-co` and Streamlit button inner text |
| Title column padding | `hdr_mobile_title` `padding: 0 76px` reserves space for toolbar | Fixed padding may not scale across 320–430px widths | Re-audit after ellipsis; tune padding vs `hdr_col_center` flex |
| Column layout | `hdr_shell_inner` columns `[2.8, 5.4, 2.8]` | Center column competes with absolute-positioned toolbar (`lc`/`rc`) | Verify bell + profile never overlap pill at min width |
| Single-company display | Non-switcher uses `st.markdown` pill (no button) | Ellipsis rules must apply to both button and static pill | Single CSS target for `.erp-hdr-co-pill` / `.erp-hdr-mobile-co` |

**Code anchors:** `app.py` `_render_app_header` (`hdr_mobile_co_switch_btn`, `hdr_mobile_title`); `ui/mobile_header.css` lines 39–69.

### UX-06 — Company switch duplication

| Surface | Behaviour today | Issue |
|---------|-----------------|-------|
| Header (multi-co) | `hdr_mobile_co_switch_btn` → `_mobile_open_surface("co_switch")` → `_render_mobile_co_switch_sheet` → `_render_company_switch_menu(key_prefix="mob_mco")` | Canonical path |
| Profile sheet | Full `_render_company_switch_menu()` inline when multi-company | Duplicate UI — same menu in two places |
| Confirm flow | `_render_company_switch_confirm` / `_confirm_company_switch` | Shared — keep unchanged |

**Proposed direction:** Header remains canonical switch surface. Profile replaces inline menu with one “Switch company” row that opens `co_switch` (same sheet). No change to company-switch logic, permissions, or accounting session scoping.

**Code anchors:** `app.py` `_render_mobile_profile_sheet` (`show_co_switch_link`, L950–958); `_render_mobile_co_switch_sheet` (L1017+).

### Ownership & constraints

- **Owner:** `ui/mobile_header.css` for mobile header layout changes.
- **Desktop:** `ui/theme.css` only if desktop header audit requires — not in initial scope.
- **Do not add** a fifth `--hdr-h` definition (AUDIT-01 / MOBILE-14 E1).
- **Non-goals:** Accounting, schema, posting, auth, notification logic.

### Test plan (required before HDR-01 close)

- Extend `tests/test_mobile_header_compact.py` — ellipsis CSS selectors, toolbar gap, no 220px-only cap (or documented replacement).
- Manual: 320px / 390px viewport; long company name; multi-company switch from header only after Profile dedup.
- Host `pytest tests/` green after implementation.

**Next step:** ~~Sign off this audit → implement HDR-01 per `ROADMAP.md` §HDR-01.~~ **Done** — closed 2026-06-10.

---

## 2026-06-10 — HDR-01 closed (UX-07 + UX-06)

**Status:** ✅ **Closed**

**Scope delivered:** Combined mobile header pass — responsive company selector, ellipsis, toolbar cluster, unified spacing, header ownership cleanup. CSS-first; no accounting/auth/notification logic changes; no company-switch logic rewrite.

### Completed

- Responsive company selector (token-based side reserve; fixed 220px cap removed)
- Ellipsis for long company names (multi-company Streamlit button `p` + single-company `.erp-hdr-mobile-co`)
- Toolbar cluster — bell + profile treated as one right-side group (32×32 controls, 8px gap)
- Unified spacing via layout tokens (`--hdr-toolbar-cluster-w: 72px`, `--hdr-toolbar-edge: 12px`, `--hdr-toolbar-gap: 8px`)
- Header ownership cleanup — `mobile_header.css` owns mobile header; `theme.css` mobile block reconciled for padding/gap conflicts only
- Company switch parity verified — header `hdr_mobile_co_switch_btn` is canonical entry point
- No duplicate mobile company switch menu — Profile `show_co_switch_link=True` opens the same `co_switch` sheet

### Decision (2026-06-10)

- Header company selector remains the canonical company switch entry point.
- Profile “Switch Company” remains available but opens the same `co_switch` sheet.
- No company-switch logic duplication.

### Tests

- `tests/test_mobile_header_compact.py` extended (7 HDR-01 contract tests)
- Host `pytest tests/` — **807/807 passed**

### Implementation notes

- `ui/mobile_header.css` remains owner of mobile header styling.
- `ui/mobile_shell.css` contains a fixed `84px` title reserve; it currently matches active token values (`--hdr-title-side-reserve` = 72px + 12px). Future header spacing changes should be audited before modifying the shell reserve.
- No new `--hdr-h` definitions. No `app.py` changes required.

**Files changed:** `ui/mobile_header.css`, `ui/theme.css` (mobile header block only), `tests/test_mobile_header_compact.py`.

**Next active roadmap item:** ~~**UX-03**~~ **UX-04** (UX-03 closed below). Post-Save State Retention · Repeat Last Transaction · Smart Defaults blocked on UX-04. **UX-05** backlog/last.

---

## 2026-06-10 — UX-03 closed (inline Expense category creation)

**Status:** ✅ **Closed**

**Scope delivered:** Expense-only inline category creation inside the mobile `More…` category picker sheet. No Sale/Purchase/subcategory/AT panel layout changes. QUICK-ENTRY-02 remains deferred.

### Completed

- `_cat_create_or_reactivate(session, txn_type, name)` — strip/normalize, case-insensitive dedup, company-scoped via `cq()`, reactivate inactive duplicate, create otherwise; preserves `_cat_add_dialog` validation semantics.
- `_cat_add_dialog` refactored to call the shared helper.
- Expense picker CTA (`expense_cat` only): non-empty search with zero matches → `+ Add "{name}"` when `_can("manage_categories")`.
- CTA tap: helper → `_mob_at_apply_category_pick(..., txn_type="Expense")` → close picker → rerun; last-used memory updated; quick-chip outside-top-5 promotion unchanged.
- Locale: `txn.mob.add_category_cta` (EN/TR).

### Tests

- `tests/test_ux03_inline_category.py` — 11 tests (helper create/dedup/reactivate/whitespace, CTA wiring, permission gate, Sale/Purchase exclusion, no AT panel controls).
- Host `pytest tests/` — **818/818 passed**

**Files changed:** `app.py`, `registry/locales/transactional.py`, `tests/test_ux03_inline_category.py`.

**Next active roadmap item:** **UX-04** — Selector Interaction Audit (Payment Method chips next).

---

## 2026-06-10 — UX-04A closed (post-save state retention)

**Status:** ✅ **Closed**

**Scope delivered:** Small post-save reset correction in Add Transaction (`_at_process_submit`). No `_at_save`, accounting, or `_COMPANY_SCOPED_AT_KEYS` changes.

### Completed

- `_AT_POST_SAVE_CLEAR_KEYS` + `_at_clear_post_save_transient_fields()` — centralized post-save reset.
- Removed `at_last_cat_id` from post-save clear list — desktop subcategory retained via `_inline_subcat_row` contract.
- Added post-save clears: `at_cust_sel`, `at_worker_gross`/`mob_at_worker_gross`, `at_worker_ded`/`mob_at_worker_ded`, `at_worker_adv_rec`/`mob_at_worker_adv_rec`.
- Retained after save: type, payment method, category, subcategory, vendor, date, currency, bank account, quick-entry memory.

### Tests

- `tests/test_ux04a_post_save_retention.py` — 8 tests.
- Host `pytest tests/` — **826/826 passed**

**Files changed:** `app.py`, `tests/test_ux04a_post_save_retention.py`.

**Next under UX-04:** ~~Payment Method chips~~ UX-04B closed below. Repeat Last · Smart Defaults remain.

---

## 2026-06-10 — UX-04B closed (mobile payment method chips)

**Status:** ✅ **Closed**

**Scope delivered:** Mobile Add Transaction only — replace payment-method bottom sheet with inline PM chip row. Desktop AT, accounting/posting, validation, date/currency pickers, category/subcategory, and Bank `mob_at_pm2` unchanged.

### Completed

- Row 1: **Type | Date | Currency** (3 buttons).
- `_mob_at_render_pm_chip_row` — uses `_at_sale_pay_methods`, `_at_expense_pay_methods`, `_at_purchase_pay_methods`.
- Chip tap: `at_pm` + `_at_clear_stale_payment_account_keys`; post-save retains active PM.
- Retired `"payment"` picker branch and `_mob_at_render_payment_picker_sheet`.
- Company CC chip when `_company_cc_charge_ready`; short label `txn.pm.company_cc_short`.
- CSS: `mob_at_pm_row` (`mobile_txn.css`) + selected-chip rule (`widgets.css`).

### Tests

- `tests/test_ux04b_payment_method_chips.py` — 14 tests.
- Host `pytest tests/` — **840/840 passed**

**Files changed:** `app.py`, `registry/locales/transactional.py`, `ui/mobile_txn.css`, `ui/widgets.css`, `tests/test_ux04b_payment_method_chips.py`, `tests/test_mobile_layout_contract.py`.

**UX-04 remainder:** ~~Smart Defaults~~ UX-04C closed below. Repeat Last Transaction — not started.

---

## 2026-06-10 — UX-04C closed (safe smart defaults)

**Status:** ✅ **Closed**

**Scope delivered:** Small smart-default layer in `app.py` only — per-type PM memory and single-bank auto-pick. No schema, persistence beyond session/company-scoped state, CSS, locale, or accounting/posting changes.

### Completed

- `_MOB_AT_LAST_PM_BY_TYPE` memory keys (`mob_at_last_pm_sale` / `expense` / `purchase`).
- `_mob_at_remember_last_pm` on PM chip tap; `_mob_at_recall_last_pm` in default chain.
- `_at_default_pay_method`: memory → `_AT_DEFAULT_PM` → first allowed; invalid memory falls back safely.
- `_coerce_at_payment_method` restores valid remembered PM on type switch (`_mob_at_coerce_pm_type`).
- Memory keys added to `_COMPANY_SCOPED_AT_KEYS` (cleared on company switch).
- `_at_apply_single_bank_auto_pick` — auto-select bank only when exactly one active account; zero or multiple → no inference.
- No inference for customer, vendor, worker, subcategory, amount, payable/invoice, or multi-bank/CC.

### Tests

- `tests/test_ux04c_smart_defaults.py` — 12 tests.
- Host `pytest tests/` — **852/852 passed**

**Files changed:** `app.py`, `tests/test_ux04c_smart_defaults.py`.

**UX-04 remainder:** ~~Repeat Last Transaction~~ closed below. UX-04 umbrella complete.

---

## 2026-06-10 — Repeat Last Transaction v1 closed (TXH row action)

**Status:** ✅ **Closed**

**Scope delivered:** Transaction History row action only — no post-save flash Repeat button. Expense (non-salary) and Purchase only. No schema, posting, or CSS changes.

### Completed

- Row action **Repeat** (🔁) visible for eligible non-void Expense/Purchase rows (`_txh_repeat_eligible`).
- `_txh_apply_repeat_prefill` — explicit allowlist copy; date → today; PM coercion; inactive category/vendor dropped.
- Navigates to Add Transaction; user must Save manually.
- Sale keeps legacy Duplicate; Expense/Purchase use Repeat in the third action slot.
- Locale: `txh.repeat_help` (EN/TR).

### Tests

- `tests/test_ux04_repeat_transaction.py` — 20 tests.
- Host `pytest tests/` — **872/872 passed**

**Files changed:** `app.py`, `registry/locales/transactional.py`, `tests/test_ux04_repeat_transaction.py`.

**UX-04 umbrella:** Complete (04A/B/C + Repeat v1).

---

## 2026-06-10 — DATE-01 closed (fast mobile date entry)

**Status:** ✅ **Closed**

**Scope delivered:** Mobile Add Transaction date sheet only — quick Today/Yesterday/Custom choices with weekday labels, `at_date_follows_today` rollover guard, backdated Row 1 indicator, closed-period courtesy check. Desktop date unchanged.

### Completed

- Sheet labels: Today · weekday+date, Yesterday · weekday+date, Custom date...
- `at_date_follows_today` in `_COMPANY_SCOPED_AT_KEYS`; rollover via `_mob_at_apply_date_follow_today`.
- Backdated marker CSS on Row 1 date pill when `at_date != today`.
- `_entry_date_posting_blocked` shared with `create_journal_entry`; courtesy caption on Yesterday/Custom confirm.
- Repeat Transaction sets `at_date_follows_today = True`.

### Tests

- `tests/test_date01_fast_mobile_date.py` — 15 tests.
- Host `pytest tests/` — **887/887 passed**

**Files changed:** `app.py`, `ui/mobile_txn.css`, `registry/locales/transactional.py`, `tests/test_date01_fast_mobile_date.py`.

---

## 2026-06-10 — UX-01 v1 closed (narrow session restore)

**Status:** ✅ **Closed**

**Scope delivered:** Safe login/session continuity after browser refresh — user identity + active company only. No AT, navigation, locale, or filter persistence.

### Completed

- HMAC-signed restore token in cookie `erp_session_restore` (8h TTL, constant-time compare).
- Payload: `user_id`, `iat`, `exp`, password-hash fragment, optional `active_company_id`.
- Company restored only via `_activate_company_in_session` (membership + active company DB checks).
- Invalid/revoked/deactivated company from token → company picker (no silent fallback).
- Cookie set/cleared via JS (`SameSite=Lax`, `Secure` on HTTPS) — **not HttpOnly** (JS-set limitation).
- Feature disabled when `ERP_SESSION_RESTORE_SECRET` unset; `DEV_MODE` untouched.

### Pre-production requirement

Set environment variable **`ERP_SESSION_RESTORE_SECRET`** to a long random secret (≥32 characters) before deploying. Without it, restore is disabled and users must log in after refresh.

### Tests

- `tests/test_ux01_session_restore.py` — 17 tests.
- Host `pytest tests/` — **904/904 passed**

**Files changed:** `app.py`, `tests/test_ux01_session_restore.py`.

---

## 2026-06-10 — MOBILE-14 re-baselined (M1–M6; documentation only)

**Status:** 🟡 **Re-baselined** — no CSS movement, no test file added yet.

**Decision:** Original MOBILE-14 E1–E13 consolidation plan is **superseded**. Prior UI work (HDR-01, AT-LIGHT-01, UI-1 chip grammar, E4–E6, E8a/b, E9, QUICK-ENTRY, UX-04B, etc.) already closed many E-steps. Remaining cleanup is smaller and focused on **ownership dedupe**, not layout migration.

### New scope (M1–M6)

| Step | Summary |
|------|---------|
| **M1** | `--hdr-h` dedupe within `theme.css`; mobile header dedupe within `mobile_header.css` — no new tokens |
| **M2** | Verify/remove dead `block-container padding-top` in `mobile_shell.css` (old E2) — only if proven dead |
| **M3** | Bottom-nav / FAB / hub remnants: `widgets.css` → `mobile_shell.css` |
| **M4** | Profile / co-switch sheet rules: `widgets.css` → `mobile_shell.css` |
| **M5** | KPI / dashboard rules: `widgets.css` → `theme.css` |
| **M6** | Re-audit notification liveness + sidebar triple-hide — delete only provably dead rules |

### Explicit non-goals

- AT picker z-index, AT-LIGHT wrapper-strip, `--mob-at-*` tokens, UI-1 chip grammar — **do not touch**.
- **Zero visible UI change** expected.

### Blocking (superseded 2026-06-10)

- ~~**LOGIN-01** and **UX-02** remain blocked until **M1 + M2** minimum complete.~~ → **Unblocked** after M1+M2 close; not started.
- **Current priority:** MOBILE-14 **M5** next (KPI move); M6 open; M3/M4 optional.

### Pre-implementation tests (planned, not yet added)

`tests/test_mobile14_ownership_contract.py` — header token contract, shell-only bottom-nav/FAB/hub, shell-only profile/co-switch sheets, no KPI in widgets, sidebar hide ownership, no `mob_at_`/`mob_rpt_`/`txh_` grids in widgets, notification liveness pin.

**Files changed:** `ROADMAP.md`, `docs/AUDIT_HISTORY.md`, `docs/TEST_COVERAGE_MAP.md`.

---

## 2026-06-10 — HDR-01 visual mockup review (no code changes)

**Deliverable:** Interactive mockup canvas — [hdr-01-mockup-review.canvas.tsx](/Users/shoaib/.cursor/projects/Users-shoaib-Documents-streamlit-accounting-erp-registry/canvases/hdr-01-mockup-review.canvas.tsx)

**UX-06 correction:** Mobile Profile already uses `show_co_switch_link=True` → `_mobile_open_surface("co_switch")`. No duplicate inline `_render_company_switch_menu()` on mobile. Implementation scope is primarily UX-07 CSS; UX-06 is verify + document (desktop popover inline menu remains out of scope).

**Proposed toolbar cluster:** Bell 32px + 8px gap + Profile 32px; center reserve 84px; company pill `max-width: calc(100% - reserve)` with ellipsis on button `p` and static `.erp-hdr-mobile-co`.

**Sign-off gates before patch:** 320px + 390px visual check; unify padding conflict (theme.css 84px vs mobile_header.css 76px); no new `--hdr-h` definitions.

---

## 2026-06-10 — MOBILE-14 Phase 1: ownership contract tests (no CSS movement)

**Scope:** Tests only. No CSS moved, no selectors moved, no app.py changes, no roadmap re-baseline.

**Done:** `tests/test_mobile14_ownership_contract.py` completed — all 7 required contracts (header token, bottom chrome, overlay sheets, KPI/dashboard, sidebar hide, widgets.css layout-grid ban, notification liveness pins). Added the two missing staged M1 dedup contracts (`--hdr-h` within-file duplication in theme.css / mobile_header.css) to match the staged M3–M6 pattern already in the file.

**Result (sandbox static run):** 8 pass (current ownership locked), 7 xfail (staged targets for M1/M3/M4/M5/M6 + txh_actions_ grid remnant), 0 unexpected failures. Host `pytest tests/` required for the official count.

**Rule encoded:** non-owner files may reference owned selectors for state suppression only; xfail contracts flip to plain passes in the same commit as their M-step.

---

## 2026-06-10 — MOBILE-14 M1 closed (header `--hdr-h` dedupe)

**Scope:** `ui/theme.css`, `ui/mobile_header.css` only. No app.py changes.

**Done:**
- Removed duplicate `--hdr-h: 120px` on `[data-testid="stAppViewContainer"]` in `theme.css` (redundant with `:root` in same `@media` block).
- Consolidated `mobile_header.css` to ≤2 `--hdr-h` definitions (base 56px + search variant); expanded `@media` gates to mirror `inject_mobile_viewport_detector()`; removed duplicate outside `html.erp-mobile` token block.
- Promoted `test_mobile14_hdr_h_theme_dedup` and `test_mobile14_hdr_h_mobile_header_dedup` from xfail → pass.

**Result:** Host `pytest tests/` — **914 passed, 5 xfailed**. Zero visible UI change.

**Files changed:** `ui/theme.css`, `ui/mobile_header.css`, `tests/test_mobile14_ownership_contract.py`.

---

## 2026-06-10 — MOBILE-14 M2 closed (verified no-op remaining)

**Scope:** `ui/mobile_shell.css` audit only.

**Finding:** The old E2 dead rule `padding-top: calc(var(--hdr-h) + 16px)` on `section[data-testid="stMain"] .block-container` was **already removed** from `mobile_shell.css` during the M1 session (prior E13 refactor). No further CSS deletion required.

**Evidence:**
- `mobile_shell.css` block-container rules set only `padding-left` + `padding-bottom` (bottom-nav clearance).
- M2 tombstone comments document that top inset is owned by `mobile_header.css` (`padding-top: calc(var(--hdr-h) + 10px)`).
- `load_theme_css()` injects `mobile_header.css` after `mobile_shell.css` — canonical mobile top inset wins in cascade.

**Done:** Added `test_mobile14_m2_mobile_shell_no_block_container_padding_top` contract test + tombstone comments.

**Result:** Host `pytest tests/` — **915 passed, 5 xfailed**.

**Files changed:** `ui/mobile_shell.css` (comments only), `tests/test_mobile14_ownership_contract.py`.

---

## 2026-06-10 — MOBILE-14 roadmap correction (documentation only)

**Decision:** Re-prioritize remaining M-steps after M1+M2 close. No CSS or app.py changes.

| Item | Disposition |
|------|-------------|
| **M1** | ✅ Closed — header `--hdr-h` dedupe; tests promoted |
| **M2** | ✅ Closed — verified no-op; padding-top already gone |
| **M3 / M4** | Downgraded to **optional low-priority** suppression-rule relocation. Ownership contracts already allow non-owner suppression references in `widgets.css`. Not blockers. |
| **M5** | **Next active CSS step** — real styling move: `.erp-kpi-section`, `.kpi-grid` from `widgets.css` → `theme.css`. Not started. |
| **M6** | Open — sidebar single-owner decision pending. Notification: `hdr_toolbar_row` rules in `widgets.css` are **live for legacy desktop**; do not delete blindly; document two-owner exception or permanent liveness contract. |
| **TXH xfail** | Relabeled independent micro-step — target owner `mobile_txn_history.css` (not `mobile_shell.css`) |
| **LOGIN-01 / UX-02** | **Unblocked** (M1+M2 done); not started |

**Files changed:** `ROADMAP.md`, `docs/AUDIT_HISTORY.md`, `docs/TEST_COVERAGE_MAP.md`.

---

## 2026-06-10 — MOBILE-14 M6 (sidebar half) implemented; notification half closed as two-owner exception

**Scope:** One CSS deletion + contract test promotion + ownership comments. No M3/M4/TXH work. No visual change intended.

**Sidebar:** Deleted the redundant sidebar-hide selector-list block from `theme.css`'s mobile `@media (max-width: 968px)` block (`stSidebar` + collapse-control selectors, `display:none/visibility/width/min-width` body, former lines ~802–811) — a strict-subset duplicate of `mobile_shell.css`'s hide (all CSS is concatenated by `load_theme_css()`, so shell's copy always applies). Surrounding rules untouched: `--hdr-h: 120px`, block-container padding, `stAppViewContainer` margin, desktop (≥969px) sidebar show rules. A tombstone comment marks the removal. `mobile_shell.css` is now sole owner (2 intentional rules: viewport media + `html.erp-mobile` fallback).

**Notifications:** No rules deleted. Liveness pin converted to a permanent two-owner contract (widgets.css = legacy desktop toolbar, confirmed live via app.py's `hdr_toolbar_row` slot; mobile_header.css = mobile slots). One-line ownership comments added at both rule sites referencing the contract test.

**Tests:** `test_mobile14_sidebar_hide_single_owner` xfail removed (now plain pass); baseline test rewritten as post-M6 lock (`theme: 0, shell: 2`); notification pin docstring rewritten as permanent contract. Contract file now 13 pass + 3 xfail (M3 optional, M4 optional, TXH micro-step). Static harness: 0 unexpected. **Host `pytest tests/` + manual visual check required:** mobile ≤968px sidebar hidden, desktop ≥969px sidebar normal, both notification bells work.

---

## 2026-06-10 — MOBILE-14 M5 closed (KPI ownership move)

**Scope:** `ui/widgets.css` → `ui/theme.css` only.

**Moved:** Four KPI/dashboard spacing rules (bordered-section `.erp-kpi-section` margins, `.kpi-grid` gap, markdown KPI container/paragraph resets). Declarations preserved exactly.

**Tests:** `test_mobile14_kpi_dashboard_not_in_widgets` promoted from xfail → pass.

**Result:** Host `pytest tests/` — **916 passed, 4 xfailed**. Zero visible UI change.

**Files changed:** `ui/theme.css`, `ui/widgets.css`, `tests/test_mobile14_ownership_contract.py`.

---

## 2026-06-10 — MOBILE-14 TXH micro-step closed

**Scope:** Remove duplicate `txh_actions_` grid from `widgets.css`. Canonical owner: `mobile_txn_history.css` (already contained full action-bar rules including grid + column + button chrome).

**Finding:** No new CSS needed in `mobile_txn_history.css` — E6 had already established ownership there. `widgets.css` carried a strict-subset duplicate inside a `@media` block (missing `padding: 0` on horizontal block and column border-right rules). `load_theme_css()` injects `mobile_txn_history.css` after `widgets.css`, so removal is a pure dedupe with no visual change.

**Removed from `widgets.css`:**
- `html.erp-mobile … [class*="st-key-txh_actions_"] [data-testid="stHorizontalBlock"]` grid block
- `html.erp-mobile … [class*="st-key-txh_actions_"] [data-testid="stColumn"]` flex-reset block

**Tests:** `test_mobile14_widgets_no_txh_layout_grids` promoted from xfail → pass.

**Result:** Host `pytest tests/` — **918 passed, 2 xfailed** (M3/M4 optional only). **MOBILE-14 ready to close.**

**Files changed:** `ui/widgets.css`, `ui/mobile_txn_history.css` (ownership comment), `tests/test_mobile14_ownership_contract.py`, `ROADMAP.md`, `docs/AUDIT_HISTORY.md`, `docs/TEST_COVERAGE_MAP.md`.

---

## 2026-06-05 — TXH-DETAIL-01 — Transaction detail JE / Edit History polish

**Scope:** Expanded Transaction History view panel readability only. No accounting, void/edit, invoice, or action changes.

**Before:** Journal Entries and Edit History rendered as 11px inline `style=` markdown (`Dr X / Cr Y` single line; red/green inline spans).

**After:** `_txh_render_view_je_block` + `_txh_render_view_edit_history_block` with semantic classes; JE account/Dr/Cr grid (12–13px, tabular nums); edit diffs via `--theme-danger-text` / `--theme-success-text`. Added `--theme-danger-text` token (THEME-CONTRAST-01 extension).

**Tests:** `tests/test_txh_detail01.py` (6 pass). Full suite **963 passed, 2 xfailed**.

**Files changed:** `app.py`, `ui/desktop_txn_history.css`, `ui/mobile_txn_history.css`, `ui/theme.css`, `ui/theme.py`, `tests/test_txh_detail01.py`, `tests/test_phase16a_theme.py`, `ROADMAP.md`, `docs/AUDIT_HISTORY.md`, `docs/TEST_COVERAGE_MAP.md`.

---

## 2026-06-05 — VIEWPORT-SYNC-01 — JS/CSS mobile threshold sync (replaces UX-02)

**Decision:** Align-up — restaurant counter tablets and large touch devices up to 1366px receive coherent POS/mobile UI.

**Problem:** JS detector tagged `html.erp-mobile` when `coarse && viewport <= 1366`, but CSS `@media` coarse arm stopped at 1024px — 1025–1366px touch tablets rendered mobile widgets without full mobile layout CSS.

**Fix:** Canonical `@media` header applied uniformly across six mobile CSS owners:
- `(max-width: 968px)`
- `((max-width: 1366px) and (hover: none) and (pointer: coarse))`
- `((max-height: 520px) and (hover: none) and (pointer: coarse))`

Constants pinned in `ui/theme.py` (`MOBILE_VIEWPORT_*`). `mobile_header.css` already had 1366; others updated from 1024.

**UX-02 status:** Original scope largely closed by HDR-01, MOBILE-14, UX-01; remaining gap reduced to VIEWPORT-SYNC-01.

**Tests:** `tests/test_viewport_sync01.py` (5 pass). Full suite **948 passed, 2 xfailed**.

**Caveat:** Fine-pointer laptops 1024–1200px stay desktop unless width ≤968.

**Files changed:** `ui/theme.py`, `ui/mobile_shell.css`, `ui/mobile_txn.css`, `ui/mobile_reports.css`, `ui/mobile_txn_history.css`, `ui/widgets.css`, `tests/test_viewport_sync01.py`, `ROADMAP.md`, `docs/AUDIT_HISTORY.md`, `docs/TEST_COVERAGE_MAP.md`.

---

## 2026-06-05 — THEME-CONTRAST-01 — Desktop/theme contrast (P0 + P1)

**Scope:** Token + CSS contrast fix only. No layout, auth UI, chip redesign, hover pass, or app/accounting logic changes.

**P0:** `--erp-primary-fill` / `--erp-primary-fill-hover` added; filled primary buttons in `widgets.css`, `mobile_shell.css`, `mobile_txn.css` use fill token. `--theme-info` preserved (`#3b82f6` dark) for links/tints.

**P1:** `--theme-success-text` / `--theme-warning-text` added for light-mode foreground text; applied in `theme.css`, `mobile_txn.css`, `mobile_txn_history.css`, `desktop_txn_history.css`.

**Contrast ratios (test report):** white on primary 5.17:1 (light+dark); text on card 17.85:1; muted on card 7.58:1; success-text on card 5.02:1; warning-text on card 5.02:1.

**Tests:** `tests/test_theme_contrast.py` (15 pass). Updated `tests/test_phase16a_theme.py` token list.

**Result:** Host `pytest tests/` — **943 passed, 2 xfailed**.

**Files changed:** `ui/theme.css`, `ui/theme.py`, `ui/widgets.css`, `ui/mobile_shell.css`, `ui/mobile_txn.css`, `ui/mobile_txn_history.css`, `ui/desktop_txn_history.css`, `tests/test_theme_contrast.py`, `tests/test_phase16a_theme.py`, `ROADMAP.md`, `docs/AUDIT_HISTORY.md`, `docs/TEST_COVERAGE_MAP.md`.

---

## 2026-06-05 — LOGIN-01 — Login / Company Picker UI modernization

**Scope:** Visual/UI only for `render_login` and `render_company_picker`. No auth logic, DEV-AUTH-01, UX-01 restore, password validation, permission logic, or company membership validation changes.

**CSS ownership:**
- Created `ui/auth.css` as sole owner for all `erp-auth-*` selectors.
- Registered in `load_theme_css()` (after `mobile_header.css`, before `mobile_txn.css`).
- Removed migrated `erp-auth-*` rules from `ui/mobile_header.css`.

**UI changes:**
- Replaced gradient banner + emoji with flat `erp-auth-header-card`.
- User tiles → avatar cards (`erp-mono-avatar`, name, role chip) + stable `select_user_{id}` keys.
- Password step → card layout; errors tinted inside card via CSS; no inline `style=`.
- Company picker → full-width tappable rows with chevron; quiet secondary create + text-style sign out.
- `_start_create_company_wizard(return_to="picker")` preserved on `picker_start_setup01`.

**Tests:** `tests/test_login01_auth_ui.py` (10 contracts). Updated `tests/test_mobile_header_compact.py` for auth.css loader order.

**Result:** Host `pytest tests/` — **928 passed, 2 xfailed** (M3/M4 optional only).

**Files changed:** `app.py`, `ui/auth.css`, `ui/theme.py`, `ui/mobile_header.css`, `tests/test_login01_auth_ui.py`, `tests/test_mobile_header_compact.py`, `ROADMAP.md`, `docs/AUDIT_HISTORY.md`, `docs/TEST_COVERAGE_MAP.md`.

---

## 2026-06-10 — Roadmap reconciliation (documentation only)

**Scope:** ROADMAP.md corrections from the full roadmap-vs-code reconciliation. No code, no tests, no CSS changed.

**Corrections applied:**

- **SETUP-01** → built and tested. Evidence: `registry/setup01_wizard.py`, `ui/setup01_wizard.py` (`render_setup01_wizard`), wizard CSS + locale strings, tests `setup01_wizard_b1/b2/b3`, `setup01_i18n`, `setup01_error_messages`, `setup01_entry_regression`. Removed from active list.
- **DEVELOPMENT_MODE** → resolved by DEV-AUTH-01: `DEV_MODE = os.getenv("ERP_DEV_MODE", "0") == "1"` (default off). Production checklist item retained: never run production with `ERP_DEV_MODE=1`.
- **AD-UI-001** → D1 + D2-P0 shipped (app.py promoted daily lookup route).
- **BANK-03** / **CHART-01** → marked "needs short verification pass" — BANK-03 wording live in SETUP-01 locales but Banking-page rename unverified; CHART-01 `chart_theme_tokens()` exists with 0 call sites and 0 native st.chart instances remain.
- **MOBILE-14** → confirmed closed: M1+M2+M5+M6+TXH micro-step done (TXH grid verified in `mobile_txn_history.css`, contract promoted); M3/M4 remain as optional backlog xfails. Host pytest 918 passed / 2 xfailed.
- **Next state** → LOGIN-01/UX-02 unblocked, not started; next recommended item is their modernization **audit** only.

---

## 2026-06-10 — PORTAL-THEME-01: portal surface theming fix

**Scope:** CSS + tests + docs only. No app.py, theme tokens, Streamlit config, auth, notification, picker, or dialog-behavior changes. Existing selectbox dropdown fix untouched (contract-pinned).

**Root cause (verified):** `stPopoverBody`, `stDialog`, and BaseWeb calendar popups render outside `[data-testid="stMain"]`; all stMain-scoped UI-1/theme rules miss them, so Streamlit's base theme (which follows the **OS** scheme, not the app preference) leaks in. Reproduced as near-invisible text whenever OS theme ≠ app theme (notification popovers desktop+mobile, profile/company popover selected row, st.dialog forms, date calendar).

**Fix:** New additive `PORTAL-THEME-01` section in `ui/widgets.css` (beside the existing popover/dropdown rules): popover-body + dialog text (markdown/captions/labels), dialog surface bg, dialog/popover inputs incl. placeholder + caret (closes the gap where input containers were themed but input text was stMain-scoped), secondary buttons (UI-1 grammar), primary buttons (`--erp-primary-fill`/`--erp-on-primary` + hover), and BaseWeb calendar (card bg, readable cells, selected day on primary fill). All rules unscoped, token-only, light/dark safe.

**Tests:** New `tests/test_portal_theme_contract.py` (7): per-surface rule presence, primary-fill grammar, calendar rules, **no-stMain-prefix regression guard**, no-literal-hex guard, selectbox-fix-untouched pin. Extended `tests/test_theme_contrast.py` (+2): portal text/caption on card and on-primary-on-fill pairs, both modes ≥ 4.5:1. Static harness: 23/23 across both files; mobile14/UI-1/layout contracts re-run clean (38 pass, 2 optional xfail). Host `pytest tests/` required for official count.

**Manual matrix (user):** OS-dark+app-light, OS-light+app-dark, both aligned × (notification popover, profile menu, Add Category dialog, date calendar).

---

## 2026-06-11 — LOGO-BUG-01: broken icon glyph rendering fixed

**Root cause:** Text-presentation-default Unicode emoji (Emoji_Presentation=No: 🗂 🗓 🏛 🕵 🗑 👁 ⚙ ⚠ ⚖ ✏ ☀ ⏸ ⏭ ⬇ 🗒) used **without** the VS16 variation selector (U+FE0F). Without VS16 the browser draws them from the text font stack, which lacks these glyphs on many desktop platforms → tofu squares. The codebase was inconsistent — "🏛️ Balance Sheet"/"🕵️ Audit Log" already carried VS16 and rendered; "🗂 General Ledger"/"🗓 Fiscal Periods" didn't and broke. Also: circled digits ①–⑦ (tab/step prefixes) and ⏻ (power symbol, sign-out) have no emoji form and poor desktop coverage.

**Fix (surgical, no redesign):** Appended VS16 to every bare fragile glyph in `app.py` (35 occurrences) and `registry/locales/transactional.py` (12); replaced ①–⑦ with plain "1."–"7." in app.py tab labels and locale strings (messages.py + transactional.py); replaced ⏻ → 🚪 in the sign-out button. Nav dispatch keys updated consistently via uniform transformation (same literal everywhere); unknown persisted `nav_selection` values fall back to Home by existing design (app.py:24741). Material Symbols deliberately **not** adopted: Streamlit's `icon=` param and label directives would change icon size/spacing (bug-fix constraint: same visual size/spacing) — VS16-forced emoji presentation meets the cross-platform requirement (macOS/Windows/iOS/Android OS emoji fonts) with zero layout change.

**Files changed:** `app.py`, `registry/locales/messages.py`, `registry/locales/transactional.py`, `tests/test_mobile_nav.py` + `tests/test_nav_accounting_tools_d2_p1.py` (literals updated to VS16 forms), new `tests/test_icon_glyph_contract.py`.

**Tests:** 3 new contracts — fragile-emoji-must-carry-VS16 (line-level violations reported), banned-glyph list (⏻, ①–⑦), nav-key consistency. All pass; all static contract suites re-run clean (45 pass, 2 optional xfail). Host `pytest tests/` + visual check required (sidebar Books group, Account Activity, Fiscal Periods, Owner Equity tab, TXH action buttons — on the desktop browser that showed squares).

---

## 2026-06-05 — ICON-SWEEP-01: remaining broken icon glyphs eliminated

**Root cause:** Same as LOGO-BUG-01 — text-presentation-default emoji without U+FE0F (VS16) rendered from the desktop text font stack (tofu squares). LOGO-BUG-01 fixed `app.py` literals but left **registry drift**: `modules_catalog.py` and `nav_labels.py` still used bare 🗂/🗓/📓/🔍/📒 keys that did not match `app.py` dispatch (🗂️/🗓️). TXH repeat used 🔁 (U+1F501), which lacks reliable coverage in compact Streamlit emoji-only buttons on some desktop browsers — the last broken square in the Transaction History action bar.

**Fix:** New `registry/icon_glyphs.py` — canonical `NAV_*` page keys and `TXH_*` action icons with `with_vs16()` helper. Wired through `app.py`, `modules_catalog.py`, `nav_labels.py`, and `registry/locales/transactional.py` (audit expander). TXH repeat → 🔄 (`TXH_REPEAT`). No layout/color/typography/spacing/logic changes; VS16-forced emoji only (Material Symbols/Lucide deliberately not adopted — would alter Streamlit button sizing).

**Icons replaced:**

| Location | Before | After |
|---|---|---|
| General Ledger nav (registry + dispatch) | 🗂 | 🗂️ |
| Fiscal Periods nav (registry + dispatch) | 🗓 | 🗓️ |
| Journal Entries nav | 📓 | 📓️ |
| Chart of Accounts nav | 🔍 | 🔍️ |
| Transaction Ledger nav | 📒 | 📒️ |
| Advanced audit expander (EN/TR) | 🔍 | 🔍️ |
| TXH repeat action button | 🔁 | 🔄 |

**Files changed:** `registry/icon_glyphs.py` (new), `registry/modules_catalog.py`, `registry/nav_labels.py`, `app.py`, `registry/locales/transactional.py`, `tests/test_icon_glyph_contract.py`, `tests/test_mobile_nav.py`, `tests/test_nav_accounting_tools_d2_p1.py`, `tests/test_nav_transaction_ledger_d2.py`, `docs/TEST_COVERAGE_MAP.md`, `docs/AUDIT_HISTORY.md`.

**Tests:** 969 passed, 2 xfailed (M3/M4 optional). Icon contracts expanded from 3 → 6 (fragile VS16 scan now includes registry files; `icon_glyphs`/`modules_catalog`/TXH wiring contracts added).

**Remaining icon debt:** Nav pages not yet centralized in `icon_glyphs` (e.g. 🏠 Home, 💼 Sales) — these use emoji-presentation-default codepoints and render reliably; migrate only if a future audit finds breakage. Comments/docs (`NAVIGATION_AUDIT.md`, `UI_SHELL.md`) still show legacy bare glyphs in prose — non-runtime, no user impact.

---

## 2026-06-05 — ICON-MODERNIZE-01: emoji nav/actions replaced with inline SVG system

**Root cause:** Emoji/VS16 was a mitigation, not a permanent fix — OS/browser font coverage still varies. `st.button` cannot safely embed SVG labels.

**Fix:** New `registry/icon_svg.py` (inline SVG, `currentColor`, no CDN/fonts) + `registry/nav_keys.py` (text-only routing keys + `LEGACY_NAV_ALIASES` for session migration). Sidebar/mobile Books nav renders SVG via `_nav_page_button()` (icon column + text button). TXH actions use ASCII labels `V/E/R/D/X` with existing `help=` tooltips. Partner tab locale strings stripped of emoji. Removed `registry/icon_glyphs.py`.

**Tests:** `tests/test_icon_svg_contract.py` (8); nav/i18n/registry tests updated. **971 passed**, 2 xfailed.

**Intentional emoji remainder:** Mobile bottom-bar chrome (🏠🏦📊), header toolbar (🔔⚙️), TXH row-type mobile card icons, dashboard quick-create — decorative/non-critical; Streamlit `st.tabs` cannot take SVG labels.

---

## 2026-06-11 — MOBILE-NAV-ICON-01: bottom nav emoji → SVG icons

**Scope:** Mobile bottom navigation only. No routing, accounting, desktop nav, hub, or notification changes. FAB untouched (plain "+" + existing blue circle styling).

**Mapping:** 🏠→`home` · 🏦→`landmark` · 📊→`bar-chart` · ☰→`menu` (all from `registry/icon_svg.py`, inline SVG, currentColor, no CDN/fonts). New `menu` path added to the registry (Lucide three-line).

**Mechanism:** Button labels swap the emoji first line for a zero-width space — the two-line button box (and therefore the touch target, 17px `::first-line` + 9px caption) is byte-identical. The SVG renders as a markdown element per tile, absolutely positioned over the blank first line with `pointer-events:none` (taps still hit the full button). Active tab: `:has(button[kind="primary"])` drives the icon to `--theme-info`, matching the label. All overlay CSS lives in `mobile_shell.css` (bottom-bar owner per MOBILE-14 contracts); icon idle color `--theme-muted`.

**Files:** `app.py` (`_MOBILE_BOTTOM_NAV` icon names, `_mob_bar_btn_label`, overlay render in `_render_mobile_bottom_nav`, `icon_svg` import), `registry/icon_svg.py` (+`menu`), `ui/mobile_shell.css` (overlay + active rules), new `tests/test_mobile_nav_icons.py`.

**Tests:** 5 new contracts (no emoji in nav definition, registry-backed icon names with render check, SVG-overlay-not-emoji in render fn + ZWSP touch-target guard, shell-owned CSS + active state, FAB-unchanged). 5/5 pass in sandbox harness; full static sweep 45 pass / 2 optional xfail / 0 unexpected. Host `pytest tests/` + phone visual check (light/dark × active/inactive tabs) required.

---

## 2026-06-11 — STATUS-TEXT-01 (Desktop Unification #1): raw status tokens off text

**Scope:** app.py markup + tests. UI only — no accounting, DB, or routing changes. Fill/tint usages (`color-mix` backgrounds, borders) deliberately keep raw tokens.

**Change:** 50 swaps in app.py — 12 inline `color:var(--theme-X)` → `color:var(--theme-X-text)` and 38 quoted colour-variable strings `"var(--theme-X)"` → `"var(--theme-X-text)"` (X ∈ success/danger/warning). Surfaces fixed: dashboard KPI deltas (▲/▼) and today-net, recon/EOD status lines, AR/AP overdue badges and warnings, partner balances, OB balanced/exceed states, recent-transaction amounts, payable/receivable status pill text, P&L net banners, year-end close banners. 26 raw lines remain — all fills/borders (verified non-text; the one `border-left: var(--theme-danger)` passes the 3:1 UI threshold at 4.83/6.17).

**Contrast (light, on card):** success 3.30 → **5.02** · warning 3.19 → **5.02** · danger 4.83 → **6.47** — all WCAG AA. Dark unchanged (dark `-text` tokens equal the already-passing raw values).

**Tests:** +2 in `test_theme_contrast.py` — raw-token-as-text ban (inline + quoted patterns; `-text` forms can't match) and light-mode AA pin for all three `-text` variants. Theme-contrast suite 18/18 in harness; full static sweep 50 pass / 2 optional xfail / 0 unexpected. Host `pytest tests/` + a light-mode dashboard glance to confirm the deltas/badges read clearly.

---

## 2026-06-11 — UI regression audit (pre-BANKING-UX-02 P4) + chart OS-theme fix

**Reported regressions, verdicts:**

1. **Charts white on dark theme — real, fixed.** Root cause: `_resolve_chart_dark` resolved theme "system" to session `dark_mode` (default False); the server can't see `prefers-color-scheme`, so charts rendered the light palette's hex on a dark UI. Not a commit revert — a CHART-01 gap made visible by the banking recon trend chart. **Fix (UI-only):** viewport detector now mirrors the OS scheme into an `erp_os_dark` cookie (same pattern as `erp_mobile_ui`, with a live change listener); `_resolve_chart_dark`'s system branch consumes it, session fallback retained for first render. Files: `ui/theme.py` only.
2. **Profile "picture/toggle → initials" — not a regression.** Photo upload was never implemented (locales say "Upload coming in a future release"; no setting, no asset path; repo history starts at the 2026-06-06 clean re-init). Likely remembered change: mono-sweep-3 flattening role-coloured avatars. Desktop theme toggle still renders. Logged as feature proposal **PROFILE-PHOTO-01**; the requested "picture mode" regression test is impossible without the feature.
3. **Other reverts — none found.** Dashboard 0 inline styles; nav SVGs intact; 173/173 banking locale keys resolve; partner-statement CSS scoped + print-fenced (no screen leak); POS focused-route covered by `test_banking_ux02_p1b`; 68 contract tests green.

**Tests added:** `tests/test_chart_os_theme_regression.py` (5): detector writes `erp_os_dark` + change listener; resolver consumes cookie before session fallback; dark chart palette never white + palettes differ; every `st.altair_chart` wrapped in `apply_altair_theme` + native-chart ban; banking locale-key completeness (raw-key guard).

**Verification:** new tests 5/5; full static sweep 68 pass / 2 optional xfail / 0 unexpected; theme.py syntax OK. Host `pytest tests/` + visual check (theme=system, OS dark → recon trend chart dark) required. Accounting logic untouched.

---

## 2026-06-11 — ADD-TXN date UX final: text-input-only (calendar expander removed)

**Follow-up to the entry below — user verdict: the collapsed calendar expander still read as a second date control.** Final state: desktop AT renders **exactly one date widget** — the typed text field (in-form, Enter submits; YYYY-MM-DD / DD.MM.YYYY / DD/MM/YYYY; invalid text blocks submit with the localized error). Calendar expander, `st.date_input`, `at_date_picker`/`at_picker_prev` keys, and the `txn.date_calendar*` locale keys all removed from the desktop AT path. `_at_resolve_entry_date` simplified: desktop = typed text wins, empty falls back to `at_date`; **mobile guard added** — on mobile UI both the resolver and `_at_entry_date_error` ignore desktop text entirely, so stale typed text can never override or block the mobile date sheet (which is unchanged). Tests rewritten in `test_add_txn_fix01.py` (single-control ban-list contract incl. expander/popover/date_input; 3-format parse-and-resolve; mobile-ignores-text; mobile-never-blocks; no-date_input-in-AT-path; checkbox-removed sweep; in-form Enter contract) and `test_date01_fast_mobile_date.py` (desktop = single text input). Logic verified 8/8 in sandbox; static sweep 74/2/0. Host run + visual check pending.

---

## 2026-06-11 — ADD-TXN date UX fix: single Date control, checkbox removed

**Problem:** the desktop AT date entry had grown a "txn.date_enter_manually" checkbox toggling between calendar and text modes — two controls + a mode switch for one date.

**Fix:** ONE visible Date control — a text input (accepts YYYY-MM-DD, DD.MM.YYYY, DD/MM/YYYY) rendered **inside** `at_entry_form` so typing a date + Enter submits the transaction, with a collapsed "🗓 Calendar" expander as the optional helper (expander-in-form is form-safe). Checkbox, mode flag (`at_date_manual_entry`), and both widget callbacks removed; locale key deleted EN/TR; new keys: `txn.date_help`, `txn.date_calendar`, `txn.date_calendar_hint`. Because forms forbid callbacks, calendar↔text reconciliation moved to submit time: `_at_resolve_entry_date` now uses **last-touched-wins** via an `at_picker_prev` shadow (calendar changed this submit → calendar wins and syncs the text; otherwise typed text wins; empty text falls back to resolved `at_date`). Invalid typed text still errors via `_at_entry_date_error` (mode gate removed) and still blocks submit (existing guard at the save path). DATE-01 rollover guard re-seeds stale "today" text. Mobile date sheet untouched.

**Tests:** `test_add_txn_fix01.py` date tests rewritten (8): parser formats; invalid-text error (ungated); typed-wins / calendar-touched-wins / empty-fallback / fresh-picker resolution; single-visible-control contract (no checkbox, 1 text + 1 date input inside expander, no callbacks); checkbox-fully-removed sweep (app + locales); date-field-inside-form (Enter-to-submit) contract. `test_date01_fast_mobile_date.py` desktop assertion updated. Resolution logic verified 4/4 in sandbox; static sweep 74 pass / 2 xfail / 0 unexpected. Host run required: `pytest tests/test_add_txn_fix01.py tests/test_date01_fast_mobile_date.py -ra` then full suite.

---

## How to use this file

1. Before a banking/CC task, read [BANKING_RECON_CC_STATUS.md](./BANKING_RECON_CC_STATUS.md) and the latest entry here.
2. After an audit or fix, append a dated section: audit name, findings, actions, tests.
3. Do not delete historical entries; strike through only if findings were superseded (note replacement date).
