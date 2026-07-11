"""IRA Design illustration provider — curated MIT illustration sets."""
from __future__ import annotations

import re

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory, ResourceProviderMeta

# IRA Design hosts categorized MIT illustrations — static catalog from known slugs.
_IRA_CATALOG: list[dict[str, str]] = [
	{'slug': 'amico', 'name': 'Amico', 'tags': 'people team collaboration'},
	{'slug': 'bro', 'name': 'Bro', 'tags': 'people character'},
	{'slug': 'cuate', 'name': 'Cuate', 'tags': 'flat illustration'},
	{'slug': 'pana', 'name': 'Pana', 'tags': 'business saas'},
	{'slug': 'rafiki', 'name': 'Rafiki', 'tags': 'concept abstract'},
	{'slug': 'amico-analytics', 'name': 'Analytics', 'tags': 'analytics data chart dashboard'},
	{'slug': 'bro-hero', 'name': 'Hero', 'tags': 'hero landing saas'},
	{'slug': 'cuate-startup', 'name': 'Startup', 'tags': 'startup business'},
	{'slug': 'pana-security', 'name': 'Security', 'tags': 'security enterprise'},
	{'slug': 'rafiki-design', 'name': 'Design', 'tags': 'design creative'},
]


class IraDesignProvider:
	provider_id = 'ira-design'

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
		scored: list[tuple[float, dict]] = []
		for item in _IRA_CATALOG:
			text = f"{item['slug']} {item['name']} {item['tags']}".lower()
			overlap = sum(1 for t in tokens if t in text) if tokens else 0.1
			scored.append((overlap, item))
		scored.sort(key=lambda x: x[0], reverse=True)
		assets: list[ResourceAssetRef] = []
		for score, item in scored[:max_results]:
			slug = item['slug']
			assets.append(
				ResourceAssetRef(
					resource_id=f'ira-design:{slug}',
					provider_id=self.provider_id,
					category=ResourceCategory.ILLUSTRATION,
					title=item['name'],
					preview_url=f'https://iradesign.io/assets/{slug}.svg',
					access_url=f'https://iradesign.io/illustrations/{slug}',
					license=license_profile,
					tags=item['tags'].split() + [query],
					format='svg',
					score=min(1.0, 0.55 + score * 0.15),
					metadata={
						'slug': slug,
						'ira_url': f'https://iradesign.io/illustrations/{slug}',
						'license': 'MIT',
						'download_guidance': 'Download from iradesign.io; customize colors in editor',
					},
				)
			)
		return assets, []
