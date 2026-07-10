"""Unit tests for component search parser, planner, and normalization."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.component_intelligence.parser import parse_query
from navigation.component_intelligence.planner import build_search_plan
from navigation.component_intelligence.providers.normalize import normalize_shadcn_item
from navigation.component_intelligence.providers.shadcn_ecosystem.scoring import score_item
from navigation.component_intelligence.search.merge import is_sufficient, merge_candidates


def test_parse_saas_pricing_rich() -> None:
	parsed = parse_query('Animated glass pricing section for SaaS')
	assert 'pricing' in parsed.component_types or 'pricing section' in parsed.page_types
	assert 'glassmorphism' in parsed.styles or 'glass' in parsed.modifiers
	assert 'animated' in parsed.animations
	assert 'saas' in parsed.audience
	assert parsed.search_hints


def test_plan_modern_glass_dashboard_navbar() -> None:
	plan = build_search_plan(parse_query('Modern glass dashboard navbar'))
	assert 'navbar' in plan.component_types
	assert plan.primary_intent
	assert any('navigation menu' in q.text for q in plan.planned_queries)
	assert any(q.pass_number == 1 for q in plan.planned_queries)
	assert any(q.pass_number == 2 for q in plan.planned_queries)
	assert '@shadcn' in plan.suggested_registries
	assert '@aceternity' in plan.suggested_registries


def test_merge_dedupes_by_id() -> None:
	a = normalize_shadcn_item(
		{'name': 'navbar-1', 'title': 'Navbar', 'type': 'registry:block'},
		provider='shadcn_ecosystem',
		provider_group='shadcn_ecosystem',
		registry='@shadcn',
		registry_homepage=None,
		item_url_template=None,
		relevance_score=0.4,
		matched_query='navbar',
		search_pass=1,
		plan_confidence=1.0,
	)
	b = normalize_shadcn_item(
		{'name': 'navbar-1', 'title': 'Navbar', 'type': 'registry:block'},
		provider='shadcn_ecosystem',
		provider_group='shadcn_ecosystem',
		registry='@shadcn',
		registry_homepage=None,
		item_url_template=None,
		relevance_score=0.9,
		matched_query='navigation menu',
		search_pass=2,
		plan_confidence=0.8,
	)
	merged = merge_candidates([a], [b])
	assert len(merged) == 1
	assert merged[0].relevance_score == 0.9
	assert merged[0].metadata.get('matched_query') == 'navigation menu'


def test_is_sufficient_threshold() -> None:
	items = [
		normalize_shadcn_item(
			{'name': f'c{i}', 'title': f'C{i}', 'type': 'registry:ui'},
			provider='shadcn_ecosystem',
			provider_group='shadcn_ecosystem',
			registry=f'@reg{i % 3}',
			registry_homepage=None,
			item_url_template=None,
			relevance_score=0.5,
		)
		for i in range(8)
	]
	assert is_sufficient(items)
	assert not is_sufficient(items[:3])


def test_score_item_prefers_name_match() -> None:
	query = parse_query('pricing card')
	item = {'name': 'pricing-cards', 'title': 'Pricing Cards', 'description': 'Pricing section', 'type': 'registry:block'}
	score = score_item(item, query)
	assert score > 0.2


def main() -> int:
	test_parse_saas_pricing_rich()
	test_plan_modern_glass_dashboard_navbar()
	test_merge_dedupes_by_id()
	test_is_sufficient_threshold()
	test_score_item_prefers_name_match()
	print('component search: PASS')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
