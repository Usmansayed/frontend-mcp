"""Figma provider protocol — execution backends are replaceable."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from navigation.figma_intelligence.models import (
	CommunitySearchPlan,
	FigmaCandidate,
	FigmaExtractionResult,
	FigmaIntent,
	FigmaSearchPlan,
)


@runtime_checkable
class FigmaProvider(Protocol):
	"""Execution provider — returns raw Figma data only.

	Figma Intelligence owns intent, planning, discovery, ranking, and evaluation.
	Providers MUST NOT decide which designs are valuable.
	"""

	provider_id: str
	display_name: str
	capabilities: frozenset[str]

	async def discover_candidates(
		self,
		plan: FigmaSearchPlan,
		*,
		community_plan: CommunitySearchPlan,
		intent: FigmaIntent,
		max_results: int = 20,
	) -> tuple[list[FigmaCandidate], list[str]]:
		"""Deprecated for Community search — use Community Discovery Adapter.

		Execution providers implement extraction only. Kept for interface stability.
		"""
		...

	async def extract_design(
		self,
		candidate: FigmaCandidate,
		*,
		intent: FigmaIntent,
	) -> FigmaExtractionResult:
		"""Fetch tokens, components, variables, screenshots for one candidate."""
		...

	async def health(self) -> dict[str, Any]:
		"""Provider connectivity — for MCP degraded reporting."""
		...
