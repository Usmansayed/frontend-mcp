"""Open-web search for inspiration URL discovery (DuckDuckGo HTML).

Not Google SERP scraping. Results are candidates for OG thumbs and/or
viewport screenshots — search itself is discovery, not the visual ref.
"""
from __future__ import annotations

import html as html_lib
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from navigation.inspiration_intelligence.browser.fetch import http_get

_RESULT_A = re.compile(
	r'<a[^>]*class=["\']result__a["\'][^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
	re.I | re.S,
)

# Domains that are ads, search chrome, or weak as live inspiration targets.
_BLOCK_HOST_FRAGMENTS = (
	'duckduckgo.',
	'bing.com',
	'microsoft.com',
	'google.',
	'yahoo.com',
	'yandex.',
	'facebook.com',
	'twitter.com',
	'x.com',
	'instagram.com',
	'linkedin.com',
	'youtube.com',
	'youtu.be',
	'wikipedia.org',
	'amazon.',
	'ebay.',
)

# Prefer design-ish hosts when ranking (soft boost, not hard filter).
_PREFER_HOST_FRAGMENTS = (
	'dribbble.com',
	'behance.net',
	'awwwards.com',
	'land-book.com',
	'onepagelove.com',
	'siteinspire.com',
	'navbar.gallery',
	'footer.design',
	'hero.gallery',
	'godly.website',
	'httpster.net',
	'lapa.ninja',
	'webflow.com',
	'framer.com',
	'figma.com',
	'ui.shadcn.com',
	'shadcn',
	'daisyui.com',
	'tailwindui.com',
	'mobbin.com',
	'saasframe',
	'saaspo.com',
	'landing.love',
	'pinterest.com',
	'css-tricks.com',
	'smashingmagazine.com',
)


@dataclass
class WebSearchHit:
	title: str
	url: str
	host: str
	rank: int = 0
	score: float = 0.0

	def to_dict(self) -> dict[str, Any]:
		return asdict(self)


@dataclass
class WebSearchResult:
	query: str
	engine: str
	elapsed_ms: float
	hits: list[WebSearchHit] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'query': self.query,
			'engine': self.engine,
			'elapsed_ms': round(self.elapsed_ms, 1),
			'hits': [h.to_dict() for h in self.hits],
			'degraded': list(self.degraded),
		}


def _unwrap_ddg_href(href: str) -> str:
	"""Resolve DuckDuckGo redirect (`uddg=`) to the destination URL."""
	href = (href or '').strip()
	if not href:
		return ''
	if href.startswith('//'):
		href = 'https:' + href
	parsed = urlparse(href)
	qs = parse_qs(parsed.query)
	if 'uddg' in qs and qs['uddg']:
		dest = unquote(qs['uddg'][0])
	else:
		dest = href
	# Ads / click trackers
	if 'duckduckgo.com/y.js' in dest or 'bing.com/aclick' in dest:
		return ''
	for _ in range(3):
		if '%' in dest and dest.startswith('http'):
			nxt = unquote(dest)
			if nxt == dest:
				break
			dest = nxt
		else:
			break
	return dest.strip()


def _host(url: str) -> str:
	try:
		return (urlparse(url).netloc or '').lower()
	except Exception:
		return ''


def _blocked(host: str) -> bool:
	h = (host or '').lower()
	return any(b in h for b in _BLOCK_HOST_FRAGMENTS)


def _prefer_boost(host: str) -> float:
	h = (host or '').lower()
	return 2.0 if any(p in h for p in _PREFER_HOST_FRAGMENTS) else 0.0


def craft_inspiration_search_query(query: str, *, scope: str = 'page') -> str:
	"""Bias SERP toward visual UI examples without hard-limiting domains."""
	q = (query or '').strip()
	if not q:
		return 'ui design inspiration'
	low = q.lower()
	# Already looks like an inspiration query
	if any(x in low for x in ('inspiration', 'examples', 'gallery', 'showcase', 'ui design')):
		base = q
	elif scope in {'component', 'chrome'}:
		base = f'{q} ui component design examples showcase'
	elif scope == 'section':
		base = f'{q} website section design examples'
	else:
		base = f'{q} website design inspiration'
	return base


def parse_duckduckgo_html(html: str) -> list[WebSearchHit]:
	"""Extract organic results from DuckDuckGo HTML endpoint markup."""
	out: list[WebSearchHit] = []
	seen_host: set[str] = set()
	seen_url: set[str] = set()
	for href, title_html in _RESULT_A.findall(html or ''):
		title = html_lib.unescape(re.sub(r'<[^>]+>', '', title_html)).strip()
		url = _unwrap_ddg_href(href)
		if not url.startswith('http'):
			continue
		host = _host(url)
		if not host or _blocked(host):
			continue
		# Dedupe by host first (variety of sites), then exact URL
		if host in seen_host or url in seen_url:
			continue
		seen_host.add(host)
		seen_url.add(url)
		score = 10.0 - len(out) + _prefer_boost(host)
		out.append(
			WebSearchHit(title=title[:160], url=url, host=host, rank=len(out), score=score)
		)
	out.sort(key=lambda h: h.score, reverse=True)
	for i, h in enumerate(out):
		h.rank = i
	return out


def search_duckduckgo(
	query: str,
	*,
	limit: int = 8,
	timeout_s: float = 8.0,
	aliases: list[str] | tuple[str, ...] | None = None,
) -> WebSearchResult:
	"""DuckDuckGo HTML search — no API key. Fail soft on network/blocks.

	If the primary query returns no organic hits, retry up to two aliases
	(query_flex search_aliases / rewritten terms).
	"""
	t0 = time.perf_counter()
	primary = _search_duckduckgo_once(query, limit=limit, timeout_s=timeout_s)
	if primary.hits:
		primary.elapsed_ms = (time.perf_counter() - t0) * 1000.0
		return primary
	for alias in list(aliases or [])[:2]:
		alias_q = (alias or '').strip()
		if not alias_q or alias_q.lower() == (query or '').strip().lower():
			continue
		alt = _search_duckduckgo_once(alias_q, limit=limit, timeout_s=timeout_s)
		if alt.hits:
			alt.degraded = list(primary.degraded) + list(alt.degraded) + [
				f'ddg_alias_retry:{alias_q[:80]}'
			]
			alt.query = query
			alt.elapsed_ms = (time.perf_counter() - t0) * 1000.0
			return alt
	primary.elapsed_ms = (time.perf_counter() - t0) * 1000.0
	return primary


def _search_duckduckgo_once(
	query: str,
	*,
	limit: int = 8,
	timeout_s: float = 8.0,
) -> WebSearchResult:
	"""Single DDG HTML fetch (no alias cascade)."""
	t0 = time.perf_counter()
	result = WebSearchResult(query=query, engine='duckduckgo_html', elapsed_ms=0.0)
	q = (query or '').strip()
	if not q:
		result.degraded.append('web_search_empty_query')
		result.elapsed_ms = (time.perf_counter() - t0) * 1000.0
		return result

	from urllib.parse import quote

	url = f'https://html.duckduckgo.com/html/?q={quote(q)}'
	try:
		html, status, err = http_get(url, timeout=timeout_s, max_bytes=200_000)
	except Exception as exc:  # noqa: BLE001
		result.degraded.append(f'web_search_fetch_failed:{exc}')
		result.elapsed_ms = (time.perf_counter() - t0) * 1000.0
		return result

	if err and not html:
		result.degraded.append(f'web_search_error:{err}')
	if status and status >= 400 and not html:
		result.degraded.append(f'web_search_http_{status}')

	hits = parse_duckduckgo_html(html or '')
	# Fallback: looser link scrape when result__a markup is empty/changed
	if not hits:
		loose = _parse_ddg_loose_links(html or '')
		if loose:
			hits = loose
			result.degraded.append('ddg_loose_link_parse')
	if not hits:
		result.degraded.append('web_search_no_organic_results')
	result.hits = hits[: max(1, limit)]
	result.elapsed_ms = (time.perf_counter() - t0) * 1000.0
	return result


_LOOSE_A = re.compile(
	r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
	re.I | re.S,
)


def _parse_ddg_loose_links(html: str) -> list[WebSearchHit]:
	"""Last-resort parse when DDG changes result__a class names."""
	out: list[WebSearchHit] = []
	seen_host: set[str] = set()
	for href, title_html in _LOOSE_A.findall(html or ''):
		url = _unwrap_ddg_href(href)
		if not url.startswith('http'):
			continue
		host = _host(url)
		if not host or _blocked(host) or host in seen_host:
			continue
		if 'duckduckgo.com' in host:
			continue
		title = html_lib.unescape(re.sub(r'<[^>]+>', '', title_html)).strip()
		if len(title) < 3:
			continue
		seen_host.add(host)
		out.append(
			WebSearchHit(
				title=title[:160],
				url=url,
				host=host,
				rank=len(out),
				score=10.0 - len(out) + _prefer_boost(host),
			)
		)
		if len(out) >= 12:
			break
	return out


def _rank_hits(hits: list[WebSearchHit], *, limit: int) -> list[WebSearchHit]:
	for h in hits:
		h.score = 10.0 - h.rank + _prefer_boost(h.host)
	hits.sort(key=lambda h: h.score, reverse=True)
	out: list[WebSearchHit] = []
	seen: set[str] = set()
	for h in hits:
		if h.host in seen or _blocked(h.host):
			continue
		seen.add(h.host)
		h.rank = len(out)
		out.append(h)
		if len(out) >= limit:
			break
	return out


def search_serper(query: str, *, limit: int = 8, timeout_s: float = 8.0) -> WebSearchResult:
	"""Optional Serper.dev Google results — requires SERPER_API_KEY."""
	import json
	import os
	import urllib.request

	t0 = time.perf_counter()
	result = WebSearchResult(query=query, engine='serper', elapsed_ms=0.0)
	key = (os.environ.get('SERPER_API_KEY') or '').strip()
	if not key:
		result.degraded.append('serper_no_api_key')
		result.elapsed_ms = (time.perf_counter() - t0) * 1000.0
		return result
	payload = {'q': query, 'num': max(1, min(limit, 10))}
	data: dict[str, Any] | None = None
	try:
		from navigation.inspiration_intelligence.browser.http_pool import pool_post_json

		pooled = pool_post_json(
			'https://google.serper.dev/search',
			payload=payload,
			headers={'X-API-KEY': key, 'Content-Type': 'application/json'},
			timeout=timeout_s,
		)
		if pooled is not None:
			data, _status, err = pooled
			if err and not data:
				raise RuntimeError(err)
	except Exception:
		data = None
	if data is None:
		body = json.dumps(payload).encode('utf-8')
		req = urllib.request.Request(
			'https://google.serper.dev/search',
			data=body,
			headers={
				'X-API-KEY': key,
				'Content-Type': 'application/json',
				'User-Agent': 'Mozilla/5.0',
			},
			method='POST',
		)
		try:
			with urllib.request.urlopen(req, timeout=timeout_s) as resp:
				data = json.loads(resp.read().decode('utf-8', errors='replace'))
		except Exception as exc:  # noqa: BLE001
			result.degraded.append(f'serper_failed:{exc}')
			result.elapsed_ms = (time.perf_counter() - t0) * 1000.0
			return result
	raw_hits: list[WebSearchHit] = []
	for i, row in enumerate((data or {}).get('organic') or []):
		url = str(row.get('link') or '').strip()
		host = _host(url)
		if not url.startswith('http') or not host or _blocked(host):
			continue
		raw_hits.append(
			WebSearchHit(
				title=str(row.get('title') or host)[:160],
				url=url,
				host=host,
				rank=i,
			)
		)
	result.hits = _rank_hits(raw_hits, limit=limit)
	if not result.hits:
		result.degraded.append('serper_no_organic_results')
	result.elapsed_ms = (time.perf_counter() - t0) * 1000.0
	return result


def search_brave(query: str, *, limit: int = 8, timeout_s: float = 8.0) -> WebSearchResult:
	"""Optional Brave Search API — requires BRAVE_API_KEY."""
	import json
	import os
	from urllib.parse import quote

	t0 = time.perf_counter()
	result = WebSearchResult(query=query, engine='brave', elapsed_ms=0.0)
	key = (os.environ.get('BRAVE_API_KEY') or '').strip()
	if not key:
		result.degraded.append('brave_no_api_key')
		result.elapsed_ms = (time.perf_counter() - t0) * 1000.0
		return result
	url = f'https://api.search.brave.com/res/v1/web/search?q={quote(query)}&count={max(1, min(limit, 10))}'
	try:
		html, status, err = http_get(
			url,
			timeout=timeout_s,
			max_bytes=200_000,
			headers={'Accept': 'application/json', 'X-Subscription-Token': key},
		)
	except Exception as exc:  # noqa: BLE001
		result.degraded.append(f'brave_failed:{exc}')
		result.elapsed_ms = (time.perf_counter() - t0) * 1000.0
		return result
	if err and not html:
		result.degraded.append(f'brave_error:{err}')
		result.elapsed_ms = (time.perf_counter() - t0) * 1000.0
		return result
	if status and status >= 400:
		result.degraded.append(f'brave_http_{status}')
	try:
		data = json.loads(html or '{}')
	except Exception as exc:  # noqa: BLE001
		result.degraded.append(f'brave_json:{exc}')
		result.elapsed_ms = (time.perf_counter() - t0) * 1000.0
		return result
	raw_hits: list[WebSearchHit] = []
	web = (data.get('web') or {}) if isinstance(data, dict) else {}
	for i, row in enumerate(web.get('results') or []):
		url_r = str(row.get('url') or '').strip()
		host = _host(url_r)
		if not url_r.startswith('http') or not host or _blocked(host):
			continue
		raw_hits.append(
			WebSearchHit(
				title=str(row.get('title') or host)[:160],
				url=url_r,
				host=host,
				rank=i,
			)
		)
	result.hits = _rank_hits(raw_hits, limit=limit)
	if not result.hits:
		result.degraded.append('brave_no_organic_results')
	result.elapsed_ms = (time.perf_counter() - t0) * 1000.0
	return result


def search_web(
	query: str,
	*,
	limit: int = 8,
	timeout_s: float = 8.0,
	use_cache: bool = True,
	aliases: list[str] | tuple[str, ...] | None = None,
) -> WebSearchResult:
	"""Best available search: Serper → Brave → DuckDuckGo HTML.

	Paid APIs are optional (env keys). DDG is the always-on default.
	Non-empty results cached ~15m by normalized query (empty SERPs are never cached).
	"""
	import os

	from navigation.inspiration_intelligence.serp_cache import (
		get_serp,
		put_serp,
		serp_fingerprint,
	)

	fp = serp_fingerprint(query, limit=limit)
	if use_cache:
		cached = get_serp(fp)
		if cached and cached.get('hits'):
			hits = [
				WebSearchHit(
					title=str(h.get('title') or ''),
					url=str(h.get('url') or ''),
					host=str(h.get('host') or ''),
					rank=int(h.get('rank') or i),
					score=float(h.get('score') or 0),
				)
				for i, h in enumerate(cached.get('hits') or [])
			]
			return WebSearchResult(
				query=query,
				engine=str(cached.get('engine') or 'cache'),
				elapsed_ms=0.0,
				hits=hits[:limit],
				degraded=list(cached.get('degraded') or []) + ['serp_cache_hit'],
			)

	def _store(result: WebSearchResult) -> WebSearchResult:
		# Never cache empty — transient DDG blocks must not stick for 15m
		if use_cache and result.hits:
			put_serp(
				fp,
				{
					'engine': result.engine,
					'degraded': list(result.degraded),
					'hits': [h.to_dict() for h in result.hits],
				},
			)
		return result

	alias_list = list(aliases or [])
	if (os.environ.get('SERPER_API_KEY') or '').strip():
		primary = search_serper(query, limit=limit, timeout_s=timeout_s)
		if primary.hits:
			return _store(primary)
		fallback = search_duckduckgo(
			query, limit=limit, timeout_s=timeout_s, aliases=alias_list
		)
		fallback.degraded = list(primary.degraded) + list(fallback.degraded) + [
			'fell_back_from_serper'
		]
		return _store(fallback)
	if (os.environ.get('BRAVE_API_KEY') or '').strip():
		primary = search_brave(query, limit=limit, timeout_s=timeout_s)
		if primary.hits:
			return _store(primary)
		fallback = search_duckduckgo(
			query, limit=limit, timeout_s=timeout_s, aliases=alias_list
		)
		fallback.degraded = list(primary.degraded) + list(fallback.degraded) + [
			'fell_back_from_brave'
		]
		return _store(fallback)
	return _store(
		search_duckduckgo(query, limit=limit, timeout_s=timeout_s, aliases=alias_list)
	)
