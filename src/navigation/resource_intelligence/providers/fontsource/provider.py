"""Fontsource provider — npm font families with install guidance."""
from __future__ import annotations

import urllib.parse

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory, ResourceProviderMeta
from navigation.resource_intelligence.providers._http import fetch_json

_API = 'https://api.fontsource.org/v1/fonts'


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
		q = urllib.parse.quote(query.strip())
		if not q:
			return [], ['empty_query']
		try:
			payload = await fetch_json(f'{_API}?q={q}&limit={max(1, min(max_results * 2, 24))}')
		except Exception as exc:
			return [], [f'fontsource_search_failed:{exc}']
		items = list(payload) if isinstance(payload, list) else list(payload.get('fonts') or payload.get('data') or [])
		if not items and isinstance(payload, dict):
			items = [payload]
		license_profile = self.provider_meta().license
		assets: list[ResourceAssetRef] = []
		for item in items:
			if not isinstance(item, dict):
				continue
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
					score=0.75,
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
