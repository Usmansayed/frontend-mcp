"""theSVG provider — brand SVG logos via simple-icons + theSVG catalog metadata."""
from __future__ import annotations

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory, ResourceProviderMeta
from navigation.resource_intelligence.providers.simple_icons.provider import SimpleIconsProvider

# theSVG curates brand SVGs; commercial logos overlap Simple Icons CC0 set.
# Adapter searches Simple Icons and tags with theSVG integration metadata.


class TheSVGProvider:
	provider_id = 'thesvg'

	def provider_meta(self) -> ResourceProviderMeta:
		meta = SEED_PROVIDERS.get(self.provider_id)
		if meta:
			return meta
		return SEED_PROVIDERS['simple-icons']

	async def search(
		self,
		query: str,
		*,
		category: ResourceCategory,
		max_results: int = 12,
	) -> tuple[list[ResourceAssetRef], list[str]]:
		simple = SimpleIconsProvider()
		assets, degraded = await simple.search(query, category=category, max_results=max_results)
		for asset in assets:
			asset.provider_id = self.provider_id
			asset.resource_id = asset.resource_id.replace('simple-icons:', 'thesvg:', 1)
			asset.metadata['source'] = 'thesvg_via_simple_icons'
			asset.metadata['thesvg_url'] = f'https://thesvg.com/?q={query}'
			asset.metadata['variants'] = ['monochrome', 'currentColor']
			asset.metadata['wordmark'] = 'search brand name on thesvg.com for wordmarks'
		return assets, degraded
