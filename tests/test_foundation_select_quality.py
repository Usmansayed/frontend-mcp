"""Foundation select quality — relevance floor + auth demotion (Test 10)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.component_intelligence.models import ComponentCandidate
from navigation.component_intelligence.selection.filter import (
	SELECT_MIN_RELEVANCE,
	filter_candidates,
)
from navigation.component_intelligence.selection.selector import select_foundation
from navigation.coordination_intelligence.models import ProjectSituationModel
from navigation.coordination_intelligence.psm.normalize import _capability_outcome
from navigation.core.envelope import make_envelope
from navigation.engineering_knowledge.adapters import compile_live_spec
from navigation.engineering_knowledge.reference_binding import (
	foundation_hint_from_psm,
	store_foundation_selection,
)
from navigation.design_snapshot_engine.models import DesignSnapshot


def _cand(
	*,
	cid: str,
	name: str,
	title: str,
	score: float,
	category: str = "block",
) -> ComponentCandidate:
	return ComponentCandidate(
		id=cid,
		provider="shadcn_ecosystem",
		provider_group="registry",
		name=name,
		title=title,
		category=category,
		description=title,
		registry="@tailark",
		item_type="block",
		relevance_score=score,
	)


@pytest.mark.unit
def test_filter_drops_auth_blocks_for_portfolio_context() -> None:
	items = [
		_cand(
			cid="tailark:forgot-password-1",
			name="forgot-password-1",
			title="Forgot Password",
			score=0.40,
		),
		_cand(
			cid="tailark:portfolio-hero",
			name="portfolio-hero",
			title="Portfolio Hero",
			score=0.38,
		),
	]
	out = filter_candidates(items, min_score=SELECT_MIN_RELEVANCE, page_context=["portfolio", "about"])
	ids = {c.id for c in out}
	assert "tailark:forgot-password-1" not in ids
	assert "tailark:portfolio-hero" in ids


@pytest.mark.unit
@pytest.mark.asyncio
async def test_select_locks_library_even_when_search_below_floor() -> None:
	"""Weak registry hits no longer block the durable @shadcn library lock."""
	weak = [
		_cand(
			cid="tailark:forgot-password-1",
			name="forgot-password-1",
			title="Forgot Password",
			score=0.29,
		),
	]
	selection = await select_foundation(weak, repo_root=ROOT)
	assert selection.usable is True
	assert selection.library_id == "@shadcn"
	assert selection.chosen is not None
	assert selection.chosen.category == "library"
	assert selection.starter is None


@pytest.mark.unit
def test_select_envelope_below_floor_not_advancement_eligible() -> None:
	env = make_envelope(
		"perception_select_component_foundation",
		ok=True,
		data={
			"foundation_selection": {
				"chosen": {
					"id": "tailark:forgot-password-1",
					"name": "forgot-password-1",
					"relevance_score": 0.29,
				},
				"usable": False,
				"reject_reason": "below_relevance_floor",
			},
			"agent_summary": {"blocking": ["below_relevance_floor"]},
		},
		degraded=["foundation_relevance_too_low"],
	)
	outcome = _capability_outcome("component_select", env)
	assert outcome["status"] == "provisional"
	assert outcome["advancement_eligible"] is False
	assert outcome["quality"]["usable"] is False


@pytest.mark.unit
def test_foundation_hint_syncs_catalog_status() -> None:
	psm = ProjectSituationModel()
	store_foundation_selection(
		{
			"id": "foundation-library:shadcn",
			"name": "shadcn",
			"title": "@shadcn foundation library",
			"registry": "@shadcn",
			"category": "library",
			"library": "@shadcn",
			"relevance_score": 0.72,
		},
		psm=psm,
	)
	hint = foundation_hint_from_psm(psm)
	assert hint is not None
	snap = DesignSnapshot.from_dict(
		{
			"url": "http://127.0.0.1:3000/about",
			"layout": {"viewport": {"width": 1280, "height": 720}, "regions": []},
			"hierarchy": {"prominence_scores": []},
			"colors": {},
			"design_tokens": {},
			"components": {"patterns": []},
		}
	)
	spec = compile_live_spec(snap, foundation_hint=hint)
	dec = spec.decisions.get("component.foundation_status")
	assert dec is not None
	assert dec.status == "resolved"
	assert (dec.value or {}).get("status") == "selected"
