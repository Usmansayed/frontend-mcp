"""3dicons provider — CC0 3D icon catalog with page URLs for download."""
from __future__ import annotations

import re

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory, ResourceProviderMeta
from navigation.resource_intelligence.providers.threedicons.catalog import ICON_CATALOG

_BASE = 'https://3dicons.co/icons'


class ThreeDiconsProvider:
	provider_id = '3dicons'

	def provider_meta(self) -> ResourceProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def search(
		self,
		query: str,
		*,
		category: ResourceCategory,
		max_results: int = 12,
	) -> tuple[list[ResourceAssetRef], list[str]]:
		tokens = {t for t in re.split(r'[^a-z0-9]+', query.lower()) if len(t) > 2}
		license_profile = self.provider_meta().license
		scored: list[tuple[float, dict[str, str]]] = []
		for item in ICON_CATALOG:
			text = f"{item['slug']} {item['name']} {item.get('tags', '')}".lower()
			overlap = sum(1 for t in tokens if t in text) if tokens else 0.05
			if tokens and overlap == 0:
				continue
			scored.append((overlap, item))
		scored.sort(key=lambda x: x[0], reverse=True)
		if not scored:
			scored = [(0.1, item) for item in ICON_CATALOG[:max_results]]
		assets: list[ResourceAssetRef] = []
		for score, item in scored[:max_results]:
			slug = item['slug']
			page = f'{_BASE}/{slug}?angle=dynamic'
			assets.append(
				ResourceAssetRef(
					resource_id=f'3dicons:{slug}',
					provider_id=self.provider_id,
					category=ResourceCategory.THREE_D,
					title=item['name'],
					preview_url=page,
					access_url=page,
					license=license_profile,
					tags=[item['name'], slug, '3d', 'cc0', query],
					style=['3d', 'clay'],
					format='png',
					score=min(1.0, 0.5 + score * 0.3),
					metadata={
						'slug': slug,
						'download_guidance': 'Open access_url to customize color/angle and download PNG or glTF',
						'angles': ['dynamic', 'front', 'iso'],
						'colors': ['color', 'clay', 'gradient', 'premium'],
					},
				)
			)
		return assets, []
