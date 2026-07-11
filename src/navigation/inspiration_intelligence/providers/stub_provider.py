"""Stub inspiration provider — navigation knowledge wired, discovery pending."""
from __future__ import annotations

from typing import Any

from navigation.inspiration_intelligence.models import (
	CommunitySearchPlan,
	InspirationCandidate,
	InspirationCaptureResult,
	InspirationIntent,
	InspirationSearchPlan,
)
from navigation.inspiration_intelligence.providers.navigation import ProviderNavigationKnowledge


class StubInspirationProvider:
	"""Provider adapter scaffold — exposes navigation knowledge before live automation."""

	def __init__(self, navigation: ProviderNavigationKnowledge) -> None:
		self.provider_id = navigation.provider_id
		self.display_name = navigation.display_name
		self.capabilities: frozenset[str] = frozenset({'discover', 'capture'})
		self._navigation = navigation

	async def discover_candidates(
		self,
		plan: InspirationSearchPlan,
		*,
		community_plan: CommunitySearchPlan,
		intent: InspirationIntent,
		max_results: int = 20,
	) -> tuple[list[InspirationCandidate], list[str]]:
		_ = plan, community_plan, intent, max_results
		return [], [f'{self.provider_id}_discovery_not_enabled']

	async def capture_design(
		self,
		candidate: InspirationCandidate,
		*,
		intent: InspirationIntent,
	) -> InspirationCaptureResult:
		_ = intent
		return InspirationCaptureResult(
			candidate_id=candidate.candidate_id,
			provider_id=self.provider_id,
			degraded=[f'{self.provider_id}_capture_not_enabled'],
		)

	async def health(self) -> dict[str, Any]:
		return {
			'provider_id': self.provider_id,
			'status': 'navigation_only',
			'search_url_pattern': self._navigation.search_url_pattern,
		}
