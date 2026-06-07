# Banking, Reconciliation & Company Credit Card — Project Status

**Last updated:** 2026-06-09 (Opening Balance CC fix)  
**Purpose:** Persistent memory for Cursor sessions. Source of truth for what is built vs planned.  
**Companion docs:** [AUDIT_HISTORY.md](./AUDIT_HISTORY.md) · [ACCOUNTING_DECISIONS.md](./ACCOUNTING_DECISIONS.md) (Decision Log Index AD-001+) · [TEST_COVERAGE_MAP.md](./TEST_COVERAGE_MAP.md)

## Documentation maintenance (required)

After every completed feature, bug fix, accounting change, audit, migration, or major test addition:

1. Update **this file** if feature status changed.
2. Add an entry to **AUDIT_HISTORY.md**.
3. Update **ACCOUNTING_DECISIONS.md** if accounting behavior changed.
4. Update **TEST_COVERAGE_MAP.md** if tests were added or modified.

**No task is complete until documentation is updated.**

---

## Executive summary

Phase **18-MVP-1 through MVP-5** plus **AD-011 sub-ledger sync** are **shipped in code** with tests. The ERP has **company credit card payable accounting** at GL 2110 with **per-card sub-ledger sync** on charges plus **bank-statement bill payment** reconciliation. It does **not** have a full credit card management system (no issuer statement import, no dedicated CC reports).

**Highest open accounting risk (reduced):** Pooled **2110** vs sum of per-card balances when multiple cards exist and bill pay selects one card — charges now sync to the selected card sub-ledger (AD-011 shipped).

---

## NEXT APPROVED ACCOUNTING TASK

> **None mandated.** Optional follow-up: per-card activity report. Do **not** build credit card issuer statement import without new phase approval.

---

## Feature status matrix

| Feature | Status | Location / notes |
|---------|--------|------------------|
| Banking toggles (`banking.*`) | **Built** | `registry/settings_catalog.py`, Banking → Settings |
| Bank statement import (staging) | **Built** | `reconciliation/statement_import.py`, Banking → Statement import |
| Statement parsing (CSV/Excel) | **Built** | `reconciliation/statement_parse.py` |
| Bank reconciliation (match & post) | **Built** | `reconciliation/match_post.py`, per-line confirm |
| Card sales clearing (1150) | **Built** | Toggle `banking.card_settlement_enabled`; `post_card_sale` |
| Card sales settlement statement | **Built** | `reconciliation/settlement_import.py` |
| Bank charges / fees | **Built** | `post_bank_charge_outflow`, account 5800 |
| Credit Card Payable GL (2110) | **Built** | `registry/coa_seed.py`, `ensure_phase18_mvp5_accounts` |
| Company CC payment method (expense/purchase/payable) | **Built** | Gated by `banking.company_card_enabled` + `_company_cc_charge_ready` |
| Desktop CC expense save (New Transaction + Expenses) | **Built** | `_save_and_post_expense_record`; flash messages; type state preserved |
| Credit card bill payment (bank stmt) | **Built** | `post_credit_card_bill_payment` |
| `BankAccount.kind=credit_card` profiles | **Built** | Banking → Accounts; multiple allowed |
| Company CC mobile/desktop parity | **Built** | Shared `_at_*_pay_methods` helpers |
| CardPurchase void/edit GL | **Built** | `_purchase_ref_type`, `test_card_purchase_void_edit.py` |
| Purchase payable lifecycle on type change | **Built** | `_sync_purchase_payable_lifecycle` |
| Company CC safety (no silent fallback) | **Built** | `_resolve_payment_credit_account`, `test_company_cc_safety.py` |
| Credit card **issuer** statement import | **Not built** | Deferred since MVP-2; design in `PHASE_18_DESIGN_REVIEW.md` |
| Needs Review queue | **Not built** | Design only |
| Rule engine / fuzzy matching | **Not built** | Deferred post-MVP |
| Dedicated CC reports / dashboard | **Not built** | 2110 on Balance Sheet only |
| CC sub-ledger ↔ GL 2110 sync on charges | **Built** | AD-011: `post_cc_subledger_charge` on expense/purchase/payable payment |
| Per-card selection on CC charges | **Built** | Auto one card; picker when multiple; `credit_card_account_id` on records |
| CC Payable Recon Health (2110 vs cards) | **Built** | Recon Health page; AD-013; `compute_cc_payable_recon_health` |
| Void/unpost `BankStmtCCBillPay` | **Built** | AD-014: `void_credit_card_bill_payment`; Review UI |
| Opening Balances page for CC accounts | **Built** | AD-015: `_post_opening_balance_bank_account`; DR OBE / CR 2110 |
| Foreign currency (Phase 17) | **Not built** | FX fields exist; no conversion module |
| VAT (Phase 19) | **Not built** | `tax_rate` setting only |

---

## Built (do not rebuild)

| Component | Reuse |
|-----------|--------|
| `reconciliation/` package (statement, settlement, match_post, clearing, company_card) | Extend, do not replace |
| `BankStatementImport` / `BankStatementRow` | Bank import staging |
| `SettlementStatementImport` / `SettlementStatementRow` | Merchant settlement |
| `banking.*` settings + `company_card_enabled()` | All CC gating |
| `create_journal_entry` | All GL posting |
| `_resolve_payment_credit_account` | Company CC vs Cash/Bank |
| `_purchase_ref_type` + void/edit purchase | CardPurchase reference types |
| `_sync_purchase_payable_lifecycle` | Credit purchase payables |
| `_business_pay_methods` / `_at_*_pay_methods` | UI payment lists (desktop + mobile) |
| `post_credit_card_bill_payment` | Bill payment DR 2110 / CR Bank |
| `apply_account_balance_delta` / `reverse_account_balance_delta` | Card sub-ledger math |
| Phase 18 tests (mvp1–mvp5) + CC safety + CardPurchase + payable lifecycle | Regression suite |

---

## Partial (extend, do not replace)

| Area | Gap |
|------|-----|
| Company credit card | Charges sync GL + sub-ledger; Recon Health shows 2110 vs card sum + breakdown |
| Multi-card | Multiple `BankAccount` rows; single pooled 2110; explicit picker when >1 card |
| Bank reconciliation | Line-by-line match & post; no full-period recon report (18F) |
| Registry `modules_catalog` | `bank_statement_import` / `credit_cards` still marked `planned` though embedded in Banking |
| Recon Health | AR/AP/bank/COA cache + **CC Payable vs sub-ledger** (AD-013) |

---

## Not built (do not assume exists)

- `CreditCardStatementImport` / `CreditCardStatementRow` models
- Credit card statement CSV/Excel import pipeline
- CC activity report, aging, statement balance, limit, due date
- Per-card GL sub-accounts under 2110
- Automatic card suggestion / ML matching
- PDF/OCR statement import

---

## Open risks

| Risk | Severity | Notes |
|------|----------|-------|
| GL 2110 vs `credit_card` `BankAccount.balance` drift on charges | **Low** (was High) | AD-011 syncs charge paths; bill pay unchanged |
| Pooled 2110 vs multi-card sub-ledger totals | **Low** (was Medium) | Recon Health surfaces drift; AD-011 keeps attributed charges in sync |
| Manual CC withdrawal without GL | **Medium** | Sub-ledger only; UI warns user |
| Interest/fees → Bank Charges, not 2110 | **Medium** | Policy choice; may misstate card liability |
| Partial void of statement-linked txns | **Low** | AD-014 blocks `bsr:*` in `void_bank_transaction`; use Review unpost |
| Opening Balances page on CC accounts | **Low–Med** | Posts to Bank/Cash GL, not 2110 |
| Documentation drift (ROADMAP test count, ARCHITECTURE_HANDOFF) | **Low** | Use this doc + code for planning |

---

## Settings reference (all default OFF)

| Key | Effect |
|-----|--------|
| `banking.reconciliation_enabled` | Statement import + match & post workspace |
| `banking.company_card_enabled` | Company CC payment method + bill pay match kind |
| `banking.bank_charges_enabled` | Post bank fees to 5800 |
| `banking.card_settlement_enabled` | Card sales → 1150 clearing |
| `banking.card_sales_clearing_backfill` | `none` \| `reclassify_to_clearing` |
| `banking.transfer_fee_threshold` | UI hint for large transfers |

---

## Key code paths

| Flow | Functions |
|------|-----------|
| CC charge (GL + sub-ledger) | `post_expense`, `post_purchase`, `post_payable_payment` → 2110 + `post_cc_subledger_charge` |
| CC bill pay | `post_credit_card_bill_payment` → DR 2110, CR Bank + card sub-ledger deposit |
| Customer card sale | `post_card_sale` → `CardSale` (never 2110) |
| Sub-ledger | `apply_account_balance_delta` in `reconciliation/company_card.py` |

---

## Related documents

- `ROADMAP.md` — Phase 18 MVP checklist (mostly accurate; test count may lag)
- `PHASE_18_DESIGN_REVIEW.md` (parent folder) — Full 18A–18G blueprint; partially implemented
- `ARCHITECTURE_HANDOFF.md` — Stale for Phase 18; use this file instead for banking/CC
