"""Figma Intelligence tests — Community Discovery decoupled from providers."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

import asyncio

from navigation.figma_intelligence import FigmaIntelligenceService
from navigation.figma_intelligence.community_intelligence.planner import build_community_plan
from navigation.figma_intelligence.discovery.community_adapter.normalize import hit_to_candidate
from navigation.figma_intelligence.discovery.community_adapter.models import CommunityDiscoveryHit
from navigation.figma_intelligence.discovery.community_adapter.service import CommunityDiscoveryService
from navigation.figma_intelligence.intent.parser import parse_intent
from navigation.figma_intelligence.models import FigmaDiscoveryRequest, FigmaIntentKind, FigmaRankedCandidate, FigmaSearchPlan
from navigation.figma_intelligence.providers.figma_console.provider import FigmaConsoleProvider
from navigation.figma_intelligence.providers.manager import FigmaProviderRegistry
from navigation.figma_intelligence.review.deep_review import deep_review_extractions
from navigation.figma_intelligence.selection.planner import build_selection_plan
from navigation.figma_intelligence.models import FigmaCandidate, FigmaExtractionResult


def test_community_intelligence_expands_dashboard_query() -> None:
	intent = parse_intent('minimal saas dashboard')
	search_plan = FigmaSearchPlan(seed_query=intent.raw_query)
	plan = build_community_plan(intent, search_plan)
	assert 'dashboard' in plan.page_types
	assert len(plan.executable_queries) >= 5


def test_community_discovery_adapter_no_pat() -> None:
	intent = parse_intent('saas dashboard')
	community_plan = build_community_plan(intent, FigmaSearchPlan(seed_query=intent.raw_query))
	hits, degraded = asyncio.run(
		CommunityDiscoveryService().discover(community_plan, max_results=5)
	)
	assert hits
	assert all(isinstance(h, CommunityDiscoveryHit) for h in hits)
	assert 'catalog_backend' in degraded or hits[0].source_backend in {'catalog', 'http'}
	assert hits[0].title
	assert hits[0].description or hits[0].tags


def test_hit_to_candidate_has_no_provider_id() -> None:
	hit = CommunityDiscoveryHit(
		hit_id='x',
		title='Test',
		description='desc',
		author='author',
		likes=100,
	)
	candidate = hit_to_candidate(hit)
	assert candidate.provider_id == ''
	assert candidate.metadata['likes'] == 100


def test_figma_console_rejects_discovery() -> None:
	provider = FigmaConsoleProvider()
	candidates, degraded = asyncio.run(
		provider.discover_candidates(
			FigmaSearchPlan(),
			community_plan=build_community_plan(parse_intent('x'), FigmaSearchPlan()),
			intent=parse_intent('x'),
		)
	)
	assert candidates == []
	assert 'community_adapter' in degraded[0]


def test_selection_planner_dedupes_design_systems() -> None:
	ranked = [
		FigmaRankedCandidate(
			candidate=FigmaCandidate(
				candidate_id='a',
				title='Analytics Dashboard UI Kit',
				source='community',
				provider_id='',
				metadata={'design_system': 'analytics dashboard'},
				discovery_score=0.95,
			),
			overall_score=0.95,
		),
		FigmaRankedCandidate(
			candidate=FigmaCandidate(
				candidate_id='b',
				title='Analytics Dashboard Pro Kit',
				source='community',
				provider_id='',
				metadata={'design_system': 'analytics dashboard'},
				discovery_score=0.93,
			),
			overall_score=0.93,
		),
	]
	plan = build_selection_plan(ranked)
	assert len({s.design_system_key for s in plan.selected}) == len(plan.selected)


def test_discover_uses_community_adapter() -> None:
	result = asyncio.run(
		FigmaIntelligenceService().discover(
			FigmaDiscoveryRequest(query='saas dashboard inspiration', max_candidates=5)
		)
	)
	assert result.candidates
	assert result.selection_plan is not None
	assert not any('figma_console_catalog' in d for d in result.degraded)


def test_deep_review_uses_extraction_payload() -> None:
	candidate = FigmaCandidate(
		candidate_id='x',
		title='SaaS Dashboard',
		source='community',
		provider_id='figma_console',
	)
	ranked = FigmaRankedCandidate(candidate=candidate, overall_score=0.5)
	extraction = FigmaExtractionResult(
		candidate_id='x',
		provider_id='figma_console',
		tokens=[{'name': 'color.primary'}],
		components=[{'name': 'Button'}],
	)
	reviews, _ = deep_review_extractions(
		[extraction],
		ranked_by_id={'x': ranked},
		intent=parse_intent('dashboard'),
		repo_root='/tmp/project',
	)
	assert reviews[0].extraction_weight > 0


def test_provider_registry_lists_backends() -> None:
	ids = {p['provider_id'] for p in FigmaProviderRegistry().list_providers()}
	assert ids == {'figma_console', 'official_figma', 'future'}
