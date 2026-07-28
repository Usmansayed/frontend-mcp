"""Fast component/section pattern inspiration — specialist galleries + direct CDN.

Measured winners (2026-07-27):
  - navbar.gallery / footer.design: Webflow CDN screenshots in <1s
  - daisyUI img.daisyui.com/components/{slug}.webp: zero-scrape chrome previews
  - Fonts: route to Resource Intelligence (not gallery collect)

Does not install packages — visual refs only.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from navigation.inspiration_intelligence.browser.fetch import extract_og_image, http_get
from navigation.inspiration_intelligence.query_flex import query_tokens, resolve_flexible_query

_WEBFLOW_CDN = re.compile(
	r'https://cdn\.prod\.website-files\.com/[a-zA-Z0-9]+/[a-zA-Z0-9]+/[^\"\'\s<>]+\.(?:webp|jpg|jpeg|png|avif)',
	re.I,
)
_FRAMER_CDN = re.compile(
	r'https://framerusercontent\.com/images/[^\"\'\s<>]+\.(?:webp|jpg|jpeg|png)',
	re.I,
)
_ANY_IMG = re.compile(
	r'(?:src|data-src|content)=[\"\'](https?://[^\"\']+\.(?:jpg|jpeg|png|webp|avif)[^\"\']*)[\"\']',
	re.I,
)


@dataclass
class PatternHit:
	provider_id: str
	candidate_id: str
	title: str
	url: str
	preview_url: str
	source_kind: str = 'pattern_gallery'
	fetch_tier: str = 'pattern_http'
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return asdict(self)


@dataclass
class PatternAcquireResult:
	query: str
	scope: str
	elapsed_ms: float
	hits: list[PatternHit] = field(default_factory=list)
	targets: list[str] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)
	font_route: dict[str, Any] | None = None
	timing: list[dict[str, Any]] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'query': self.query,
			'scope': self.scope,
			'elapsed_ms': round(self.elapsed_ms, 1),
			'hits': [h.to_dict() for h in self.hits],
			'targets': list(self.targets),
			'degraded': list(self.degraded),
			'font_route': self.font_route,
			'timing': list(self.timing),
		}


@lru_cache(maxsize=1)
def load_pattern_sources() -> dict[str, Any]:
	path = Path(__file__).resolve().parent / 'data' / 'pattern_inspiration_sources.json'
	return json.loads(path.read_text(encoding='utf-8'))


def is_font_query(query: str) -> bool:
	cfg = load_pattern_sources().get('font_policy') or {}
	text = (query or '').lower()
	return any(m in text for m in (cfg.get('match') or []))


def _skip_asset(url: str) -> bool:
	low = url.lower()
	if any(x in low for x in ('favicon', 'logo', 'apple-touch', 'sprite', '1x1', 'pixel')):
		return True
	# Prefer real shots over site chrome OG when we have alternatives
	if 'open-graph' in low or 'ogimage' in low or '/og.' in low:
		return True
	return False


def extract_pattern_previews(html: str, *, extract: str = 'webflow_cdn', limit: int = 8) -> list[str]:
	found: list[str] = []
	seen: set[str] = set()

	def add(u: str) -> None:
		u = unquote(u.strip())
		if not u.startswith('http') or u in seen or _skip_asset(u):
			return
		seen.add(u)
		found.append(u)

	if extract == 'webflow_cdn':
		for m in _WEBFLOW_CDN.finditer(html or ''):
			add(m.group(0))
			if len(found) >= limit:
				return found
	elif extract == 'framer_cdn':
		for m in _FRAMER_CDN.finditer(html or ''):
			add(m.group(0))
			if len(found) >= limit:
				return found

	for m in _ANY_IMG.finditer(html or ''):
		add(m.group(1))
		if len(found) >= limit:
			break
	og = extract_og_image(html or '')
	if og.startswith('http') and not found:
		add(og)
	return found[:limit]


def resolve_daisy_slugs(query: str) -> list[str]:
	cfg = load_pattern_sources()
	block = next((b for b in (cfg.get('component_docs_cdn') or []) if b.get('id') == 'daisyui_components'), None)
	if not block:
		return []
	mapping: dict[str, str] = dict(block.get('map') or {})
	# Related companions so chrome/component packs are not a single card
	companions: dict[str, list[str]] = {
		'button': ['button', 'dropdown', 'badge', 'loading'],
		'modal': ['modal', 'drawer', 'alert', 'toast'],
		'navbar': ['navbar', 'menu', 'dropdown', 'drawer'],
		'menu': ['menu', 'navbar', 'dropdown'],
		'drawer': ['drawer', 'menu', 'navbar'],
		'card': ['card', 'badge', 'stat'],
		# form controls — ≥4 so chrome min_pattern soft-stop can fire
		'input': ['input', 'select', 'checkbox', 'toggle', 'textarea', 'label'],
		'textarea': ['textarea', 'input', 'label', 'fieldset'],
		'checkbox': ['checkbox', 'toggle', 'input', 'select'],
		'toggle': ['toggle', 'checkbox', 'input', 'badge'],
		'select': ['select', 'input', 'dropdown', 'checkbox'],
		'fieldset': ['fieldset', 'input', 'label', 'checkbox'],
		'label': ['label', 'input', 'fieldset', 'textarea'],
		'file-input': ['file-input', 'input', 'label', 'button'],
		'range': ['range', 'input', 'label', 'badge'],
		'footer': ['footer', 'link', 'hero'],
		'hero': ['hero', 'button', 'card'],
		'tab': ['tab', 'menu', 'badge'],
		'toast': ['toast', 'alert', 'badge'],
		'alert': ['alert', 'toast', 'badge'],
	}
	text = (query or '').lower()
	slugs: list[str] = []
	seen: set[str] = set()
	# Longer keys first (mega menu before menu)
	for key in sorted(mapping.keys(), key=len, reverse=True):
		if key in text:
			slug = mapping[key]
			bundle = companions.get(slug, [slug])
			for s in bundle:
				if s not in seen:
					seen.add(s)
					slugs.append(s)
	return slugs[:6]


def select_specialist_targets(query: str, *, scope: str | None = None) -> list[dict[str, Any]]:
	"""Pick specialist galleries by keyword match (navbar → navbar.gallery, etc.)."""
	_ = scope  # reserved for future soft weighting
	text = (query or '').lower()
	cfg = load_pattern_sources()
	out: list[dict[str, Any]] = []
	search_ask = any(
		x in text for x in ('search bar', 'search field', 'search input', 'search box', 'site search')
	)
	_BUTTON_ONLY = {'button', 'btn', 'hover', 'cta', 'primary button', 'button hover'}
	for g in cfg.get('specialist_galleries') or []:
		match = [str(m).lower() for m in (g.get('match') or [])]
		if not match or not any(m in text for m in match):
			continue
		# Search-bar asks: skip pure button chrome galleries
		if search_ask and match and set(match) <= _BUTTON_ONLY:
			continue
		out.append(dict(g))
	# Sticky winners first when present
	try:
		from navigation.inspiration_intelligence.source_affinity import (
			affinity_key,
			prefer_providers,
		)

		key = affinity_key(scope=scope or 'component', query=query)
		prefer = prefer_providers(key)
		if prefer:
			rank = {pid: i for i, pid in enumerate(prefer)}
			out.sort(key=lambda g: rank.get(str(g.get('id') or ''), 99))
	except Exception:
		pass
	return out


# Intent → always-include specialists (web-empty / thin-pack rescue)
_INTENT_FORCE_SPECIALISTS: dict[str, tuple[str, ...]] = {
	'auth': ('saasframe_login', 'saasframe_signup', 'nicelydone_auth'),
	'checkout': ('saasframe_checkout',),
}


def force_specialists_for_intent(intent_class: str) -> list[dict[str, Any]]:
	"""Return auth/checkout specialists even when query keywords miss."""
	ids = _INTENT_FORCE_SPECIALISTS.get((intent_class or '').strip().lower()) or ()
	if not ids:
		return []
	cfg = load_pattern_sources()
	by_id = {str(g.get('id') or ''): dict(g) for g in (cfg.get('specialist_galleries') or [])}
	return [by_id[i] for i in ids if i in by_id]


def select_section_doc_targets(query: str) -> list[dict[str, Any]]:
	"""Docs pages with extractable thumbs (Flowbite etc.) — wired after specialists."""
	text = (query or '').lower()
	cfg = load_pattern_sources()
	out: list[dict[str, Any]] = []
	for g in cfg.get('section_doc_pages') or []:
		match = [str(m).lower() for m in (g.get('match') or [])]
		if not match or not any(m in text for m in match):
			continue
		row = dict(g)
		row.setdefault('extract', 'any_img')
		out.append(row)
	return out


async def _fetch_gallery(url: str, *, timeout: float, extract: str, limit: int) -> tuple[list[str], float, str | None]:
	t0 = time.perf_counter()
	try:
		html, status, err = await asyncio.to_thread(http_get, url, timeout=timeout, max_bytes=120_000)
	except Exception as exc:  # noqa: BLE001
		return [], (time.perf_counter() - t0) * 1000.0, str(exc)
	ms = (time.perf_counter() - t0) * 1000.0
	if err and not html:
		return [], ms, err
	if status and status >= 400 and not html:
		return [], ms, f'http_{status}'
	previews = extract_pattern_previews(html or '', extract=extract, limit=limit)
	return previews, ms, None


async def acquire_pattern_inspiration(
	query: str,
	*,
	max_visuals: int = 8,
	concurrency: int = 6,
	timeout_s: float = 2.5,
) -> PatternAcquireResult:
	"""Concurrent specialist gallery + direct CDN acquire for component/section/chrome."""
	t0 = time.perf_counter()
	flex = resolve_flexible_query(query)
	result = PatternAcquireResult(query=query, scope=flex.scope, elapsed_ms=0.0)

	if is_font_query(query):
		cfg = load_pattern_sources().get('font_policy') or {}
		result.font_route = {
			'route': cfg.get('route') or 'resource_intelligence',
			'tools': list(cfg.get('tools') or ['perception_resource_font_search']),
			'message': (
				'Font/typeface asks use Resource Intelligence '
				'(perception_resource_font_search). Inspiration galleries are a weak fit.'
			),
		}
		result.degraded.append('font_routed_to_resource_intelligence')
		result.elapsed_ms = (time.perf_counter() - t0) * 1000.0
		return result

	hits: list[PatternHit] = []
	seen_preview: set[str] = set()

	# 1) Direct daisy CDN — instant, reliable chrome/component stills
	daisy = next(
		(b for b in (load_pattern_sources().get('component_docs_cdn') or []) if b.get('id') == 'daisyui_components'),
		None,
	)
	if daisy and flex.scope in {'component', 'chrome', 'section'}:
		base = str(daisy.get('base') or '')
		docs = str(daisy.get('docs') or '')
		for slug in resolve_daisy_slugs(query):
			preview = base.replace('{slug}', slug)
			doc_url = docs.replace('{slug}', slug)
			key = preview.split('?')[0].lower()
			if key in seen_preview:
				continue
			seen_preview.add(key)
			hits.append(
				PatternHit(
					provider_id='daisyui',
					candidate_id=f'pattern:daisyui:{slug}',
					title=f'daisyUI {slug}',
					url=doc_url,
					preview_url=preview,
					source_kind='pattern_cdn',
					fetch_tier='direct_cdn',
					degraded=['pattern:daisyui_cdn'],
				)
			)
			result.targets.append(f'daisyui:{slug}')
			if len(hits) >= max_visuals:
				break

	# 2) Specialist galleries + docs pages concurrent
	galleries = select_specialist_targets(query, scope=flex.scope)
	# Auth/checkout: always include category specialists (keyword miss / web-empty rescue)
	if flex.intent_class in {'auth', 'checkout'}:
		seen_g = {str(g.get('id') or '') for g in galleries}
		for g in force_specialists_for_intent(flex.intent_class):
			gid = str(g.get('id') or '')
			if gid and gid not in seen_g:
				galleries.append(g)
				seen_g.add(gid)
	docs = select_section_doc_targets(query)
	# Prefer real galleries first; docs fill gaps
	targets = list(galleries) + [d for d in docs if d.get('id') not in {g.get('id') for g in galleries}]

	sem = asyncio.Semaphore(max(1, concurrency))

	async def _one(g: dict[str, Any]) -> None:
		nonlocal hits
		url = str(g.get('url') or '')
		gid = str(g.get('id') or 'pattern')
		if not url.startswith('http'):
			return
		async with sem:
			previews, ms, err = await _fetch_gallery(
				url,
				timeout=timeout_s,
				extract=str(g.get('extract') or 'webflow_cdn'),
				limit=max(4, max_visuals),
			)
		result.timing.append(
			{'source_id': gid, 'elapsed_ms': round(ms, 1), 'ok': bool(previews), 'count': len(previews), 'error': err}
		)
		result.targets.append(gid)
		if err and not previews:
			result.degraded.append(f'{gid}:{err}'[:80])
			return
		title_base = str(g.get('title') or gid)
		for i, preview in enumerate(previews):
			if len(hits) >= max_visuals:
				return
			key = preview.split('?')[0].lower()
			if key in seen_preview:
				continue
			# Skip generic Flowbite OG shared across all docs
			if 'flowbite.com/docs/images/og-image' in key:
				continue
			seen_preview.add(key)
			hits.append(
				PatternHit(
					provider_id=gid,
					candidate_id=f'pattern:{gid}:{i}',
					title=f'{title_base} #{i + 1}',
					url=url,
					preview_url=preview,
					source_kind='pattern_gallery',
					fetch_tier='pattern_http',
					degraded=[f'pattern:{gid}'],
				)
			)

	if targets and len(hits) < max_visuals:
		await asyncio.gather(*[_one(g) for g in targets])

	result.hits = hits[:max_visuals]
	# Drop dead thumbs before soft-stop counts them (fail-open if all drop)
	if result.hits:
		from navigation.inspiration_intelligence.preview_validate import filter_valid_previews

		kept, deg = await filter_valid_previews(result.hits, concurrency=max(4, concurrency))
		result.degraded.extend(deg)
		if kept:
			result.hits = list(kept)[:max_visuals]
		else:
			result.degraded.append('preview_validate_all_failed_kept_raw')
	if not result.hits and flex.scope in {'component', 'section', 'chrome'}:
		result.degraded.append('pattern_acquire_empty')
	result.elapsed_ms = (time.perf_counter() - t0) * 1000.0
	return result
