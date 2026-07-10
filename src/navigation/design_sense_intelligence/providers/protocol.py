"""Provider protocol — Design Sense never depends on external implementations directly."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import ProviderContribution, ReviewRequest


@runtime_checkable
class DesignSenseProvider(Protocol):
	"""Adapter for an external system or ported methodology."""

	name: str
	kind: str  # integration | methodology | knowledge
	lane: str  # objective | subjective

	async def contribute(self, request: ReviewRequest) -> ProviderContribution:
		"""Return findings, scores, or notes without mutating the request."""
