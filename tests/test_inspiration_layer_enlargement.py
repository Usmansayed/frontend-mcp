"""Inspiration layer enlargement — planner, concurrency, reuse."""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_source_planner_landing_fast() -> None:
	from navigation.inspiration_intelligence.planning.source_planner import (
		InspirationMode,
		build_source_plan,
		classify_intent_class,
	)

	assert classify_intent_class("SaaS marketing landing page") == "landing"
	plan = build_source_plan("SaaS marketing landing page", mode="fast")
	assert plan.mode == InspirationMode.FAST
	assert plan.intent_class == "landing"
	assert "gallery_image" in plan.channels
	assert "onepagelove" in plan.provider_ids
	assert "dribbble" not in plan.provider_ids
	assert plan.max_famous_sites == 2
	assert "marketing" in plan.famous_categories


def test_source_planner_dashboard_deep_includes_browser() -> None:
	from navigation.inspiration_intelligence.planning.source_planner import build_source_plan

	plan = build_source_plan("dense analytics dashboard", mode="deep")
	assert plan.intent_class == "dashboard"
	assert "dribbble" in plan.provider_ids or "awwwards" in plan.provider_ids
	# Deep caps to one browser-heavy gallery (time-box); HTTP stays first.
	from navigation.inspiration_intelligence.concurrent import BROWSER_HEAVY_PROVIDERS

	assert sum(1 for p in plan.provider_ids if p in BROWSER_HEAVY_PROVIDERS) <= 1
	assert plan.provider_ids[0] not in BROWSER_HEAVY_PROVIDERS
	assert plan.browser_concurrency >= 1


def test_source_planner_broad_excludes_waf_browsers() -> None:
	from navigation.inspiration_intelligence.concurrent import BROWSER_HEAVY_PROVIDERS
	from navigation.inspiration_intelligence.planning.source_planner import build_source_plan

	plan = build_source_plan("fintech dashboard dark", mode="broad")
	assert not any(p in BROWSER_HEAVY_PROVIDERS for p in plan.provider_ids)
	assert "behance" in plan.provider_ids or "onepagelove" in plan.provider_ids


def test_split_provider_tiers() -> None:
	from navigation.inspiration_intelligence.concurrent import split_provider_tiers

	http, browser = split_provider_tiers(
		["onepagelove", "dribbble", "behance", "awwwards", "lapa"]
	)
	assert http == ["onepagelove", "behance", "lapa"]
	assert browser == ["dribbble", "awwwards"]


def test_famous_sites_select() -> None:
	from navigation.inspiration_intelligence.famous_sites import (
		famous_site_hit_sketch,
		select_famous_sites,
	)

	sites = select_famous_sites(["marketing"], max_sites=2)
	assert len(sites) == 2
	assert sites[0]["source_kind"] == "live_site"
	assert sites[0]["url"].startswith("http")
	hit = famous_site_hit_sketch(sites[0], screenshot_blob="blob://x")
	assert hit["source_kind"] == "live_site"
	assert hit["provider_id"] == "famous_site"


def test_scout_cache_roundtrip() -> None:
	from navigation.inspiration_intelligence.scout_cache import (
		clear_scout_cache,
		consume_discover_token,
		mint_discover_token,
	)

	clear_scout_cache()
	token = mint_discover_token(
		query="saas landing",
		candidates=[{"preview_url": "https://cdn.example.com/a.jpg", "title": "A"}],
	)
	row = consume_discover_token(token)
	assert row is not None
	assert row["query"] == "saas landing"
	assert len(row["candidates"]) == 1


@pytest.mark.asyncio
async def test_concurrent_wave_faster_than_serial() -> None:
	from navigation.inspiration_intelligence.discovery.concurrent_wave import (
		discover_providers_concurrent,
	)
	from navigation.inspiration_intelligence.models import (
		CommunitySearchPlan,
		InspirationCandidate,
		InspirationIntent,
		InspirationIntentKind,
		InspirationSearchPlan,
	)

	async def slow_discover(pid: str, delay: float):
		await asyncio.sleep(delay)
		cands = [
			InspirationCandidate(
				candidate_id=f"{pid}:1",
				title=pid,
				source=pid,
				provider_id=pid,
				external_id="1",
				url=f"https://example.com/{pid}",
				preview_ref=f"https://cdn.example.com/{pid}.jpg",
			)
		]
		return cands, []

	providers = {}
	for name in ("onepagelove", "lapa", "behance"):
		p = MagicMock()

		async def _discover(*_a, _n=name, **_k):
			return await slow_discover(_n, 0.15)

		p.discover_candidates = AsyncMock(side_effect=_discover)
		providers[name] = p

	registry = MagicMock()
	registry.get = MagicMock(side_effect=lambda pid: providers.get(pid))

	intent = InspirationIntent(kind=InspirationIntentKind.INSPIRE, raw_query="saas")
	plan = InspirationSearchPlan(seed_query="saas", provider_ids=list(providers))
	community = CommunitySearchPlan(seed_query="saas")

	t0 = time.perf_counter()
	results, traces, searched = await discover_providers_concurrent(
		registry,
		list(providers),
		search_plan=plan,
		community_plan=community,
		intent=intent,
		max_results=4,
		http_concurrency=5,
	)
	elapsed = time.perf_counter() - t0

	assert len(results) == 3
	assert set(searched) == set(providers)
	# Parallel: should be well under serial 0.45s
	assert elapsed < 0.40, f"expected parallel wall time, got {elapsed:.3f}s"
	assert all(t.get("tier") == "http" for t in traces if t.get("provider_id") in providers)


@pytest.mark.asyncio
async def test_collect_reuses_candidate_urls_without_providers() -> None:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits

	urls = [
		{
			"preview_url": f"https://cdn.example.com/reuse/{i}.jpg",
			"url": f"https://gallery.example.com/{i}",
			"title": f"Hit {i}",
			"provider_id": "reuse",
			"candidate_id": f"reuse:{i}",
		}
		for i in range(5)
	]

	with patch(
		"navigation.inspiration_intelligence.collect.InspirationProviderRegistry"
	) as reg_cls:
		reg_cls.return_value.get.return_value = None
		with patch("navigation.inspiration_intelligence.collect.InspirationBlobStore") as blob_cls:
			blob_cls.return_value.create_session.return_value = "insp_reuse"
			blob_cls.return_value.materialize_hits_async = AsyncMock(
				return_value={"materialized": 0}
			)
			manifest = await collect_inspiration_hits(
				"saas landing",
				provider_ids=["behance"],
				candidate_urls=urls,
				materialize_blobs=True,
				target_refs=5,
				min_refs=3,
				include_web_search=False,
				use_multi_scout=False,
			)

	assert manifest["reuse_mode"] == "candidate_urls"
	assert manifest["total_hits"] >= 3
	assert any(h.get("fetch_tier") == "reuse" for h in manifest["hits"])
	# Soft-stop may or may not fire after reuse depending on relevance scoring
	assert manifest.get("ref_policy") == "soft_stop_only_no_hard_cap"


@pytest.mark.asyncio
async def test_collect_concurrent_http_emits_timing() -> None:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits
	from navigation.inspiration_intelligence.models import (
		InspirationCandidate,
		InspirationCaptureResult,
	)

	async def make_cands(n: int, pid: str):
		return [
			InspirationCandidate(
				candidate_id=f"{pid}:{i}",
				title=f"SaaS analytics dashboard {pid} {i}",
				source=pid,
				provider_id=pid,
				external_id=str(i),
				url=f"https://example.com/{pid}/{i}",
				preview_ref=f"https://cdn.example.com/{pid}/{i}.jpg",
				metadata={"fetch_tier": "http"},
				discovery_score=0.9,
			)
			for i in range(n)
		]

	async def fake_capture(candidate, *, intent, allow_browser_screenshot=False):
		_ = intent, allow_browser_screenshot
		return InspirationCaptureResult(
			candidate_id=candidate.candidate_id,
			provider_id=candidate.provider_id,
			screenshot_refs=[candidate.preview_ref],
			degraded=["capture_tier:discovery_preview"],
		)

	providers = {}
	for pid in ("onepagelove", "lapa", "behance"):
		p = MagicMock()
		p.discover_candidates = AsyncMock(return_value=(await make_cands(4, pid), []))
		p.capture_design = fake_capture
		providers[pid] = p

	registry = MagicMock()
	registry.get = MagicMock(side_effect=lambda pid: providers.get(pid))

	with patch(
		"navigation.inspiration_intelligence.collect.InspirationProviderRegistry",
		return_value=registry,
	):
		with patch("navigation.inspiration_intelligence.collect.InspirationBlobStore") as blob_cls:
			blob_cls.return_value.create_session.return_value = "insp_t"
			blob_cls.return_value.materialize_hits_async = AsyncMock(
				return_value={"materialized": 0}
			)
			manifest = await collect_inspiration_hits(
				"saas analytics dashboard",
				provider_ids=["onepagelove", "lapa", "behance"],
				materialize_blobs=True,
				target_refs=5,
				min_refs=3,
				mode="fast",
				include_web_search=False,
				use_multi_scout=False,
			)

	assert manifest["mode"].startswith("image_first")
	assert "collect_ms" in manifest
	assert isinstance(manifest.get("provider_ms"), list)
	assert manifest.get("ref_policy") == "soft_stop_only_no_hard_cap"
	assert manifest["total_hits"] >= 3
	assert manifest["stopped_early"] is True
