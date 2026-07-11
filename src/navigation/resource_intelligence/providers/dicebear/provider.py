"""DiceBear avatars — generates preview URLs from query seeds."""
from __future__ import annotations

import hashlib
import re
import urllib.parse

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory, ResourceProviderMeta

_STYLES = ('avataaars', 'lorelei', 'micah', 'notionists', 'personas', 'pixel-art')


def _seeds_from_query(query: str, *, max_seeds: int) -> list[str]:
	base = re.sub(r'[^a-zA-Z0-9]+', '-', query.strip()).strip('-').lower() or 'avatar'
	seeds = [base]
	for style in _STYLES[: max(0, max_seeds - 1)]:
		digest = hashlib.sha1(f'{base}:{style}'.encode()).hexdigest()[:10]
		seeds.append(f'{base}-{digest}')
	return seeds[:max_seeds]


class DiceBearProvider:
	provider_id = 'dicebear'

	def provider_meta(self) -> ResourceProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def search(
		self,
		query: str,
		*,
		category: ResourceCategory,
		max_results: int = 12,
	) -> tuple[list[ResourceAssetRef], list[str]]:
		degraded = ['dicebear_public_api_non_commercial:prefer_self_host_for_production']
		assets: list[ResourceAssetRef] = []
		license_profile = self.provider_meta().license
		for idx, seed in enumerate(_seeds_from_query(query, max_seeds=max_results)):
			style = _STYLES[idx % len(_STYLES)]
			encoded = urllib.parse.quote(seed)
			preview = f'https://api.dicebear.com/9.x/{style}/svg?seed={encoded}'
			assets.append(
				ResourceAssetRef(
					resource_id=f'dicebear:{style}:{seed}',
					provider_id=self.provider_id,
					category=ResourceCategory.AVATAR,
					title=f'{style} avatar ({seed})',
					preview_url=preview,
					access_url=preview,
					license=license_profile,
					tags=[style, seed, query],
					format='svg',
					score=0.6,
					metadata={'style': style, 'seed': seed, 'self_host_recommended': True},
				)
			)
		return assets, degraded
