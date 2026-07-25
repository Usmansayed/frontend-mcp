"""Durable library-first foundation lock — closes Test 10–12 failure classes forever."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.component_intelligence.models import ComponentCandidate, ParsedQuery
from navigation.component_intelligence.selection.library_lock import (
	make_library_candidate,
	resolve_foundation_library,
)
from navigation.component_intelligence.selection.selector import select_foundation
from navigation.coordination_intelligence.models import ProjectSituationModel
from navigation.coordination_intelligence.psm.normalize import _capability_outcome
from navigation.core.envelope import make_envelope
from navigation.engineering_knowledge.reference_binding import (
	foundation_hint_from_psm,
	store_foundation_selection,
)


def _cand(
	*,
	cid: str,
	name: str,
	title: str,
	score: float,
	registry: str,
	matched_query: str = "",
	category: str = "block",
	item_type: str = "registry:block",
	description: str = "",
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
		item_type=item_type,
		relevance_score=score,
		metadata={"matched_query": matched_query} if matched_query else {},
	)


@pytest.mark.unit
def test_default_library_is_shadcn_without_repo_signals() -> None:
	res = resolve_foundation_library(None, ParsedQuery(raw="select component foundation for about"))
	assert res.refused is False
	assert res.library_id == "@shadcn"


@pytest.mark.unit
def test_components_json_detects_shadcn() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		(root / "components.json").write_text("{}", encoding="utf-8")
		res = resolve_foundation_library(root, ParsedQuery(raw="foundation"))
		assert res.library_id == "@shadcn"
		assert any("components.json" in e for e in res.evidence)


@pytest.mark.unit
def test_ambiguous_ds_prefers_priority_or_refuses() -> None:
	with tempfile.TemporaryDirectory() as tmp:
		root = Path(tmp)
		(root / "package.json").write_text(
			json.dumps(
				{
					"dependencies": {
						"@mui/material": "5.0.0",
						"@chakra-ui/react": "2.0.0",
					}
				}
			),
			encoding="utf-8",
		)
		res = resolve_foundation_library(root, ParsedQuery(raw="select foundation"))
		# Priority prefers @mui over hard refuse when multiple DS deps present.
		assert res.library_id == "@mui" or res.refuse_reason == "ambiguous_library"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_never_locks_forgot_password_auth_block() -> None:
	"""Test 10 failure class."""
	parsed = ParsedQuery(
		raw="select component foundation for portfolio about",
		page_context=["portfolio", "about"],
	)
	bad = [
		_cand(
			cid="tailark:forgot-password-1",
			name="forgot-password-1",
			title="Forgot Password",
			score=0.40,
			registry="@tailark",
			matched_query="about",
		)
	]
	selection = await select_foundation(bad, repo_root=ROOT, parsed_query=parsed)
	assert selection.usable is True
	assert selection.library_id == "@shadcn"
	assert selection.chosen is not None
	assert selection.chosen.category == "library"
	assert selection.chosen.registry == "@shadcn"
	assert "forgot" not in (selection.chosen.name or "").lower()
	assert selection.starter is None  # auth/wrong-registry starter dropped


@pytest.mark.unit
@pytest.mark.asyncio
async def test_never_locks_calendar_via_button() -> None:
	"""Test 11 failure class."""
	parsed = ParsedQuery(
		raw="select component foundation for portfolio about",
		page_context=["portfolio", "about"],
	)
	bad = [
		_cand(
			cid="shadcn:calendar-10",
			name="calendar-10",
			title="Calendar 10",
			score=1.0,
			registry="@shadcn",
			matched_query="button",
			category="component",
			item_type="registry:ui",
			description="A calendar with date buttons",
		)
	]
	selection = await select_foundation(bad, repo_root=ROOT, parsed_query=parsed)
	assert selection.usable is True
	assert selection.library_id == "@shadcn"
	assert selection.chosen.category == "library"
	# Calendar may be starter only if it passes weak filters; library is still @shadcn.
	assert selection.chosen.registry == "@shadcn"
	if selection.starter is not None:
		assert selection.starter.registry == "@shadcn"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_never_locks_aceternity_hero_navbar() -> None:
	"""Test 12 failure class — specialty composite is never the foundation."""
	parsed = ParsedQuery(
		raw="select component foundation for portfolio about page",
		page_context=["portfolio", "about"],
	)
	noise = [
		_cand(
			cid="aceternity:hero-navbar",
			name="hero-section-with-images-grid-and-navbar",
			title="Hero + Navbar",
			score=1.0,
			registry="@aceternity",
			matched_query="navbar",
			category="block",
			item_type="registry:block",
		),
		_cand(
			cid="shadcn:button",
			name="button",
			title="Button",
			score=0.5,
			registry="@shadcn",
			matched_query="portfolio about",
			category="component",
			item_type="registry:ui",
		),
	]
	selection = await select_foundation(noise, repo_root=ROOT, parsed_query=parsed)
	assert selection.usable is True
	assert selection.library_id == "@shadcn"
	assert selection.chosen.id.startswith("foundation-library:")
	assert selection.chosen.registry == "@shadcn"
	assert "aceternity" not in selection.chosen.id
	assert selection.starter is not None
	assert selection.starter.id == "shadcn:button"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_search_still_locks_default_library() -> None:
	parsed = ParsedQuery(raw="component foundation", page_context=["about"])
	selection = await select_foundation([], repo_root=ROOT, parsed_query=parsed)
	assert selection.usable is True
	assert selection.library_id == "@shadcn"
	assert selection.starter is None


@pytest.mark.unit
def test_store_persists_library_not_block_name() -> None:
	psm = ProjectSituationModel()
	store_foundation_selection(
		{
			"id": "foundation-library:shadcn",
			"name": "shadcn",
			"title": "@shadcn foundation library",
			"registry": "@shadcn",
			"category": "library",
			"library_id": "@shadcn",
			"relevance_score": 0.9,
		},
		psm=psm,
	)
	hint = foundation_hint_from_psm(psm)
	assert hint is not None
	assert hint["library"] == "@shadcn"
	assert hint["foundation"] == "@shadcn"


@pytest.mark.unit
def test_store_rejects_aceternity_block_as_library() -> None:
	psm = ProjectSituationModel()
	store_foundation_selection(
		{
			"id": "aceternity:hero-navbar",
			"name": "hero-section-with-images-grid-and-navbar",
			"registry": "@aceternity",
			"category": "block",
			"relevance_score": 1.0,
		},
		psm=psm,
	)
	assert foundation_hint_from_psm(psm) is None


@pytest.mark.unit
def test_capability_outcome_library_first_advances() -> None:
	lib = make_library_candidate("@shadcn", confidence=0.9, evidence=["default"])
	env = make_envelope(
		"perception_select_component_foundation",
		ok=True,
		data={
			"foundation_selection": {
				"chosen": lib.to_dict(),
				"library_id": "@shadcn",
				"usable": True,
				"starter": None,
				"lock_evidence": ["default_react_foundation"],
			},
			"agent_summary": {"blocking": []},
		},
	)
	outcome = _capability_outcome("component_select", env)
	assert outcome["status"] == "succeeded"
	assert outcome["advancement_eligible"] is True
	assert outcome["quality"]["library_id"] == "@shadcn"
