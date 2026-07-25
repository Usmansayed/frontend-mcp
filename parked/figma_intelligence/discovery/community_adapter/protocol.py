"""Community Discovery Adapter protocol — public search, no PAT."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from navigation.figma_intelligence.discovery.community_adapter.models import CommunityDiscoveryHit
from navigation.figma_intelligence.models import CommunitySearchPlan, PlannedCommunityQuery


@runtime_checkable
class CommunityDiscoveryBackend(Protocol):
	"""Pluggable backend for public Community search."""

	backend_id: str

	async def search(
		self,
		query: PlannedCommunityQuery,
		*,
		max_results: int,
	) -> tuple[list[CommunityDiscoveryHit], list[str]]:
		...


@runtime_checkable
class CommunityDiscoveryAdapter(Protocol):
	"""Orchestrates backends — never calls Figma Console or PAT APIs."""

	async def discover(
		self,
		plan: CommunitySearchPlan,
		*,
		max_results: int,
	) -> tuple[list[CommunityDiscoveryHit], list[str]]:
		...

	def list_backends(self) -> list[dict[str, Any]]:
		...
