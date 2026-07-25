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

# Descriptive-query expansion (no embeddings): category filters + style → family ids.
_CATEGORY_SYNONYMS: dict[str, str] = {
	'sans': 'sans-serif',
	'sans-serif': 'sans-serif',
	'serif': 'serif',
	'mono': 'monospace',
	'monospace': 'monospace',
	'display': 'display',
	'heading': 'display',
	'handwriting': 'handwriting',
}
_STYLE_FAMILY_HINTS: dict[str, tuple[str, ...]] = {
	'geometric': ('inter', 'space-grotesk', 'geist', 'manrope', 'dm-sans', 'outfit', 'figtree', 'plus-jakarta-sans'),
	'humanist': ('source-sans-3', 'noto-sans', 'ibm-plex-sans', 'open-sans'),
	'grotesk': ('space-grotesk', 'inter', 'helvetica', 'arial'),
	'modern': ('inter', 'geist', 'manrope', 'outfit'),
	'classic': ('libre-baskerville', 'merriweather', 'playfair-display', 'lora'),
	'mono': ('geist-mono', 'jetbrains-mono', 'fira-code', 'source-code-pro'),
}
_NOISE_TOKENS = frozenset({
	'font', 'fonts', 'typeface', 'typography', 'heading', 'body', 'title', 'similar',
	'like', 'for', 'a', 'an', 'the', 'to', 'of', 'and', 'with',
})


def _expand_font_query(query: str) -> tuple[str | None, set[str], set[str]]:
	"""Return (category_filter, hint_family_ids, leftover_tokens)."""
	normalized = query.strip().lower().replace(',', ' ')
	# Multi-word category phrases before token split.
	category: str | None = None
	for phrase, cat in (
		('sans-serif', 'sans-serif'),
		('sans serif', 'sans-serif'),
		('mono space', 'monospace'),
	):
		if phrase in normalized:
			category = cat
			normalized = normalized.replace(phrase, ' ')
			break
	tokens = [t for t in normalized.split() if t]
	hints: set[str] = set()
	leftover: set[str] = set()
	for tok in tokens:
		if tok in _NOISE_TOKENS:
			continue
		if tok in _CATEGORY_SYNONYMS:
			# Don't let bare "serif" override an already-detected sans-serif.
			mapped = _CATEGORY_SYNONYMS[tok]
			if category is None or (category == 'serif' and mapped == 'sans-serif'):
				category = mapped
			elif mapped == 'serif' and category == 'sans-serif':
				pass
			elif category is None:
				category = mapped
			continue
		if tok in _STYLE_FAMILY_HINTS:
			hints.update(_STYLE_FAMILY_HINTS[tok])
			continue
		leftover.add(tok)
	return category, hints, leftover


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

		category_filter, style_hints, leftover = _expand_font_query(needle)

		# Prefer id/family substring matches (geist → geist / geist-sans / geist-mono).
		matched: list[dict] = []
		exact: list[dict] = []
		hinted: list[dict] = []
		category_hits: list[dict] = []
		for item in items:
			if not isinstance(item, dict):
				continue
			family_id = str(item.get('id') or '').strip().lower()
			family = str(item.get('family') or item.get('name') or '').strip().lower()
			item_cat = str(item.get('category') or '').strip().lower()
			blob = f'{family_id} {family}'
			if family_id == needle or family == needle or family_id.replace('-', ' ') == needle:
				exact.append(item)
			elif needle in family_id or needle in family or needle.replace(' ', '-') in family_id:
				matched.append(item)
			elif leftover and any(tok in family_id or tok in family for tok in leftover):
				matched.append(item)
			elif family_id in style_hints or family.replace(' ', '-') in style_hints:
				hinted.append(item)
			elif category_filter and item_cat == category_filter and not exact and not matched:
				category_hits.append(item)

		ordered = exact + matched + hinted
		if not ordered and category_hits:
			ordered = category_hits[: max(max_results * 3, 12)]
			degraded.append('fontsource_category_fallback')
		elif hinted and not exact and not matched:
			degraded.append('fontsource_style_hint_match')
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
			fid_l = family_id.lower()
			score = 0.9 if fid_l == needle else (0.82 if fid_l in style_hints else 0.75)
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
					score=score,
					metadata={
						'npm_package': npm_pkg,
						'install_command': f'npm install {npm_pkg}',
						'import_css': f"import '@fontsource/{family_id}/400.css'",
						'subsets': subsets[:8],
						'version': version,
						'category': str(item.get('category') or ''),
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
