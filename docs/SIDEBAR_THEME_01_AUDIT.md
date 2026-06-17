# SIDEBAR-THEME-01 — Sidebar Theming Audit (Option A+ Final Blend)

**Mode:** Audit + implementation suggestion only. **No code changes, no nav-structure change, no posting/accounting change.** Targets the chosen **Option A+ Final Blend** (accounting-first shadcn spine + dense tables + **mono + one blue accent**, Stripe×Linear feel) and covers **both desktop and mobile**.

## Headline — you are ~80% there already

The chosen theme is **already the token foundation in the codebase**. `ui/design_tokens.py` (the single source of truth, injected by `ui/theme.py` under THEME-AUTHORITY-01) already defines:
- **Neutral surfaces:** `--theme-bg #F8FAFC`, `--theme-card #FFFFFF`, `--theme-border #E6E9EE`, slate text `--theme-text #0F172A` (+ a full dark set).
- **One blue accent (exactly the chosen blue):** `--erp-primary-fill #2563EB`, hover `#1D4ED8`, `--theme-info #2563EB`, `--theme-focus #2563EB`.
- **shadcn-like scales:** spacing 4/8/12/16/24/32, radius 6/8/12/pill, shadow sm/md/lg, type 11/13/15/18.

So SIDEBAR-THEME-01 is **not** "introduce a theme" — it is "**apply the existing tokens to the nav grammar consistently, with desktop+mobile parity**." No new colors; the mono + single-accent policy is preserved by construction.

## 1. Current sidebar architecture (what renders today)

### Desktop
- **`_render_navigation_tree(container=st.sidebar, …)`** (`app.py:3189`) iterates **`SIDEBAR_LAYOUT`** (`registry/sidebar_layout.py`) → section headers + direct buttons + accordion groups.
- Building blocks: `_nav_section_header` → `<div class="erp-nav-section-hdr">`; group header button (`type="primary"` when active) + marker `<div class="nav-grp-hdr-mark [nav-grp-active] [nav-grp-open]">`; item buttons via `_nav_page_button` with `nav-item-active-mark` / `nav-item-mark`.
- **Width token:** `--side-nav-w` / `--erp-sidebar-w = 244px`; header `--hdr-h = 60px`.
- **Styling lives in `ui/theme.css`** (the nav classes) — the render code emits classes; CSS owns the look.
- Nav is **registry-derived** (NAV-ARCH-S2/S3): `_PAGE_DISPATCH`, `_NAV_ACCORDION`, `_NAV_DIRECT_PAGES`, `_NAV_ROLE_PAGES` all build from `registry/navigation.py`.

### Mobile
- **`_MOBILE_BOTTOM_NAV`** (5 slots: home / money / new(＋) / reports / more) + **`_MOBILE_HUB_CONFIG`** (money/reports/people/more hubs); CSS in `ui/mobile_shell.css` + `ui/mobile_components.css`; `--bottom-nav-h = 62px`, mobile header `56px`.
- Desktop sidebar is **hidden on mobile** (bottom bar is primary) — so "sidebar theming" on mobile = the **bottom-nav active slot + hub cards**.

## 2. Gap vs Option A+ (what's missing for the sidebar specifically)

| Aspect | Today | Option A+ target |
|---|---|---|
| **Active item** | class marker + Streamlit `type="primary"` (solid blue button) | shadcn grammar: subtle **tinted bg** + **left accent bar** + blue text/icon — not a full solid fill on every active row |
| **Hover (idle item)** | minimal | subtle neutral hover (`color-mix(--theme-text 6%)`) |
| **Section header** | `erp-nav-section-hdr` | muted **uppercase caption** (11px, `--theme-muted`, letter-spacing) — Linear/shadcn style |
| **Density** | OK | tighten row height/padding to the 4/8/12 scale (dense, data-first) |
| **Accent usage** | blue solid buttons | blue reserved for **active + focus only**; everything else neutral (mono discipline) |
| **Desktop/mobile parity** | separate CSS files | same accent token drives the desktop active item **and** the mobile bottom-nav active slot |

The fix is **CSS + tokens**, applied to classes the render code **already emits** — no Python/nav changes.

## 3. Recommended implementation (suggestion only — DO NOT implement here)

**Principle:** add **sidebar-state tokens defined *by reference* to existing tokens** (so no new color values enter the system, preserving mono + one accent), then apply them to the existing nav classes in `ui/theme.css` (desktop) and `ui/mobile_*.css` (mobile).

**New token references (in `ui/design_tokens.py` + mirrored in `ui/theme.css :root`):**
```
--erp-nav-active-bg:     color-mix(in srgb, var(--erp-primary-fill) 12%, transparent)
--erp-nav-active-fg:     var(--erp-primary-fill)
--erp-nav-active-bar:    var(--erp-primary-fill)        /* 3px left accent bar */
--erp-nav-hover-bg:      color-mix(in srgb, var(--theme-text) 6%, transparent)
--erp-nav-section-fg:    var(--theme-muted)
```
- **Active item:** `--erp-nav-active-bg` background + 3px `--erp-nav-active-bar` left border + `--erp-nav-active-fg` text/icon. Replace the solid-blue `type="primary"` look on items with this lighter grammar (the button can stay; CSS restyles it).
- **Idle hover:** `--erp-nav-hover-bg`.
- **Section header:** uppercase, 11px (`--erp-font-caption`), `--erp-nav-section-fg`, letter-spacing.
- **Density:** row padding to `--erp-space-2`/`--erp-space-3`; radius `--erp-radius-md (8px)`.
- **Dark mode:** all of the above are token-derived, so dark "just works" (the dark `--erp-primary-fill` is the same `#2563EB`, surfaces swap automatically).

**Desktop ↔ mobile parity:** the **same** `--erp-nav-active-bg/-fg/-bar` tokens style the **mobile bottom-nav active slot** and the **hub cards** (`ui/mobile_shell.css` / `mobile_components.css`), so "active" looks identical in grammar on both surfaces. Hub cards reuse `--theme-card` / `--theme-border` / `--erp-radius-lg` / `--erp-shadow-sm`.

## 4. Implementation slices (suggested)

- **SIDEBAR-THEME-01-S1 — token references (no visual change yet):** add the `--erp-nav-*` reference tokens to `ui/design_tokens.py` + `ui/theme.css :root`; extend the existing token-parity contract test. Pure tokens.
- **SIDEBAR-THEME-01-S2 — desktop sidebar grammar:** apply tokens to `erp-nav-section-hdr`, `.nav-grp-active`, `.nav-item-active-mark`, hover, density in `ui/theme.css`. No `_render_navigation_tree` change.
- **SIDEBAR-THEME-01-S3 — mobile parity:** apply the same tokens to the bottom-nav active slot + hub cards in `ui/mobile_*.css`.
- **SIDEBAR-THEME-01-S4 — contract tests + React contract note:** active/hover/section-state token assertions; record the `--erp-nav-*` tokens in the React design contract (`docs/UI_SYSTEM_02_REACT_DESIGN_CONTRACT.md`) so the shadcn sidebar reuses them 1:1.

## 5. Risks

- **Mono-policy drift** — *mitigated:* tokens are defined by reference to `--erp-primary-fill` / `--theme-*`; no new color values, so the "mono + one accent" rule holds by construction.
- **Active-state legibility in dark** — verify `color-mix 12%` tint has enough contrast on `--theme-card` dark `#141C2B`; the contract test should assert the tokens resolve, and a manual dark check confirms contrast.
- **Streamlit button override fragility** — restyling `type="primary"`/`secondary` sidebar buttons via CSS depends on Streamlit's DOM; scope selectors to the sidebar/nav classes and guard with a visual smoke (screenshot) check.
- **Desktop/mobile divergence** — *mitigated:* one token set drives both; a test asserts the same `--erp-nav-active-*` tokens are referenced in both `theme.css` and the mobile CSS.
- **THEME-AUTHORITY-01 single-injection** — new tokens must flow through `ui/theme.py` injection, not ad-hoc `<style>`; keep one authority.

## 6. Boundaries

- **Touch:** `ui/design_tokens.py` (reference tokens), `ui/theme.css` (desktop nav grammar), `ui/mobile_shell.css` / `ui/mobile_components.css` (mobile parity), the token-parity contract tests, the React design-contract doc.
- **Never touch:** `_render_navigation_tree` logic, `registry/navigation.py` / `registry/sidebar_layout.py` (nav structure), `_PAGE_DISPATCH`, `services/posting.py`, accounting/GL — **theming is CSS/token-only**.
- **No new color values; no schema change; no nav behavior change.**

## 7. Recommendation — **PROCEED** (low risk, CSS/token-only)

The chosen Option A+ blend is already the token reality (neutral surfaces + `#2563EB` accent + shadcn scales). SIDEBAR-THEME-01 is a thin, token-driven CSS pass that (a) restyles the existing nav classes to the shadcn active/hover/section grammar and (b) mirrors the same accent token to the mobile bottom-nav + hubs for parity. It rides THEME-AUTHORITY-01, changes no navigation logic or accounting, and is guarded by the existing token-parity tests. Proceed S1→S4.

## ROADMAP suggestions (separate from implementation)

- Record **SIDEBAR-THEME-01 = PROCEED**, CSS/token-only, building on UI-SYSTEM-02 tokens + NAV-ARCH registry (no duplicate fixes): S1 reference tokens → S2 desktop grammar → S3 mobile parity → S4 tests + React contract.
- State the rule: **sidebar state colors are references to `--erp-primary-fill`/`--theme-*`; blue is reserved for active+focus; desktop and mobile share the same active token.**

## No-change statement (SIDEBAR-THEME-01 audit)

- **No code changes, no nav-structure change, no posting/accounting change, no new color values, no schema change.** Architecture assessment + gap + token plan + slices + risks + boundaries + recommendation only.

---

*Audit only. The chosen Option A+ Final Blend is **already the token foundation**: `ui/design_tokens.py` defines neutral surfaces (`--theme-bg/card/border`, slate text), the single blue accent `--erp-primary-fill #2563EB` (+ hover/info/focus), and shadcn-like spacing/radius/shadow/type scales, injected via `ui/theme.py` (THEME-AUTHORITY-01). The desktop sidebar (`_render_navigation_tree`, `app.py:3189`, styled by `ui/theme.css` nav classes, 244px) and mobile (`_MOBILE_BOTTOM_NAV` + `_MOBILE_HUB_CONFIG`, `ui/mobile_*.css`, 62px bottom nav) just need the existing tokens applied to the **active/hover/section grammar** with desktop+mobile parity. Recommendation: add `--erp-nav-active-bg/-fg/-bar` + `--erp-nav-hover-bg` defined **by reference** (color-mix of `--erp-primary-fill`/`--theme-text` — no new colors), apply to the nav classes (desktop) and bottom-nav/hub cards (mobile); slices S1 tokens → S2 desktop → S3 mobile → S4 tests+React contract. CSS/token-only; never touch nav logic, registry, posting, or GL. PROCEED (low risk).*
