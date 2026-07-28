"""Famous-site corpus loader — live screenshot channel targets."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_CORPUS_PATH = Path(__file__).resolve().parent / 'data' / 'famous_sites_corpus.json'

# Prefer softer hosts first — these often burn Chromium on bot challenges.
_HARD_WAF_HOSTS = (
	'stripe.com',
	'vercel.com',
	'figma.com',
	'notion.so',
	'apple.com',
	'shopify.com',
	'datadoghq.com',
)


@lru_cache(maxsize=1)
def load_famous_sites_corpus() -> dict[str, Any]:
	if not _CORPUS_PATH.is_file():
		return {'schema': 'famous_sites_corpus.v1', 'categories': {}, 'defaults': {}}
	return json.loads(_CORPUS_PATH.read_text(encoding='utf-8'))


def _host(url: str) -> str:
	try:
		return (urlparse(url).netloc or '').lower().removeprefix('www.')
	except Exception:
		return ''


def _waf_risk(url: str) -> bool:
	h = _host(url)
	return any(h == w or h.endswith('.' + w) for w in _HARD_WAF_HOSTS)


def select_famous_sites(
	categories: list[str],
	*,
	max_sites: int = 2,
	prefer_soft: bool = True,
) -> list[dict[str, str]]:
	"""Pick curated live-site targets for the given category keys.

	Soft sites (lower WAF risk) are preferred so Chromium budget is not burned
	on Stripe/Vercel/Figma challenge pages first.
	"""
	corpus = load_famous_sites_corpus()
	cats = corpus.get('categories') or {}
	seen: set[str] = set()
	soft: list[dict[str, str]] = []
	hard: list[dict[str, str]] = []
	for cat in categories:
		bucket = cats.get(cat) or {}
		for site in bucket.get('sites') or []:
			sid = str(site.get('id') or site.get('url') or '')
			if not sid or sid in seen:
				continue
			seen.add(sid)
			row = {
				'id': sid,
				'url': str(site.get('url') or ''),
				'title': str(site.get('title') or sid),
				'category': cat,
				'source_kind': 'live_site',
			}
			if prefer_soft and _waf_risk(row['url']):
				hard.append(row)
			else:
				soft.append(row)
	picked: list[dict[str, str]] = []
	for row in soft + hard:
		picked.append(row)
		if len(picked) >= max(1, max_sites):
			break
	return picked


def famous_site_hit_sketch(
	site: dict[str, str],
	*,
	screenshot_blob: str = '',
	page_title: str = '',
) -> dict[str, Any]:
	"""Manifest hit shape for channel B (live_site)."""
	return {
		'source_kind': 'live_site',
		'provider_id': 'famous_site',
		'candidate_id': f"live_site:{site.get('id') or ''}",
		'title': page_title or site.get('title') or '',
		'url': site.get('url') or '',
		'external_id': site.get('id') or '',
		'preview_url': '',
		'screenshot_blob': screenshot_blob,
		'category': site.get('category') or '',
		'capture': 'viewport',
	}
