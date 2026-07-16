"""Progressive image-first inspiration search — quality over quantity."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.inspiration_intelligence.planning.progressive_search import (
    IMAGE_FIRST_PROVIDER_ORDER,
    MIN_IMAGE_REFS,
    TARGET_IMAGE_REFS,
    has_enough_image_refs,
    progressive_queries,
)


def test_progressive_queries_saas_dashboard() -> None:
    qs = progressive_queries("Build a SaaS analytics dashboard", max_queries=5)
    assert qs
    assert any("analytics" in q.lower() or "dashboard" in q.lower() for q in qs)
    assert len(qs) <= 5


def test_progressive_queries_dedupe() -> None:
    qs = progressive_queries("admin dashboard ui", max_queries=5)
    lowered = [q.lower() for q in qs]
    assert len(lowered) == len(set(lowered))


def test_has_enough_image_refs_stops_at_target() -> None:
    hits = [
        {"preview_url": f"https://cdn.example.com/{i}.jpg"} for i in range(TARGET_IMAGE_REFS)
    ]
    assert has_enough_image_refs(hits, min_refs=MIN_IMAGE_REFS, target_refs=TARGET_IMAGE_REFS)
    assert not has_enough_image_refs(
        hits[: MIN_IMAGE_REFS - 1],
        min_refs=MIN_IMAGE_REFS,
        target_refs=TARGET_IMAGE_REFS,
    )


def test_image_first_provider_order_http_friendly() -> None:
    assert IMAGE_FIRST_PROVIDER_ORDER[0] in ("behance", "onepagelove")
    assert "land-book" == IMAGE_FIRST_PROVIDER_ORDER[-1]


@pytest.mark.asyncio
async def test_collect_stops_early_with_enough_previews() -> None:
    from navigation.inspiration_intelligence.collect import collect_inspiration_hits
    from navigation.inspiration_intelligence.models import (
        InspirationCandidate,
        InspirationCaptureResult,
    )

    candidates = [
        InspirationCandidate(
            candidate_id=f"behance:{i}",
            title=f"Dash {i}",
            source="behance",
            provider_id="behance",
            external_id=str(i),
            url=f"https://behance.net/gallery/{i}",
            preview_ref=f"https://cdn.behance.net/{i}.jpg",
            metadata={"fetch_tier": "http"},
            discovery_score=0.9,
        )
        for i in range(8)
    ]

    async def fake_capture(candidate, *, intent, allow_browser_screenshot=False):
        _ = intent, allow_browser_screenshot
        return InspirationCaptureResult(
            candidate_id=candidate.candidate_id,
            provider_id=candidate.provider_id,
            screenshot_refs=[candidate.preview_ref],
            degraded=["capture_tier:discovery_preview"],
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
        with patch(
            "navigation.inspiration_intelligence.collect.InspirationBlobStore"
        ) as blob_cls:
            blob_cls.return_value.create_session.return_value = "insp_test"
            blob_cls.return_value.materialize_hits.return_value = {"materialized": 0}
            manifest = await collect_inspiration_hits(
                "saas analytics dashboard",
                provider_ids=["behance", "awwwards", "land-book"],
                materialize_blobs=True,
                target_refs=5,
                min_refs=3,
                per_provider=8,
            )

    assert manifest["mode"].startswith("image_first")
    assert manifest["stopped_early"] is True
    assert manifest["total_hits"] <= 5
    assert manifest["image_ref_count"] >= 3
    land = (manifest.get("provider_summary") or {}).get("land-book")
    assert land is None or int(land.get("count") or 0) == 0
