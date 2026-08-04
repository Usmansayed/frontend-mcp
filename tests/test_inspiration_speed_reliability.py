"""Speed/reliability upgrades — cache, circuit, fast provider set."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_fast_http_excludes_siteinspire() -> None:
	from navigation.inspiration_intelligence.planning.progressive_search import (
		FAST_HTTP_PROVIDER_ORDER,
	)

	assert "siteinspire" not in FAST_HTTP_PROVIDER_ORDER
	assert "onepagelove" in FAST_HTTP_PROVIDER_ORDER
	assert "httpster" in FAST_HTTP_PROVIDER_ORDER


def test_circuit_opens_after_failures() -> None:
	from navigation.inspiration_intelligence.circuit import (
		clear_circuits,
		filter_open_circuits,
		is_open,
		record_failure,
	)

	clear_circuits()
	assert not is_open("behance")
	record_failure("behance")
	assert not is_open("behance")  # threshold 2
	record_failure("behance")
	assert is_open("behance")
	eligible, skipped = filter_open_circuits(["onepagelove", "behance", "lapa"])
	assert "behance" in skipped
	assert "onepagelove" in eligible
	clear_circuits()


def test_result_cache_roundtrip() -> None:
	from navigation.inspiration_intelligence.result_cache import (
		clear_result_cache,
		fingerprint,
		get_cached_hits,
		put_cached_hits,
	)

	clear_result_cache()
	fp = fingerprint("saas landing", mode="fast", provider_ids=["onepagelove"])
	assert get_cached_hits(fp) is None
	put_cached_hits(
		fp,
		[{"preview_url": "https://cdn.example.com/a.jpg", "title": "A", "candidate_id": "a"}],
	)
	hit = get_cached_hits(fp)
	assert hit is not None
	assert hit[0]["preview_url"].startswith("http")


@pytest.mark.asyncio
async def test_collect_second_call_uses_result_cache() -> None:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits
	from navigation.inspiration_intelligence.models import (
		InspirationCandidate,
		InspirationCaptureResult,
	)
	from navigation.inspiration_intelligence.result_cache import clear_result_cache

	clear_result_cache()

	candidates = [
		InspirationCandidate(
			candidate_id=f"opl:{i}",
			title=f"Hit {i}",
			source="onepagelove",
			provider_id="onepagelove",
			external_id=str(i),
			url=f"https://onepagelove.com/{i}",
			preview_ref=f"https://cdn.example.com/{i}.jpg",
			metadata={"fetch_tier": "http"},
			discovery_score=0.9,
		)
		for i in range(5)
	]

	async def fake_capture(candidate, *, intent, allow_browser_screenshot=False):
		_ = intent, allow_browser_screenshot
		return InspirationCaptureResult(
			candidate_id=candidate.candidate_id,
			provider_id=candidate.provider_id,
			screenshot_refs=[candidate.preview_ref],
			degraded=[],
		)

	discover_calls = {"n": 0}

	async def fake_discover(*_a, **_k):
		discover_calls["n"] += 1
		return candidates, []

	provider = MagicMock()
	provider.discover_candidates = AsyncMock(side_effect=fake_discover)
	provider.capture_design = fake_capture
	registry = MagicMock()
	registry.get = MagicMock(return_value=provider)

	with patch(
		"navigation.inspiration_intelligence.collect.InspirationProviderRegistry",
		return_value=registry,
	):
		with patch("navigation.inspiration_intelligence.collect.InspirationBlobStore") as blob_cls:
			blob_cls.return_value.create_session.return_value = "insp_c"
			blob_cls.return_value.materialize_hits_async = AsyncMock(
				return_value={"materialized": 0}
			)
			m1 = await collect_inspiration_hits(
				"saas landing page unique-cache-key",
				provider_ids=["onepagelove"],
				mode="fast",
				include_live_sites=False,
				include_web_search=False,
				use_multi_scout=False,
				materialize_blobs=True,
				target_refs=5,
				min_refs=3,
			)
			m2 = await collect_inspiration_hits(
				"saas landing page unique-cache-key",
				provider_ids=["onepagelove"],
				mode="fast",
				include_live_sites=False,
				include_web_search=False,
				use_multi_scout=False,
				materialize_blobs=True,
				target_refs=5,
				min_refs=3,
			)

	assert m1["cache_hit"] is False
	assert m2["cache_hit"] is True
	assert m2["reuse_mode"] == "result_cache"
	# First collect may run progressive query waves (≤2 for standard); second must not rediscover
	assert discover_calls["n"] <= 2
	assert m2["total_hits"] >= 3
	assert m2.get("stop_reason") == "result_cache"
