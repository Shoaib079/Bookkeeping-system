# MONO-THEME-02 — Implementation Audit

**Updated:** 2026-06-05 (crash recovery)  
**Contract:** [MONO_THEME_02_VISUAL_CONTRACT.md](./MONO_THEME_02_VISUAL_CONTRACT.md)

## Current slice status

| Slice | Git state | Tag | Notes |
|-------|-----------|-----|-------|
| **S0** | ✅ Committed `ebdfe42` | `mono-theme-02-s0-visual-contract` | Audit only — frozen |
| **S1** | ✅ Committed (this slice) | `mono-theme-02-s1-sidebar-refinement` | Sidebar-only `ui/theme.css` |
| **S2** | ✅ Committed (this slice) | `mono-theme-02-s2-topbar-refinement` | Desktop hdr_shell only |
| **S3** | ✅ Committed `0e3ec99` | `mono-theme-02-s3-dashboard-refinement` | Desktop dashboard `.erp-dash-*`, `.kpi-*`, widgets bordered panels |
| **S4** | ✅ Committed `cb5e1a1` | `mono-theme-02-s4-table-refinement` | Desktop `.erp-fin-table`, `.erp-data-table`, `widgets.css` stTable |
| **S5** | ✅ Committed (this slice) | `mono-theme-02-s5-mobile-parity` | widgets mob_bar fix, mobile KPI/table parity, hub sheet radius |

## Dirty changes audit (pre-S1 commit)

| File | Scope | Safe for S1? |
|------|-------|--------------|
| `ui/theme.css` | `[data-testid="stSidebar"]` selectors only | ✅ Yes — no dashboard/topbar/mobile |
| `tests/test_mono_theme_02_s1_sidebar_polish.py` | New — sidebar contract | ✅ Yes |
| `tests/test_mono_theme_01_s3_nav_active_grammar.py` | Anchor update for `border: none` before `border-left` | ✅ Yes |
| `tests/test_ui_system_02_s3_sidebar_modernization.py` | Section spacing token update | ✅ Yes |
| `docs/MONO_THEME_02_VISUAL_CONTRACT.md` | Slice table + S1 complete marker | ✅ Yes |
| `ROADMAP.md` | Premature S1 complete — corrected on commit | ✅ Yes |

**Not included in S1:** `docs/SIDEBAR_THEME_01_AUDIT.md`, `tests/test_sidebar_theme_01_audit.py` (untracked, separate epic).

## S1 implementation plan (executing now)

**Files:** `ui/theme.css` (sidebar blocks only), `tests/test_mono_theme_02_s1_sidebar_polish.py`, test updates above.

**Visual grammar (token-backed, no new hex):**

- Active: `--erp-nav-active-bg` (~12% blue tint), `border-left: 3px solid --erp-nav-active-bar`, `--erp-nav-active-fg` text/icon
- No filled button box: `border: none`, `box-shadow: none`
- Idle: transparent bg, neutral text, `--erp-nav-hover-bg` on hover
- Section headers: 11px caption, weight 600, letter-spacing 0.08em, muted `--erp-nav-section-fg`
- Spacing: item padding `--erp-space-2` (8px), group gap `--erp-space-4` (16px), section gap `--erp-space-5` (24px)

**Not touched:** `registry/navigation.py`, `app.py` nav renderers, mobile CSS, header, dashboard, tables.

## Risks

| Risk | Mitigation |
|------|------------|
| Streamlit `kind="primary"` sidebar buttons still read as buttons | Removed full border box; accent bar + tint only |
| Open folder shadow looked button-like | Removed `box-shadow` on open folder header |
| Scope creep from crashed session | `test_theme_css_s1_diff_scope_sidebar_only` guard |
| Dark mode contrast on tint | Uses existing `COMPONENT_GRAMMAR_TOKENS` mixes |

## S2–S5 deferred plan

- **S2:** Compact `--hdr-h` desktop override, search panel prominence, softer toolbar buttons — `theme.css` hdr section + desktop media only
- **S3:** KPI grid gap/padding, welcome card, activity rows — `theme.css` `.erp-dash-*` / `.kpi-*`, `widgets.css` bordered wrappers
- **S4:** Table cell padding, hover, sticky thead where safe — `theme.css` fin/data tables
- **S5:** Fix `widgets.css` mob_bar override to restore `--erp-nav-active-*` on mobile bottom nav

## Navigation confirmation

`registry/navigation.py` — **no changes required or made**. Routes and registry ownership unchanged.
