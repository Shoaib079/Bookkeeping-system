# Audit History

Chronological record of read-only audits and accounting fixes for banking, reconciliation, and company credit card. Future sessions should **append** here rather than re-audit from scratch.

## Documentation maintenance (required)

After every completed feature, bug fix, accounting change, audit, migration, or major test addition — append a dated entry here and update the other project memory docs as needed. See [BANKING_RECON_CC_STATUS.md](./BANKING_RECON_CC_STATUS.md#documentation-maintenance-required).

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

## How to use this file

1. Before a banking/CC task, read [BANKING_RECON_CC_STATUS.md](./BANKING_RECON_CC_STATUS.md) and the latest entry here.
2. After an audit or fix, append a dated section: audit name, findings, actions, tests.
3. Do not delete historical entries; strike through only if findings were superseded (note replacement date).
