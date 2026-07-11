"""Placeholder for future Figma providers — Figwright, community MCPs, etc."""
from __future__ import annotations

from typing import Any

from navigation.figma_intelligence.models import (
	CommunitySearchPlan,
	FigmaCandidate,
	FigmaExtractionResult,
	FigmaIntent,
	FigmaSearchPlan,
)


class FutureFigmaProvider:
	provider_id = 'future'
	display_name = 'Future Figma Provider'
	capabilities: frozenset[str] = frozenset()

	async def discover_candidates(
		self,
		plan: FigmaSearchPlan,
		*,
		community_plan: CommunitySearchPlan,
		intent: FigmaIntent,
		max_results: int = 20,
	) -> tuple[list[FigmaCandidate], list[str]]:
		_ = plan, community_plan, intent, max_results
		return [], ['future_provider_discovery_not_supported']

	async def extract_design(
		self,
		candidate: FigmaCandidate,
		*,
		intent: FigmaIntent,
	) -> FigmaExtractionResult:
		_ = intent
		return FigmaExtractionResult(
			candidate_id=candidate.candidate_id,
			provider_id=self.provider_id,
			degraded=['future_provider_not_enabled'],
		)

	async def health(self) -> dict[str, Any]:
		return {'provider_id': self.provider_id, 'status': 'disabled'}
