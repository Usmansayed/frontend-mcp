"""Inspiration provider protocol — execution backends are replaceable."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from navigation.inspiration_intelligence.models import (
	CommunitySearchPlan,
	InspirationCandidate,
	InspirationCaptureResult,
	InspirationIntent,
	InspirationSearchPlan,
)


@runtime_checkable
class InspirationProvider(Protocol):
	"""Execution provider — returns screenshot-first capture data only.

	Inspiration Intelligence owns intent, planning, discovery, ranking, and evaluation.
	Providers MUST NOT decide which designs are valuable.
	"""

	provider_id: str
	display_name: str
	capabilities: frozenset[str]

	async def discover_candidates(
		self,
		plan: InspirationSearchPlan,
		*,
		community_plan: CommunitySearchPlan,
		intent: InspirationIntent,
		max_results: int = 20,
	) -> tuple[list[InspirationCandidate], list[str]]:
		"""Search inspiration sources for ranked candidates."""
		...

	async def capture_design(
		self,
		candidate: InspirationCandidate,
		*,
		intent: InspirationIntent,
	) -> InspirationCaptureResult:
		"""Fetch screenshots and optional pattern metadata for one candidate."""
		...

	async def health(self) -> dict[str, Any]:
		"""Provider connectivity — for degraded reporting."""
		...
