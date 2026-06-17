# MONO-THEME-01 — Option A+ ERP Theme: Full Design Audit (Desktop + Mobile)

**Mode:** Full design/architecture audit only. **No implementation, no CSS changes, no code generation, no route/nav changes, no accounting/PostgreSQL changes.** Goal: make desktop and mobile feel like **one app**, on the user-approved **Option A+ Final Blend** (accounting-first shadcn spine, mono/neutral, one blue accent, dense tables, color only when it carries meaning).

## 1. Executive verdict — **PROCEED (revise-light)**

The token foundation **already is** Option A+. There is **no new color system to build** and **no giant rewrite needed**. The real work is (a) **consolidating component grammar that is currently defined twice** (desktop `theme.css`/`widgets.css` vs mobile `mobile_*.css`) onto **shared tokens**, (b) **deprecating the leftover rainbow role hues** (already flagged deprecated in code), and (c) applying the **mono + single-accent grammar** to nav/cards/chips consistently. That is the entire reason it can "feel like two apps" today: same tokens, **duplicated component CSS**. Proceed with safe slices S1–S7.

## 2. What already exists

- **Token SSOT:** `ui/design_tokens.py` (injected by `ui/theme.py`, THEME-AUTHORITY-01) — light + dark color sets, system-dark media, layout/spacing/radius/shadow/type scales. Mirrored + contract-tested in `ui/theme.css :root`.
- **Neutral surfaces (light):** `--theme-bg #F8FAFC`, `--theme-card #FFFFFF`, `--theme-border #E6E9EE`, text `--theme-text #0F172A`, muted `#475569` (+ full dark set: bg `#0B1220`, card `#141C2B`, border `#2D3A4D`).
- **One blue accent (the chosen blue):** `--erp-primary-fill #2563EB`, hover `#1D4ED8`, `--theme-info #2563EB`, `--theme-focus #2563EB`.
- **Semantic colors:** success `#16A34A`, danger `#DC2626`, warning `#D97706` (+ `*-text` variants, dark variants).
- **shadcn-like scales:** spacing 4/8/12/16/24/32, radius 6/8/12/pill, shadow sm/md/lg, type 11/13/15/18, line-height tight/body.
- **Chip grammar:** `CHIP_TOKEN_KEYS` via `color-mix` (CSS-only).
- **CSS owners (7,325 lines):** desktop = `theme.css` (2,161) + `widgets.css` (1,181) + `desktop_*.css` + `banking.css` + `auth.css` + `setup01_wizard.css` + `icons.css`; **mobile = `mobile_shell.css` (1,053) + `mobile_txn.css` (1,114) + `mobile_components.css` (327) + `mobile_header.css` (168) + `mobile_reports.css` (93) + `mobile_txn_history.css` (319)**.
- **Mobile shell grammar:** bottom nav (5 slots, `--bottom-nav-h 62px`) + hubs, mobile header (`56px`).
- **React-ready pieces:** `ui/react_design_contract.py` + `docs/UI_SYSTEM_02_REACT_DESIGN_CONTRACT.md` (token contract), `registry/navigation.py` + React route contract (NAV-ARCH-S4), sidebar registry-driven.
- **Hardcoded color debt:** **minimal** — almost everything already references tokens (a stray-hex scan found only a couple outside the token files). Good.

## 3. What to keep

- **The entire token SSOT** (`design_tokens.py`) — it *is* Option A+; do not introduce a parallel palette (hard rule).
- **Neutral surfaces + the single `#2563EB` accent + the scales** — keep verbatim.
- **All semantic colors** — success/danger/warning + `*-text` variants (P&L, errors, reconciliation states depend on them).
- **Light/dark foundations + THEME-AUTHORITY-01 single-injection** — keep one injection authority.
- **Financial table patterns** (desktop_reports/txn_history) and **mobile bottom-nav + hub patterns** — keep the structure; only align their *active/card* grammar to shared tokens.
- **React contract artifacts** — extend, don't replace.

## 4. What to change (mono alignment + parity)

- **Rainbow / decorative role hues** — `DEPRECATED_ROLE_TOKEN_KEYS/VALUES` (owner `#1e40af`, manager `#0891b2`, cashier `#065f46`, partner `#6d28d9`, viewer `#6b7280`) are **already marked deprecated** in `design_tokens.py` but still referenced (e.g. `auth.css`). **Finish the deprecation** → mono avatars/badges (neutral surface + initials), no per-role hue.
- **Non-semantic card tinting** — any decorative card background should resolve to `--theme-card` + `--theme-border`; tint only for meaning (success/warn/danger).
- **Sidebar active/hover grammar** — adopt the SIDEBAR-THEME-01 plan (tinted bg + left accent bar + blue text for active; subtle neutral hover) using **shared** `--erp-nav-active-*` tokens.
- **Mobile active/hub styling** — the **same** `--erp-nav-active-*` tokens drive the mobile bottom-nav active slot + hub cards (this is the core "one app" fix).
- **Dashboard card / KPI / chip / badge** — unify to one card grammar token set (`--erp-card-bg/-border/-radius/-shadow`) referenced by **both** desktop and mobile.
- **Button hierarchy** — primary = blue fill (`--erp-primary-fill`), secondary = neutral outline, destructive = danger; reserve blue for primary/active/focus only.
- **Form surfaces** — inputs on `--theme-card`, border `--theme-input-border`, focus ring `--theme-focus`; consistent across surfaces.
- **Banking/reconciliation status + report/P&L tables** — keep semantic colors, but standardize the **chip/row grammar** (shared chip tokens) so a "matched/review/mismatch" chip looks identical on desktop and mobile.
- **Any remaining hardcoded hex** — replace with token references (small, low-risk).

## 5. What NOT to change

- **Posting/accounting semantic colors** — profit/loss (success/danger), debit/credit emphasis.
- **Error / warning / success states** — keep meaning + contrast.
- **Reconciliation matched / review / mismatch colors** — semantic; keep.
- **Void / destructive colors** — danger stays loud.
- **Route/navigation ownership** (NAV-ARCH registry), **business logic**, **posting/GL**, **PostgreSQL/Alembic** — untouched (this is theming only).

## 6. Old vs new (text preview)

**Dashboard card**
```
CURRENT: white card, soft shadow, sometimes a colored top accent / tinted bg per section
OPTION A+: --theme-card bg, 1px --theme-border, --erp-radius-lg, --erp-shadow-sm;
           figure is the hero (tabular-nums); accent ONLY on a meaningful delta (green/red)
```
**Sidebar item**
```
CURRENT: active = solid blue Streamlit "primary" button
OPTION A+: active = --erp-nav-active-bg (12% blue tint) + 3px left --erp-primary-fill bar
           + blue text/icon; idle hover = 6% neutral tint; section header = muted UPPERCASE 11px
```
**Mobile bottom nav**
```
CURRENT: own CSS in mobile_shell.css; active slot styled independently of desktop
OPTION A+: active slot uses the SAME --erp-nav-active-fg blue token as the desktop sidebar
           → identical "active" grammar across surfaces (the "one app" cue)
```
**Banking status row**
```
CURRENT: status colors present; chip styling differs desktop vs mobile
OPTION A+: one shared chip token set; matched=success / review=warning / mismatch=danger,
           identical pill shape/size on both surfaces (semantics unchanged)
```
**Report / P&L table**
```
CURRENT: dense table; positive/negative colored
OPTION A+: same density, tabular-nums, right-aligned money, hairline --theme-border rows;
           green/red kept ONLY for P&L sign — no decorative row tints
```
**Light/dark notes:** all of the above are token-derived, so dark "just works"; the one check is that `color-mix` tints (active bg, chips) keep contrast on dark card `#141C2B` — a contrast assertion + manual dark pass.

## 7. Suggested preview boards (specify only — do NOT generate now)

1. **Board A — Dashboard + Add Transaction (desktop, light+dark):** KPI cards (mono + one delta color), dense recent-activity table, the Add Transaction form surfaces + button hierarchy.
2. **Board B — Banking / Reconcile (desktop):** reconciliation cockpit rows with matched/review/mismatch chips, statement table, status grammar.
3. **Board C — Reports / P&L (desktop):** dense P&L table, sign coloring, totals; light+dark.
4. **Board D — Mobile Dashboard + Money hub:** bottom nav (active slot blue), hub cards, a mobile KPI/list card — shown **beside** Board A to prove desktop/mobile parity.

## 8. Code owner map

| Concern | Owner |
|---|---|
| Token SSOT (colors/scales) | `ui/design_tokens.py` (+ `ui/theme.py` injection) |
| Desktop `:root` mirror + nav/card/table grammar | `ui/theme.css` (2,161) |
| Desktop widgets (chips/badges/kpi/buttons) | `ui/widgets.css` (1,181) |
| Desktop reports / txn tables | `ui/desktop_reports.css`, `ui/desktop_txn_history.css`, `ui/banking.css` |
| Mobile shell + bottom nav + hubs | `ui/mobile_shell.css` (1,053) |
| Mobile transaction surfaces | `ui/mobile_txn.css` (1,114), `ui/mobile_txn_history.css` |
| Mobile cards/chips | `ui/mobile_components.css` (327) |
| Mobile header | `ui/mobile_header.css` |
| Mobile reports | `ui/mobile_reports.css` |
| Section header helper | `ui/section.py` |
| React contract | `ui/react_design_contract.py` + `docs/UI_SYSTEM_02_REACT_DESIGN_CONTRACT.md` |
| Auth / setup chrome | `ui/auth.css`, `ui/setup01_wizard.css` |

## 9. Delete / deprecate plan

- **Deprecate (finish):** `DEPRECATED_ROLE_TOKEN_KEYS/VALUES` (role hues) — remove remaining references (`auth.css`, any avatar) → mono avatars. They are already labelled deprecated; this closes it.
- **Selectors to remove later:** decorative per-section card-tint selectors / colored top-accents that don't carry meaning (enumerate during S4/S6, remove only with a screenshot guard).
- **Duplicate CSS owners (consolidate, don't delete wholesale):** card/chip/nav-active grammar duplicated across `theme.css`/`widgets.css` (desktop) and `mobile_*.css` (mobile) → route both to **shared `--erp-card-*` / `--erp-chip-*` / `--erp-nav-active-*` tokens**; keep the per-surface selectors but make them reference one token set.
- **Streamlit-only hacks to keep (temporarily):** `type="primary"/"secondary"` button overrides, sidebar DOM scoping, `st.html`/`st.markdown` class injectors — keep until React; document them as Streamlit-bridge.
- **React-ready classes to preserve:** token names, `erp-*` semantic classes, the chip grammar, the React contract — carry across 1:1.

## 10. Slice plan

- **MONO-THEME-01-S1 — audit + design spec (this doc):** ✅ **Complete** — `docs/MONO_THEME_01_AUDIT.md` + `tests/test_mono_theme_01_audit.py`. Tag: `mono-theme-01-s1-audit-design-spec`.
- **MONO-THEME-01-S2 — token refinements:** ✅ **Complete** — shared component-grammar tokens in `ui/design_tokens.py` (`COMPONENT_GRAMMAR_TOKENS`) mirrored in `ui/theme.css` `:root` (`--erp-nav-*`, `--erp-card-*`, `--erp-chip-*` extensions, `--erp-table-*`); `tests/test_mono_theme_01_s2_shared_grammar_tokens.py`. Tag: `mono-theme-01-s2-shared-grammar-tokens`. Token definitions only — no component migration yet.
- **MONO-THEME-01-S3 — sidebar/nav active states:** ✅ **Complete** — desktop sidebar (`theme.css` + `icons.css`) and mobile bottom-nav/hub (`mobile_shell.css`) route active/hover/section styling through `--erp-nav-*` grammar tokens; `tests/test_mono_theme_01_s3_nav_active_grammar.py`. Tag: `mono-theme-01-s3-nav-active-grammar`. No nav-structure or Python changes.
- **MONO-THEME-01-S4 — desktop cards / dashboard / forms:** ✅ **Complete** — desktop KPI/dashboard/banner/activity cards and form containers (`theme.css`, `widgets.css`) route neutral card surfaces through `--erp-card-*` tokens; `tests/test_mono_theme_01_s4_desktop_card_grammar.py`. Tag: `mono-theme-01-s4-desktop-card-grammar`. Semantic accent borders unchanged.
- **MONO-THEME-01-S5 — mobile shell / cards / nav:** ✅ **Complete** — mobile KPI/list/sheet/form surfaces (`mobile_components.css`, `mobile_shell.css`, `mobile_txn.css`, `mobile_reports.css`) route neutral card shells through `--erp-card-*` via `--mob-surface-*` / `--mob-at-surface-*` aliases; `tests/test_mono_theme_01_s5_mobile_card_grammar.py`. Tag: `mono-theme-01-s5-mobile-card-grammar`. Nav active unchanged (S3).
- **MONO-THEME-01-S6 — reports / tables / banking statuses:** standardize chip/row grammar (semantics unchanged) across desktop + mobile.
- **MONO-THEME-01-S7 — cleanup + React contract update:** finish role-hue deprecation; record the shared grammar tokens in the React design contract; remove dead decorative selectors with screenshot guards.

Each slice: CSS/token-only, token-parity + (where useful) screenshot smoke, no nav/posting change.

## 11. Risk matrix

| Risk | Severity | Mitigation |
|---|---|---|
| Dark-mode contrast (color-mix tints on dark card) | Medium | Contrast assertion + manual dark pass per slice |
| Over-flattening financial meaning | High | Keep semantic colors (§5); mono applies only to *decorative* hues |
| Losing warning/error/success semantics | High | Never touch semantic tokens; tests assert they remain |
| Breaking Streamlit selectors | Medium | Scope selectors; screenshot smoke; keep Streamlit-bridge hacks until React |
| Duplicate theme systems persist | Medium | S2 shared tokens are the single grammar both surfaces reference |
| Mobile/desktop divergence (the core risk) | High | Shared `--erp-*` grammar tokens + a test asserting both desktop and mobile CSS reference the same active/card/chip tokens |
| React migration drift | Low | Record shared grammar in the React contract; tokens carry 1:1 |

## 12. Final recommendation

**PROCEED (revise-light), design-first.** Option A+ is already the token reality; the "two apps" feeling comes from **duplicated component CSS**, not divergent tokens. Fix it by introducing a **shared component-grammar token layer** (no new colors) and routing desktop `theme.css`/`widgets.css` and mobile `mobile_*.css` through it, finishing the role-hue deprecation, and keeping every semantic color. Execute as CSS/token-only slices S1–S7 with token-parity + screenshot guards. No nav/posting/PostgreSQL change; shadcn is inspiration, not a dependency.

## ROADMAP suggestions (separate from implementation)

- Record **MONO-THEME-01 = PROCEED (revise-light)**, CSS/token-only, building on UI-SYSTEM-02 tokens + SIDEBAR-THEME-01 + NAV-ARCH (no duplicate fixes).
- State the rule: **one shared component-grammar token layer; desktop and mobile reference the same active/card/chip tokens; blue accent for primary/active/focus only; semantic colors immutable; no parallel palette.**

## No-change statement (MONO-THEME-01 audit)

- **No implementation, no CSS changes, no code generation, no route/nav change, no accounting/PostgreSQL change, no new color system, no removal of semantic colors.** Verdict + exists/keep/change/not-change + old-vs-new preview + preview boards + owner map + delete/deprecate plan + slices + risk matrix + recommendation only.

---

*Audit only. Option A+ is already the token foundation (`ui/design_tokens.py` → neutral surfaces, single blue `#2563EB`, semantic success/danger/warning, shadcn scales, light/dark, injected via THEME-AUTHORITY-01). The "two apps" feeling is **duplicated component grammar**: desktop (`theme.css` 2,161 / `widgets.css` 1,181) and mobile (`mobile_shell.css` 1,053 / `mobile_txn.css` 1,114 / `mobile_components.css` 327 / …) style cards/nav-active/chips separately while sharing the same tokens. Verdict PROCEED (revise-light): introduce **shared component-grammar tokens** (`--erp-nav-active-*`, `--erp-card-*`, `--erp-chip-*` — by reference, no new colors), route both surfaces through them, finish the already-deprecated **role-hue** removal (mono avatars), keep ALL semantic colors (P&L sign, success/danger/warning, recon matched/review/mismatch, void). Slices S1 spec → S2 shared tokens → S3 sidebar+mobile-nav active → S4 desktop cards/forms → S5 mobile parity → S6 reports/tables/banking chips → S7 cleanup + React contract. Risks: dark contrast, over-flattening financial meaning, Streamlit selector fragility, desktop/mobile divergence (mitigated by the shared token layer + a parity test). CSS/token-only; no nav/posting/PostgreSQL change; shadcn is inspiration, not a dependency.*
