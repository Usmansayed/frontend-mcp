"""Resource provider protocol — implement in Phase 1."""
from __future__ import annotations

from typing import Protocol

from navigation.resource_intelligence.models import (
	ResourceAssetRef,
	ResourceCategory,
	ResourceProviderMeta,
)


class ResourceProvider(Protocol):
	provider_id: str

	async def search(
		self,
		query: str,
		*,
		category: ResourceCategory,
		max_results: int = 12,
	) -> tuple[list[ResourceAssetRef], list[str]]:
		"""Return (assets, degraded)."""
		...

	def provider_meta(self) -> ResourceProviderMeta:
		...
