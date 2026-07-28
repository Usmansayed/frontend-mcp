"""Live-site channel + blob pool + perf budget tests."""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_should_run_live_sites_policy() -> None:
	from navigation.inspiration_intelligence.live_capture import should_run_live_sites

	# Fast + enough gallery → skip
	assert (
		should_run_live_sites(
			mode="fast",
			channels=["gallery_image", "live_site"],
			max_famous_sites=2,
			gallery_ref_count=3,
			min_refs=3,
			include_live_sites=None,
		)
		is False
	)
	# Fast + under-delivered → fill gap
	assert (
		should_run_live_sites(
			mode="fast",
			channels=["gallery_image", "live_site"],
			max_famous_sites=2,
			gallery_ref_count=1,
			min_refs=3,
			include_live_sites=None,
		)
		is True
	)
	# Broad always
	assert (
		should_run_live_sites(
			mode="broad",
			channels=["gallery_image", "live_site"],
			max_famous_sites=4,
			gallery_ref_count=5,
			min_refs=3,
			include_live_sites=None,
		)
		is True
	)
	# Explicit off
	assert (
		should_run_live_sites(
			mode="broad",
			channels=["gallery_image", "live_site"],
			max_famous_sites=4,
			gallery_ref_count=0,
			min_refs=3,
			include_live_sites=False,
		)
		is False
	)


@pytest.mark.asyncio
async def test_capture_famous_sites_injectable(tmp_path: Path) -> None:
	from navigation.inspiration_intelligence.live_capture import capture_famous_sites

	shot = tmp_path / "stripe.png"
	shot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)

	async def fake_capture(site: dict[str, str]):
		return str(shot), site.get("title") or "T", ["capture_tier:test"]

	result = await capture_famous_sites(
		["marketing"],
		max_sites=2,
		browser_concurrency=1,
		capture_fn=fake_capture,
	)
	assert result.sites_attempted == 2
	assert len(result.hits) == 2
	assert all(h["source_kind"] == "live_site" for h in result.hits)
	assert all(h.get("screenshot_path") for h in result.hits)
	assert result.hits[0]["preview_url"].startswith("file:")


@pytest.mark.asyncio
async def test_collect_includes_live_sites_when_forced(tmp_path: Path) -> None:
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits
	from navigation.inspiration_intelligence.models import (
		InspirationCandidate,
		InspirationCaptureResult,
	)

	shot = tmp_path / "linear.png"
	shot.write_bytes(b"fake-image-bytes")

	async def fake_live(site: dict[str, str]):
		return str(shot), site.get("title") or "Live", []

	candidates = [
		InspirationCandidate(
			candidate_id=f"behance:{i}",
			title=f"G {i}",
			source="behance",
			provider_id="behance",
			external_id=str(i),
			url=f"https://behance.net/{i}",
			preview_ref=f"https://cdn.behance.net/{i}.jpg",
			metadata={"fetch_tier": "http"},
			discovery_score=0.9,
		)
		for i in range(2)
	]

	async def fake_capture(candidate, *, intent, allow_browser_screenshot=False):
		_ = intent, allow_browser_screenshot
		return InspirationCaptureResult(
			candidate_id=candidate.candidate_id,
			provider_id=candidate.provider_id,
			screenshot_refs=[candidate.preview_ref],
			degraded=[],
		)

	provider = MagicMock()
	provider.discover_candidates = AsyncMock(return_value=(candidates, []))
	provider.capture_design = fake_capture
	registry = MagicMock()
	registry.get = MagicMock(side_effect=lambda pid: provider if pid == "behance" else None)

	with patch(
		"navigation.inspiration_intelligence.collect.InspirationProviderRegistry",
		return_value=registry,
	):
		with patch("navigation.inspiration_intelligence.collect.InspirationBlobStore") as blob_cls:
			blob_cls.return_value.create_session.return_value = "insp_live"
			blob_cls.return_value.materialize_hits_async = AsyncMock(
				return_value={"materialized": 0, "blob_concurrency": 4}
			)
			manifest = await collect_inspiration_hits(
				"saas marketing landing",
				provider_ids=["behance"],
				mode="fast",
				include_live_sites=True,
				live_capture_fn=fake_live,
				materialize_blobs=True,
				target_refs=5,
				min_refs=3,
			)

	assert manifest["live_sites_used"] is True
	live_hits = [h for h in manifest["hits"] if h.get("source_kind") == "live_site"]
	assert live_hits, manifest["hits"]
	assert any(h.get("provider_id") == "famous_site" for h in manifest["hits"])
	assert any(t.get("tier") == "live_site" for t in manifest.get("provider_ms") or [])


@pytest.mark.asyncio
async def test_parallel_blob_materialize_faster(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	from navigation.inspiration_intelligence.tools.blob_store import InspirationBlobStore

	monkeypatch.setenv("INSPIRATION_BLOB_ROOT", str(tmp_path / "blobs"))
	monkeypatch.setenv("INSPIRATION_SESSIONS_CACHE", str(tmp_path / "sessions.json"))

	store = InspirationBlobStore()
	sid = store.create_session(purpose="perf")

	calls: list[float] = []

	def slow_materialize(session_id, **kwargs):
		_ = session_id, kwargs
		time.sleep(0.08)
		calls.append(time.perf_counter())
		# Return a fake path without real image work
		return str(tmp_path / f"{kwargs.get('candidate_id')}.jpg")

	store.materialize = slow_materialize  # type: ignore[method-assign]

	hits = [
		{
			"preview_url": f"https://cdn.example.com/{i}.jpg",
			"url": f"https://ex.com/{i}",
			"provider_id": "behance",
			"candidate_id": f"c{i}",
			"title": f"T{i}",
		}
		for i in range(4)
	]

	t0 = time.perf_counter()
	summary = await store.materialize_hits_async(sid, hits, concurrency=4)
	elapsed = time.perf_counter() - t0

	assert summary["materialized"] == 4
	assert summary["blob_concurrency"] == 4
	# Serial would be ~0.32s; parallel should be well under that
	assert elapsed < 0.25, f"expected parallel blobs, got {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_fast_path_budget_with_mocked_providers() -> None:
	"""Perf harness: concurrent HTTP wave should stay under 15s budget (mocked)."""
	from navigation.inspiration_intelligence.collect import collect_inspiration_hits
	from navigation.inspiration_intelligence.models import (
		InspirationCandidate,
		InspirationCaptureResult,
	)

	async def delayed_discover(*_a, **_k):
		await asyncio.sleep(0.12)
		return (
			[
				InspirationCandidate(
					candidate_id=f"p:{i}",
					title=f"Hit {i}",
					source="onepagelove",
					provider_id="onepagelove",
					external_id=str(i),
					url=f"https://onepagelove.com/{i}",
					preview_ref=f"https://cdn.example.com/{i}.jpg",
					metadata={"fetch_tier": "http"},
					discovery_score=0.9,
				)
				for i in range(4)
			],
			[],
		)

	async def fake_capture(candidate, *, intent, allow_browser_screenshot=False):
		_ = intent, allow_browser_screenshot
		return InspirationCaptureResult(
			candidate_id=candidate.candidate_id,
			provider_id=candidate.provider_id,
			screenshot_refs=[candidate.preview_ref],
			degraded=[],
		)

	providers = {}
	for pid in ("onepagelove", "lapa", "behance"):
		p = MagicMock()
		p.discover_candidates = AsyncMock(side_effect=delayed_discover)
		p.capture_design = fake_capture
		providers[pid] = p

	registry = MagicMock()
	registry.get = MagicMock(side_effect=lambda pid: providers.get(pid))

	with patch(
		"navigation.inspiration_intelligence.collect.InspirationProviderRegistry",
		return_value=registry,
	):
		with patch("navigation.inspiration_intelligence.collect.InspirationBlobStore") as blob_cls:
			blob_cls.return_value.create_session.return_value = "insp_budget"
			blob_cls.return_value.materialize_hits_async = AsyncMock(
				return_value={"materialized": 0}
			)
			t0 = time.perf_counter()
			manifest = await collect_inspiration_hits(
				"saas landing page",
				provider_ids=["onepagelove", "lapa", "behance"],
				mode="fast",
				include_live_sites=False,
				materialize_blobs=True,
				target_refs=5,
				min_refs=3,
			)
			wall = time.perf_counter() - t0

	# Budget: <15s (mock should be well under 1s)
	assert wall < 15.0
	assert manifest["collect_ms"] < 15_000
	assert manifest["total_hits"] >= 3
	assert manifest["stopped_early"] is True
