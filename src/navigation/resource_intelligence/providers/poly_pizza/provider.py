"""Poly Pizza 3D model provider — API v1.1 with per-model license."""
from __future__ import annotations

import os
import urllib.parse

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import LicenseProfile, ResourceAssetRef, ResourceCategory, ResourceProviderMeta
from navigation.resource_intelligence.providers._http import fetch_json

_API_BASE = 'https://api.poly.pizza/v1.1'


def _license_profile(license_name: str, attribution: str) -> LicenseProfile:
	lic = (license_name or '').upper().strip()
	if 'NC' in lic:
		return LicenseProfile(
			spdx_id=lic or 'CC-BY-NC',
			commercial_use=False,
			attribution_required=True,
			mcp_download_allowed=False,
			source_url='https://poly.pizza/docs/api/v1.1',
			notes=['Non-commercial model license'],
		)
	attribution_required = lic.startswith('CC-BY') and 'CC0' not in lic
	return LicenseProfile(
		spdx_id=lic or 'CC0',
		commercial_use=True,
		attribution_required=attribution_required,
		mcp_download_allowed=True,
		source_url='https://poly.pizza/docs/api/v1.1',
		notes=['Per-model license — include attribution when CC-BY'],
	)


class PolyPizzaProvider:
	provider_id = 'poly-pizza'

	def provider_meta(self) -> ResourceProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def search(
		self,
		query: str,
		*,
		category: ResourceCategory,
		max_results: int = 12,
	) -> tuple[list[ResourceAssetRef], list[str]]:
		token = os.environ.get('POLY_PIZZA_API_KEY', '').strip() or os.environ.get('POLYPIZZA_AUTH_TOKEN', '').strip()
		if not token:
			return [], ['poly_pizza_api_key_missing:set_POLY_PIZZA_API_KEY']
		degraded: list[str] = []
		keyword = urllib.parse.quote(query.strip())
		limit = max(1, min(max_results, 32))
		headers = {'x-auth-token': token, 'Content-Type': 'application/json'}
		try:
			payload = await fetch_json(
				f'{_API_BASE}/search/{keyword}?limit={limit}&license=CC0',
				headers=headers,
			)
		except Exception as exc:
			return [], [f'poly_pizza_search_failed:{exc}']
		results = list(payload.get('results') or [])
		if not results:
			try:
				payload = await fetch_json(
					f'{_API_BASE}/search/{keyword}?limit={limit}',
					headers=headers,
				)
				results = list(payload.get('results') or [])
			except Exception as exc:
				return [], [f'poly_pizza_search_failed:{exc}']
		assets: list[ResourceAssetRef] = []
		for model in results:
			if not isinstance(model, dict):
				continue
			mid = str(model.get('id') or '')
			title = str(model.get('title') or mid or '3D Model')
			license_name = str(model.get('license') or 'CC0')
			attribution = str(model.get('attribution') or '')
			profile = _license_profile(license_name, attribution)
			thumb = str(model.get('thumbnail') or '')
			download = str(model.get('download') or '')
			creator = model.get('creator') or {}
			creator_name = str(creator.get('name') or 'Unknown') if isinstance(creator, dict) else 'Unknown'
			page = f'https://poly.pizza/m/{mid}' if mid else 'https://poly.pizza'
			assets.append(
				ResourceAssetRef(
					resource_id=f'poly-pizza:{mid}',
					provider_id=self.provider_id,
					category=ResourceCategory.THREE_D,
					title=title,
					preview_url=thumb,
					access_url=download or page,
					license=profile,
					tags=[query, title, '3d', 'low-poly'],
					style=['low-poly', '3d'],
					format='gltf',
					score=0.75,
					attribution_text=attribution or (f'Model by {creator_name} (CC-BY)' if profile.attribution_required else ''),
					metadata={
						'poly_pizza_url': page,
						'creator': creator_name,
						'tri_count': model.get('triCount'),
						'animated': model.get('animated'),
						'category_id': model.get('category'),
						'license_raw': license_name,
					},
				)
			)
		return assets[:max_results], degraded
