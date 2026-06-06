#!/usr/bin/env python3
"""Mobile add-transaction keypad smoke — buffer updates without full-page errors."""
from __future__ import annotations

import json
import re
import sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"
VIEWPORT = {"width": 390, "height": 844}


def login(page) -> None:
    if page.locator('[data-testid="stSidebar"]').count():
        try:
            if "Home" in page.locator('[data-testid="stSidebar"]').inner_text(timeout=1500):
                return
        except Exception:
            pass
    sel = page.locator('[data-testid="stButton"] button').filter(
        has_text=re.compile(r"select|seç", re.I)
    )
    if sel.count():
        sel.first.click()
        page.wait_for_timeout(1000)
    if page.locator('input[type="password"]').count():
        page.locator('input[type="password"]').first.fill("admin123")
        page.locator('[data-testid="stFormSubmitButton"] button').first.click()
        page.wait_for_timeout(2000)
    enter = page.locator('[data-testid="stButton"] button').filter(
        has_text=re.compile(r"enter|gir", re.I)
    )
    if enter.count():
        enter.first.click()
        page.wait_for_timeout(2500)


def _amount_text(page) -> str:
    loc = page.locator(".erp-mob-at-amount-display").first
    if loc.count():
        return loc.inner_text(timeout=3000)
    return page.locator('[class*="st-key-mob_at_amount_row"]').first.inner_text(timeout=3000)


def main() -> int:
    results: dict = {"pass": [], "fail": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=VIEWPORT)
        context.add_cookies(
            [
                {
                    "name": "erp_mobile_ui",
                    "value": "1",
                    "domain": "localhost",
                    "path": "/",
                }
            ]
        )
        page = context.new_page()
        try:
            page.goto(URL, wait_until="networkidle", timeout=30000)
        except Exception as exc:
            results["fail"].append(f"goto: {exc}")
            print(json.dumps(results, indent=2))
            return 1

        login(page)
        page.wait_for_timeout(1500)

        bar_new = page.locator('[class*="st-key-mob_bar_new"] button').first
        if not bar_new.count() or not bar_new.is_visible():
            results["fail"].append("bottom New button missing")
        else:
            bar_new.click()
            page.wait_for_timeout(2500)

        panel = page.locator('[class*="st-key-erp_mob_at_panel"]')
        if not panel.count():
            results["fail"].append("mobile AT panel (erp_mob_at_panel) missing — is erp_mobile_ui=1?")
            print(json.dumps(results, indent=2))
            return 1

        keypad_host = page.locator('[class*="st-key-mob_at_keypad"]')
        keypad_host.scroll_into_view_if_needed(timeout=5000)
        page.wait_for_timeout(800)

        keypad = keypad_host.locator("button")
        if keypad.count() < 12:
            results["fail"].append(f"keypad buttons found: {keypad.count()} (expected 12)")
        else:
            results["pass"].append("keypad grid rendered")

        def _key_btn(digit: str):
            loc = page.locator(f'[class*="st-key-mob_at_key_{digit}"] button')
            if loc.count():
                return loc.first
            return keypad.filter(has_text=re.compile(rf"^{re.escape(digit)}$")).first

        for digit in ("1", "2", "3"):
            btn = _key_btn(digit)
            if not btn.count():
                results["fail"].append(f"key {digit!r} button missing")
                print(json.dumps(results, indent=2))
                return 1
            btn.scroll_into_view_if_needed()
            btn.click(timeout=10000)
            page.wait_for_timeout(800)

        try:
            amt = _amount_text(page)
            if re.search(r"123", amt.replace(",", "").replace(" ", "")):
                results["pass"].append(f"buffer shows 123 ({amt!r})")
            else:
                results["fail"].append(f"buffer expected 123, got {amt!r}")
        except Exception as exc:
            results["fail"].append(f"amount read failed: {exc}")

        bksp = page.locator('[class*="st-key-mob_at_key_⌫"] button').first
        if not bksp.count():
            bksp = page.locator('[class*="st-key-mob_at_keypad"] button').filter(
                has_text="⌫"
            ).first
        if bksp.count():
            bksp.click()
            page.wait_for_timeout(600)
            try:
                amt = _amount_text(page)
                if re.search(r"12\b", amt.replace(",", "")) and "123" not in amt.replace(" ", ""):
                    results["pass"].append(f"backspace works ({amt!r})")
                else:
                    results["fail"].append(f"backspace expected 12, got {amt!r}")
            except Exception as exc:
                results["fail"].append(f"backspace read failed: {exc}")
        else:
            results["fail"].append("backspace key missing")

        browser.close()

    print(json.dumps(results, indent=2))
    return 1 if results["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
