"""Multi-source scout → rank → acquire tests."""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_score_probe_prefers_token_and_images() -> None:
	from navigation.inspiration_intelligence.multi_scout import score_probe

	html = "<html><title>SaaS landing page</title>" + (
		'<img src="https://cdn.example.com/a.jpg"/>' * 4
	)
	score, reason = score_probe(
		query="saas landing page",
		source={"id": "x", "title": "Gallery", "tier": "fast_http"},
		category="landing_gallery",
		category_hints=["landing", "saas"],
		html=html,
		status=200,
		preview_urls=["https://cdn.example.com/a.jpg"] * 4,
	)
	assert score >= 0.4
	assert "tokens" in reason or "hints" in reason


@pytest.mark.asyncio
async def test_scout_rank_concurrent_faster_than_serial() -> None:
	from navigation.inspiration_intelligence.multi_scout import scout_rank_sources

	async def slow_probe(url: str, timeout: float):
		_ = timeout
		await asyncio.sleep(0.08)
		# Put query tokens in body so score > 0
		body = f"<html>saas landing page hero <img src='https://cdn.example.com/{hash(url) % 99}.jpg'/></html>"
		return body, 200, None

	t0 = time.perf_counter()
	result = await scout_rank_sources(
		"saas landing page",
		mode="broad",
		max_sources=8,
		concurrency=8,
		timeout_s=2.0,
		top_n=3,
		min_score=0.05,
		probe_fn=slow_probe,
		early_cancel=False,
	)
	elapsed = time.perf_counter() - t0

	assert result.probed == 8
	assert result.winners
	# Serial would be ~0.64s; parallel should be well under
	assert elapsed < 0.35, f"expected concurrent scout, got {elapsed:.3f}s"
	assert result.scout_ms < 350


@pytest.mark.asyncio
async def test_acquire_uses_preview_urls_from_winners() -> None:
	from navigation.inspiration_intelligence.multi_scout import ScoutHit, acquire_from_winners

	winners = [
		ScoutHit(
			source_id="onepagelove",
			title="OPL",
			url="https://onepagelove.com",
			category="landing_gallery",
			tier="fast_http",
			score=0.8,
			preview_urls=[
				"https://cdn.example.com/1.jpg",
				"https://cdn.example.com/2.jpg",
			],
			probe_url="https://onepagelove.com",
			ok=True,
			reason="test",
		)
	]
	acquired, deg, _timing = await acquire_from_winners(
		winners, max_visuals=5, allow_screenshots=False
	)
	assert len(acquired) == 2
	assert acquired[0]["preview_url"].startswith("http")
	assert acquired[0]["fetch_tier"] == "multi_scout"


@pytest.mark.asyncio
async def test_collect_merges_multi_scout_when_gallery_empty() -> None:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits
	from navigation.inspiration_intelligence.multi_scout import MultiScoutResult, ScoutHit

	async def fake_multi(query: str):
		_ = query
		return MultiScoutResult(
			query=query,
			scout_ms=12.0,
			probed=5,
			winners=[
				ScoutHit(
					source_id="landing_love",
					title="Landing Love",
					url="https://www.landing.love",
					category="landing_gallery",
					tier="browser_gallery",
					score=0.7,
					preview_urls=["https://cdn.example.com/ll1.jpg", "https://cdn.example.com/ll2.jpg"],
					ok=True,
				)
			],
			acquired=[
				{
					"source_kind": "gallery_image",
					"provider_id": "landing_love",
					"candidate_id": "multi:landing_love:0",
					"title": "LL 1",
					"url": "https://www.landing.love",
					"preview_url": "https://cdn.example.com/ll1.jpg",
					"agent_view_url": "https://cdn.example.com/ll1.jpg",
					"fetch_tier": "multi_scout",
					"degraded": [],
				},
				{
					"source_kind": "gallery_image",
					"provider_id": "landing_love",
					"candidate_id": "multi:landing_love:1",
					"title": "LL 2",
					"url": "https://www.landing.love",
					"preview_url": "https://cdn.example.com/ll2.jpg",
					"agent_view_url": "https://cdn.example.com/ll2.jpg",
					"fetch_tier": "multi_scout",
					"degraded": [],
				},
				{
					"source_kind": "gallery_image",
					"provider_id": "landing_love",
					"candidate_id": "multi:landing_love:2",
					"title": "LL 3",
					"url": "https://www.landing.love",
					"preview_url": "https://cdn.example.com/ll3.jpg",
					"agent_view_url": "https://cdn.example.com/ll3.jpg",
					"fetch_tier": "multi_scout",
					"degraded": [],
				},
			],
		)

	# Empty gallery providers
	registry = type("R", (), {"get": lambda self, pid: None})()

	with patch(
		"navigation.inspiration_intelligence.collect.InspirationProviderRegistry",
		return_value=registry,
	):
		with patch("navigation.inspiration_intelligence.collect.InspirationBlobStore") as blob_cls:
			blob_cls.return_value.create_session.return_value = "insp_ms"
			blob_cls.return_value.materialize_hits_async = AsyncMock(
				return_value={"materialized": 0}
			)
			manifest = await collect_inspiration_hits(
				"saas landing page",
				provider_ids=["onepagelove"],
				mode="broad",
				use_multi_scout=True,
				multi_scout_fn=fake_multi,
				include_live_sites=False,
				materialize_blobs=True,
				target_refs=5,
				min_refs=3,
				use_result_cache=False,
			)

	assert manifest["total_hits"] >= 3
	assert manifest.get("multi_scout", {}).get("probed") == 5
	assert any(h.get("fetch_tier") == "multi_scout" for h in manifest["hits"])
