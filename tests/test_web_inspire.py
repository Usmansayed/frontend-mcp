"""Web search + visual inspiration (DuckDuckGo → OG → screenshots)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


_DDG_HTML = """
<html><body>
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.navbar.gallery%2Ftype%2Fmega-menu">Mega Menu Gallery</a>
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fdribbble.com%2Ftags%2Fmega-menu">Dribbble mega menu</a>
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwebflow.com%2Fblog%2Fmega-menu-examples">Webflow examples</a>
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fduckduckgo.com%2Fy.js%3Fad=1">Ad skip</a>
</body></html>
"""


def test_parse_duckduckgo_html_organic_only() -> None:
	from navigation.inspiration_intelligence.web_search import parse_duckduckgo_html

	hits = parse_duckduckgo_html(_DDG_HTML)
	assert len(hits) >= 3
	hosts = {h.host for h in hits}
	assert "www.navbar.gallery" in hosts
	assert "dribbble.com" in hosts
	assert not any("duckduckgo" in h.host for h in hits)


def test_craft_search_query_biases_examples() -> None:
	from navigation.inspiration_intelligence.web_search import craft_inspiration_search_query

	q = craft_inspiration_search_query("modal dialog", scope="component")
	assert "modal" in q.lower()
	assert "example" in q.lower() or "design" in q.lower()


def test_should_run_web_when_thin() -> None:
	from navigation.inspiration_intelligence.web_inspire import should_run_web_inspire

	assert should_run_web_inspire(
		level="standard",
		hit_count=1,
		soft_stop_refs=8,
		include_web_search=True,
		font_routed=False,
	)
	assert not should_run_web_inspire(
		level="standard",
		hit_count=8,
		soft_stop_refs=8,
		include_web_search=True,
		font_routed=False,
	)
	assert not should_run_web_inspire(
		level="standard",
		hit_count=0,
		soft_stop_refs=8,
		include_web_search=True,
		font_routed=True,
	)


@pytest.mark.asyncio
async def test_acquire_web_inspiration_og_wave() -> None:
	from navigation.inspiration_intelligence.web_inspire import acquire_web_inspiration
	from navigation.inspiration_intelligence.web_search import WebSearchHit, WebSearchResult

	fake_search = WebSearchResult(
		query="q",
		engine="duckduckgo_html",
		elapsed_ms=12.0,
		hits=[
			WebSearchHit(title="A", url="https://example.com/a", host="example.com", rank=0, score=10),
			WebSearchHit(title="B", url="https://other.test/b", host="other.test", rank=1, score=9),
		],
	)

	async def fake_og(url: str, *, timeout_s: float):
		_ = timeout_s
		return f"https://cdn.example/og/{urlparse_host(url)}.png", 5.0, None

	def urlparse_host(url: str) -> str:
		from urllib.parse import urlparse

		return urlparse(url).netloc.replace(".", "_")

	with patch(
		"navigation.inspiration_intelligence.web_inspire.search_web",
		return_value=fake_search,
	):
		with patch(
			"navigation.inspiration_intelligence.web_inspire._og_for_url",
			side_effect=fake_og,
		):
			result = await acquire_web_inspiration(
				"modal dialog",
				scope="component",
				max_search=4,
				max_og=4,
				max_screenshots=0,
			)

	assert result.og_hits >= 2
	assert len(result.hits) >= 2
	assert all(h.fetch_tier == "web_og" for h in result.hits)


@pytest.mark.asyncio
async def test_collect_merges_web_hits_when_pattern_thin() -> None:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits
	from navigation.inspiration_intelligence.pattern_acquire import PatternAcquireResult, PatternHit
	from navigation.inspiration_intelligence.web_inspire import WebInspireHit, WebInspireResult

	async def fake_pattern(query: str, **kwargs):
		_ = kwargs
		return PatternAcquireResult(
			query=query,
			scope="chrome",
			elapsed_ms=1.0,
			hits=[
				PatternHit(
					provider_id="daisyui",
					candidate_id="pattern:daisyui:button",
					title="daisyUI button",
					url="https://daisyui.com/components/button/",
					preview_url="https://img.daisyui.com/images/components/button.webp",
					fetch_tier="direct_cdn",
					source_kind="pattern_cdn",
				)
			],
			targets=["daisyui:button"],
		)

	async def fake_web(query: str, **kwargs):
		_ = query, kwargs
		return WebInspireResult(
			query=query,
			search_query="primary button ui design examples",
			elapsed_ms=20.0,
			hits=[
				WebInspireHit(
					provider_id="web_search",
					candidate_id="web_og:dribbble.com:0",
					title="Button shots",
					url="https://dribbble.com/tags/button",
					preview_url="https://cdn.dribbble.com/og.png",
				),
				WebInspireHit(
					provider_id="web_search",
					candidate_id="web_og:behance.net:1",
					title="UI buttons",
					url="https://www.behance.net/search/projects?search=button",
					preview_url="https://mir-s3-cdn-cf.behance.net/og.jpg",
				),
				WebInspireHit(
					provider_id="web_live",
					candidate_id="web_live:ui.shadcn.com:0",
					title="shadcn",
					url="https://ui.shadcn.com",
					preview_url="file:///tmp/ss.png",
					screenshot_path="/tmp/ss.png",
					fetch_tier="web_live_screenshot",
					source_kind="web_live",
				),
			],
			search_hits=5,
			og_hits=2,
			screenshot_hits=1,
		)

	registry = type("R", (), {"get": lambda self, pid: None})()
	with patch(
		"navigation.inspiration_intelligence.collect.InspirationProviderRegistry",
		return_value=registry,
	):
		with patch(
			"navigation.inspiration_intelligence.collect.acquire_pattern_inspiration",
			side_effect=fake_pattern,
		):
			with patch(
				"navigation.inspiration_intelligence.collect.acquire_web_inspiration",
				side_effect=fake_web,
			):
				with patch("navigation.inspiration_intelligence.collect.InspirationBlobStore") as blob_cls:
					blob_cls.return_value.create_session.return_value = "insp_w"
					blob_cls.return_value.materialize_hits_async = AsyncMock(
						return_value={"materialized": 0}
					)
					manifest = await collect_inspiration_hits(
						"primary button",
						inspiration_level="standard",
						include_live_sites=False,
						include_web_search=True,
						materialize_blobs=False,
						use_result_cache=False,
						write_per_hit_files=False,
						use_multi_scout=False,
					)

	assert manifest["total_hits"] >= 4
	providers = {h.get("provider_id") for h in manifest["hits"]}
	assert "daisyui" in providers
	assert "web_search" in providers
	assert manifest.get("web_inspire", {}).get("og_hits", 0) >= 2


def test_daisy_companions_expand_pack() -> None:
	from navigation.inspiration_intelligence.pattern_acquire import resolve_daisy_slugs

	slugs = resolve_daisy_slugs("primary button")
	assert "button" in slugs
	assert len(slugs) >= 3
