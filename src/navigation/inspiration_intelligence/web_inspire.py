"""Web visual inspiration — search → OG thumbs → optional live screenshots.

Channel C for Inspiration Intelligence: open-web discovery when pattern/CDN
packs are thin, or when the agent wants a real search + look loop.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from navigation.inspiration_intelligence.browser.fetch import extract_og_image, http_get
from navigation.inspiration_intelligence.live_capture import CaptureFn, _default_capture
from navigation.inspiration_intelligence.web_search import (
	craft_inspiration_search_query,
	search_web,
)


@dataclass
class WebInspireHit:
	provider_id: str
	candidate_id: str
	title: str
	url: str
	preview_url: str
	screenshot_path: str = ''
	source_kind: str = 'web_search'
	fetch_tier: str = 'web_og'
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'provider_id': self.provider_id,
			'candidate_id': self.candidate_id,
			'title': self.title,
			'url': self.url,
			'preview_url': self.preview_url,
			'screenshot_path': self.screenshot_path,
			'source_kind': self.source_kind,
			'fetch_tier': self.fetch_tier,
			'degraded': list(self.degraded),
		}


@dataclass
class WebInspireResult:
	query: str
	search_query: str
	elapsed_ms: float
	hits: list[WebInspireHit] = field(default_factory=list)
	search_hits: int = 0
	og_hits: int = 0
	screenshot_hits: int = 0
	degraded: list[str] = field(default_factory=list)
	timing: list[dict[str, Any]] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'query': self.query,
			'search_query': self.search_query,
			'elapsed_ms': round(self.elapsed_ms, 1),
			'hits': [h.to_dict() for h in self.hits],
			'search_hits': self.search_hits,
			'og_hits': self.og_hits,
			'screenshot_hits': self.screenshot_hits,
			'degraded': list(self.degraded),
			'timing': list(self.timing),
		}


def _skip_og(url: str) -> bool:
	low = (url or '').lower()
	if not low.startswith('http'):
		return True
	return any(
		x in low
		for x in ('favicon', '1x1', 'pixel', 'sprite', 'logo-only', 'apple-touch')
	)


async def _og_for_url(url: str, *, timeout_s: float) -> tuple[str, float, str | None]:
	t0 = time.perf_counter()
	try:
		html, status, err = await asyncio.to_thread(
			http_get, url, timeout=timeout_s, max_bytes=80_000
		)
	except Exception as exc:  # noqa: BLE001
		return '', (time.perf_counter() - t0) * 1000.0, str(exc)
	ms = (time.perf_counter() - t0) * 1000.0
	if err and not html:
		return '', ms, err
	if status and status >= 400 and not html:
		return '', ms, f'http_{status}'
	og = extract_og_image(html or '')
	if _skip_og(og):
		return '', ms, 'no_og'
	return og, ms, None


async def acquire_web_inspiration(
	query: str,
	*,
	scope: str = 'page',
	max_search: int = 8,
	max_og: int = 6,
	max_screenshots: int = 0,
	og_concurrency: int = 6,
	og_timeout_s: float = 4.0,
	search_timeout_s: float = 8.0,
	capture_fn: CaptureFn | None = None,
	browser_concurrency: int = 1,
	search_aliases: list[str] | tuple[str, ...] | None = None,
	parallel_queries: list[str] | tuple[str, ...] | None = None,
	deadline_mono: float | None = None,
) -> WebInspireResult:
	"""Search the open web, pull OG thumbs, optionally screenshot top pages."""
	t0 = time.perf_counter()
	hunt = craft_inspiration_search_query(query, scope=scope)
	result = WebInspireResult(query=query, search_query=hunt, elapsed_ms=0.0)

	# Fan out distinct hunt strings in parallel (not sequential alias retry).
	pq = [q.strip() for q in (parallel_queries or []) if (q or '').strip()]
	hunts: list[str] = []
	seen_hunt: set[str] = set()
	for raw_q in pq or [query]:
		h = craft_inspiration_search_query(raw_q, scope=scope)
		k = h.strip().lower()
		if k and k not in seen_hunt:
			seen_hunt.add(k)
			hunts.append(h)
	if not hunts:
		hunts = [hunt]

	async def _search_one(hunt_q: str, *, aliases: list[str] | None = None):
		return await asyncio.to_thread(
			search_web,
			hunt_q,
			limit=max_search,
			timeout_s=search_timeout_s,
			aliases=list(aliases or []),
		)

	if len(hunts) == 1:
		search = await _search_one(hunts[0], aliases=list(search_aliases or []))
	else:
		searches = await asyncio.gather(
			*[_search_one(h) for h in hunts[:4]],
			return_exceptions=True,
		)
		from navigation.inspiration_intelligence.web_search import WebSearchHit, WebSearchResult

		merged: list[WebSearchHit] = []
		seen_host: set[str] = set()
		seen_url: set[str] = set()
		degraded: list[str] = []
		engine = 'parallel'
		elapsed = 0.0
		for i, row in enumerate(searches):
			if isinstance(row, Exception):
				degraded.append(f'parallel_web_search_failed:{hunts[i][:60]}:{row}')
				continue
			degraded.extend(list(row.degraded or []))
			elapsed = max(elapsed, float(row.elapsed_ms or 0))
			engine = str(row.engine or engine)
			for hit in row.hits or []:
				host = (hit.host or '').lower()
				url = (hit.url or '').strip()
				if host and host in seen_host:
					continue
				if url and url in seen_url:
					continue
				if host:
					seen_host.add(host)
				if url:
					seen_url.add(url)
				merged.append(hit)
		merged.sort(key=lambda h: h.score, reverse=True)
		search = WebSearchResult(
			query=query,
			engine=engine,
			elapsed_ms=elapsed,
			hits=merged[: max(1, max_search * 2)],
			degraded=degraded + [f'parallel_web_queries:{len(hunts)}'],
		)
		result.search_query = ' | '.join(hunts[:3])
	result.degraded.extend(search.degraded)
	result.timing.append(
		{
			'provider_id': '_web_search',
			'engine': search.engine,
			'elapsed_ms': search.elapsed_ms,
			'ok': bool(search.hits),
			'count': len(search.hits),
		}
	)
	result.search_hits = len(search.hits)
	if not search.hits:
		result.elapsed_ms = (time.perf_counter() - t0) * 1000.0
		return result

	# --- Fast wave: OG images from result pages ---
	sem = asyncio.Semaphore(max(1, og_concurrency))

	async def _one_og(hit: Any) -> tuple[Any, str] | None:
		async with sem:
			og, ms, err = await _og_for_url(hit.url, timeout_s=og_timeout_s)
			result.timing.append(
				{
					'provider_id': 'web_og',
					'host': hit.host,
					'elapsed_ms': round(ms, 1),
					'ok': bool(og),
					'error': err,
				}
			)
			if og:
				return hit, og
			return None

	og_results = await asyncio.gather(*[_one_og(h) for h in search.hits[:max_search]])
	og_rows = [row for row in og_results if row]

	seen_preview: set[str] = set()
	for hit, og in og_rows:
		if len(result.hits) >= max_og:
			break
		if og in seen_preview:
			continue
		seen_preview.add(og)
		result.hits.append(
			WebInspireHit(
				provider_id='web_search',
				candidate_id=f'web_og:{hit.host}:{len(result.hits)}',
				title=hit.title or hit.host,
				url=hit.url,
				preview_url=og,
				source_kind='web_search',
				fetch_tier='web_og',
			)
		)
		result.og_hits += 1

	# Drop dead OG URLs before soft-stop counts them (fail-open if all drop)
	if result.hits:
		from navigation.inspiration_intelligence.preview_validate import filter_valid_previews

		kept, deg = await filter_valid_previews(result.hits, concurrency=max(4, og_concurrency))
		result.degraded.extend(deg)
		if kept:
			result.hits = list(kept)
		else:
			result.degraded.append('preview_validate_all_failed_kept_raw')
		result.og_hits = sum(1 for h in result.hits if h.fetch_tier == 'web_og')

	# --- Slow wave: viewport screenshots — prefer OG-validated hosts, not raw SERP ---
	n_ss = max(0, int(max_screenshots))
	if n_ss > 0:
		from navigation.inspiration_intelligence.browser.host_cooldown import is_cooled
		from navigation.inspiration_intelligence.live_capture import _MIN_CAPTURE_BUDGET_S

		if deadline_mono is not None and (deadline_mono - time.monotonic()) < _MIN_CAPTURE_BUDGET_S:
			result.degraded.append('web_ss_deadline_skip')
			n_ss = 0

	if n_ss > 0:
		fn = capture_fn or _default_capture
		ss_sem = asyncio.Semaphore(1)  # singleton browser — always serial

		# Prefer pages that already yielded a valid OG thumb (less WAF lottery)
		og_hosts = {h.host for h, _og in og_rows}
		prefer = [h for h in search.hits if h.host in og_hosts and not is_cooled(h.url)]
		rest = [
			h
			for h in search.hits
			if h.host not in og_hosts and not is_cooled(h.url)
		]
		targets = (prefer + rest)[:n_ss]
		if not targets:
			result.degraded.append('web_ss_no_uncooked_targets')

		async def _one_ss(hit: Any, idx: int) -> None:
			async with ss_sem:
				if deadline_mono is not None and (deadline_mono - time.monotonic()) < _MIN_CAPTURE_BUDGET_S:
					result.degraded.append(f'web_ss_deadline_stop:{hit.host}')
					return
				if is_cooled(hit.url):
					result.degraded.append(f'host_cooldown_skip:{hit.host}')
					return
				site = {
					'id': f'web_{hit.host}',
					'url': hit.url,
					'title': hit.title or hit.host,
					'category': 'web_search',
					'focus_scope': scope,
				}
				t_ss = time.perf_counter()
				try:
					path, title, deg = await asyncio.wait_for(
						fn(site) if capture_fn else _default_capture(site, deadline_mono=deadline_mono),
						timeout=11.0,
					)
				except asyncio.TimeoutError:
					path, title, deg = '', hit.title or hit.host, ['web_live_capture_timeout']
				ms = (time.perf_counter() - t_ss) * 1000.0
				result.degraded.extend(deg)
				result.timing.append(
					{
						'provider_id': 'web_live',
						'host': hit.host,
						'elapsed_ms': round(ms, 1),
						'ok': bool(path),
					}
				)
				if not path:
					result.degraded.append(f'web_live_no_screenshot:{hit.host}')
					return
				preview = ''
				p = Path(path)
				if p.is_file():
					preview = p.resolve().as_uri()
				result.hits.append(
					WebInspireHit(
						provider_id='web_live',
						candidate_id=f'web_live:{hit.host}:{idx}',
						title=title or hit.title or hit.host,
						url=hit.url,
						preview_url=preview,
						screenshot_path=path,
						source_kind='web_live',
						fetch_tier='web_live_screenshot',
						degraded=list(deg[:4]),
					)
				)
				result.screenshot_hits += 1

		for i, h in enumerate(targets):
			await _one_ss(h, i)

	result.elapsed_ms = (time.perf_counter() - t0) * 1000.0
	return result


def should_run_web_inspire(
	*,
	level: str,
	hit_count: int,
	soft_stop_refs: int,
	include_web_search: bool | None,
	font_routed: bool,
) -> bool:
	"""When Channel C fires.

	- Explicit False → never
	- Font route → never (Resource Intelligence owns fonts)
	- True / level-on → fill until soft-stop variety
	- Auto None on light → only empty packs
	"""
	if font_routed:
		return False
	if include_web_search is False:
		return False
	need = max(4, min(int(soft_stop_refs or 8), 8))
	if include_web_search is True:
		return hit_count < need
	level_l = (level or 'standard').lower()
	if level_l == 'light':
		return hit_count < 1
	return hit_count < need
