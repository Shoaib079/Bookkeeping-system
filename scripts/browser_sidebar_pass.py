#!/usr/bin/env python3
"""Quick sidebar + label smoke test against a running Streamlit app."""
from __future__ import annotations

import json
import re
import sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"
TIMEOUT_MS = 30_000
VIEWPORT = {"width": 1400, "height": 900}


def login_if_needed(page) -> None:
    """Sign in when DEVELOPMENT_MODE is off (default admin / admin123)."""
    sidebar = page.locator('[data-testid="stSidebar"]')
    if sidebar.count() and sidebar.is_visible():
        return

    # Step 1: user tile selection (if shown)
    select_btn = page.locator('[data-testid="stButton"] button').filter(
        has_text=re.compile(r"select|seç", re.I)
    )
    if select_btn.count():
        select_btn.first.click()
        page.wait_for_timeout(1200)

    # Step 2: password form
    page.wait_for_selector('input[type="password"]', timeout=TIMEOUT_MS)
    user_inputs = page.locator('input:not([type="password"])')
    if user_inputs.count():
        user_inputs.first.fill("admin")
    page.locator('input[type="password"]').first.fill("admin123")
    page.locator(
        '[data-testid="stFormSubmitButton"] button, '
        '[data-testid="baseButton-primary"] button'
    ).filter(has_text=re.compile(r"sign in|giriş", re.I)).first.click()
    page.wait_for_timeout(2000)

    # Company picker (multi-company users only)
    if page.locator('[data-testid="stSidebar"]').count() == 0:
        company_btn = page.locator('[data-testid="stButton"] button').filter(
            has_text=re.compile(r"spice|company|şirket", re.I)
        )
        if company_btn.count():
            company_btn.first.click()
            page.wait_for_timeout(2000)


def wait_for_app(page) -> None:
    page.wait_for_selector('[data-testid="stSidebar"]', timeout=TIMEOUT_MS)
    page.wait_for_function(
        """() => {
            const el = document.querySelector('[data-testid="stSidebar"]');
            return el && el.innerText.includes('Home');
        }""",
        timeout=TIMEOUT_MS,
    )


def sidebar_text(page) -> str:
    return page.locator('[data-testid="stSidebar"]').inner_text()


def nav_button_texts(page) -> list[str]:
    loc = page.locator(
        '[data-testid="stSidebar"] [data-testid="stButton"] button, '
        '[data-testid="stSidebar"] [data-testid="baseButton-primary"] button, '
        '[data-testid="stSidebar"] [data-testid="baseButton-secondary"] button'
    )
    return [t.strip() for t in loc.all_text_contents() if t.strip()]


def click_nav(page, pattern: str) -> None:
    loc = page.locator(
        '[data-testid="stSidebar"] [data-testid="stButton"] button, '
        '[data-testid="stSidebar"] [data-testid="baseButton-primary"] button, '
        '[data-testid="stSidebar"] [data-testid="baseButton-secondary"] button'
    ).filter(has_text=re.compile(pattern, re.I))
    loc.first.click()
    page.wait_for_timeout(1800)


def has_marker(page, cls: str) -> bool:
    return page.locator(f'[data-testid="stSidebar"] .{cls}').count() > 0


def primary_nav_buttons(page) -> list[str]:
    loc = page.locator(
        '[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"], '
        '[data-testid="stSidebar"] [data-testid="baseButton-primary"] button'
    )
    return [t.strip() for t in loc.all_text_contents() if t.strip()]


def text_has(blob: str, needle: str) -> bool:
    return needle.lower() in blob.lower()


def main() -> int:
    results: dict = {"pass": [], "fail": [], "notes": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=VIEWPORT)
        page.goto(URL, wait_until="networkidle", timeout=TIMEOUT_MS)
        login_if_needed(page)
        wait_for_app(page)

        blob = sidebar_text(page)
        buttons = nav_button_texts(page)
        results["notes"].append(f"Nav buttons: {buttons}")

        # ── Label checks (case-insensitive; CSS may uppercase group headers) ─
        for label in ["Books", "Closings", "Settings", "Team & partners"]:
            if text_has(blob, label):
                results["pass"].append(f"Label present: {label}")
            else:
                results["fail"].append(f"Label missing: {label}")

        for label in ["Books & accounting", "Close your day"]:
            if text_has(blob, label):
                results["fail"].append(f"Old label still visible: {label}")
            else:
                results["pass"].append(f"Old label absent: {label}")

        # Members should not appear until Settings is opened
        if text_has(blob, "Members"):
            results["fail"].append("Members visible in collapsed sidebar")
        else:
            results["pass"].append("Members not shown in collapsed sidebar")

        # ── Accordion: Books ─────────────────────────────────────────────────
        click_nav(page, r"Books\s*▸")
        blob = sidebar_text(page)
        if text_has(blob, "Account activity"):
            results["pass"].append("Books accordion opens (Account activity visible)")
        else:
            results["fail"].append("Books accordion did not open")

        # ── Accordion switch: Team & partners ────────────────────────────────
        click_nav(page, r"Team\s*&\s*partners\s*▸")
        blob = sidebar_text(page)
        if text_has(blob, "Workers"):
            results["pass"].append("Team & partners opens (Workers visible)")
        else:
            results["fail"].append("Team & partners accordion did not open")

        if not text_has(blob, "Account activity"):
            results["pass"].append("Books closes when switching accordion")
        else:
            results["fail"].append("Books still open after Team & partners click")

        # ── Sales navigation + active state ────────────────────────────────
        click_nav(page, r"Record transactions\s*▸")
        click_nav(page, r"^💼\s*Sales$|Sales")
        blob = sidebar_text(page)

        if has_marker(page, "nav-item-active-mark"):
            results["pass"].append("nav-item-active-mark on Sales")
        else:
            results["fail"].append("nav-item-active-mark missing on Sales")

        primaries = primary_nav_buttons(page)
        if any(text_has(t, "Sales") for t in primaries):
            results["pass"].append("Sales button is primary")
        else:
            results["fail"].append(f"Sales not primary; primaries={primaries}")

        if has_marker(page, "nav-grp-active"):
            results["pass"].append("nav-grp-active on Record transactions")
        else:
            results["fail"].append("nav-grp-active missing")

        # ── Users label in Settings ────────────────────────────────────────
        click_nav(page, r"Settings\s*▸")
        blob = sidebar_text(page)
        if text_has(blob, "Users"):
            results["pass"].append("Users label in Settings group")
        else:
            results["fail"].append("Users label missing in Settings")

        if text_has(blob, "Members"):
            results["fail"].append("Still shows Members instead of Users")
        else:
            results["pass"].append("Members label absent (renamed to Users)")

        click_nav(page, r"Users")
        main_text = page.locator('[data-testid="stMain"]').inner_text()
        if text_has(main_text, "Users"):
            results["pass"].append("Users page content in main area")
        else:
            results["fail"].append("Users page content not found in main")

        browser.close()

    print(json.dumps(results, indent=2))
    return 1 if results["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
