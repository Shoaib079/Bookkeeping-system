# Test Coverage Map — Banking, Reconciliation & Company CC

**Last updated:** 2026-06-09 (UI readability Sweep 2 + Opening Balance CC)  
**Full suite:** run `pytest tests/` (452+ tests total; count grows with new files).

This map covers the **minimum regression set** for banking/CC work. Run these before and after any change in those areas.

## Documentation maintenance (required)

When tests are added or modified, update **this file** (counts, gaps, risk levels) and follow the full checklist in [BANKING_RECON_CC_STATUS.md](./BANKING_RECON_CC_STATUS.md#documentation-maintenance-required).

---

## Quick command

```bash
pytest tests/test_phase18_mvp1.py tests/test_phase18_mvp2.py \
  tests/test_phase18_mvp3.py tests/test_phase18_mvp4.py tests/test_phase18_mvp5.py \
  tests/test_company_cc_safety.py tests/test_card_purchase_void_edit.py \
  tests/test_purchase_payable_lifecycle.py tests/test_cc_subledger_sync.py \
  tests/test_cc_recon_health.py tests/test_cc_bill_payment_void.py \
  tests/test_cc_expense_form.py tests/test_opening_balance_cc.py \
  tests/test_cash_reconciliation.py tests/test_end_of_day_close.py -q
```

**181 tests** in this bundle (as of 2026-06-09).

---

## Phase 18 MVP tests

### `tests/test_phase18_mvp1.py` (10 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `BankTransaction` schema (`is_reconciled`, `statement_ref`, `charge_subtype`) | Reconciliation provenance columns exist | **High** — match & post breaks |
| Banking toggles default OFF | Legacy behavior until opt-in | **High** |
| Phase 18 accounts 1150, 5800 seed | Clearing + Bank Charges exist | **High** |
| `post_card_sale` → Bank when settlement OFF | Default card sale path unchanged | **High** |
| `post_card_sale` → 1150 when settlement ON | Clearing architecture | **High** |
| Card sales reclassify backfill | One-time migration idempotent | **Medium** |
| Banking i18n EN/TR keys | Settings UI parity | **Low** |

---

### `tests/test_phase18_mvp2.py` (18 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `import_bank_statement_file` | Staging only — no GL on import | **High** |
| File hash / duplicate detection | Soft duplicate warning | **Medium** |
| Column mapping / parsing | CSV/Excel → `BankStatementRow` | **High** |
| Raw file storage + provenance | `raw_line_text`, upload path | **Medium** |
| Delete import | Cleanup staging data | **Medium** |
| Parse edge cases / i18n | Operator-facing errors | **Low** |

---

### `tests/test_phase18_mvp3.py` (4 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `post_deposit_clearing_match` | Card clearing deposit ties to sales | **High** |
| Amount mismatch raises | No unbalanced clearing match | **High** |
| `post_vendor_outflow` | Vendor payment / ad-hoc expense from stmt | **High** |
| `BankTransaction.statement_ref` | `bsr:{id}` provenance | **Medium** |

---

### `tests/test_phase18_mvp4.py` (14 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Inferred settlement fee → Bank Charges | Fee posting when confirmed | **High** |
| Fee requires `banking.bank_charges_enabled` | Toggle gating | **Medium** |
| Deposit label heuristics (gross/net) | Turkish bank description patterns | **Medium** |
| `looks_like_commission` / transfer fee / CC fee vs bill pay | Correct match kind routing | **High** |
| `post_bank_charge_outflow` | DR 5800 / CR Bank | **High** |
| Settlement CSV import | `SettlementStatementImport` staging | **High** |
| Settlement-linked clearing match | Gross/fee/net cross-check | **High** |

---

### `tests/test_phase18_mvp5.py` (7 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `apply_account_balance_delta` CC direction | Withdrawal increases CC liability cache | **Medium** |
| `post_expense` with CC → CR 2110 | Company CC expense GL | **High** |
| `post_payable_payment` with CC → CR 2110 | AP paid by card | **High** |
| `post_credit_card_bill_payment` | DR 2110 / CR Bank + sub-ledger | **High** |
| Bill pay requires company card toggle | Gating | **Medium** |
| Partner/owner statement matches | Extended match_post paths | **Medium** |

---

## Company credit card safety & purchases

### `tests/test_company_cc_safety.py` (10 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| CC hidden in pay method helpers when disabled | UI list = posting gate | **High** |
| CC visible when enabled | Feature toggle | **Medium** |
| Desktop/mobile share same AT helpers | Parity | **High** |
| `_resolve_payment_credit_account` blocks disabled CC | No silent post | **High** |
| Customer `"Card"` ≠ company CC in resolver | Card sale safety | **Critical** |
| `post_expense` blocks CC when disabled | Backend enforcement | **High** |
| `_coerce_at_payment_method` resets stale `at_pm` | Session hygiene | **Medium** |

---

### `tests/test_card_purchase_void_edit.py` (8 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| CC purchase void → GL net zero | `CardPurchase` reversal | **High** |
| CC purchase edit amount / type | Correct reverse + repost ref types | **High** |
| Cash purchase void unchanged | Regression | **Medium** |
| `CardSale` never uses `CardPurchase` | Customer vs company separation | **Critical** |

---

### `tests/test_purchase_payable_lifecycle.py` (11 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Credit edit amount → payable updated | AP sub-ledger sync | **High** |
| Credit → Cash/Bank/CC → payable voided | Open AP not orphaned | **High** |
| Cash/Bank/CC → Credit → payable created | AP created when owed | **High** |
| Void credit purchase → payable voided | AP cleanup | **High** |
| Paid payable blocks tier-2 edit | Data integrity | **Medium** |

---

## Core ERP (related operational closes)

### `tests/test_cash_reconciliation.py` (20 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Balanced cash count (no JE) | Physical = GL cash | **High** |
| Shortage / overage approval JEs | Cash Over/Short posting | **High** |
| Void creates reversal | Reversal pattern | **High** |
| Duplicate date/account prevention | One recon per day/account | **Medium** |
| Closed period block | Period lock | **High** |
| Role permissions (cashier/manager/owner) | Authorization | **Medium** |

*Not company CC — but part of daily banking/cash ops.*

---

### `tests/test_end_of_day_close.py` (33 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| EOD snapshot / warnings | Operational close record | **Medium** |
| Pending cash recon warning | Cross-module signal | **Medium** |
| Duplicate close prevention | One close per date | **Medium** |
| Void / reclose | Lifecycle | **Medium** |
| Stale detection after new JEs | Snapshot invalidation | **Medium** |
| **EOD posts no JEs** | GL integrity | **High** |
| Permissions | Role gates | **Low** |

---

### `tests/test_cc_subledger_sync.py` (11 tests) — AD-011

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| CC expense → 2110 + card balance + `BankTransaction` | Charge sync | **Critical** |
| CC purchase → 2110 + card balance | CardPurchase sub-ledger | **Critical** |
| CC payable payment → 2110 + card balance | AP paid by card sync | **Critical** |
| Bill pay after synced charge zeros GL + card | No negative card after pay | **High** |
| Multiple cards require explicit `credit_card_account_id` | No wrong-card attribution | **High** |
| No cards blocks posting | Clear error | **High** |
| Void CC expense / purchase reverses card | Void symmetry | **High** |
| Edit CC purchase amount re-syncs card | Edit symmetry | **High** |
| Customer `CardSale` regression | AD-003 separation | **Critical** |

---

### `tests/test_cc_recon_health.py` (7 tests) — AD-013

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `compute_cc_payable_recon_health` after synced expense/purchase/payable | No drift when AD-011 paths used | **High** |
| Bill pay after synced charge | GL + cards net zero | **High** |
| Manual CC withdrawal without GL | Drift warning surfaced | **High** |
| Multiple cards sum in health total | Multi-card aggregation | **Medium** |
| Customer `CardSale` regression | AD-003 isolation | **Critical** |

---

### `tests/test_cc_bill_payment_void.py` (8 tests) — AD-014

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `void_credit_card_bill_payment` full reversal | 2110, Bank GL, bank + card balances restored | **Critical** |
| Reversal JE for `BankStmtCCBillPay` | GL undo provenance | **High** |
| Both `bsr:{id}` and `bsr:{id}:cc` txns voided | No orphan sub-ledger | **Critical** |
| Double void blocked | `row.status=voided` guard | **High** |
| Wrong `match_type` rejected | Scope limited to cc bill pay | **Medium** |
| `void_bank_transaction` blocks `bsr:*` | No partial unsafe void | **Critical** |
| Wrong-card bill pay void | Restores selected card only | **High** |
| Partial bill payment void | Amount-accurate reversal | **High** |

---

### `tests/test_cc_expense_form.py` (13 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| `_company_cc_charge_ready` visibility gating | CC hidden when toggle off or no card | **High** |
| `_resolve_submit_company_cc_card_id` one-card auto-pick | Save without manual picker | **High** |
| Multi-card requires explicit selection | Clear validation error | **Medium** |
| `_save_and_post_expense_record` GL 2110 + sub-ledger | AD-011 charge path | **Critical** |
| Failed save rolls back, no orphan row | No silent failure | **Critical** |
| `_at_save_succeeded` flag on success only | No silent form reset | **Critical** |
| Desktop `at_type_idx` preserved vs `mob_at_tab` | No silent reset to Sale | **Critical** |
| `_at_set_flash` survives rerun | Success/error visible after submit | **High** |

---

### `tests/test_opening_balance_cc.py` (6 tests)

| Feature covered | Business rule protected | Risk if untested |
|-----------------|-------------------------|------------------|
| Bank OB DR Bank / CR OBE | Normal asset opening unchanged | **High** |
| CC OB DR OBE / CR 2110 | Liability opening (AD-015) | **Critical** |
| CC `withdrawal` txn + balance cache | Sub-ledger matches GL | **Critical** |
| Recon Health clean after CC OB | 2110 vs card total | **High** |
| Duplicate `OBBank` blocked | No double post | **High** |
| CC OB blocked when feature OFF | Gating | **Medium** |
| CardSale does not credit 2110 | AD-003 separation | **High** |

---

## UI / theme regression (run after CSS or table helper changes)

```bash
pytest tests/test_phase16a_theme.py tests/test_ui1_design_language.py -q
```

**36 tests** (as of 2026-06-09) — includes financial table classes, `readable_dataframe_table_html`, `infer_column_kind`, `_render_readable_df`, no-`st.dataframe` policy grep, dark-mode widget rules.

| Area | Protected |
|------|-----------|
| `.erp-fin-table` / code-name-amount | Financial + operational readable tables |
| `readable_dataframe_table_html` status rows | Budget over/on-track tint |
| No `st.dataframe` in app display path | Sweep 2 policy (grep audit in tests) |

---

## Coverage gaps (known — tests NOT yet written)

| Gap | Risk | When to add |
|-----|------|-------------|
| Partial payable CC payments (multiple sub-ledger rows per payable) | **Low** | If partial CC payments become common |

---

## Risk level legend

| Level | Meaning |
|-------|---------|
| **Critical** | Wrong GL account or customer/company CC confusion |
| **High** | Material misstatement or broken posting path |
| **Medium** | Wrong sub-ledger, gating, or workflow inconsistency |
| **Low** | i18n, permissions edge, UI-only |
