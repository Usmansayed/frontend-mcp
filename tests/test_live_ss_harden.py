"""Live Chromium / WAF harden — host cooldown, block-before-shot, deadline skip."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_host_cooldown_roundtrip() -> None:
	from navigation.inspiration_intelligence.browser.host_cooldown import (
		clear_host_cooldown,
		is_cooled,
		mark_blocked,
		mark_from_degraded,
	)

	clear_host_cooldown()
	assert not is_cooled("https://stripe.com/pricing")
	mark_blocked("https://stripe.com/pricing", reason="bot_challenge")
	assert is_cooled("https://www.stripe.com/x")
	assert mark_from_degraded(
		"https://linear.app",
		["perception_block:bot_challenge_detected", "screenshot_skipped_blocked"],
	)
	assert is_cooled("linear.app")
	clear_host_cooldown()
	assert not is_cooled("stripe.com")


def test_wide_no_default_web_screenshots() -> None:
	from navigation.inspiration_intelligence.levels import resolve_inspiration_level

	wide = resolve_inspiration_level("wide")
	assert wide.max_web_screenshots == 0
	mx = resolve_inspiration_level("max")
	assert mx.max_web_screenshots == 2
	assert mx.include_live_sites is True


@pytest.mark.asyncio
async def test_screenshot_url_skips_cooled_host() -> None:
	from navigation.inspiration_intelligence.browser.host_cooldown import (
		clear_host_cooldown,
		mark_blocked,
	)
	from navigation.inspiration_intelligence.browser.policy import ProviderFetchPolicy
	from navigation.inspiration_intelligence.browser.session import InspirationBrowserSession

	clear_host_cooldown()
	mark_blocked("https://blocked.example/page")
	sess = InspirationBrowserSession(
		provider_id="famous_site",
		policy=ProviderFetchPolicy(provider_id="famous_site"),
		headless=True,
		base_url="https://blocked.example",
	)
	path, deg = await sess.screenshot_url("https://blocked.example/page")
	assert path == ""
	assert "host_cooldown_skip" in deg
	clear_host_cooldown()


@pytest.mark.asyncio
async def test_screenshot_url_block_before_capture() -> None:
	from navigation.inspiration_intelligence.browser.host_cooldown import clear_host_cooldown
	from navigation.inspiration_intelligence.browser.policy import ProviderFetchPolicy
	from navigation.inspiration_intelligence.browser.session import InspirationBrowserSession

	clear_host_cooldown()
	sess = InspirationBrowserSession(
		provider_id="famous_site",
		policy=ProviderFetchPolicy(provider_id="famous_site"),
		headless=True,
		base_url="https://example.com",
	)
	runtime = MagicMock()
	runtime.navigate_and_observe = AsyncMock(
		return_value=MagicMock(ok=True, degraded=[], error=None, screenshot_path=None)
	)
	runtime.execute_script = AsyncMock(
		return_value="<html>cf-browser-verification please verify captcha</html>"
	)
	runtime._capture_screenshot = AsyncMock(return_value="/tmp/should_not.png")
	sess._runtime = runtime

	path, deg = await sess.screenshot_url("https://example.com/")
	assert path == ""
	assert any("screenshot_skipped_blocked" in d for d in deg)
	runtime._capture_screenshot.assert_not_called()
	# navigate must request screenshot=False
	kwargs = runtime.navigate_and_observe.await_args.kwargs
	assert kwargs.get("screenshot") is False
	clear_host_cooldown()


@pytest.mark.asyncio
async def test_default_capture_deadline_skip() -> None:
	import time

	from navigation.inspiration_intelligence.browser.host_cooldown import clear_host_cooldown
	from navigation.inspiration_intelligence.live_capture import _default_capture

	clear_host_cooldown()
	path, title, deg = await _default_capture(
		{"url": "https://example.com/x", "title": "Ex"},
		deadline_mono=time.monotonic() + 1.0,  # under 6s budget
	)
	assert path == ""
	assert any("deadline_skip" in d for d in deg)
