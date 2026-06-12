# Completed Features

Shipped capabilities with business outcomes. Append when a roadmap item reaches **Complete** status.

---

## PARTNER-STATEMENT-01 — Partner Settlement Statement

**Status:** Complete (June 2026)  
**Phases:** P1 Read-only statement · P2 Detail lines + Excel · P3 PDF + print · P4 All-partners settlement summary

### Business outcome

A partnership owner can:

- **Review** a single partner’s opening position, period activity, closing position, and settlement status (P1)
- **Drill into** detail lines with running position and export to Excel (P2)
- **Print or PDF** a polished partner statement (P3)
- **See all partners at once** in a period-scoped settlement board with KPI cards, filters, and consolidated export (P4)
- **Jump** from any P4 row to that partner’s full statement with one click

### Technical scope (read-only)

- P4 is a projection of P1 `build_partner_statement()` results — no parallel accounting math
- Position = Capital + Current − Advances; AdvanceOffset has zero net-position effect
- Profit/loss allocation included by fiscal period `end_date`; uses stored allocation amounts
- Tab 4 Summary remains separate (point-in-time balances without advances netted)
- No changes to `post_partner_movement`, `allocate_profit_to_partners`, or journal entry logic
- Tests: `tests/test_partner_statement_p1.py` · `p2` · `p3` · `p4` (64 tests total)

### References

- [ROADMAP.md](../ROADMAP.md) — PARTNER-STATEMENT-01 rows
- [TEST_COVERAGE_MAP.md](./TEST_COVERAGE_MAP.md) — partner statement coverage
- [AUDIT_HISTORY.md](./AUDIT_HISTORY.md) — P1–P4 entries

---

## BANKING-UX-02 — POS Settlement Transparency

**Status:** Complete (June 2026)  
**Phases:** P1 Settlement Preview · P1B Focused POS/Card Settlement entry · P2 Card Sales Clearing Visibility · P3 Unsettled Card Sales List · P4 Match Failure Explanation

### Business outcome

A restaurant owner can:

- **See** the Card Sales Clearing (1150) balance and how it relates to unsettled card sales
- **View** unsettled card sales in a filterable list before matching a deposit
- **Open** a focused POS / Card Settlement path on Banking without wading through full statement-import chrome
- **Preview** settlement amounts, fees, and expected bank deposit before posting
- **Understand** why a deposit cannot be matched (match check panel) in plain language
- **Reconcile** POS settlements with confidence — without changing how sales revenue or journal entries are recorded

### Technical scope (UX only)

- No changes to revenue recognition
- No changes to `post_deposit_clearing_match` or other posting logic
- Card Sales Clearing account **1150** retained
- Tests: `tests/test_banking_ux02_p1.py` · `p1b` · `p2` · `p3` · `p4`

### References

- [ROADMAP.md](../ROADMAP.md) — BANKING-UX-02 section
- [TEST_COVERAGE_MAP.md](./TEST_COVERAGE_MAP.md) — BANKING-UX-02 coverage
- [AUDIT_HISTORY.md](./AUDIT_HISTORY.md) — completion entry
