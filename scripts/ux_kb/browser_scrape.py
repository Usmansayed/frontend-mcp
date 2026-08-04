"""Headed slow Playwright scraping — anti-bot friendly fallback for httpx failures."""
from __future__ import annotations

import random
import re
from typing import Any
from urllib.parse import urlparse

from .scrape_worker import USER_AGENT, html_to_text

SLOW_MO_MS = 800
PAGE_SETTLE_MS = 2500
NAV_TIMEOUT_MS = 120_000

COOKIE_DISMISS_SELECTORS = [
	'button:has-text("Accept all")',
	'button:has-text("Accept All")',
	'button:has-text("Accept")',
	'button:has-text("Got it")',
	'button:has-text("I agree")',
	'[data-testid="accept-all"]',
]


def fetch_with_browser(
	url: str,
	*,
	headless: bool = False,
	slow_mo_ms: int = SLOW_MO_MS,
	wait_until: str = "domcontentloaded",
) -> tuple[str, bytes]:
	"""Launch Chromium with human-ish pacing; returns markdown snapshot bytes."""
	try:
		from playwright.sync_api import sync_playwright
	except ImportError as exc:  # pragma: no cover
		raise RuntimeError("playwright not installed — run: pip install playwright && python -m playwright install chromium") from exc

	with sync_playwright() as p:
		browser = p.chromium.launch(
			headless=headless,
			slow_mo=slow_mo_ms,
			args=[
				"--disable-blink-features=AutomationControlled",
				"--no-sandbox",
			],
		)
		context = browser.new_context(
			user_agent=USER_AGENT,
			viewport={"width": 1366, "height": 900},
			locale="en-US",
			timezone_id="America/New_York",
			extra_http_headers={
				"Accept-Language": "en-US,en;q=0.9",
				"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
			},
		)
		context.add_init_script(
			"""
			Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
			window.chrome = { runtime: {} };
			"""
		)
		page = context.new_page()
		page.goto(url, wait_until=wait_until, timeout=NAV_TIMEOUT_MS)
		page.wait_for_timeout(PAGE_SETTLE_MS + random.randint(200, 1200))

		# SPA / design-system sites need extra render time
		host = urlparse(url).netloc.lower()
		if any(h in host for h in ("material.io", "apple.com", "carbondesignsystem.com", "polaris.shopify.com")):
			page.wait_for_timeout(3000)
			try:
				page.wait_for_load_state("networkidle", timeout=15_000)
			except Exception:
				pass

		for sel in COOKIE_DISMISS_SELECTORS:
			try:
				loc = page.locator(sel).first
				if loc.is_visible(timeout=800):
					loc.click(timeout=2000)
					page.wait_for_timeout(600)
					break
			except Exception:
				continue

		# Scroll to trigger lazy content
		page.evaluate(
			"""() => {
			  const h = document.body.scrollHeight;
			  window.scrollTo(0, Math.min(h, 800));
			  window.scrollTo(0, 0);
			}"""
		)
		page.wait_for_timeout(800)

		html = page.content()
		browser.close()

	text = html_to_text(html, url)
	# Strip wayback toolbar noise
	text = re.sub(r"\n(?:About this capture|The Wayback Machine)[^\n]*\n", "\n", text, flags=re.I)
	data = text.encode("utf-8")
	if len(data) < 800:
		raise RuntimeError(f"browser snapshot too small: {len(data)} bytes")
	return text, data


def browser_available() -> bool:
	try:
		from playwright.sync_api import sync_playwright  # noqa: F401

		return True
	except ImportError:
		return False
