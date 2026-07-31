# tests/test_episode_prefetch.py
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.planning.episode_prefetch import (
	clear_prefetch_store,
	families_for_prefetch,
	get_prefetch_snapshot,
	peek_inspiration_prefetch,
	schedule_episode_prefetch,
)


@pytest.fixture(autouse=True)
def _clean_store(monkeypatch):
	monkeypatch.setenv("PERCEPTION_EPISODE_PREFETCH", "1")
	clear_prefetch_store()
	yield
	clear_prefetch_store()


@pytest.mark.unit
def test_families_heavy_greenfield():
	fams = families_for_prefetch(
		face_class="greenfield",
		evidence_band="very_heavy",
		pack_remaining=["inspiration", "component", "verify"],
	)
	assert "inspiration" in fams
	assert "component" in fams
	assert "creative_kit" in fams


@pytest.mark.unit
def test_families_hotfix_stays_lean():
	assert (
		families_for_prefetch(
			face_class="hotfix",
			evidence_band="heavy",
			pack_remaining=["observe", "verify"],
		)
		== []
	)


@pytest.mark.unit
def test_families_light_band_skips():
	assert (
		families_for_prefetch(
			face_class="greenfield",
			evidence_band="light",
			pack_remaining=["inspiration", "verify"],
		)
		== []
	)


@pytest.mark.unit
def test_families_medium_design_warms_light():
	fams = families_for_prefetch(
		face_class="greenfield",
		evidence_band="medium",
		pack_remaining=[],
	)
	assert "creative_kit" in fams
	assert "inspiration" in fams
	assert "component" not in fams


@pytest.mark.unit
def test_families_medium_hotfix_stays_lean():
	assert (
		families_for_prefetch(
			face_class="hotfix",
			evidence_band="medium",
			pack_remaining=["observe", "verify"],
		)
		== []
	)


@pytest.mark.unit
def test_families_fallback_when_remaining_empty():
	fams = families_for_prefetch(
		face_class="greenfield",
		evidence_band="heavy",
		pack_remaining=[],
	)
	assert "inspiration" in fams
	assert "component" in fams


@pytest.mark.unit
def test_agent_face_includes_spine_alias():
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)

	card = build_agent_face_card(
		episode_id="ep_test",
		strategy={
			"task_scope": "design_driven",
			"influence_level": "structural",
			"implementation_gate": {"state": "blocked", "prohibited_actions": []},
			"episode_portfolio": {"paid": [], "unpaid": [{"family": "inspiration"}]},
			"recommended_resource": "perception://spine/greenfield",
		},
	)
	assert card.get("resource") == card.get("spine")
	assert str(card.get("spine") or "").startswith("perception://")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_schedule_prefetch_marks_running(monkeypatch):
	async def _fake_insp(query, *, repo_root="", project_id="default"):
		from navigation.inspiration_intelligence.scout_cache import mint_discover_token

		token = mint_discover_token(query=query, candidates=[{"url": "https://example.com"}])
		return {
			"discover_token": token,
			"query": query,
			"candidate_count": 1,
			"candidates": [{"url": "https://example.com"}],
			"providers": ["fixture"],
			"tool": "perception_inspiration_collect",
		}

	async def _fake_comp(query):
		return {
			"query": query,
			"shortlist_count": 1,
			"shortlist": [{"name": "Button"}],
			"tool": "perception_select_component_foundation",
		}

	async def _fake_kit(query, *, repo_root="", project_id="default"):
		return {
			"query": query,
			"asset_count": 1,
			"assets": [{"title": "gear"}],
			"tool": "perception_creative_assets",
		}

	monkeypatch.setattr(
		"navigation.coordination_intelligence.planning.episode_prefetch._prefetch_inspiration",
		_fake_insp,
	)
	monkeypatch.setattr(
		"navigation.coordination_intelligence.planning.episode_prefetch._prefetch_component",
		_fake_comp,
	)
	monkeypatch.setattr(
		"navigation.coordination_intelligence.planning.episode_prefetch._prefetch_creative_kit",
		_fake_kit,
	)

	snap = schedule_episode_prefetch(
		episode_id="ep1",
		session_id="sess1",
		query="build a landing page for a coffee brand",
		face_class="greenfield",
		evidence_band="very_heavy",
		pack_remaining=["inspiration", "component", "verify"],
	)
	assert snap is not None
	assert snap["status"] == "running"
	assert "inspiration" in snap["families"]

	# Let background tasks finish.
	for _ in range(40):
		await asyncio.sleep(0.05)
		done = get_prefetch_snapshot("ep1")
		if done and done.get("status") in {"ready", "partial"}:
			break
	final = get_prefetch_snapshot("ep1")
	assert final is not None
	assert final["prefetch_ready"] is True or "inspiration" in final["ready"]
	assert "browser_parallel" in final and final["browser_parallel"] is False
	warm = peek_inspiration_prefetch(episode_id="ep1", query="build a landing page for a coffee brand")
	assert warm is not None
	assert warm.get("discover_token")


@pytest.mark.unit
def test_creative_assets_in_dispatch_registry():
	from navigation.mcp.handlers import handle_creative_assets
	from navigation.execution_runtime import dispatch_registry as dr

	assert callable(handle_creative_assets)
	src = Path(dr.__file__).read_text(encoding="utf-8")
	assert "perception_creative_assets" in src
	assert "handle_creative_assets" in src
