"""Pipeline orchestration — Community Discovery decoupled from providers."""
from __future__ import annotations

from navigation.figma_intelligence.candidate_intelligence.normalizer import normalize_candidates
from navigation.figma_intelligence.community_intelligence.planner import build_community_plan
from navigation.figma_intelligence.discovery.community import discover_community
from navigation.figma_intelligence.extraction.pipeline import extract_selection_plan
from navigation.figma_intelligence.intent.parser import parse_intent
from navigation.figma_intelligence.models import (
	FigmaDiscoveryRequest,
	FigmaDiscoveryResult,
	FigmaIntentKind,
	FigmaPipelineResult,
)
from navigation.figma_intelligence.planning.search_planner import build_search_plan
from navigation.figma_intelligence.ranking.ranker import rank_candidates
from navigation.figma_intelligence.providers.manager import FigmaProviderRegistry
from navigation.figma_intelligence.registry.reference_bridge import register_extractions
from navigation.figma_intelligence.review.deep_review import deep_review_extractions
from navigation.figma_intelligence.selection.planner import build_selection_plan


class FigmaPipelineOrchestrator:
	def __init__(self, providers: FigmaProviderRegistry | None = None) -> None:
		self._providers = providers or FigmaProviderRegistry()

	async def discover(self, request: FigmaDiscoveryRequest) -> FigmaDiscoveryResult:
		intent = parse_intent(
			request.query,
			kind=request.intent,
			repo_root=request.repo_root,
			project_id=request.project_id,
		)
		search_plan = build_search_plan(intent, provider_preference=request.provider_preference)
		community_plan = build_community_plan(intent, search_plan)
		degraded = list(search_plan.degraded) + list(community_plan.degraded)

		raw, discover_degraded = await discover_community(
			community_plan,
			intent=intent,
			max_results=request.max_candidates,
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

		return FigmaDiscoveryResult(
			intent=intent,
			search_plan=search_plan,
			community_plan=community_plan,
			candidates=ranked[: request.max_candidates],
			selection_plan=selection_plan,
			degraded=degraded,
		)

	async def run_pipeline(self, request: FigmaDiscoveryRequest) -> FigmaPipelineResult:
		discovery = await self.discover(request)
		selection_plan = discovery.selection_plan
		if selection_plan is None:
			return FigmaPipelineResult(
				discovery=discovery,
				degraded=list(discovery.degraded) + ['selection_plan_missing'],
			)

		extractions, extract_degraded = await extract_selection_plan(
			selection_plan,
			intent=discovery.intent,
			providers=self._providers,
			provider_preference=request.provider_preference or 'figma_console',
		)
		ranked_by_id = {c.candidate.candidate_id: c for c in discovery.candidates}
		deep_reviews, review_degraded = deep_review_extractions(
			extractions,
			ranked_by_id=ranked_by_id,
			intent=discovery.intent,
			repo_root=request.repo_root,
		)
		ref_ids, reg_degraded = register_extractions(extractions, intent=discovery.intent)
		degraded = list(discovery.degraded) + extract_degraded + review_degraded + reg_degraded
		return FigmaPipelineResult(
			discovery=discovery,
			extractions=extractions,
			deep_reviews=deep_reviews,
			reference_registry_ids=ref_ids,
			pdg_ingest_ready=discovery.intent.kind == FigmaIntentKind.LEARN_PATTERNS,
			degraded=degraded,
		)
