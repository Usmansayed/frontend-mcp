"""HTTP parsers for gallery inspiration sites."""
from __future__ import annotations

import re
import urllib.parse
from html import unescape

from navigation.inspiration_intelligence.providers.dribbble.parser import query_to_slug
from navigation.inspiration_intelligence.tools.media_urls import normalize_image_url

_GALLERY = re.compile(r'href="(https?://[^"]*/gallery/(\d+)[^"]*)"', re.I)
# Absolute or relative /sites/{slug}
_AWWWARDS = re.compile(
	r'href="((?:https?://(?:www\.)?awwwards\.com)?/sites/([^"/?#]+)[^"]*)"',
	re.I,
)
_SITEINSPIRE = re.compile(
	r'href="(/website/(\d+)[^"]*|https?://[^"]*siteinspire\.com/website/(\d+)[^"]*)"',
	re.I,
)
# recent.design / godly.website cards: /i/{id}-{slug}
_GODLY = re.compile(
	r'href="((?:https?://(?:www\.)?(?:recent\.design|godly\.website))?/i/([^"/?#]+)[^"]*)"',
	re.I,
)
_LANDBOOK = re.compile(
	r'href="(https?://[^"]*land-book\.com/(?:design|designs)/([^"/?#]+)[^"]*)"',
	re.I,
)
_OPL_LINK = re.compile(r'href="(https://onepagelove\.com/([a-z0-9-]+))"', re.I)
_OPL_ASSET = re.compile(
	r'https://assets\.onepagelove\.com/cdn-cgi/image/[^"\s]+/wp-content/uploads/[^"\s]+\.jpg',
	re.I,
)
_SITEINSPIRE_CDN = re.compile(
	r'https://r2\.siteinspire\.com/cdn-cgi/image/[^"\s\']+',
	re.I,
)
_AWWWARDS_CDN = re.compile(
	r'https://assets\.awwwards\.com/[^"\s\']+\.(?:jpg|jpeg|png|webp)',
	re.I,
)
_BEHANCE_CDN = re.compile(
	r'https://mir-s3-cdn-cf\.behance\.net/(?:project_modules|projects)/[^"\s\']+',
	re.I,
)
_RECENT_CDN = re.compile(
	r'https://cdn\.recent\.design/[^"\s\']+',
	re.I,
)
_LAPA_POST = re.compile(r'href="(/post/([a-z0-9-]+)/)"', re.I)
_LAPA_CDN = re.compile(
	r'https://cdn\.lapa\.ninja/assets/images/(?:1x|2x)/[a-z0-9-]+-thumb\.(?:jpg|jpeg|png|webp)',
	re.I,
)
_HTTPSTER_ARTICLE = re.compile(
	r'<article\s+class="Preview"[^>]*>(.*?)</article>',
	re.I | re.S,
)
_HTTPSTER_IMG = re.compile(
	r'Preview__img[^>]*\ssrc="((?:https://httpster\.net)?/assets/media/[^"]+\.(?:webp|jpg|jpeg|png))"',
	re.I,
)
_HTTPSTER_TITLE = re.compile(
	r'Preview__title[^>]*\shref="(/website/([a-z0-9-]+)/)"[^>]*>([^<]*)',
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
	'letters',
	'search',
	'login',
	'signup',
	'api-signup',
	# Category / listing pages that look like design refs but are not
	'gallery',
	'og-gallery',
	'lo-fi-feed',
	'lofi-feed',
	'archive',
	'collections',
	'collection',
	'awards',
	'features',
	'featured',
	'blog',
	'news',
	'resources',
	'pricing',
	'jobs',
	'advertise-with-us',
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


def _preview_near(html: str, pos: int, *, cdn_patterns: list[re.Pattern[str]] | None = None) -> str:
	"""Prefer real CDN image URLs; skip data: placeholders and tiny icons."""
	window = html[max(0, pos - 1200) : min(len(html), pos + 1200)]
	for pattern in cdn_patterns or []:
		found = pattern.findall(window)
		if found:
			return normalize_image_url(unescape(max(found, key=len)))
	# srcset first (often has the real thumb while src is a data-URI)
	srcset = re.search(r'srcset="([^"]+)"', window, re.I)
	if srcset:
		candidate = normalize_image_url(unescape(srcset.group(1)))
		if candidate.startswith('http') and not candidate.startswith('data:'):
			return candidate
	for img in re.finditer(r'(?:src|data-src|data-lazy-src)="([^"]+)"', window, re.I):
		src = unescape(img.group(1)).strip()
		if not src or src.startswith('data:') or len(src) < 12:
			continue
		if src.startswith('//'):
			src = 'https:' + src
		if src.startswith('http'):
			return normalize_image_url(src)
	return ''


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
				'preview_url': _preview_near(html, match.start(), cdn_patterns=[_BEHANCE_CDN]),
			}
		)
	return hits


def parse_awwwards_html(html: str, base_url: str) -> list[dict[str, str]]:
	seen: set[str] = set()
	hits: list[dict[str, str]] = []
	base = urllib.parse.urlparse(base_url)
	origin = (
		f'{base.scheme}://{base.netloc}'
		if base.scheme and base.netloc
		else 'https://www.awwwards.com'
	)
	for match in _AWWWARDS.finditer(html):
		path, external_id = match.group(1), match.group(2)
		if external_id in seen or external_id in {'websites', 'sites'}:
			continue
		seen.add(external_id)
		url = path if path.startswith('http') else urllib.parse.urljoin(origin, path)
		hits.append(
			{
				'external_id': external_id,
				'title': _title_near(html, match.start(), external_id),
				'url': url.split('"')[0].split('?')[0],
				'preview_url': _preview_near(html, match.start(), cdn_patterns=[_AWWWARDS_CDN]),
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
				'preview_url': _preview_near(html, match.start(), cdn_patterns=[_SITEINSPIRE_CDN]),
			}
		)
	return hits


def parse_godly_html(html: str, base_url: str) -> list[dict[str, str]]:
	seen: set[str] = set()
	hits: list[dict[str, str]] = []
	base = urllib.parse.urlparse(base_url)
	origin = (
		f'{base.scheme}://{base.netloc}'
		if base.scheme and base.netloc
		else 'https://recent.design'
	)
	for match in _GODLY.finditer(html):
		path, external_id = match.group(1), match.group(2)
		if external_id in seen:
			continue
		seen.add(external_id)
		url = path if path.startswith('http') else urllib.parse.urljoin(origin, path)
		title_fallback = external_id.split('-', 1)[-1] if '-' in external_id else external_id
		hits.append(
			{
				'external_id': external_id,
				'title': _title_near(html, match.start(), title_fallback),
				'url': url.split('"')[0].split('?')[0],
				'preview_url': _preview_near(html, match.start(), cdn_patterns=[_RECENT_CDN]),
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


def parse_lapa_html(html: str, base_url: str) -> list[dict[str, str]]:
	"""Parse Lapa Ninja post cards with CDN thumbs (HTTP-reliable)."""
	seen: set[str] = set()
	hits: list[dict[str, str]] = []
	base = urllib.parse.urlparse(base_url)
	origin = (
		f'{base.scheme}://{base.netloc}'
		if base.scheme and base.netloc
		else 'https://www.lapa.ninja'
	)
	for match in _LAPA_POST.finditer(html):
		path, external_id = match.group(1), match.group(2)
		if external_id in seen:
			continue
		window = html[max(0, match.start() - 1600) : min(len(html), match.start() + 400)]
		cdn = _LAPA_CDN.findall(window)
		if not cdn:
			continue
		# Prefer 2x when both tiers appear in the card window.
		preview = next((u for u in reversed(cdn) if '/2x/' in u), cdn[-1])
		seen.add(external_id)
		hits.append(
			{
				'external_id': external_id,
				'title': _title_near(html, match.start(), external_id),
				'url': urllib.parse.urljoin(origin, path),
				'preview_url': normalize_image_url(unescape(preview)),
			}
		)
	return hits


def parse_httpster_html(html: str, base_url: str) -> list[dict[str, str]]:
	"""Parse Httpster article.Preview cards (local /assets/media thumbs)."""
	seen: set[str] = set()
	hits: list[dict[str, str]] = []
	base = urllib.parse.urlparse(base_url)
	origin = (
		f'{base.scheme}://{base.netloc}'
		if base.scheme and base.netloc
		else 'https://httpster.net'
	)
	for article in _HTTPSTER_ARTICLE.finditer(html):
		block = article.group(1)
		title_m = _HTTPSTER_TITLE.search(block)
		img_m = _HTTPSTER_IMG.search(block)
		if not title_m or not img_m:
			continue
		path, external_id, title = title_m.group(1), title_m.group(2), title_m.group(3)
		if external_id in seen:
			continue
		preview = unescape(img_m.group(1).strip())
		if preview.startswith('/'):
			preview = urllib.parse.urljoin(origin, preview)
		seen.add(external_id)
		hits.append(
			{
				'external_id': external_id,
				'title': unescape(title.strip()) or external_id.replace('-', ' '),
				'url': urllib.parse.urljoin(origin, path),
				'preview_url': normalize_image_url(preview),
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
		'https://www.siteinspire.com/websites',
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


def lapa_search_urls(query: str) -> list[str]:
	"""Category/year browse — free-text ?s= is ignored by the site."""
	q = query.strip().lower()
	urls: list[str] = []
	token_map = {
		'saas': 'https://www.lapa.ninja/category/saas/',
		'dashboard': 'https://www.lapa.ninja/category/saas/',
		'analytics': 'https://www.lapa.ninja/category/saas/',
		'app': 'https://www.lapa.ninja/category/app/',
		'portfolio': 'https://www.lapa.ninja/category/portfolio/',
		'agency': 'https://www.lapa.ninja/category/agency/',
		'ecommerce': 'https://www.lapa.ninja/category/ecommerce/',
		'shop': 'https://www.lapa.ninja/category/ecommerce/',
		'product': 'https://www.lapa.ninja/category/product/',
		'startup': 'https://www.lapa.ninja/category/saas/',
		'ai': 'https://www.lapa.ninja/category/artificial-intelligence/',
		'fintech': 'https://www.lapa.ninja/category/saas/',
		'finance': 'https://www.lapa.ninja/category/saas/',
	}
	for token, url in token_map.items():
		if token in q and url not in urls:
			urls.append(url)
	# Fresh curated archives — always populated
	urls.extend([
		'https://www.lapa.ninja/year/2026/',
		'https://www.lapa.ninja/',
	])
	return urls


def httpster_search_urls(query: str) -> list[str]:
	"""Type/style browse — no free-text search on Httpster."""
	q = query.strip().lower()
	urls: list[str] = []
	type_map = {
		'saas': 'https://httpster.net/type/application-or-software/',
		'app': 'https://httpster.net/type/application-or-software/',
		'software': 'https://httpster.net/type/application-or-software/',
		'dashboard': 'https://httpster.net/type/application-or-software/',
		'product': 'https://httpster.net/type/product/',
		'shop': 'https://httpster.net/type/online-store/',
		'ecommerce': 'https://httpster.net/type/online-store/',
		'store': 'https://httpster.net/type/online-store/',
		'finance': 'https://httpster.net/type/finance/',
		'fintech': 'https://httpster.net/type/finance/',
		'portfolio': 'https://httpster.net/type/showcase/',
		'agency': 'https://httpster.net/type/service/',
	}
	style_map = {
		'minimal': 'https://httpster.net/style/minimal/',
		'dark': 'https://httpster.net/style/dark/',
		'brutalist': 'https://httpster.net/style/brutalist/',
		'colourful': 'https://httpster.net/style/colourful/',
		'colorful': 'https://httpster.net/style/colourful/',
		'grid': 'https://httpster.net/style/grid/',
	}
	for token, url in type_map.items():
		if token in q and url not in urls:
			urls.append(url)
	for token, url in style_map.items():
		if token in q and url not in urls:
			urls.append(url)
	urls.append('https://httpster.net/')
	return urls
