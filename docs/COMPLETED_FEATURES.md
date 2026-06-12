# Completed Features

Shipped capabilities with business outcomes. Append when a roadmap item reaches **Complete** status.

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
