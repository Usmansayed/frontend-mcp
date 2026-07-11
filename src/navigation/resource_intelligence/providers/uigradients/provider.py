"""uiGradients provider — MIT CSS gradient strings from GitHub catalog."""
from __future__ import annotations

import re
from functools import lru_cache

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory, ResourceProviderMeta
from navigation.resource_intelligence.providers._http import fetch_json

_CATALOG_URL = 'https://raw.githubusercontent.com/ghosh/uiGradients/master/gradients.json'


@lru_cache(maxsize=1)
def _load_gradients() -> tuple[dict[str, str], ...]:
	try:
		from navigation.resource_intelligence.providers._http import fetch_json_sync

		payload = fetch_json_sync(_CATALOG_URL)
	except Exception:
		return tuple(_FALLBACK_GRADIENTS)
	if not isinstance(payload, list):
		return tuple(_FALLBACK_GRADIENTS)
	out: list[dict[str, str]] = []
	for item in payload:
		if not isinstance(item, dict):
			continue
		name = str(item.get('name') or '').strip()
		colors = item.get('colors') or []
		if not name or not isinstance(colors, list) or len(colors) < 2:
			continue
		hex_colors = [str(c).strip() for c in colors if str(c).strip()]
		if len(hex_colors) < 2:
			continue
		css = f"background: linear-gradient(to right, {', '.join(hex_colors)});"
		out.append({'name': name, 'css': css, 'colors': ','.join(hex_colors)})
	return tuple(out or _FALLBACK_GRADIENTS)


class UiGradientsProvider:
	provider_id = 'uigradients'

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
		items = list(_load_gradients())
		if len(items) <= len(_FALLBACK_GRADIENTS):
			try:
				await fetch_json(_CATALOG_URL)
				_load_gradients.cache_clear()
				items = list(_load_gradients())
			except Exception:
				degraded.append('uigradients_catalog_fetch_failed')
		tokens = {t for t in re.split(r'[^a-z0-9]+', query.lower()) if len(t) > 2}
		license_profile = self.provider_meta().license
		scored: list[tuple[float, dict[str, str]]] = []
		for item in items:
			text = f"{item['name']} {item.get('colors', '')}".lower()
			overlap = sum(1 for t in tokens if t in text) if tokens else 0.05
			if tokens and overlap == 0:
				continue
			scored.append((overlap, item))
		scored.sort(key=lambda x: x[0], reverse=True)
		if not scored and items:
			scored = [(0.1, item) for item in items[:max_results]]
		assets: list[ResourceAssetRef] = []
		for score, item in scored[:max_results]:
			slug = re.sub(r'[^a-z0-9]+', '-', item['name'].lower()).strip('-')
			assets.append(
				ResourceAssetRef(
					resource_id=f'uigradients:{slug}',
					provider_id=self.provider_id,
					category=ResourceCategory.GRADIENT,
					title=item['name'],
					preview_url='',
					access_url=_CATALOG_URL,
					license=license_profile,
					tags=[item['name'], 'gradient', 'css', query],
					style=['gradient'],
					format='css',
					score=min(1.0, 0.55 + score * 0.25),
					metadata={
						'css': item['css'],
						'colors': item.get('colors', '').split(','),
						'tailwind_hint': 'Use arbitrary gradient or map colors to theme tokens',
					},
				)
			)
		return assets, degraded


_FALLBACK_GRADIENTS = [
	{'name': 'Omolon', 'css': 'background: linear-gradient(to right, #091E3A, #2F80ED, #2D9EE0);', 'colors': '#091E3A,#2F80ED,#2D9EE0'},
	{'name': 'Purple Dream', 'css': 'background: linear-gradient(to right, #bf5ae0, #a811da);', 'colors': '#bf5ae0,#a811da'},
	{'name': 'Ibtesam', 'css': 'background: linear-gradient(to right, #00F5A0, #00D9F5);', 'colors': '#00F5A0,#00D9F5'},
	{'name': 'Blue & Orange', 'css': 'background: linear-gradient(to right, #FD8112, #0085CA);', 'colors': '#FD8112,#0085CA'},
]
