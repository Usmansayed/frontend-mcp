"""Batch regression — Test 12 foundation library preference."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.component_intelligence.models import ComponentCandidate, ParsedQuery
from navigation.component_intelligence.selection.filter import (
	SELECT_MIN_RELEVANCE,
	filter_candidates,
	is_composite_marketing_block,
	is_weak_foundation_candidate,
)
from navigation.component_intelligence.selection.selector import select_foundation


def _cand(
	*,
	cid: str,
	name: str,
	title: str,
	score: float,
	registry: str = "@shadcn",
	matched_query: str = "",
	description: str = "",
	category: str = "component",
	item_type: str = "registry:ui",
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
def test_composite_aceternity_hero_navbar_is_weak_foundation() -> None:
	c = _cand(
		cid="aceternity:hero-navbar",
		name="hero-section-with-images-grid-and-navbar",
		title="Hero + Navbar",
		score=1.0,
		registry="@aceternity",
		matched_query="navbar",
		category="block",
		item_type="registry:block",
	)
	assert is_composite_marketing_block(c)
	assert is_weak_foundation_candidate(
		c,
		parsed_query=ParsedQuery(raw="select component foundation for portfolio about"),
		page_context=["portfolio", "about"],
	)


@pytest.mark.unit
def test_filter_prefers_shadcn_component_over_aceternity_hero_navbar() -> None:
	items = [
		_cand(
			cid="aceternity:hero-navbar",
			name="hero-section-with-images-grid-and-navbar",
			title="Hero section with images grid and navbar",
			score=1.0,
			registry="@aceternity",
			matched_query="navbar",
			category="block",
			item_type="registry:block",
			description="Hero with navbar",
		),
		_cand(
			cid="shadcn:card",
			name="card",
			title="Card",
			score=0.55,
			registry="@shadcn",
			matched_query="about hero",
			category="component",
			item_type="registry:ui",
		),
	]
	parsed = ParsedQuery(
		raw="select component foundation for portfolio about page",
		page_context=["portfolio", "about"],
	)
	out = filter_candidates(
		items,
		min_score=SELECT_MIN_RELEVANCE,
		page_context=["portfolio", "about"],
		parsed_query=parsed,
	)
	ids = [c.id for c in out]
	assert ids[0] == "shadcn:card"
	assert "aceternity:hero-navbar" not in ids


@pytest.mark.unit
@pytest.mark.asyncio
async def test_select_rejects_aceternity_composite_as_foundation() -> None:
	only = [
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
	]
	parsed = ParsedQuery(
		raw="select component foundation for portfolio about",
		page_context=["portfolio", "about"],
	)
	selection = await select_foundation(only, repo_root=ROOT, parsed_query=parsed)
	assert selection.usable is True
	assert selection.library_id == "@shadcn"
	assert selection.chosen is not None
	assert selection.chosen.registry == "@shadcn"
	assert selection.chosen.category == "library"
	assert selection.starter is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_select_locks_shadcn_over_aceternity_when_both_present() -> None:
	items = [
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
			score=0.6,
			registry="@shadcn",
			matched_query="portfolio about",
			category="component",
			item_type="registry:ui",
		),
	]
	parsed = ParsedQuery(
		raw="select component foundation for portfolio about",
		page_context=["portfolio", "about"],
	)
	selection = await select_foundation(items, repo_root=ROOT, parsed_query=parsed)
	assert selection.usable is True
	assert selection.library_id == "@shadcn"
	assert selection.chosen is not None
	assert selection.chosen.category == "library"
	assert selection.chosen.registry == "@shadcn"
	assert selection.starter is not None
	assert selection.starter.id == "shadcn:button"
