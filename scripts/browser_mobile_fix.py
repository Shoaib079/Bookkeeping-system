#!/usr/bin/env python3
"""Mobile smoke test — bottom nav (Home/New/hubs), role/module checks."""
from __future__ import annotations

import json
import re
import sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"

VIEWPORTS = {
    "small_phone": {"width": 390, "height": 844},
    "large_phone": {"width": 430, "height": 932},
    "tablet": {"width": 768, "height": 1024},
}


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


def _visible(locator) -> bool:
    return locator.count() > 0 and locator.first.is_visible()


def check_mobile_chrome(page, label: str, results: dict) -> None:
    top_legacy = page.locator('[class*="st-key-mob_top_"] button').first
    bar_home = page.locator('[class*="st-key-mob_bar_home"] button').first
    bar_new = page.locator('[class*="st-key-mob_bar_new"] button').first
    bar_banking = page.locator('[class*="st-key-mob_bar_banking"] button').first
    bar_reports = page.locator('[class*="st-key-mob_bar_reports"] button').first
    bar_more = page.locator('[class*="st-key-mob_bar_more"] button').first

    if _visible(top_legacy):
        results["fail"].append(f"{label}: legacy top action bar still visible")
    else:
        results["pass"].append(f"{label}: no legacy top action bar")

    for name, loc in [
        ("bottom Home", bar_home),
        ("bottom New", bar_new),
        ("bottom Banking", bar_banking),
        ("bottom Reports", bar_reports),
        ("bottom More", bar_more),
    ]:
        key = f"{label}: {name}"
        if _visible(loc):
            results["pass"].append(key)
        else:
            results["fail"].append(key)

    if _visible(bar_more):
        bar_more.click()
        page.wait_for_timeout(1500)
        if page.locator(".erp-mobile-hub-host").count():
            results["pass"].append(f"{label}: More hub sheet opens")
            hist = page.locator('[class*="st-key-mob_hub_"] button').filter(
                has_text=re.compile(r"Sales", re.I)
            )
            if hist.count():
                results["pass"].append(f"{label}: Sales history in More hub")
            else:
                results["fail"].append(f"{label}: Sales history missing in More")
        else:
            results["fail"].append(f"{label}: More hub sheet missing")

    if _visible(bar_new):
        bar_new.click()
        page.wait_for_timeout(2000)
        main_text = page.locator('[data-testid="stMain"]').inner_text()
        if re.search(r"New Transaction|Yeni işlem|Add Transaction", main_text, re.I):
            results["pass"].append(f"{label}: bottom New navigates")
        else:
            results["fail"].append(f"{label}: New Transaction page not loaded")


def check_desktop_sidebar(page, results: dict) -> None:
    page.set_viewport_size({"width": 1280, "height": 900})
    page.wait_for_timeout(1500)
    sidebar = page.locator('[data-testid="stSidebar"]')
    bar_home = page.locator('[class*="st-key-mob_bar_home"] button')
    if sidebar.is_visible():
        results["pass"].append("desktop: sidebar visible")
    else:
        results["fail"].append("desktop: sidebar hidden")
    if bar_home.count() == 0 or not bar_home.first.is_visible():
        results["pass"].append("desktop: mobile bottom bar hidden")
    else:
        results["fail"].append("desktop: mobile bottom bar still visible")


def main() -> int:
    results: dict = {"pass": [], "fail": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for vp_name, vp in VIEWPORTS.items():
            page = browser.new_page(viewport=vp)
            page.goto(URL, wait_until="networkidle", timeout=30000)
            login(page)
            page.wait_for_timeout(2000)
            sidebar_vis = page.locator('[data-testid="stSidebar"]').is_visible()
            if not sidebar_vis:
                results["pass"].append(f"{vp_name}: sidebar hidden")
            else:
                results["fail"].append(f"{vp_name}: sidebar visible on mobile")
            check_mobile_chrome(page, vp_name, results)
            page.close()

        page = browser.new_page(viewport=VIEWPORTS["small_phone"])
        page.goto(URL, wait_until="networkidle", timeout=30000)
        login(page)
        check_desktop_sidebar(page, results)
        browser.close()

    print(json.dumps(results, indent=2))
    return 1 if results["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
