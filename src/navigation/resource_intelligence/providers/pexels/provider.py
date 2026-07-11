"""Pexels photo provider — API search with attribution."""
from __future__ import annotations

import os
import urllib.parse

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import LicenseProfile, ResourceAssetRef, ResourceCategory, ResourceProviderMeta
from navigation.resource_intelligence.providers._http import fetch_json

_API = 'https://api.pexels.com/v1/search'


class PexelsProvider:
	provider_id = 'pexels'

	def provider_meta(self) -> ResourceProviderMeta:
		return SEED_PROVIDERS['pexels']

	async def search(
		self,
		query: str,
		*,
		category: ResourceCategory,
		max_results: int = 12,
	) -> tuple[list[ResourceAssetRef], list[str]]:
		api_key = os.environ.get('PEXELS_API_KEY', '').strip()
		if not api_key:
			return [], ['pexels_api_key_missing:set_PEXELS_API_KEY']
		degraded: list[str] = []
		q = urllib.parse.quote(query.strip())
		per_page = max(1, min(max_results, 40))
		try:
			payload = await fetch_json(
				f'{_API}?query={q}&per_page={per_page}',
				headers={'Authorization': api_key},
			)
		except Exception as exc:
			return [], [f'pexels_search_failed:{exc}']
		photos = list(payload.get('photos') or [])
		license_profile = LicenseProfile(
			spdx_id='Pexels License',
			commercial_use=True,
			attribution_required=True,
			redistribution_allowed=False,
			mcp_download_allowed=True,
			source_url='https://www.pexels.com/license/',
			notes=['Pexels API requires attribution link to Pexels and photographer'],
		)
		assets: list[ResourceAssetRef] = []
		for photo in photos:
			pid = str(photo.get('id') or '')
			src = photo.get('src') or {}
			photographer = str(photo.get('photographer') or 'Unknown')
			photo_url = str(photo.get('url') or '')
			preview = str(src.get('medium') or src.get('small') or src.get('original') or '')
			access = str(src.get('original') or preview)
			assets.append(
				ResourceAssetRef(
					resource_id=f'pexels:{pid}',
					provider_id=self.provider_id,
					category=ResourceCategory.PHOTO,
					title=f'Photo by {photographer}',
					preview_url=preview,
					access_url=access,
					license=license_profile,
					tags=[query, photographer],
					format='jpeg',
					score=0.7,
					attribution_text=f'Photo by {photographer} on Pexels ({photo_url})',
					metadata={
						'photographer': photographer,
						'pexels_url': photo_url,
						'download_guidance': 'Use access_url; include attribution_text in UI credits',
						'width': photo.get('width'),
						'height': photo.get('height'),
					},
				)
			)
		return assets, degraded
