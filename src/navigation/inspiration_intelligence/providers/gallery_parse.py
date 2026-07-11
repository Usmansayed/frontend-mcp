"""HTTP parsers for gallery inspiration sites."""
from __future__ import annotations

import re
import urllib.parse
from html import unescape

from navigation.inspiration_intelligence.providers.dribbble.parser import query_to_slug

_GALLERY = re.compile(r'href="(https?://[^"]*/gallery/(\d+)[^"]*)"', re.I)
_AWWWARDS = re.compile(r'href="(https?://[^"]*awwwards\.com/sites/([^"/?#]+)[^"]*)"', re.I)
_SITEINSPIRE = re.compile(r'href="(/website/(\d+)[^"]*|https?://[^"]*siteinspire\.com/website/(\d+)[^"]*)"', re.I)
_GODLY = re.compile(r'href="(https?://godly\.website/website/([^"/?#]+)[^"]*)"', re.I)
_LANDBOOK = re.compile(
	r'href="(https?://[^"]*land-book\.com/(?:design|designs)/([^"/?#]+)[^"]*)"',
	re.I,
)
_OPL_LINK = re.compile(r'href="(https://onepagelove\.com/([a-z0-9-]+))"', re.I)
_OPL_ASSET = re.compile(
	r'https://assets\.onepagelove\.com/cdn-cgi/image/[^"\s]+/wp-content/uploads/[^"\s]+\.jpg',
	re.I,
)

_OPL_RESERVED = frozenset({
	'about',
	'api',
	'articles',
	'feed',
	'inspiration',
	'templates',
	'framer-templates',
	'free-landing-page-templates',
	'claude',
	'genre',
	'category',
	'platform',
	'tag',
	'submit',
	'advertise',
	'contact',
	'privacy',
	'terms',
	'go',
	'sections',
	'page-sections',
	'builder',
	'hosting',
	'newsletter',
	'search',
	'login',
	'signup',
	'api-signup',
})

OPL_RESERVED_SLUGS = _OPL_RESERVED


def _title_near(html: str, pos: int, fallback: str) -> str:
	window = html[max(0, pos - 350) : min(len(html), pos + 350)]
	for pattern in (
		re.compile(r'title="([^"]+)"', re.I),
		re.compile(r'aria-label="([^"]+)"', re.I),
		re.compile(r'alt="([^"]+)"', re.I),
	):
		match = pattern.search(window)
		if match:
			return unescape(match.group(1).strip())
	return unescape(fallback.replace('-', ' ').strip())


def _preview_near(html: str, pos: int) -> str:
	window = html[max(0, pos - 500) : min(len(html), pos + 500)]
	img = re.search(r'src="([^"]+)"', window, re.I)
	return unescape(img.group(1)) if img else ''


def parse_behance_html(html: str, base_url: str) -> list[dict[str, str]]:
	seen: set[str] = set()
	hits: list[dict[str, str]] = []
	for match in _GALLERY.finditer(html):
		url, gallery_id = match.group(1), match.group(2)
		if gallery_id in seen:
			continue
		seen.add(gallery_id)
		hits.append(
			{
				'external_id': gallery_id,
				'title': _title_near(html, match.start(), gallery_id),
				'url': url.split('"')[0],
				'preview_url': _preview_near(html, match.start()),
			}
		)
	return hits


def parse_awwwards_html(html: str, base_url: str) -> list[dict[str, str]]:
	seen: set[str] = set()
	hits: list[dict[str, str]] = []
	for match in _AWWWARDS.finditer(html):
		url, external_id = match.group(1), match.group(2)
		if external_id in seen:
			continue
		seen.add(external_id)
		hits.append(
			{
				'external_id': external_id,
				'title': _title_near(html, match.start(), external_id),
				'url': url.split('"')[0],
				'preview_url': _preview_near(html, match.start()),
			}
		)
	return hits


def parse_siteinspire_html(html: str, base_url: str) -> list[dict[str, str]]:
	seen: set[str] = set()
	hits: list[dict[str, str]] = []
	base = urllib.parse.urlparse(base_url)
	origin = f'{base.scheme}://{base.netloc}'
	for match in _SITEINSPIRE.finditer(html):
		path, id_a, id_b = match.group(1), match.group(2), match.group(3)
		external_id = id_a or id_b or ''
		if not external_id or external_id in seen:
			continue
		seen.add(external_id)
		url = path if path.startswith('http') else urllib.parse.urljoin(origin, path)
		hits.append(
			{
				'external_id': external_id,
				'title': _title_near(html, match.start(), external_id),
				'url': url.split('"')[0],
				'preview_url': _preview_near(html, match.start()),
			}
		)
	return hits


def parse_godly_html(html: str, base_url: str) -> list[dict[str, str]]:
	seen: set[str] = set()
	hits: list[dict[str, str]] = []
	for match in _GODLY.finditer(html):
		url, external_id = match.group(1), match.group(2)
		if external_id in seen:
			continue
		seen.add(external_id)
		hits.append(
			{
				'external_id': external_id,
				'title': _title_near(html, match.start(), external_id),
				'url': url.split('"')[0],
				'preview_url': _preview_near(html, match.start()),
			}
		)
	return hits


def parse_landbook_html(html: str, base_url: str) -> list[dict[str, str]]:
	seen: set[str] = set()
	hits: list[dict[str, str]] = []
	for match in _LANDBOOK.finditer(html):
		url, external_id = match.group(1), match.group(2)
		if external_id in seen or external_id in {'design', 'designs'}:
			continue
		seen.add(external_id)
		hits.append(
			{
				'external_id': external_id,
				'title': _title_near(html, match.start(), external_id),
				'url': url.split('"')[0],
				'preview_url': _preview_near(html, match.start()),
			}
		)
	return hits


def _opl_preview(window: str) -> str:
	matches = _OPL_ASSET.findall(window)
	if matches:
		return unescape(max(matches, key=len))
	return ''


def parse_onepagelove_html(html: str, base_url: str) -> list[dict[str, str]]:
	seen: set[str] = set()
	hits: list[dict[str, str]] = []
	for match in _OPL_LINK.finditer(html):
		url, slug = match.group(1), match.group(2)
		if slug in _OPL_RESERVED or slug in seen:
			continue
		window = html[max(0, match.start() - 800) : min(len(html), match.end() + 800)]
		preview = _opl_preview(window)
		if not preview:
			continue
		seen.add(slug)
		hits.append(
			{
				'external_id': slug,
				'title': _title_near(html, match.start(), slug),
				'url': url,
				'preview_url': preview,
			}
		)
	return hits


def behance_search_urls(query: str) -> list[str]:
	encoded = urllib.parse.quote(query.strip())
	return [f'https://www.behance.net/search/projects?search={encoded}']


def awwwards_search_urls(query: str) -> list[str]:
	slug = query_to_slug(query)
	return [
		f'https://www.awwwards.com/websites/?search={slug}',
		'https://www.awwwards.com/websites/',
	]


def siteinspire_search_urls(query: str) -> list[str]:
	encoded = urllib.parse.quote(query.strip())
	return [
		f'https://www.siteinspire.com/search?q={encoded}',
		f'https://www.siteinspire.com/websites',
	]


def godly_search_urls(query: str) -> list[str]:
	_ = query_to_slug(query)
	# godly.website redirects to recent.design (2026)
	return [
		'https://recent.design/websites',
		'https://recent.design/',
	]


def landbook_search_urls(query: str) -> list[str]:
	q = query.strip().lower()
	urls: list[str] = []
	if 'landing' in q or 'saas' in q:
		urls.append('https://land-book.com/design/landing-page')
	if 'saas' in q or 'dashboard' in q:
		urls.append('https://land-book.com/design/website')
	urls.extend([
		'https://land-book.com/design/landing-page',
		'https://land-book.com/',
	])
	return urls


def onepagelove_search_urls(query: str) -> list[str]:
	q = query.strip().lower()
	urls: list[str] = []
	token_map = {
		'saas': 'https://onepagelove.com/genre/saas',
		'dashboard': 'https://onepagelove.com/genre/saas',
		'landing': 'https://onepagelove.com/genre/landing-page',
		'portfolio': 'https://onepagelove.com/genre/portfolio',
		'app': 'https://onepagelove.com/genre/app',
		'product': 'https://onepagelove.com/genre/product',
		'minimal': 'https://onepagelove.com/genre/minimal',
		'dark': 'https://onepagelove.com/genre/dark',
	}
	for token, url in token_map.items():
		if token in q and url not in urls:
			urls.append(url)
	# Archive always has fresh content — ultimate reliable fallback
	urls.append('https://onepagelove.com/inspiration')
	return urls
