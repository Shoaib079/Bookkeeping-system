#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import re, json

def login(page):
    sel = page.locator('[data-testid="stButton"] button').filter(has_text=re.compile(r"select|seç", re.I))
    if sel.count():
        sel.first.click(); page.wait_for_timeout(1000)
    if page.locator('input[type="password"]').count():
        page.locator('input[type="password"]').first.fill("admin123")
        page.locator('[data-testid="stFormSubmitButton"] button').first.click()
        page.wait_for_timeout(2000)
    enter = page.locator('[data-testid="stButton"] button').filter(has_text=re.compile(r"enter|gir", re.I))
    if enter.count():
        enter.first.click(); page.wait_for_timeout(2500)

results = {"pass": [], "fail": []}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
    login(page)
    page.wait_for_timeout(2000)

    search = page.locator('div[data-testid="stHorizontalBlock"]:has(.erp-hdr-appname) input').first
    box = search.bounding_box()
    if box and box["height"] >= 30 and box["width"] >= 200:
        results["pass"].append(f"Search visible {box['width']}x{box['height']}")
    else:
        results["fail"].append(f"Search not visible enough: {box}")

    instr = page.locator('[data-testid="InputInstructions"]')
    if instr.count() == 0 or not instr.first.is_visible():
        results["pass"].append("InputInstructions hidden")
    else:
        results["fail"].append("InputInstructions still visible")

    search.click()
    search.fill("test")
    page.wait_for_timeout(500)
    if instr.count() == 0 or not instr.first.is_visible():
        results["pass"].append("No hint after typing in search")
    else:
        results["fail"].append(f"Hint after typing: {instr.first.inner_text()}")

    browser.close()
print(json.dumps(results, indent=2))
