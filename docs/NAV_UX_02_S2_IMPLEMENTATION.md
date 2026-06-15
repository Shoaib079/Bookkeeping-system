# NAV-UX-02-S2 — Today's Summary Route Retirement (Implemented)

**Status:** **Implemented** (NAV-UX-02-S2-IMPL). Approved decision D from `docs/NAV_UX_02_S2_TODAY_SUMMARY_PLAN.md`.

## What changed

| Item | Before | After |
|------|--------|-------|
| `_PAGE_DISPATCH` | Included `Today's Summary` → `render_today_summary` | **Removed** — 43 dispatch routes |
| `ALL_NAV_PAGE_KEYS` | Included `NAV_TODAY_SUMMARY` | **Removed** — constant retained for legacy detection |
| `LEGACY_NAV_ALIASES` | Emoji alias → `NAV_TODAY_SUMMARY` | **Repointed** → `NAV_REPORTS` |
| `main()` legacy handling | None for Today's Summary | `_LEGACY_NAV_TO_REPORTS_EXEC` presets `rpt_exec_sel="today_summary"` |
| `KNOWN_HIDDEN` (tests) | `{Today's Summary}` | **Empty** — no orphan dispatch routes |

## What did not change

- `render_today_summary()` — unchanged
- Reports → Accounting Tools → `rpt_exec_sel="today_summary"` — unchanged
- Sidebar, mobile nav, role gates — unchanged
- Accounting logic — unchanged

## Legacy bookmark behavior

Persisted `nav_selection` values `"Today's Summary"` or `"📅 Today's Summary"` now:

1. Set `nav_selection` → `Reports`
2. Set `rpt_exec_sel` → `today_summary`
3. Render `render_today_summary` inside Reports (same view as picker)

## Tests

```bash
pytest tests/test_nav_ux_02_s2_today_summary_retirement.py
pytest tests/test_nav_ux_02_s1_navigation_structural_contract.py
pytest tests/test_nav_ux_02_s1_purpose_validation.py
```

---

*S2 implemented — dead dispatch route retired; function and Reports exec picker preserved; legacy aliases graceful-reroute to Reports + today_summary preset.*
