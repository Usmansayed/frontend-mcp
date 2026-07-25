"""Fontsource provider — npm font families with install guidance."""
from __future__ import annotations

import time

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory, ResourceProviderMeta
from navigation.resource_intelligence.providers._http import fetch_json

_API = 'https://api.fontsource.org/v1/fonts'
# Fontsource v1 does NOT support ?q= or ?limit= (HTTP 400). Filter client-side.
_CACHE: tuple[float, list[dict]] | None = None
_CACHE_TTL_S = 3600.0


class FontsourceProvider:
	provider_id = 'fontsource'

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
		needle = query.strip().lower()
		if not needle:
			return [], ['empty_query']
		try:
			items = await self._load_catalog()
		except Exception as exc:
			return [], [f'fontsource_search_failed:{exc}']

		# Prefer id/family substring matches (geist → geist / geist-sans / geist-mono).
		matched: list[dict] = []
		exact: list[dict] = []
		for item in items:
			if not isinstance(item, dict):
				continue
			family_id = str(item.get('id') or '').strip().lower()
			family = str(item.get('family') or item.get('name') or '').strip().lower()
			blob = f'{family_id} {family}'
			if family_id == needle or family == needle or family_id.replace('-', ' ') == needle:
				exact.append(item)
			elif needle in family_id or needle in family or needle.replace(' ', '-') in family_id:
				matched.append(item)
		ordered = exact + matched
		if not ordered:
			return [], degraded + ['fontsource_no_match']

		license_profile = self.provider_meta().license
		assets: list[ResourceAssetRef] = []
		for item in ordered:
			family_id = str(item.get('id') or item.get('family') or item.get('name') or '').strip()
			if not family_id:
				continue
			display = str(item.get('family') or item.get('name') or family_id).replace('-', ' ').title()
			subsets = list(item.get('subsets') or [])
			version = str(item.get('version') or item.get('lastModified') or '')
			npm_pkg = f'@fontsource/{family_id}'
			assets.append(
				ResourceAssetRef(
					resource_id=f'fontsource:{family_id}',
					provider_id=self.provider_id,
					category=ResourceCategory.FONT,
					title=display,
					preview_url=f'https://fontsource.org/fonts/{family_id}',
					access_url=f'https://www.npmjs.com/package/{npm_pkg}',
					license=license_profile,
					tags=[family_id, query, 'font'],
					format='npm',
					score=0.9 if family_id.lower() == needle else 0.75,
					metadata={
						'npm_package': npm_pkg,
						'install_command': f'npm install {npm_pkg}',
						'import_css': f"import '@fontsource/{family_id}/400.css'",
						'font_family_css': f"font-family: '{display}', sans-serif;",
						'subsets': subsets,
						'version': version,
						'delivery': 'url_only',
						'framework_compat': ['react', 'next', 'vite', 'any'],
					},
				)
			)
			if len(assets) >= max_results:
				break
		return assets, degraded

	async def _load_catalog(self) -> list[dict]:
		global _CACHE
		now = time.monotonic()
		if _CACHE is not None and (now - _CACHE[0]) < _CACHE_TTL_S:
			return _CACHE[1]
		payload = await fetch_json(_API)
		items = list(payload) if isinstance(payload, list) else list(
			payload.get('fonts') or payload.get('data') or []
		)
		_CACHE = (now, items)
		return items
