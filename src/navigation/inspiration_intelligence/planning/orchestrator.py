"""Pipeline orchestration — inspiration discovery decoupled from capture providers."""
from __future__ import annotations

from navigation.inspiration_intelligence.candidate_intelligence.normalizer import normalize_candidates
from navigation.inspiration_intelligence.capture.pipeline import capture_selection_plan
from navigation.inspiration_intelligence.community_intelligence.planner import build_community_plan
from navigation.inspiration_intelligence.discovery.inspiration import discover_inspiration
from navigation.inspiration_intelligence.intent.parser import parse_intent
from navigation.inspiration_intelligence.models import (
	InspirationDiscoveryRequest,
	InspirationDiscoveryResult,
	InspirationIntentKind,
	InspirationPipelineResult,
)
from navigation.inspiration_intelligence.planning.search_planner import build_search_plan
from navigation.inspiration_intelligence.providers.manager import InspirationProviderRegistry
from navigation.inspiration_intelligence.ranking.ranker import rank_candidates
from navigation.inspiration_intelligence.registry.reference_bridge import register_captures
from navigation.inspiration_intelligence.review.deep_review import deep_review_captures
from navigation.inspiration_intelligence.selection.planner import build_selection_plan


class InspirationPipelineOrchestrator:
	def __init__(self, providers: InspirationProviderRegistry | None = None) -> None:
		self._providers = providers or InspirationProviderRegistry()

	async def discover(self, request: InspirationDiscoveryRequest) -> InspirationDiscoveryResult:
		intent = parse_intent(
			request.query,
			kind=request.intent,
			repo_root=request.repo_root,
			project_id=request.project_id,
		)
		search_plan = build_search_plan(intent, provider_preference=request.provider_preference)
		community_plan = build_community_plan(intent, search_plan)
		degraded = list(search_plan.degraded) + list(community_plan.degraded)

		raw, discover_degraded = await discover_inspiration(
			search_plan,
			community_plan,
			intent=intent,
			max_results=request.max_candidates,
			providers=self._providers,
		)
		degraded.extend(discover_degraded)

		normalized = normalize_candidates(raw)
		ranked = rank_candidates(
			normalized,
			intent=intent,
			hints=search_plan.intelligence_hints,
			community_plan=community_plan,
		)
		selection_plan = build_selection_plan(ranked)
		degraded.extend(selection_plan.degraded)

		return InspirationDiscoveryResult(
			intent=intent,
			search_plan=search_plan,
			community_plan=community_plan,
			candidates=ranked[: request.max_candidates],
			selection_plan=selection_plan,
			degraded=degraded,
		)

	async def run_pipeline(self, request: InspirationDiscoveryRequest) -> InspirationPipelineResult:
		discovery = await self.discover(request)
		selection_plan = discovery.selection_plan
		if selection_plan is None:
			return InspirationPipelineResult(
				discovery=discovery,
				degraded=list(discovery.degraded) + ['selection_plan_missing'],
			)

		preference = request.provider_preference or (
			discovery.search_plan.provider_ids[0] if discovery.search_plan.provider_ids else 'dribbble'
		)
		captures, capture_degraded = await capture_selection_plan(
			selection_plan,
			intent=discovery.intent,
			providers=self._providers,
			provider_preference=preference,
		)
		ranked_by_id = {c.candidate.candidate_id: c for c in discovery.candidates}
		deep_reviews, review_degraded = deep_review_captures(
			captures,
			ranked_by_id=ranked_by_id,
			intent=discovery.intent,
			repo_root=request.repo_root,
		)
		ref_ids, reg_degraded = register_captures(captures, intent=discovery.intent)
		degraded = list(discovery.degraded) + capture_degraded + review_degraded + reg_degraded
		return InspirationPipelineResult(
			discovery=discovery,
			captures=captures,
			deep_reviews=deep_reviews,
			reference_registry_ids=ref_ids,
			pdg_ingest_ready=discovery.intent.kind == InspirationIntentKind.LEARN_PATTERNS,
			degraded=degraded,
		)
