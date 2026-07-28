"""Production harden — http pool, region focus, level bump, search aliases."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_http_pool_get_roundtrip() -> None:
	from navigation.inspiration_intelligence.browser.http_pool import (
		close_shared_httpx_client,
		pool_get,
		shared_httpx_client,
	)

	close_shared_httpx_client()
	client = shared_httpx_client()
	assert client is not None
	# Fail-soft against network: just ensure pool returns a 3-tuple shape
	with patch.object(client, "get", side_effect=RuntimeError("boom")):
		out = pool_get("https://example.com", timeout=1.0)
	assert out is not None
	body, status, err = out
	assert body == "" and status is None and err


def test_region_focus_selectors() -> None:
	from navigation.inspiration_intelligence.region_focus import (
		clip_from_script_result,
		selectors_for_scope,
		should_crop_scope,
	)

	assert should_crop_scope("chrome")
	assert should_crop_scope("component")
	assert not should_crop_scope("page")
	assert "nav" in selectors_for_scope("chrome")
	clip = clip_from_script_result({"x": 0, "y": 0, "width": 800, "height": 120})
	assert clip and clip["width"] == 800 and clip["scale"] == 1
	assert clip_from_script_result({"x": 0, "y": 0, "width": 1, "height": 1}) is None


def test_next_inspiration_level() -> None:
	from navigation.inspiration_intelligence.levels import next_inspiration_level

	assert next_inspiration_level("light") == "standard"
	assert next_inspiration_level("standard") == "wide"
	assert next_inspiration_level("wide") == "max"
	assert next_inspiration_level("max") == "max"
	assert next_inspiration_level("broad") == "max"  # alias → wide → next max


def test_ddg_alias_retry() -> None:
	from navigation.inspiration_intelligence.web_search import (
		WebSearchHit,
		WebSearchResult,
		search_duckduckgo,
	)

	calls: list[str] = []

	def _once(query: str, *, limit: int = 8, timeout_s: float = 8.0):
		calls.append(query)
		if query == "primary empty":
			return WebSearchResult(
				query=query, engine="duckduckgo_html", elapsed_ms=1.0, hits=[], degraded=["empty"]
			)
		return WebSearchResult(
			query=query,
			engine="duckduckgo_html",
			elapsed_ms=1.0,
			hits=[WebSearchHit(title="Nav", url="https://navbar.gallery/x", host="navbar.gallery")],
		)

	with patch(
		"navigation.inspiration_intelligence.web_search._search_duckduckgo_once",
		side_effect=_once,
	):
		result = search_duckduckgo(
			"primary empty", aliases=["navbar mega menu ui", "navigation header"]
		)
	assert result.hits
	assert any("ddg_alias_retry" in d for d in result.degraded)
	assert calls[0] == "primary empty"
	assert calls[1] == "navbar mega menu ui"


@pytest.mark.asyncio
async def test_live_capture_force_close_on_timeout() -> None:
	from navigation.inspiration_intelligence import live_capture as lc

	closed: list[str] = []

	class FakeSession:
		_runtime = None

		async def start(self):
			return None

		async def close(self):
			closed.append("close")

		async def screenshot_url(self, *a, **k):
			await __import__("asyncio").sleep(30)
			return "", []

	class FakeRuntime:
		async def force_kill(self):
			closed.append("kill")

	async def _fake_ctor(*a, **k):
		return None

	sess = FakeSession()
	sess._runtime = FakeRuntime()

	with patch.object(lc, "InspirationBrowserSession", create=True):
		# Patch where session is imported inside _default_capture
		with patch(
			"navigation.inspiration_intelligence.browser.session.InspirationBrowserSession",
			return_value=sess,
		):
			# InspirationBrowserSession(...) is called as constructor not async
			pass

	with patch(
		"navigation.inspiration_intelligence.browser.session.InspirationBrowserSession",
		side_effect=lambda **kwargs: sess,
	):
		path, title, deg = await lc._default_capture(
			{"url": "https://example.com/x", "title": "Ex"},
			timeout_s=0.2,
		)
	assert path == ""
	assert any("live_site_capture_timeout" in d for d in deg)
	assert "browser_force_closed" in deg
	assert "kill" in closed or "close" in closed
