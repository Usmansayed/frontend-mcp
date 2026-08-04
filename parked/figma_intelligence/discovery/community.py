"""Community discovery — public search via Community Discovery Adapter (no PAT)."""
from __future__ import annotations

from navigation.figma_intelligence.discovery.community_adapter.normalize import hits_to_candidates
from navigation.figma_intelligence.discovery.community_adapter.service import CommunityDiscoveryService
from navigation.figma_intelligence.models import CommunitySearchPlan, FigmaCandidate, FigmaIntent


async def discover_community(
	community_plan: CommunitySearchPlan,
	*,
	intent: FigmaIntent,
	max_results: int,
	adapter: CommunityDiscoveryService | None = None,
) -> tuple[list[FigmaCandidate], list[str]]:
	_ = intent
	svc = adapter or CommunityDiscoveryService()
	hits, degraded = await svc.discover(community_plan, max_results=max_results)
	return hits_to_candidates(hits), degraded
