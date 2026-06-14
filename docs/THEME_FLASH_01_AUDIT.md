# THEME-FLASH-01 — Dark/Light Flash Audit

**Mode:** Characterization only. No code, no implementation.  
**Problem:** On open, the ERP briefly renders in light mode, then switches to dark mode.  
**Date:** 2026-06-14

---

## Executive summary

The flash is **not a single bug** — it is the combination of three mechanisms that all push the **first paint toward light** even when the user's effective theme is dark:

| # | Mechanism | Class | Severity |
|---|-----------|-------|----------|
| 1 | `bootstrap_theme()` runs **before** auth/session restore, so the first run injects theme for `auth_user=None` | **B** Session-state initialization | High on cold open |
| 2 | Base stylesheet defines **light `:root` tokens first**; dark override arrives in a **later** `<style>` block | **A + C** Late injection + CSS order | High every run (explicit dark) |
| 3 | `data-erp-theme` is set by a **client `<script>`** after HTML parse; explicit-dark users **cannot** use `@media (prefers-color-scheme: dark)` fallback | **A + D** Late injection + Streamlit delivery | Medium |
| 4 | Streamlit native chrome (`.streamlit/config.toml` `[theme]`) defaults to **light**; ERP override uses CSS vars that start light | **D** Streamlit limitation | Low–medium |

**Primary root cause (exact lines):**

```507:534:ui/theme.py
def bootstrap_theme(session_factory, auth_user: dict | None) -> None:
    render_global_style()                    # ← light :root first (theme.css L6–53)
    inject_mobile_viewport_detector()
    ...
    inject_theme_authority_marker(theme_mode)  # ← JS; not available at first CSS pass
    if theme_mode == "light":
        inject_theme_css(False)
    elif theme_mode == "dark":
        inject_theme_css(True)               # ← dark :root SECOND style block
    else:
        os_inject = _system_theme_injection_dark()
        if os_inject is not None:
            inject_theme_css(os_inject)
```

```25667:25721:app.py
def main():
    ...
    bootstrap_theme(get_session, st.session_state.get("auth_user"))  # ← runs BEFORE restore
    ...
    if _current_user() is None and not st.session_state.get(_SESSION_LOGGED_OUT):
        with get_session() as _restore_s:
            if _try_restore_session_from_cookie(_restore_s):  # ← sets theme_mode HERE
                st.rerun()                                     # ← correct theme only run 2
```

**Classification:** **A (theme injected too late)** + **B (session-state initialization)** + **C (CSS override order)**. Streamlit progressive delivery amplifies **D**.

---

## 1. Theme initialization order

### Call chain (every `main()` run)

| Step | Function | File:line | What happens |
|------|----------|-----------|--------------|
| 1 | `bootstrap_theme()` | `app.py:25671` | Entry point — **first UI-side effect in `main()`** |
| 2 | `render_global_style()` | `ui/theme.py:509` → `154–156` | `st.markdown("<style>…</style>")` — concatenates **all** CSS files |
| 3 | `inject_mobile_viewport_detector()` | `ui/theme.py:510` → `159–204` | Hidden `st.iframe` + JS: `erp-mobile`, `data-erp-os-dark`, cookies |
| 4 | `apply_user_theme_from_db()` | `ui/theme.py:512–515` | Only if `auth_user.id` present — reads `AppSetting` `user_pref_{id}_theme` |
| 5 | `setdefault("theme_mode", "system")` | `ui/theme.py:515–519` | If no auth or no DB row |
| 6 | `sync_derived_dark_mode()` | `ui/theme.py:521` | Mirrors `theme_mode` → `dark_mode` |
| 7 | `inject_theme_authority_marker(theme_mode)` | `ui/theme.py:522–523` → `328–340` | `<script>` sets `html[data-erp-theme]` |
| 8 | `inject_theme_css(effective_dark)` | `ui/theme.py:525–532` → `215–219` | **Second** `<style>:root{…}</style>` override |
| 9 | `sync_os_dark_flag_from_cookie()` | `ui/theme.py:534` | System-mode OS hint for charts |

### Is any UI rendered before theme injection?

**Within a single Python run:** No — `bootstrap_theme()` is the first call in `main()` (after `os.chdir`). No `st.button`, header, or page body runs before step 1–8 complete.

**Across Streamlit's delivery model:** Yes — effectively. Each `st.markdown` / `st.iframe` is a **separate delta** streamed to the browser. The browser can paint after step 2 (global CSS with light `:root`) before step 8 (dark override) arrives. That is the within-run flash.

**Before `main()`:** Streamlit serves its own shell HTML + `[theme]` from `.streamlit/config.toml` (light baseline) before any app script output.

---

## 2. Session state

### Keys

| Key | Authority | Set where |
|-----|-----------|-----------|
| `theme_mode` | **Authoritative** (`light` \| `dark` \| `system`) | `apply_user_theme_from_db`, `_establish_auth_session`, header toggle, My Account radio |
| `dark_mode` | **Derived mirror only** — must not drive injection | `sync_derived_dark_mode()` |
| `_erp_os_dark` | System-mode OS hint | `sync_os_dark_flag_from_cookie()` |
| `_erp_os_dark_from_cookie` | Sticky OS signal | `sync_os_dark_flag_from_cookie()` |

### Initialization vs first render

**Cold open (cookie restore, production):**

1. `st.session_state` empty → `auth_user` absent at `bootstrap_theme` line 25671.
2. `bootstrap_theme(..., None)` → `theme_mode` defaults to `"system"`; **no DB preference loaded**.
3. Later: `_try_restore_session_from_cookie` → `_establish_auth_session` → loads theme from DB (`app.py:4705–4709`) and sets `theme_mode`.
4. `st.rerun()` (`app.py:25721`) — **first streamed frame used wrong injection; second run correct**.

**Dev mode cold open:**

1. Same: `bootstrap_theme` with `auth_user=None`.
2. `_dev_auto_login` (`app.py:25707–25711`) calls `_establish_auth_session` **after** bootstrap — sets `theme_mode` but **does not re-inject CSS** and **does not `st.rerun()`**.
3. Entire first dev session can show light injection while `theme_mode` is already `"dark"` in session (until user toggles theme or any full rerun).

**Login flow:**

1. First run: unauthenticated → bootstrap without DB theme → login page (light).
2. Submit login → `_establish_auth_session` sets theme → `st.rerun()` (`app.py:5062`).
3. Second run: bootstrap with `auth_user` → correct dark inject.

**Warm session (tab refresh, `auth_user` already in `st.session_state`):**

- `bootstrap_theme` sees `auth_user` immediately → DB theme loaded in same run → **no restore rerun**.
- Flash may still occur from **CSS order** (mechanism 2), not session order.

### Does initialization trigger `st.rerun()`?

| Event | Rerun? | Theme impact |
|-------|--------|--------------|
| Cookie session restore | **Yes** (`app.py:25721`) | Run 1 wrong, run 2 correct |
| Login success | **Yes** (`app.py:5062`) | Run 1 login light, run 2 app dark |
| Dev auto-login | **No** | Injection stale for whole run |
| Header theme toggle | **Yes** (`app.py:3152`) | Expected intentional switch |
| My Account theme save | **Yes** (`app.py:25637`) | Expected intentional switch |

---

## 3. Registry / settings

### Source of truth

- **Per-user preference:** `AppSetting` row `user_pref_{user_id}_theme` → values `light` \| `dark` \| `system`.
- **Load paths:**
  - `apply_user_theme_from_db()` in `bootstrap_theme` when `auth_user` present (`ui/theme.py:492–504`).
  - `_establish_auth_session()` on login/restore (`app.py:4705–4709`) — duplicate load into `theme_mode`.
- **Default when missing:** `"system"` (`ui/theme.py:515–519`); invalid DB values coerced to `"light"` in `apply_user_theme_from_db` (`ui/theme.py:500–501`).

### System-mode resolution order (`sync_os_dark_flag_from_cookie`, `ui/theme.py:270–292`)

1. Explicit `light` / `dark` → ignore OS cookie.
2. `erp_os_dark` cookie (`0` / `1`) — set by viewport iframe JS (`ui/theme.py:190–192`).
3. `Sec-CH-Prefers-Color-Scheme` header.
4. Sticky `_erp_os_dark_from_cookie` session.
5. **Default `False` (light)** if none available.

**First-request gap:** `erp_os_dark` cookie does not exist until the iframe JS runs on a prior visit. First cold request in system mode with OS dark may get server default `False` and **no** `inject_theme_css` — relies on CSS `@media` until cookie exists on next request.

There is **no company-level theme setting** — user preference only.

---

## 4. CSS loading

### Files injected (single bundle, `load_theme_css()`, `ui/theme.py:107–146`)

Concatenated in order: `theme.css` → `widgets.css` → `mobile_components.css` → `mobile_shell.css` → `mobile_header.css` → `auth.css` → `mobile_txn.css` → `mobile_reports.css` → `mobile_txn_history.css` → `desktop_txn_history.css` → `desktop_reports.css` → `banking.css` → `setup01_wizard.css` → `icons.css`.

### Token cascade

```6:53:ui/theme.css
:root {
  --theme-bg: #f8fafc;   /* LIGHT defaults — always parsed first */
  ...
}
```

```72:98:ui/theme.css
@media (prefers-color-scheme: dark) {
  html[data-erp-theme="system"] :root,
  html:not([data-erp-theme]) :root {
    --theme-bg: #0b1220;   /* DARK via OS — only system or unset attribute */
    ...
  }
}
```

```215:219:ui/theme.py
def inject_theme_css(dark_mode: bool) -> None:
    vars_map = DARK_ROOT_VARS if dark_mode else LIGHT_ROOT_VARS
    st.markdown(f"<style>:root{{…}}</style>")  /* SECOND override block */
```

**Explicit `dark` preference:** `@media` selector requires `data-erp-theme="system"` or absent attribute. Once `inject_theme_authority_marker` sets `data-erp-theme="dark"`, **OS media dark vars no longer apply**. Dark appearance depends entirely on the **second** `inject_theme_css(True)` block.

**Explicit `light` preference:** `inject_theme_css(False)` re-asserts light vars after media — correct.

**Multiple sequential injections:** Yes — (1) global bundle, (2) authority script, (3) `:root` override. Dark override **always** comes last for explicit dark users, but **after** the browser may have already painted light.

---

## 5. Browser / system theme

### `prefers-color-scheme`

| Location | Role |
|----------|------|
| `ui/theme.css:72–108` | OS dark vars for `system` mode or before `data-erp-theme` is set |
| `inject_mobile_viewport_detector` JS (`ui/theme.py:184–198`) | Sets `data-erp-os-dark`, writes `erp_os_dark` cookie, listens for OS changes |
| `_os_dark_from_client_hint()` (`ui/theme.py:227–237`) | `Sec-CH-Prefers-Color-Scheme` server hint |
| `.streamlit/config.toml [theme.dark]` | Streamlit native widget chrome when OS dark |

### Post-load JS

- `inject_theme_authority_marker` — synchronous IIFE, sets `data-erp-theme` (`ui/theme.py:333–337`).
- Viewport iframe — async relative to main document; sets cookies for **next** request.

No theme-toggle JS beyond Streamlit reruns. No localStorage theme cache.

---

## 6. Mobile / desktop split

**Same bootstrap path** — no separate mobile theme loader. Mobile-specific files (`mobile_shell.css`, `mobile_txn.css`, etc.) are bundled into the **same** `load_theme_css()` payload as desktop.

Mobile-only behavior in bootstrap:

- `inject_mobile_viewport_detector()` adds `html.erp-mobile` class and `erp_os_dark` cookie.
- Does **not** change light/dark token injection order.

`UI_STYLE_GUIDE.md` and `docs/MOBILE_UX_02_THEME_DESIGN_AUDIT.md` confirm one token system (`--theme-*`) for both surfaces.

---

## 7. Root cause (detailed)

### Scenario A — Returning user, saved **dark**, warm session

1. `bootstrap_theme` loads `theme_mode="dark"` from DB ✓  
2. `render_global_style()` streams light `:root` first.  
3. Browser paints light frame.  
4. `inject_theme_css(True)` streams dark `:root`.  
5. Browser repaints dark → **visible flash**.

**Lines:** `ui/theme.py:509` then `528`; `ui/theme.css:6–16`.

### Scenario B — Cold open, cookie restore, saved **dark**

1. Run 1: `bootstrap_theme(..., None)` → system/light injection.  
2. `_establish_auth_session` sets `theme_mode="dark"` **after** injection.  
3. `st.rerun()`.  
4. Run 2: correct dark injection but user already saw run 1 (login shell or blank).  
**Lines:** `app.py:25671`, `4705–4709`, `25721`.

### Scenario C — System mode, OS dark, first visit (no `erp_os_dark` cookie)

1. Server: no `inject_theme_css` (`test_theme_authority01.py:96–105` pins this).  
2. CSS `@media` should apply dark via `html:not([data-erp-theme])`.  
3. Then script sets `data-erp-theme="system"` → media still applies ✓  
4. Flash risk lower unless Streamlit shell light chrome visible before custom CSS.

### Scenario D — Explicit **dark**, OS **light**

Worst case for mechanism 2: no `@media` fallback after script runs; full reliance on second inject block. **Maximum flash.**

---

## 8. Safe fix (smallest possible — not implemented)

Constraints: no visual redesign; preserve `light` / `dark` / `system` semantics and existing tokens.

### Fix 1 — Resolve theme **before** first CSS byte (addresses A + C)

**Idea:** In `bootstrap_theme`, resolve `theme_mode` / `effective_dark` first (including DB load), then emit **one** initial `<style>` block that starts with the correct `:root{…}` vars, followed by the rest of `load_theme_css()`.

- Eliminates light-then-dark two-block cascade for explicit preferences.
- No token changes; same `LIGHT_ROOT_VARS` / `DARK_ROOT_VARS`.

### Fix 2 — Move auth restore before `bootstrap_theme` (addresses B)

**Idea:** In `main()`, run cookie restore / dev auto-login **before** `bootstrap_theme(get_session, st.session_state.get("auth_user"))`.

- Ensures DB `theme_mode` is in session before injection on cold open.
- Removes the restore-triggered double-run flash for theme (restore rerun may still occur for other reasons).

### Fix 3 — Inline `data-erp-theme` in first style block (addresses A + D)

**Idea:** Replace late `<script>` authority marker with CSS that does not depend on JS for first paint, e.g. `html { color-scheme: … }` or scoped rules keyed off a server-rendered attribute in the same first `st.markdown` block.

- Reduces gap where `html:not([data-erp-theme])` allows unintended media behavior.

### Fix 4 — Blocking anti-flash snippet (minimal, optional add-on)

**Idea:** First output of `main()` — before any other markdown — a tiny inline style or script that sets `document.documentElement` vars from server-known `effective_dark` (when auth/session already resolved).

- Streamlit has no true `<head>` hook; must be first `st.markdown` in the run.

### Recommended minimal combination

**Fix 2 + Fix 1** — restore auth first, then single-bundle correct `:root` prefix. Smallest behavioral change, no new tokens, no redesign.

**Do not** change `.streamlit/config.toml` alone — it only affects Streamlit native chrome, not ERP token injection, and does not follow per-user `dark` preference when OS is light.

---

## 9. Test / doc anchors

| Asset | Relevance |
|-------|-----------|
| `tests/test_theme_authority01.py` | Pins bootstrap inject count, system-no-inject-without-hint, media scoping |
| `docs/UI_STYLE_GUIDE.md` L240–260 | Dark verification checklist; Glide `--gdg-*` + config.toml note |
| `.streamlit/config.toml` L1–19 | Streamlit light default; `[theme.dark]` OS-gated |
| `UI_SHELL.md` L431 | Documents `bootstrap_theme()` on every `main()` |

---

## 10. What must not change (fix phase)

- `theme_mode` authority model (`light` \| `dark` \| `system`).
- `LIGHT_ROOT_VARS` / `DARK_ROOT_VARS` values.
- Mono KPI policy in dark mode (`_DARK_MONO_KPI_CSS`).
- Chart token resolver (`resolve_effective_dark`, `chart_theme_tokens`).
- Per-user DB key `user_pref_{id}_theme`.
- Mobile viewport detector cookies (orthogonal to flash fix).

---

*Characterization only. No code modified. Accounting and theme behavior unchanged.*
