"""Pattern inspiration — component/section specialist galleries + daisy CDN."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_daisy_slug_resolve() -> None:
	from navigation.inspiration_intelligence.pattern_acquire import resolve_daisy_slugs

	assert "navbar" in resolve_daisy_slugs("navbar with mega menu")
	assert "modal" in resolve_daisy_slugs("modal dialog confirmation")
	assert "button" in resolve_daisy_slugs("primary button hover")


def test_specialist_targets_navbar_footer() -> None:
	from navigation.inspiration_intelligence.pattern_acquire import (
		load_pattern_sources,
		select_specialist_targets,
	)

	load_pattern_sources.cache_clear()
	nav = select_specialist_targets("navbar with mega menu")
	assert any(g["id"] == "navbar_gallery" for g in nav)
	foot = select_specialist_targets("site footer links")
	assert any(g["id"] == "footer_design" for g in foot)
	assert select_specialist_targets("random unrelated widget xyz") == []
	pricing = select_specialist_targets("pricing section cards")
	assert any(g["id"] == "saasframe" for g in pricing)
	sidebar = select_specialist_targets("dashboard sidebar navigation")
	assert any(g["id"] == "saasinterface" for g in sidebar)
	saas = select_specialist_targets("saas landing page")
	assert any(g["id"] in {"saasframe", "saaslandingpage"} for g in saas)


def test_font_query_routes() -> None:
	from navigation.inspiration_intelligence.pattern_acquire import is_font_query

	assert is_font_query("expressive serif display font")
	assert not is_font_query("navbar mega menu")


def test_extract_webflow_previews() -> None:
	from navigation.inspiration_intelligence.pattern_acquire import extract_pattern_previews

	html = '''
	<img src="https://cdn.prod.website-files.com/abc/def/Screenshot%20nav.webp"/>
	<img src="https://cdn.prod.website-files.com/abc/def/open-graph.webp"/>
	<img src="https://cdn.prod.website-files.com/abc/def/Frame%201.webp"/>
	'''
	previews = extract_pattern_previews(html, extract="webflow_cdn", limit=5)
	assert len(previews) >= 2
	assert all("open-graph" not in p for p in previews)


@pytest.mark.asyncio
async def test_acquire_pattern_uses_daisy_without_network_for_slug() -> None:
	from navigation.inspiration_intelligence.pattern_acquire import acquire_pattern_inspiration

	# Patch gallery fetch empty so only daisy CDN hits remain
	with patch(
		"navigation.inspiration_intelligence.pattern_acquire._fetch_gallery",
		new_callable=AsyncMock,
		return_value=([], 1.0, None),
	):
		result = await acquire_pattern_inspiration("primary button hover", max_visuals=4)
	assert result.hits
	assert result.hits[0].provider_id == "daisyui"
	assert "button" in result.hits[0].preview_url
	assert result.hits[0].fetch_tier == "direct_cdn"


@pytest.mark.asyncio
async def test_collect_navbar_prefers_pattern_hits() -> None:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits
	from navigation.inspiration_intelligence.pattern_acquire import PatternAcquireResult, PatternHit

	async def fake_pattern(query: str, **kwargs):
		_ = query, kwargs
		return PatternAcquireResult(
			query=query,
			scope="component",
			elapsed_ms=12.0,
			hits=[
				PatternHit(
					provider_id="navbar_gallery",
					candidate_id="pattern:navbar_gallery:0",
					title="Navbar Gallery #1",
					url="https://www.navbar.gallery/",
					preview_url="https://cdn.prod.website-files.com/x/y/nav1.webp",
				),
				PatternHit(
					provider_id="daisyui",
					candidate_id="pattern:daisyui:navbar",
					title="daisyUI navbar",
					url="https://daisyui.com/components/navbar/",
					preview_url="https://img.daisyui.com/images/components/navbar.webp",
					fetch_tier="direct_cdn",
				),
			],
			targets=["navbar_gallery", "daisyui:navbar"],
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
			with patch("navigation.inspiration_intelligence.collect.InspirationBlobStore") as blob_cls:
				blob_cls.return_value.create_session.return_value = "insp_p"
				blob_cls.return_value.materialize_hits_async = AsyncMock(
					return_value={"materialized": 0}
				)
				manifest = await collect_inspiration_hits(
					"navbar with mega menu",
					inspiration_level="standard",
					include_live_sites=False,
					include_web_search=False,
					materialize_blobs=False,
					use_result_cache=False,
					write_per_hit_files=False,
					use_multi_scout=False,
				)

	assert manifest["total_hits"] >= 2
	assert any(h.get("provider_id") == "navbar_gallery" for h in manifest["hits"])
	assert manifest.get("pattern", {}).get("targets")
