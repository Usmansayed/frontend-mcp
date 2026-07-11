#!/usr/bin/env python3
"""Gentle live probe — 3 searches per inspiration site, results to artifacts/.

Respectful pacing: ~40s between searches, ~90s between sites.
Set INSPIRATION_FORCE=1 to bypass usage gate (probe only).
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.inspiration_intelligence.browser.policy import RateLimitTracker, detect_block_signal, production_policy
from navigation.inspiration_intelligence.browser.fetch import enrich_preview_from_detail, http_get
from navigation.inspiration_intelligence.providers.dribbble.parser import parse_search_html, query_to_slug

QUERIES = ['saas dashboard', 'landing page', 'minimal ui']
SITE_DELAY_S = 90
SEARCH_DELAY_S = 40

_GALLERY = re.compile(r'href="(https?://[^"]*/gallery/\d+[^"]*)"', re.I)
_SITES = re.compile(r'href="(https?://[^"]*awwwards\.com/sites/[^"]+)"', re.I)
_WEBSITE = re.compile(r'href="(/website/\d+[^"]*)"', re.I)
_GODLY = re.compile(r'href="(https?://godly\.website/website/[^"]+)"', re.I)
_DESIGN = re.compile(r'href="(https?://[^"]*land-book\.com/design/[^"]+)"', re.I)
_OPL = re.compile(r'href="(https://onepagelove\.com/([a-z0-9-]+))"', re.I)
_OPL_IMG = re.compile(r'https://assets\.onepagelove\.com/[^"\']+', re.I)
_OPL_RESERVED = frozenset({'about', 'api', 'articles', 'feed', 'inspiration', 'templates'})


@dataclass
class ProbeHit:
	title: str = ''
	url: str = ''
	preview_url: str = ''
	external_id: str = ''


@dataclass
class ProbeSearchResult:
	query: str
	url: str
	ok: bool
	block_signal: str | None = None
	hits: list[ProbeHit] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)
	extracted_preview: str = ''


@dataclass
class ProbeSiteResult:
	provider_id: str
	searches: list[ProbeSearchResult] = field(default_factory=list)
	passed: int = 0
	failed: int = 0

	def to_dict(self) -> dict[str, object]:
		return {
			'provider_id': self.provider_id,
			'passed': self.passed,
			'failed': self.failed,
			'searches': [
				{
					'query': s.query,
					'url': s.url,
					'ok': s.ok,
					'block_signal': s.block_signal,
					'hits_count': len(s.hits),
					'hits': [asdict(h) for h in s.hits[:5]],
					'extracted_preview': s.extracted_preview,
					'degraded': s.degraded,
				}
				for s in self.searches
			],
		}


def _search_url(provider_id: str, query: str) -> str:
	slug = query_to_slug(query)
	encoded = urllib.parse.quote(query)
	if provider_id == 'dribbble':
		return f'https://dribbble.com/search/{slug}'
	if provider_id == 'behance':
		return f'https://www.behance.net/search/projects?search={encoded}'
	if provider_id == 'awwwards':
		return f'https://www.awwwards.com/websites/?search={slug}'
	if provider_id == 'siteinspire':
		return f'https://www.siteinspire.com/search?q={encoded}'
	if provider_id == 'godly':
		return f'https://godly.website/?search={slug}'
	if provider_id == 'land-book':
		return f'https://www.land-book.com/design?search={slug}'
	if provider_id == 'onepagelove':
		return 'https://onepagelove.com/inspiration'
	raise ValueError(provider_id)


def _parse_hits(provider_id: str, html: str, base_url: str) -> list[ProbeHit]:
	hits: list[ProbeHit] = []
	seen: set[str] = set()

	if provider_id == 'dribbble':
		for h in parse_search_html(html):
			hits.append(ProbeHit(title=h.title, url=h.url, preview_url=h.preview_url, external_id=h.shot_id))
		return hits[:8]

	patterns: list[tuple[re.Pattern[str], str]] = [
		(_GALLERY, 'behance'),
		(_SITES, 'awwwards'),
		(_WEBSITE, 'siteinspire'),
		(_GODLY, 'godly'),
		(_DESIGN, 'land-book'),
		(_OPL, 'onepagelove'),
	]
	for pattern, site in patterns:
		if site != provider_id:
			continue
		if site == 'onepagelove':
			for match in pattern.finditer(html):
				url, slug = match.group(1), match.group(2)
				if slug in _OPL_RESERVED:
					continue
				window = html[max(0, match.start() - 800) : match.end() + 800]
				if not _OPL_IMG.search(window):
					continue
				key = url.split('?')[0]
				if key in seen:
					continue
				seen.add(key)
				hits.append(ProbeHit(title=slug.replace('-', ' '), url=url, external_id=slug))
				if len(hits) >= 8:
					break
			return hits
		for match in pattern.finditer(html):
			url = match.group(1)
			if url.startswith('/'):
				url = urllib.parse.urljoin(base_url, url)
			key = url.split('?')[0]
			if key in seen:
				continue
			seen.add(key)
			ext = key.rstrip('/').split('/')[-1]
			hits.append(ProbeHit(title=ext.replace('-', ' '), url=url, external_id=ext))
			if len(hits) >= 8:
				break
	return hits


async def _probe_dribbble(query: str, tracker: RateLimitTracker) -> ProbeSearchResult:
	return _probe_http('dribbble', query, tracker)


def _probe_http(provider_id: str, query: str, tracker: RateLimitTracker) -> ProbeSearchResult:
	policy = production_policy(provider_id)
	tracker.wait_if_needed(provider_id, policy)
	url = _search_url(provider_id, query)
	result = ProbeSearchResult(query=query, url=url, ok=False)

	html, status, err = http_get(url)
	if err:
		result.degraded.append(f'fetch_error:{err}')
		result.block_signal = err
		return result

	block = detect_block_signal(html, status_code=status)
	if block:
		result.block_signal = block
		result.degraded.append(f'block:{block}')
		return result

	base = urllib.parse.urlparse(url).scheme + '://' + urllib.parse.urlparse(url).netloc
	hits = _parse_hits(provider_id, html, base)
	if hits:
		result.ok = True
		result.hits = hits
		preview, _, og_deg = enrich_preview_from_detail(hits[0].url)
		result.extracted_preview = preview
		result.degraded.extend(og_deg)
	else:
		result.degraded.append('parse_empty')
		result.block_signal = 'parse_empty'

	return result


async def run_probe(output_dir: Path) -> dict[str, object]:
	output_dir.mkdir(parents=True, exist_ok=True)
	tracker = RateLimitTracker()
	sites = ['dribbble', 'behance', 'onepagelove', 'awwwards', 'siteinspire', 'godly', 'land-book']
	site_results: list[ProbeSiteResult] = []

	for i, site in enumerate(sites):
		if i > 0:
			print(f'  ... waiting {SITE_DELAY_S}s before {site}')
			time.sleep(SITE_DELAY_S)

		sr = ProbeSiteResult(provider_id=site)
		print(f'\n=== {site} ===')

		for j, query in enumerate(QUERIES):
			if j > 0:
				print(f'  ... waiting {SEARCH_DELAY_S}s')
				time.sleep(SEARCH_DELAY_S)

			print(f'  search: {query!r}')
			if site == 'dribbble':
				pr = await _probe_dribbble(query, tracker)
			else:
				pr = _probe_http(site, query, tracker)

			sr.searches.append(pr)
			if pr.ok:
				sr.passed += 1
				print(f'    OK — {len(pr.hits)} hits')
			else:
				sr.failed += 1
				print(f'    FAIL — {pr.block_signal or pr.degraded}')

		site_results.append(sr)
		(site_dir := output_dir / site).mkdir(exist_ok=True)
		(site_dir / 'results.json').write_text(json.dumps(sr.to_dict(), indent=2), encoding='utf-8')

	summary = {
		'run_at': datetime.now(timezone.utc).isoformat(),
		'queries_per_site': len(QUERIES),
		'site_delay_s': SITE_DELAY_S,
		'search_delay_s': SEARCH_DELAY_S,
		'sites': [s.to_dict() for s in site_results],
		'total_passed': sum(s.passed for s in site_results),
		'total_failed': sum(s.failed for s in site_results),
		'failed_sites': [s.provider_id for s in site_results if s.failed > 0],
	}
	(output_dir / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
	return summary


def main() -> int:
	import os

	os.environ.setdefault('INSPIRATION_FORCE', '1')
	os.environ.setdefault('INSPIRATION_MIN_DELAY_S', '35')

	stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
	out = ROOT / 'artifacts' / 'inspiration_probes' / stamp
	print(f'Output: {out}')
	print(f'Pacing: {SEARCH_DELAY_S}s between searches, {SITE_DELAY_S}s between sites')

	summary = asyncio.run(run_probe(out))

	print('\n=== SUMMARY ===')
	print(json.dumps(summary, indent=2))
	print(f"\nPassed: {summary['total_passed']}/{summary['total_passed'] + summary['total_failed']}")
	if summary['failed_sites']:
		print(f"Failed sites (partial or full): {', '.join(summary['failed_sites'])}")
	return 0 if summary['total_failed'] == 0 else 1


if __name__ == '__main__':
	raise SystemExit(main())
