"""Iconify API provider — icons with per-collection license checks."""
from __future__ import annotations

import asyncio
import json
import re
import urllib.parse
import urllib.request
from typing import Any

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import LicenseProfile, ResourceAssetRef, ResourceCategory, ResourceProviderMeta

_ICONIFY_API = 'https://api.iconify.design'
_NC_LICENSE_MARKERS = ('nc', 'non-commercial', 'non commercial', 'cc-by-nc')


def _fetch_json(url: str) -> dict[str, Any]:
	req = urllib.request.Request(url, headers={'User-Agent': 'frontend-perception-engine/1.0'})
	with urllib.request.urlopen(req, timeout=30) as resp:
		data = json.loads(resp.read().decode('utf-8'))
		return data if isinstance(data, dict) else {}


def _collection_license(prefix: str, cache: dict[str, LicenseProfile]) -> LicenseProfile:
	if prefix in cache:
		return cache[prefix]
	default = SEED_PROVIDERS['iconify'].license
	try:
		payload = _fetch_json(f'{_ICONIFY_API}/collection?prefix={urllib.parse.quote(prefix)}')
		license_name = str(payload.get('license') or payload.get('license_spdx') or 'MIT').lower()
		if any(m in license_name for m in _NC_LICENSE_MARKERS):
			profile = LicenseProfile(
				spdx_id='CC-BY-NC',
				commercial_use=False,
				attribution_required=True,
				mcp_download_allowed=False,
				source_url='https://iconify.design/docs/licenses.html',
				notes=[f'Collection {prefix} license: {license_name}'],
			)
		else:
			profile = LicenseProfile(
				spdx_id=str(payload.get('license_spdx') or 'MIT'),
				commercial_use=True,
				attribution_required='by' in license_name and 'cc0' not in license_name,
				redistribution_allowed=True,
				mcp_download_allowed=True,
				source_url='https://iconify.design/docs/licenses.html',
				notes=[f'Iconify collection {prefix}'],
			)
	except Exception:
		profile = default
	cache[prefix] = profile
	return profile


class IconifyProvider:
	provider_id = 'iconify'

	def provider_meta(self) -> ResourceProviderMeta:
		return SEED_PROVIDERS[self.provider_id]

	async def search(
		self,
		query: str,
		*,
		category: ResourceCategory,
		max_results: int = 12,
		prefix_filter: str | None = None,
	) -> tuple[list[ResourceAssetRef], list[str]]:
		degraded: list[str] = []
		q = urllib.parse.quote(query.strip())
		if not q:
			return [], ['empty_query']
		url = f'{_ICONIFY_API}/search?query={q}&limit={max(1, min(max_results * 3, 64))}'
		if prefix_filter:
			url += f'&prefixes={urllib.parse.quote(prefix_filter)}'
		try:
			payload = await asyncio.to_thread(_fetch_json, url)
		except Exception as exc:
			return [], [f'iconify_search_failed:{exc}']

		icons = list(payload.get('icons') or [])
		if not icons:
			return [], degraded or ['iconify_no_results']

		cache: dict[str, LicenseProfile] = {}
		assets: list[ResourceAssetRef] = []
		for icon_ref in icons:
			if ':' not in str(icon_ref):
				continue
			prefix, name = str(icon_ref).split(':', 1)
			if prefix_filter and prefix != prefix_filter:
				continue
			license_profile = await asyncio.to_thread(_collection_license, prefix, cache)
			if not license_profile.commercial_use:
				degraded.append(f'skipped_nc_collection:{prefix}')
				continue
			preview = f'{_ICONIFY_API}/{prefix}/{name}.svg?height=128'
			access = f'{_ICONIFY_API}/{prefix}/{name}.svg'
			assets.append(
				ResourceAssetRef(
					resource_id=f'iconify:{prefix}:{name}',
					provider_id=self.provider_id,
					category=category,
					title=re.sub(r'[-_]+', ' ', name).strip().title(),
					preview_url=preview,
					access_url=access,
					license=license_profile,
					tags=[prefix, name, query],
					format='svg',
					score=0.7,
					metadata={'prefix': prefix, 'icon_name': name},
				)
			)
			if len(assets) >= max_results:
				break
		return assets, degraded
