"""Lucide icons via Iconify prefix filter."""
from __future__ import annotations

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory, ResourceProviderMeta
from navigation.resource_intelligence.providers.iconify.provider import IconifyProvider


class LucideProvider:
	provider_id = 'lucide'

	def __init__(self) -> None:
		self._iconify = IconifyProvider()

	def provider_meta(self) -> ResourceProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def search(
		self,
		query: str,
		*,
		category: ResourceCategory,
		max_results: int = 12,
	) -> tuple[list[ResourceAssetRef], list[str]]:
		assets, degraded = await self._iconify.search(
			query,
			category=category,
			max_results=max_results,
			prefix_filter='lucide',
		)
		for asset in assets:
			asset.provider_id = self.provider_id
			asset.resource_id = asset.resource_id.replace('iconify:', 'lucide:', 1)
			if asset.license:
				asset.license = self.provider_meta().license
		return assets, degraded
