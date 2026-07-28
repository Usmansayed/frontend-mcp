"""Concurrent multi-source inspiration scout — probe many sites, rank, then deep-acquire winners.

Pipeline:
  1. SCOUT  — fan-out lightweight HTTP GETs across curated corpus (tight timeout)
  2. RANK   — score relevance (intent hints + query tokens + preview density)
  3. ACQUIRE — only top-N winners: CDN previews from scout HTML, else viewport screenshot

Wall time ≈ max(probe) under concurrency, not sum(sites). Full page scrapes of 30+
sites in \"a few ms\" is not realistic; target is a few hundred ms–low seconds for scout.
"""
from __future__ import annotations

import asyncio
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Awaitable, Callable
from urllib.parse import quote_plus, urljoin, urlparse

from navigation.inspiration_intelligence.browser.fetch import extract_og_image, http_get
from navigation.inspiration_intelligence.inspiration_sources import load_inspiration_sources_corpus

ProbeFn = Callable[[str, float], Awaitable[tuple[str, int | None, str | None]]]
# (url, timeout) → (html, status, err)

_IMG_SRC = re.compile(
	r'<img[^>]+(?:src|data-src|data-lazy-src)=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp|avif)[^"\']*)["\']',
	re.IGNORECASE,
)
_TOKEN = re.compile(r'[a-z0-9]{3,}')


@dataclass
class ScoutHit:
	source_id: str
	title: str
	url: str
	category: str
	tier: str
	score: float
	preview_urls: list[str] = field(default_factory=list)
	probe_url: str = ''
	elapsed_ms: float = 0.0
	ok: bool = False
	reason: str = ''

	def to_dict(self) -> dict[str, Any]:
		return asdict(self)


@dataclass
class MultiScoutResult:
	query: str
	scout_ms: float
	probed: int
	ranked: list[ScoutHit] = field(default_factory=list)
	winners: list[ScoutHit] = field(default_factory=list)
	acquired: list[dict[str, Any]] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)
	timing: list[dict[str, Any]] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'query': self.query,
			'scout_ms': round(self.scout_ms, 1),
			'probed': self.probed,
			'ranked': [h.to_dict() for h in self.ranked[:12]],
			'winners': [h.to_dict() for h in self.winners],
			'acquired': list(self.acquired),
			'degraded': list(self.degraded),
			'timing': list(self.timing),
		}


def _tokens(text: str) -> set[str]:
	return set(_TOKEN.findall((text or '').lower()))


def _probe_url_for(source: dict[str, Any], query: str) -> str:
	"""Best lightweight URL to probe for this source + query."""
	demos = list(source.get('demo_urls') or [])
	base = str(source.get('url') or '')
	tier = str(source.get('tier') or '')
	sid = str(source.get('id') or '')
	q = quote_plus((query or '').strip()[:80])

	# Known search patterns for registered / common galleries
	search_patterns: dict[str, str] = {
		'onepagelove': f'https://onepagelove.com/inspiration?s={q}',
		'lapa': f'https://www.lapa.ninja/?s={q}',
		'behance': f'https://www.behance.net/search/projects?search={q}',
		'httpster': 'https://httpster.net/',
		'siteinspire': f'https://www.siteinspire.com/websites?search={q}',
		'dribbble': f'https://dribbble.com/search/{quote_plus((query or "").strip().lower().replace(" ", "-")[:60])}',
		'land_book': f'https://land-book.com/design?search={q}',
		'awwwards': f'https://www.awwwards.com/websites/?text={q}',
	}
	if sid in search_patterns:
		return search_patterns[sid]
	if tier == 'screenshot_demo' and demos:
		return str(demos[0])
	if demos:
		return str(demos[0])
	return base


def _extract_previews(html: str, base_url: str, *, limit: int = 6) -> list[str]:
	found: list[str] = []
	seen: set[str] = set()
	og = extract_og_image(html or '')
	if og.startswith('http') and og not in seen:
		seen.add(og)
		found.append(og)
	for m in _IMG_SRC.finditer(html or ''):
		u = m.group(1).strip()
		# Skip tiny icons / tracking
		low = u.lower()
		if any(x in low for x in ('favicon', 'logo-icon', '1x1', 'pixel', 'sprite', 'avatar')):
			continue
		if u not in seen:
			seen.add(u)
			found.append(u)
		if len(found) >= limit:
			break
	# Relative → absolute (rare for src=https)
	out: list[str] = []
	for u in found:
		if u.startswith('http'):
			out.append(u)
		else:
			out.append(urljoin(base_url, u))
	return out


def score_probe(
	*,
	query: str,
	source: dict[str, Any],
	category: str,
	category_hints: list[str],
	html: str,
	status: int | None,
	preview_urls: list[str],
) -> tuple[float, str]:
	"""Return (score 0..1, reason)."""
	if status and status >= 400:
		return 0.0, f'http_{status}'
	if not (html or '').strip():
		return 0.0, 'empty'

	q_tokens = _tokens(query)
	score = 0.0
	reasons: list[str] = []

	# Category / intent alignment
	hints = [h.lower() for h in category_hints]
	hint_hits = sum(1 for h in hints if h and h in (query or '').lower())
	if hint_hits:
		score += min(0.35, 0.12 * hint_hits)
		reasons.append(f'hints:{hint_hits}')

	# Query tokens in page (title-ish / body sample)
	sample = ((html or '')[:12000]).lower()
	if q_tokens:
		present = sum(1 for t in q_tokens if t in sample)
		cov = present / max(1, len(q_tokens))
		score += 0.40 * cov
		reasons.append(f'tokens:{present}/{len(q_tokens)}')

	# Visual density
	n_img = len(preview_urls)
	if n_img:
		score += min(0.25, 0.06 * n_img)
		reasons.append(f'imgs:{n_img}')

	# Tier preference for fast acquire
	tier = str(source.get('tier') or '')
	if tier == 'fast_http':
		score += 0.05
	elif tier == 'screenshot_demo' and n_img:
		score += 0.03

	# Soft boost if source title words overlap
	title = str(source.get('title') or '').lower()
	if any(t in title for t in q_tokens):
		score += 0.05

	# Auth/checkout-ish queries: prefer flow + landing galleries over random dark-mode
	ql = (query or '').lower()
	authish = any(x in ql for x in ('login', 'sign in', 'signin', 'signup', 'auth', 'checkout', 'payment'))
	if authish and category in {'flow_library', 'landing_gallery', 'ui_gallery'}:
		score += 0.12
		reasons.append('intent_flow_boost')
	elif authish and category in {'dashboard_gallery', 'component_showcase'}:
		score += 0.06
		reasons.append('intent_ui_boost')

	return min(1.0, score), '+'.join(reasons) or 'weak'


def iter_scout_targets(
	*,
	query: str,
	mode: str = 'broad',
	max_sources: int | None = None,
	prefer_categories: list[str] | None = None,
) -> list[dict[str, Any]]:
	"""Flatten corpus into probe targets for this mode/query."""
	corpus = load_inspiration_sources_corpus()
	defaults = (corpus.get('planner_defaults') or {}).get(mode) or (corpus.get('planner_defaults') or {}).get(
		'broad'
	) or {}
	want_cats = list(
		prefer_categories
		or defaults.get('categories')
		or ['landing_gallery', 'ui_gallery', 'component_showcase']
	)
	tiers_allowed = set(defaults.get('tiers_allowed') or ['fast_http', 'browser_gallery', 'screenshot_demo'])
	cap = max_sources if max_sources is not None else int(defaults.get('max_sources') or 16)

	# Prefer categories whose hints match query
	q = (query or '').lower()
	cats = corpus.get('categories') or {}
	ordered_cats = sorted(
		want_cats,
		key=lambda c: -sum(1 for h in ((cats.get(c) or {}).get('intent_hints') or []) if str(h).lower() in q),
	)

	targets: list[dict[str, Any]] = []
	seen: set[str] = set()
	for cat in ordered_cats:
		bucket = cats.get(cat) or {}
		hints = list(bucket.get('intent_hints') or [])
		for src in bucket.get('sources') or []:
			sid = str(src.get('id') or '')
			tier = str(src.get('tier') or '')
			if not sid or sid in seen:
				continue
			if tier == 'research_only':
				continue
			if tier not in tiers_allowed and tier not in {'fast_http', 'screenshot_demo'}:
				continue
			url = _probe_url_for(src, query)
			if not url.startswith('http'):
				continue
			seen.add(sid)
			targets.append(
				{
					'source': src,
					'category': cat,
					'hints': hints,
					'probe_url': url,
				}
			)
			if len(targets) >= cap:
				return targets
	return targets


async def _default_probe(url: str, timeout: float) -> tuple[str, int | None, str | None]:
	# Scout only needs head of page for thumbs/meta — 48KB is enough and much faster.
	return await asyncio.to_thread(http_get, url, timeout=timeout, max_bytes=48_000)


async def scout_rank_sources(
	query: str,
	*,
	mode: str = 'broad',
	max_sources: int | None = None,
	concurrency: int = 12,
	timeout_s: float = 1.2,
	top_n: int = 3,
	min_score: float = 0.12,
	probe_fn: ProbeFn | None = None,
	prefer_fast_http: bool = True,
	early_cancel: bool = True,
	prefer_categories: list[str] | None = None,
) -> MultiScoutResult:
	"""Phase 1–2: concurrent probe + rank. Does not screenshot yet.

	Early-cancel: once we have `top_n` hits above a strong score with previews,
	cancel remaining probes (keeps wall time near the fastest winners).
	"""
	t0 = time.perf_counter()
	targets = iter_scout_targets(
		query=query,
		mode=mode,
		max_sources=max_sources,
		prefer_categories=prefer_categories,
	)
	if prefer_fast_http:
		targets = sorted(
			targets,
			key=lambda t: (
				0 if str((t.get('source') or {}).get('tier') or '') == 'fast_http' else 1,
				str((t.get('source') or {}).get('id') or ''),
			),
		)
	result = MultiScoutResult(query=query, scout_ms=0.0, probed=0)
	if not targets:
		result.degraded.append('multi_scout_no_targets')
		result.scout_ms = (time.perf_counter() - t0) * 1000.0
		return result

	probe = probe_fn or _default_probe
	sem = asyncio.Semaphore(max(1, concurrency))
	strong = max(min_score, 0.35)
	cancel_event = asyncio.Event()

	async def _one(target: dict[str, Any]) -> ScoutHit | None:
		if cancel_event.is_set():
			return None
		src = target['source']
		sid = str(src.get('id') or '')
		probe_url = str(target['probe_url'])
		async with sem:
			if cancel_event.is_set():
				return None
			t1 = time.perf_counter()
			try:
				html, status, err = await asyncio.wait_for(
					probe(probe_url, timeout_s),
					timeout=timeout_s + 0.4,
				)
			except Exception as exc:  # noqa: BLE001
				html, status, err = '', None, str(exc)
			elapsed = (time.perf_counter() - t1) * 1000.0
		previews = _extract_previews(html or '', probe_url) if html else []
		score, reason = score_probe(
			query=query,
			source=src,
			category=str(target['category']),
			category_hints=[str(h) for h in target.get('hints') or []],
			html=html or '',
			status=status,
			preview_urls=previews,
		)
		if err and not html:
			reason = f'err:{err}'[:80]
			score = 0.0
		return ScoutHit(
			source_id=sid,
			title=str(src.get('title') or sid),
			url=str(src.get('url') or probe_url),
			category=str(target['category']),
			tier=str(src.get('tier') or ''),
			score=round(score, 3),
			preview_urls=previews[:5],
			probe_url=probe_url,
			elapsed_ms=round(elapsed, 1),
			ok=score >= min_score,
			reason=reason,
		)

	tasks = [asyncio.create_task(_one(t)) for t in targets]
	hits: list[ScoutHit] = []
	strong_ready = 0
	pending = set(tasks)
	while pending:
		done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
		for task in done:
			hit = None
			try:
				hit = task.result()
			except Exception:
				hit = None
			if hit is None:
				continue
			hits.append(hit)
			if hit.score >= strong and hit.preview_urls:
				strong_ready += 1
			if early_cancel and strong_ready >= top_n:
				cancel_event.set()
				for p in pending:
					p.cancel()
				await asyncio.gather(*pending, return_exceptions=True)
				result.degraded.append(f'multi_scout_early_cancel:{len(pending)}')
				pending = set()
				break

	result.probed = len(hits)
	result.timing = [
		{
			'source_id': h.source_id,
			'elapsed_ms': h.elapsed_ms,
			'score': h.score,
			'ok': h.ok,
			'tier': h.tier,
		}
		for h in hits
	]
	ranked = sorted(hits, key=lambda h: (-h.score, h.elapsed_ms))
	result.ranked = ranked
	result.winners = [h for h in ranked if h.score >= min_score][: max(1, top_n)]
	if not result.winners and ranked:
		result.winners = ranked[:1]
		result.degraded.append('multi_scout_low_scores_kept_best')
	result.scout_ms = (time.perf_counter() - t0) * 1000.0
	return result


async def acquire_from_winners(
	winners: list[ScoutHit],
	*,
	max_visuals: int = 5,
	capture_fn: Any | None = None,
	allow_screenshots: bool = True,
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
	"""Phase 3: turn winner scout hits into visual refs (CDN first, screenshot fallback)."""
	acquired: list[dict[str, Any]] = []
	degraded: list[str] = []
	timing: list[dict[str, Any]] = []
	seen: set[str] = set()

	for w in winners:
		if len(acquired) >= max_visuals:
			break
		# Prefer CDN/previews discovered during scout
		for i, preview in enumerate(w.preview_urls):
			if len(acquired) >= max_visuals:
				break
			key = preview.split('?')[0].lower()
			if key in seen:
				continue
			seen.add(key)
			acquired.append(
				{
					'source_kind': 'gallery_image',
					'provider_id': w.source_id,
					'candidate_id': f'multi:{w.source_id}:{i}',
					'title': f'{w.title} #{i + 1}',
					'url': w.url,
					'external_id': f'{w.source_id}-{i}',
					'preview_url': preview,
					'agent_view_url': preview,
					'fetch_tier': 'multi_scout',
					'source_score': w.score,
					'category': w.category,
					'degraded': [f'multi_scout:{w.reason}'],
				}
			)

		# Screenshot demo page when no usable previews
		need_ss = allow_screenshots and not w.preview_urls and w.tier in {
			'screenshot_demo',
			'browser_gallery',
			'flow_library',
		}
		if need_ss and len(acquired) < max_visuals and capture_fn is not None:
			t1 = time.perf_counter()
			site = {
				'id': w.source_id,
				'url': w.probe_url or w.url,
				'title': w.title,
				'category': w.category,
			}
			try:
				path, title, deg = await capture_fn(site)
			except Exception as exc:  # noqa: BLE001
				path, title, deg = '', w.title, [f'acquire_failed:{exc}']
			elapsed = (time.perf_counter() - t1) * 1000.0
			timing.append(
				{
					'source_id': w.source_id,
					'elapsed_ms': round(elapsed, 1),
					'ok': bool(path),
					'tier': 'screenshot_demo',
				}
			)
			degraded.extend(deg)
			if path:
				from pathlib import Path

				p = Path(path)
				preview = p.resolve().as_uri() if p.is_file() else ''
				acquired.append(
					{
						'source_kind': 'screenshot_demo',
						'provider_id': w.source_id,
						'candidate_id': f'multi_ss:{w.source_id}',
						'title': title or w.title,
						'url': site['url'],
						'external_id': w.source_id,
						'preview_url': preview,
						'screenshot_path': path,
						'agent_view_url': preview or path,
						'fetch_tier': 'multi_scout_screenshot',
						'source_score': w.score,
						'category': w.category,
						'degraded': deg[:4],
					}
				)

	if acquired:
		from navigation.inspiration_intelligence.preview_validate import filter_valid_previews

		kept, degv = await filter_valid_previews(acquired, concurrency=6)
		degraded.extend(degv)
		if kept:
			acquired = list(kept)
		else:
			degraded.append('preview_validate_all_failed_kept_raw')

	if not acquired:
		degraded.append('multi_scout_acquire_empty')
	return acquired, degraded, timing


async def multi_source_inspire(
	query: str,
	*,
	mode: str = 'broad',
	max_sources: int | None = None,
	concurrency: int = 12,
	timeout_s: float = 1.2,
	top_n: int = 3,
	max_visuals: int = 5,
	allow_screenshots: bool = True,
	probe_fn: ProbeFn | None = None,
	capture_fn: Any | None = None,
	early_cancel: bool = True,
	prefer_categories: list[str] | None = None,
) -> MultiScoutResult:
	"""Full scout → rank → acquire pipeline."""
	result = await scout_rank_sources(
		query,
		mode=mode,
		max_sources=max_sources,
		concurrency=concurrency,
		timeout_s=timeout_s,
		top_n=top_n,
		probe_fn=probe_fn,
		early_cancel=early_cancel,
		prefer_categories=prefer_categories,
	)
	# Default screenshot capture for demo winners lacking previews
	fn = capture_fn
	if fn is None and allow_screenshots:
		from navigation.inspiration_intelligence.live_capture import _default_capture

		fn = _default_capture

	acquired, deg, timing = await acquire_from_winners(
		result.winners,
		max_visuals=max_visuals,
		capture_fn=fn,
		allow_screenshots=allow_screenshots,
	)
	result.acquired = acquired
	result.degraded.extend(deg)
	result.timing.extend(timing)
	return result


async def multi_source_inspire_parallel(
	queries: list[str],
	*,
	mode: str = 'broad',
	max_sources: int | None = None,
	concurrency: int = 12,
	timeout_s: float = 1.2,
	top_n: int = 3,
	max_visuals: int = 5,
	allow_screenshots: bool = True,
	probe_fn: ProbeFn | None = None,
	capture_fn: Any | None = None,
	early_cancel: bool = True,
	prefer_categories: list[str] | None = None,
) -> MultiScoutResult:
	"""Scout several **different** queries concurrently, merge winners, acquire once."""
	uniq: list[str] = []
	seen: set[str] = set()
	for q in queries:
		k = (q or '').strip().lower()
		if k and k not in seen:
			seen.add(k)
			uniq.append(q.strip())
	if not uniq:
		return MultiScoutResult(query='', scout_ms=0.0, probed=0)
	if len(uniq) == 1:
		return await multi_source_inspire(
			uniq[0],
			mode=mode,
			max_sources=max_sources,
			concurrency=concurrency,
			timeout_s=timeout_s,
			top_n=top_n,
			max_visuals=max_visuals,
			allow_screenshots=allow_screenshots,
			probe_fn=probe_fn,
			capture_fn=capture_fn,
			early_cancel=early_cancel,
			prefer_categories=prefer_categories,
		)

	t0 = time.perf_counter()
	cap = min(4, len(uniq))

	async def _scout_one(q: str) -> MultiScoutResult:
		return await scout_rank_sources(
			q,
			mode=mode,
			max_sources=max_sources,
			concurrency=concurrency,
			timeout_s=timeout_s,
			top_n=top_n,
			probe_fn=probe_fn,
			early_cancel=early_cancel,
			prefer_categories=prefer_categories,
		)

	scouts = await asyncio.gather(*[_scout_one(q) for q in uniq[:cap]], return_exceptions=True)
	merged_ranked: list[ScoutHit] = []
	seen_sid: set[str] = set()
	total_probed = 0
	degraded: list[str] = []
	for i, row in enumerate(scouts):
		if isinstance(row, Exception):
			degraded.append(f'parallel_scout_failed:{uniq[i][:48]}:{row}')
			continue
		total_probed += int(row.probed or 0)
		degraded.extend(list(row.degraded or []))
		for hit in row.ranked:
			if hit.source_id in seen_sid:
				continue
			seen_sid.add(hit.source_id)
			merged_ranked.append(hit)

	merged_ranked.sort(key=lambda h: h.score, reverse=True)
	winner_cap = max(top_n, top_n * cap // 2)
	winners = merged_ranked[:winner_cap]
	result = MultiScoutResult(
		query=' | '.join(uniq[:cap]),
		scout_ms=(time.perf_counter() - t0) * 1000.0,
		probed=total_probed,
		ranked=merged_ranked,
		winners=winners,
		degraded=degraded + [f'parallel_scout_queries:{cap}'],
	)

	fn = capture_fn
	if fn is None and allow_screenshots:
		from navigation.inspiration_intelligence.live_capture import _default_capture

		fn = _default_capture

	acquired, deg, timing = await acquire_from_winners(
		result.winners,
		max_visuals=max_visuals,
		capture_fn=fn,
		allow_screenshots=allow_screenshots,
	)
	result.acquired = acquired
	result.degraded.extend(deg)
	result.timing.extend(timing)
	return result
