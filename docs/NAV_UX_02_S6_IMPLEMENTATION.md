# NAV-UX-02-S6-IMPL-1 — Legacy nav telemetry

**Status:** Implemented (2026-06). **No alias/route deletion; no UI/role/render change.**

## Change

Added behavior-neutral `nav.legacy` logging at the five legacy substitution points in `main()`:

| kind | Trigger |
|------|---------|
| `reports_exec` | `_LEGACY_NAV_TO_REPORTS_EXEC` fires |
| `alias_normalize` | `normalize_nav_key` changes raw → canonical |
| `bank_statement_import` | `"Bank Statement Import"` section-preserving reroute |
| `rpt_exec_statement` | `_LEGACY_RPT_EXEC_TO_STATEMENT` fires |
| `rpt_exec_books` | `_LEGACY_RPT_EXEC_TO_BOOKS` fires |

Helper: `_log_legacy_nav_hit()` + `_NAV_LEGACY_LOGGER = logging.getLogger("nav.legacy")`.

## Invariants preserved

- All `LEGACY_NAV_ALIASES` targets ∈ `ALL_NAV_PAGE_KEYS`
- Reroute targets ∈ `_PAGE_DISPATCH`
- Today's Summary → `NAV_REPORTS` + `rpt_exec_sel="today_summary"`
- Bank Statement Import → `NAV_BANKING` + `banking_section="import"`
- Unknown disallowed nav → `NAV_HOME` (unchanged; not logged)
- `rpt_exec_sel` popped after statement/books reroute (idempotent)

## Tests

`tests/test_nav_ux_02_s6_legacy_reroute_structural_contract.py`

## Next slices (not implemented)

- **S6-IMPL-2:** bake-in review of `nav.legacy` hit counts
- **S6-IMPL-3:** telemetry-gated C-class retirement (zero-hit window)
