"""Rive provider — metadata and integration guidance only (no .riv file hosting)."""
from __future__ import annotations

import re

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory, ResourceProviderMeta
from navigation.resource_intelligence.providers.rive.catalog import RIVE_CATALOG


class RiveProvider:
	provider_id = 'rive'

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
		for item in RIVE_CATALOG:
			text = f"{item['title']} {item.get('tags', '')} {item['slug']}".lower()
			overlap = sum(1 for t in tokens if t in text) if tokens else 0.05
			if tokens and overlap == 0:
				continue
			scored.append((overlap, item))
		scored.sort(key=lambda x: x[0], reverse=True)
		if not scored:
			scored = [(0.1, item) for item in RIVE_CATALOG[:max_results]]
		assets: list[ResourceAssetRef] = []
		for score, item in scored[:max_results]:
			slug = item['slug']
			marketplace = item['url']
			search_hint = f'https://rive.app/marketplace/?q={query.replace(" ", "+")}'
			assets.append(
				ResourceAssetRef(
					resource_id=f'rive:{slug}',
					provider_id=self.provider_id,
					category=ResourceCategory.ANIMATION,
					title=item['title'],
					preview_url='',
					access_url=search_hint,
					license=license_profile,
					tags=[item['title'], 'rive', 'animation', query],
					style=['interactive', 'state-machine'],
					format='riv',
					score=min(1.0, 0.45 + score * 0.35),
					metadata={
						'integration_runtime': item.get('runtime', '@rive-app/react-canvas'),
						'marketplace_url': marketplace,
						'search_url': search_hint,
						'download_guidance': 'Export .riv from Rive Editor (paid plan) or browse marketplace; self-host in public/animations/',
						'no_public_cdn': True,
						'mcp_download_allowed': False,
						'install_command': 'npm install @rive-app/react-canvas',
					},
				)
			)
		return assets, ['rive_metadata_only:no_riv_file_hosting']
