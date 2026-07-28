"""Inspiration effort levels — agent picks; MCP executes budgets."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_resolve_levels_and_aliases() -> None:
	from navigation.inspiration_intelligence.levels import (
		INSPIRATION_LEVELS,
		levels_card,
		resolve_inspiration_level,
	)

	assert INSPIRATION_LEVELS == ("light", "standard", "wide", "max")
	assert resolve_inspiration_level("light").use_multi_scout is False
	assert resolve_inspiration_level("standard").use_multi_scout is True
	assert resolve_inspiration_level("wide").max_sources >= 12
	assert resolve_inspiration_level("max").include_live_sites is True
	assert resolve_inspiration_level("fast").level == "light"
	assert resolve_inspiration_level("broad").level == "wide"
	assert resolve_inspiration_level(None, mode="deep").level == "max"
	assert resolve_inspiration_level(None, mode="fast").level == "standard"
	# Levels are search effort — soft_stop grows with level; not a tiny hard quota
	assert resolve_inspiration_level("standard").soft_stop_refs >= 8
	assert resolve_inspiration_level("wide").soft_stop_refs >= 12
	card = levels_card()
	assert card["resource"] == "perception://guide/inspiration"
	assert "not a hard ref quota" in card["rule"]
	assert len(card["levels"]) == 4


def test_wide_excludes_browser_galleries_and_sets_deadline() -> None:
	from navigation.inspiration_intelligence.concurrent import BROWSER_HEAVY_PROVIDERS
	from navigation.inspiration_intelligence.levels import resolve_inspiration_level

	wide = resolve_inspiration_level("wide")
	assert wide.include_browser_galleries is False
	assert wide.overlap_scout is True
	assert wide.hard_deadline_s >= wide.budget_s
	max_plan = resolve_inspiration_level("max")
	assert max_plan.include_browser_galleries is True


@pytest.mark.asyncio
async def test_collect_wide_does_not_order_dribbble() -> None:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits
	from navigation.inspiration_intelligence.concurrent import BROWSER_HEAVY_PROVIDERS

	registry = type("R", (), {"get": lambda self, pid: None})()
	with patch(
		"navigation.inspiration_intelligence.collect.InspirationProviderRegistry",
		return_value=registry,
	):
		with patch("navigation.inspiration_intelligence.collect.InspirationBlobStore") as blob_cls:
			blob_cls.return_value.create_session.return_value = "insp_w"
			blob_cls.return_value.materialize_hits_async = AsyncMock(
				return_value={"materialized": 0}
			)
			with patch(
				"navigation.inspiration_intelligence.collect.multi_source_inspire",
				new_callable=AsyncMock,
			) as ms:
				from navigation.inspiration_intelligence.multi_scout import MultiScoutResult

				ms.return_value = MultiScoutResult(query="x", scout_ms=1, probed=0, acquired=[])
				manifest = await collect_inspiration_hits(
					"fintech dashboard dark",
					inspiration_level="wide",
					include_live_sites=False,
					include_web_search=False,
					max_web_screenshots=0,
					materialize_blobs=False,
					use_result_cache=False,
					write_per_hit_files=False,
				)

	assert not any(p in BROWSER_HEAVY_PROVIDERS for p in manifest["providers"])
	assert "dribbble" not in manifest["providers"]


@pytest.mark.asyncio
async def test_light_skips_multi_scout() -> None:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits

	called = {"n": 0}

	async def fake_multi(query: str):
		called["n"] += 1
		raise AssertionError("light must not multi-scout")

	registry = type("R", (), {"get": lambda self, pid: None})()
	with patch(
		"navigation.inspiration_intelligence.collect.InspirationProviderRegistry",
		return_value=registry,
	):
		with patch("navigation.inspiration_intelligence.collect.InspirationBlobStore") as blob_cls:
			blob_cls.return_value.create_session.return_value = "insp_light"
			blob_cls.return_value.materialize_hits_async = AsyncMock(
				return_value={"materialized": 0}
			)
			manifest = await collect_inspiration_hits(
				"saas landing",
				provider_ids=["onepagelove"],
				inspiration_level="light",
				multi_scout_fn=fake_multi,
				include_live_sites=False,
				include_web_search=False,
				materialize_blobs=False,
				use_result_cache=False,
				write_per_hit_files=False,
			)

	assert called["n"] == 0
	assert manifest["inspiration_level"] == "light"
	assert manifest["inspiration_level_plan"]["use_multi_scout"] is False


@pytest.mark.asyncio
async def test_wide_passes_level_budgets_to_multi_scout() -> None:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits
	from navigation.inspiration_intelligence.multi_scout import MultiScoutResult

	seen: dict = {}

	async def capture_multi(query: str, **kwargs):
		seen.update(kwargs)
		seen["query"] = query
		return MultiScoutResult(query=query, scout_ms=1.0, probed=0, acquired=[])

	registry = type("R", (), {"get": lambda self, pid: None})()
	with patch(
		"navigation.inspiration_intelligence.collect.InspirationProviderRegistry",
		return_value=registry,
	):
		with patch(
			"navigation.inspiration_intelligence.collect.multi_source_inspire",
			side_effect=capture_multi,
		):
			with patch(
				"navigation.inspiration_intelligence.collect.multi_source_inspire_parallel",
				side_effect=capture_multi,
			):
				with patch("navigation.inspiration_intelligence.collect.InspirationBlobStore") as blob_cls:
					blob_cls.return_value.create_session.return_value = "insp_wide"
					blob_cls.return_value.materialize_hits_async = AsyncMock(
						return_value={"materialized": 0}
					)
					manifest = await collect_inspiration_hits(
						"saas landing page",
						provider_ids=["onepagelove"],
						inspiration_level="wide",
						include_live_sites=False,
						include_web_search=False,
						max_web_screenshots=0,
						materialize_blobs=False,
						use_result_cache=False,
						write_per_hit_files=False,
						min_refs=3,
						target_refs=5,
					)

	assert manifest["inspiration_level"] == "wide"
	assert seen.get("max_sources") == 14
	assert seen.get("concurrency") == 12
	assert seen.get("early_cancel") is True
	assert manifest.get("ref_policy") == "soft_stop_only_no_hard_cap"


@pytest.mark.asyncio
async def test_scout_early_cancel_stops_after_strong_winners() -> None:
	from navigation.inspiration_intelligence.multi_scout import scout_rank_sources

	started = 0
	lock = asyncio.Lock()

	async def slow_probe(url: str, timeout: float):
		nonlocal started
		_ = timeout
		async with lock:
			started += 1
		await asyncio.sleep(0.05)
		body = (
			"<html>saas landing page "
			"<img src='https://cdn.example.com/a.jpg'/>"
			"<img src='https://cdn.example.com/b.jpg'/>"
			"</html>"
		)
		return body, 200, None

	result = await scout_rank_sources(
		"saas landing page",
		mode="broad",
		max_sources=10,
		concurrency=10,
		timeout_s=2.0,
		top_n=2,
		min_score=0.05,
		probe_fn=slow_probe,
		early_cancel=True,
	)
	assert result.winners
	assert any("early_cancel" in d for d in result.degraded)
	# Should not wait for all 10 to finish ranking work
	assert result.probed <= 10
	assert result.probed >= 2


def test_guide_inspiration_resource_registered() -> None:
	from navigation.mcp.resources import list_resources, read_resource

	uris = {r["uri"] for r in list_resources()}
	assert "perception://guide/inspiration" in uris
	mime, text, is_blob = read_resource("perception://guide/inspiration")
	assert mime == "text/markdown"
	assert is_blob is False
	assert "inspiration_level" in text
	assert "light" in text and "max" in text
