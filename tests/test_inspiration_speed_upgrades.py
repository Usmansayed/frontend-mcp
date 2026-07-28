"""Speed/reliability helpers — SERP cache, preview validate, source affinity."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_serp_cache_roundtrip() -> None:
	from navigation.inspiration_intelligence.serp_cache import (
		clear_serp_cache,
		get_serp,
		put_serp,
		serp_fingerprint,
	)
	from navigation.inspiration_intelligence.web_search import WebSearchHit, search_web

	clear_serp_cache()
	fp = serp_fingerprint("modal ui design examples", limit=4)
	put_serp(
		fp,
		{
			"engine": "test",
			"hits": [
				{"title": "A", "url": "https://a.example/x", "host": "a.example", "rank": 0, "score": 1},
			],
			"degraded": [],
		},
	)
	cached = get_serp(fp)
	assert cached and cached["hits"]

	with patch(
		"navigation.inspiration_intelligence.web_search.search_duckduckgo",
		side_effect=AssertionError("should use serp cache"),
	):
		result = search_web("modal ui design examples", limit=4, use_cache=True)
	assert result.hits
	assert "serp_cache_hit" in result.degraded


def test_trusted_preview_skips_network() -> None:
	from navigation.inspiration_intelligence.preview_validate import is_trusted_preview, _head_ok

	assert is_trusted_preview("https://img.daisyui.com/images/components/button.webp")
	ok, reason = _head_ok("https://img.daisyui.com/images/components/button.webp")
	assert ok and reason == "trusted_cdn"


def test_source_affinity_sticky() -> None:
	from navigation.inspiration_intelligence.source_affinity import (
		affinity_key,
		clear_affinity,
		prefer_categories_from_providers,
		prefer_providers,
		record_winners,
	)

	clear_affinity()
	key = affinity_key(scope="component", intent_class="navigation", query="navbar")
	record_winners(key, ["navbar_gallery", "daisyui"])
	assert prefer_providers(key)[0] == "navbar_gallery"
	assert "navigation" in prefer_categories_from_providers(["navbar_gallery"])


@pytest.mark.asyncio
async def test_filter_valid_previews_fail_open() -> None:
	from navigation.inspiration_intelligence.preview_validate import filter_valid_previews
	from navigation.inspiration_intelligence.web_inspire import WebInspireHit

	hits = [
		WebInspireHit(
			provider_id="web_search",
			candidate_id="1",
			title="x",
			url="https://example.com",
			preview_url="https://this-host-definitely-does-not-exist-xyz.invalid/a.png",
		)
	]
	with patch(
		"navigation.inspiration_intelligence.preview_validate._head_ok",
		return_value=(False, "fail"),
	):
		kept, deg = await filter_valid_previews(hits)
	assert kept == []  # filter drops; web_inspire fail-opens above this
	assert any("dropped" in d for d in deg)
