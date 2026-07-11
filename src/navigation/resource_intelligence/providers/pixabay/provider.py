"""Pixabay photo provider — API search with Pixabay License."""
from __future__ import annotations

import os
import urllib.parse

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import LicenseProfile, ResourceAssetRef, ResourceCategory, ResourceProviderMeta
from navigation.resource_intelligence.providers._http import fetch_json

_API = 'https://pixabay.com/api/'


class PixabayProvider:
	provider_id = 'pixabay'

	def provider_meta(self) -> ResourceProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def search(
		self,
		query: str,
		*,
		category: ResourceCategory,
		max_results: int = 12,
	) -> tuple[list[ResourceAssetRef], list[str]]:
		api_key = os.environ.get('PIXABAY_API_KEY', '').strip()
		if not api_key:
			return [], ['pixabay_api_key_missing:set_PIXABAY_API_KEY']
		degraded: list[str] = []
		q = urllib.parse.quote(query.strip())
		per_page = max(3, min(max_results, 50))
		image_type = 'photo'
		if category == ResourceCategory.ILLUSTRATION:
			image_type = 'illustration'
		elif category == ResourceCategory.SVG:
			image_type = 'vector'
		try:
			payload = await fetch_json(
				f'{_API}?key={urllib.parse.quote(api_key)}&q={q}&image_type={image_type}'
				f'&per_page={per_page}&safesearch=true',
			)
		except Exception as exc:
			return [], [f'pixabay_search_failed:{exc}']
		hits = list(payload.get('hits') or [])
		license_profile = LicenseProfile(
			spdx_id='Pixabay License',
			commercial_use=True,
			attribution_required=False,
			redistribution_allowed=True,
			mcp_download_allowed=True,
			source_url='https://pixabay.com/service/license/',
			notes=['Show where images are from when displaying search results (Pixabay API terms)'],
		)
		assets: list[ResourceAssetRef] = []
		for hit in hits:
			pid = str(hit.get('id') or '')
			user = str(hit.get('user') or 'Unknown')
			page_url = str(hit.get('pageURL') or '')
			preview = str(hit.get('previewURL') or hit.get('webformatURL') or '')
			access = str(hit.get('largeImageURL') or hit.get('webformatURL') or preview)
			tags = [t.strip() for t in str(hit.get('tags') or '').split(',') if t.strip()]
			assets.append(
				ResourceAssetRef(
					resource_id=f'pixabay:{pid}',
					provider_id=self.provider_id,
					category=ResourceCategory.PHOTO if image_type == 'photo' else category,
					title=f'Photo by {user}' if image_type == 'photo' else f'Image by {user}',
					preview_url=preview,
					access_url=access,
					license=license_profile,
					tags=tags or [query],
					format='jpeg' if image_type == 'photo' else 'vector',
					score=0.68,
					attribution_text=f'Image from Pixabay by {user} ({page_url})' if page_url else f'Image from Pixabay by {user}',
					metadata={
						'user': user,
						'pixabay_url': page_url,
						'views': hit.get('views'),
						'downloads': hit.get('downloads'),
						'image_type': image_type,
					},
				)
			)
		return assets[:max_results], degraded
