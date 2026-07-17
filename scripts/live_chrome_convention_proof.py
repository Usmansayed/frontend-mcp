"""Live proof: chrome permanence assertion fails on sandbox non-sticky sidebar."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.planning.chrome_conventions import (
    CHROME_PERMANENCE_ASSERTION,
    HORIZONTAL_OVERFLOW_ASSERTION,
)


def main() -> int:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto("http://localhost:5173/login", wait_until="domcontentloaded")
        page.locator("input").nth(0).fill("admin")
        page.locator("input").nth(1).fill("pass")
        page.get_by_role("button", name="Continue").click()
        page.wait_for_url("**/dashboard**", timeout=15000)

        soft_ok = (
            "Welcome, admin" in page.inner_text("body")
            and "/dashboard" in page.url
        )
        print("1. soft text/url:", soft_ok)

        permanence = page.evaluate(f"({CHROME_PERMANENCE_ASSERTION})()")
        overflow = page.evaluate(f"({HORIZONTAL_OVERFLOW_ASSERTION})()")
        print("2. chrome permanence (sticky/fixed):", permanence)
        print("3. no horizontal overflow:", overflow)

        # Confirm sidebar exists but is static
        pos = page.evaluate(
            """() => {
              const el = document.querySelector('aside, nav, .sidebar');
              return el ? getComputedStyle(el).position : null;
            }"""
        )
        print("4. sidebar computed position:", pos)
        browser.close()

        if not soft_ok:
            print("FAIL: soft criteria should pass")
            return 1
        if permanence is True:
            print("FAIL: expected non-sticky sidebar to fail permanence")
            return 1
        print("PASS: soft criteria pass but chrome permanence fails — verify would block claim-done")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
