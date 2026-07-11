"""Open Doodles illustration provider — static catalog."""
from __future__ import annotations

import re

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory, ResourceProviderMeta
from navigation.resource_intelligence.providers._http import fetch_json

_CATALOG_URL = 'https://raw.githubusercontent.com/lukaszadam/open-doodles/master/doodles.json'


class OpenDoodlesProvider:
	provider_id = 'open-doodles'

	def provider_meta(self) -> ResourceProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def search(
		self,
		query: str,
		*,
		category: ResourceCategory,
		max_results: int = 12,
	) -> tuple[list[ResourceAssetRef], list[str]]:
		degraded: list[str] = []
		try:
			catalog = await fetch_json(_CATALOG_URL)
		except Exception:
			catalog = _FALLBACK_DOODLES
			degraded.append('open_doodles_catalog_fallback')
		items = catalog if isinstance(catalog, list) else list(catalog.get('doodles') or catalog.values())
		tokens = {t for t in re.split(r'[^a-z0-9]+', query.lower()) if len(t) > 2}
		license_profile = self.provider_meta().license
		scored: list[tuple[float, dict]] = []
		for item in items:
			if isinstance(item, str):
				item = {'name': item, 'slug': item}
			if not isinstance(item, dict):
				continue
			slug = str(item.get('slug') or item.get('name') or '').strip()
			name = str(item.get('name') or slug).replace('-', ' ')
			text = f'{slug} {name}'.lower()
			overlap = sum(1 for t in tokens if t in text) if tokens else 0.1
			scored.append((overlap, item))
		scored.sort(key=lambda x: x[0], reverse=True)
		assets: list[ResourceAssetRef] = []
		for score, item in scored[:max_results]:
			slug = str(item.get('slug') or item.get('name') or 'doodle')
			base = f'https://raw.githubusercontent.com/lukaszadam/open-doodles/master/static/{slug}'
			assets.append(
				ResourceAssetRef(
					resource_id=f'open-doodles:{slug}',
					provider_id=self.provider_id,
					category=ResourceCategory.ILLUSTRATION,
					title=slug.replace('-', ' ').title(),
					preview_url=f'{base}.png',
					access_url=f'{base}.svg',
					license=license_profile,
					tags=[slug, query, 'illustration', 'cc0'],
					format='svg',
					score=min(1.0, 0.5 + score * 0.2),
					metadata={'slug': slug, 'png_url': f'{base}.png', 'svg_url': f'{base}.svg'},
				)
			)
		return assets, degraded


_FALLBACK_DOODLES = [
	{'slug': 'sitting', 'name': 'Sitting'},
	{'slug': 'floating', 'name': 'Floating'},
	{'slug': 'dancing', 'name': 'Dancing'},
	{'slug': 'reading', 'name': 'Reading'},
	{'slug': 'plant', 'name': 'Plant'},
	{'slug': 'roller-skating', 'name': 'Roller Skating'},
]
