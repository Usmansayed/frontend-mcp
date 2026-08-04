"""Batch regression — Test 11 leftovers (select context, sticky scope, catalog sync)."""
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
from navigation.coordination_intelligence.models import IntentFrame, ProjectSituationModel
from navigation.coordination_intelligence.planning.situation_policy import _derive_task_scope
from navigation.coordination_intelligence.service import CoordinationIntelligenceService
from navigation.engineering_knowledge.reference_binding import (
	foundation_hint_from_psm,
	get_measured_spec,
	store_foundation_selection,
	store_measured_spec,
)


def _cand(
	*,
	cid: str,
	name: str,
	title: str,
	score: float,
	matched_query: str = "",
	description: str = "",
	category: str = "block",
	registry: str = "@shadcn",
) -> ComponentCandidate:
	return ComponentCandidate(
		id=cid,
		provider="shadcn_ecosystem",
		provider_group="registry",
		name=name,
		title=title,
		category=category,
		description=description or title,
		registry=registry,
		item_type="block" if category == "block" else "registry:ui",
		relevance_score=score,
		metadata={"matched_query": matched_query} if matched_query else {},
	)


@pytest.mark.unit
def test_filter_drops_generic_button_match_for_portfolio() -> None:
	items = [
		_cand(
			cid="shadcn:calendar-10",
			name="calendar-10",
			title="Calendar 10",
			score=1.0,
			matched_query="button",
			description="A calendar with date buttons",
		),
		_cand(
			cid="shadcn:portfolio-hero",
			name="portfolio-hero",
			title="Portfolio Hero",
			score=0.55,
			matched_query="portfolio hero",
			description="Portfolio about hero section",
		),
	]
	out = filter_candidates(items, min_score=SELECT_MIN_RELEVANCE, page_context=["portfolio", "about"])
	ids = {c.id for c in out}
	assert "shadcn:calendar-10" not in ids
	assert "shadcn:portfolio-hero" in ids


@pytest.mark.unit
@pytest.mark.asyncio
async def test_select_locks_library_despite_generic_calendar_noise() -> None:
	only_calendar = [
		_cand(
			cid="shadcn:calendar-10",
			name="calendar-10",
			title="Calendar 10",
			score=1.0,
			matched_query="button",
			description="Date picker buttons",
			registry="@shadcn",
		),
	]
	from navigation.component_intelligence.models import ParsedQuery

	parsed = ParsedQuery(raw="select foundation for portfolio about", page_context=["portfolio", "about"])
	selection = await select_foundation(only_calendar, repo_root=ROOT, parsed_query=parsed)
	assert selection.usable is True
	assert selection.library_id == "@shadcn"
	assert selection.chosen is not None
	assert selection.chosen.category == "library"
	assert selection.starter is None  # generic button→calendar excluded as starter


@pytest.mark.unit
def test_sticky_seed_component_foundation_not_system_setup() -> None:
	psm = ProjectSituationModel()
	psm.episode.intent_stack = [
		IntentFrame(intent="select component foundation for portfolio about page", pushed_at="2026-07-24T00:00:00Z"),
	]
	CoordinationIntelligenceService._seed_sticky_design_scope(psm)
	assert psm.episode.retry_counters.get("episode_design_scope") != "system_setup"
	assert _derive_task_scope(
		"select component foundation for portfolio about page", "", "", psm
	) == "design_driven"


@pytest.mark.unit
def test_foundation_select_patches_measured_catalog() -> None:
	psm = ProjectSituationModel()
	store_measured_spec(
		{
			"catalog_version": "v1",
			"source_kind": "live_dom",
			"decisions": {
				"component.foundation_status": {
					"decision_id": "component.foundation_status",
					"status": "unresolved",
					"value": None,
					"why_code": "foundation_unknown",
				}
			},
			"unresolved_by_impact": [{"decision_id": "component.foundation_status"}],
			"coverage": {"total": 1, "settled": 0, "settled_ratio": 0.0},
		},
		psm=psm,
		source="live_dom",
	)
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
	spec, _meta = get_measured_spec(psm=psm)
	assert spec is not None
	dec = spec.decisions.get("component.foundation_status")
	assert dec is not None
	assert dec.status == "resolved"
	assert (dec.value or {}).get("status") == "selected"
