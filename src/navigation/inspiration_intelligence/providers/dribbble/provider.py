"""Dribbble inspiration provider — browser-first discovery and capture.

The official Dribbble API is not used for Inspiration Intelligence.
Browsing is subject to Dribbble's terms of service.
"""
from __future__ import annotations

import asyncio
from typing import Any

from navigation.inspiration_intelligence.browser.fetch import enrich_preview_from_detail, http_get
from navigation.inspiration_intelligence.browser.policy import (
	RateLimitTracker,
	detect_block_signal,
	is_fast_mode,
	load_global_policy,
)
from navigation.inspiration_intelligence.browser.session import InspirationBrowserSession
from navigation.inspiration_intelligence.models import (
	CommunitySearchPlan,
	InspirationCandidate,
	InspirationCaptureResult,
	InspirationIntent,
	InspirationSearchPlan,
)
from navigation.inspiration_intelligence.providers.dribbble.navigation import DRIBBBLE_NAVIGATION
from navigation.inspiration_intelligence.providers.dribbble.parser import parse_search_html, query_to_slug


def _http_is_waf_stub(html: str, status: int | None) -> bool:
	signal = detect_block_signal(html, status_code=status)
	return signal in {'http_202', 'waf_stub_page'}


class DribbbleProvider:
	provider_id = 'dribbble'
	display_name = 'Dribbble'
	capabilities: frozenset[str] = frozenset({'discover', 'capture'})

	def __init__(
		self,
		*,
		fetch_html: Any | None = None,
		session_cookie: str = '',
		headless: bool | None = None,
	) -> None:
		self._fetch_html = fetch_html
		cfg = load_global_policy()
		self._session_cookie = session_cookie or str(cfg.get('dribbble_session_cookie', ''))
		self._headless = headless if headless is not None else bool(cfg.get('headless', False))
		self._policy = RateLimitTracker().policy_for('dribbble')
		self._tracker = RateLimitTracker()

	async def discover_candidates(
		self,
		plan: InspirationSearchPlan,
		*,
		community_plan: CommunitySearchPlan,
		intent: InspirationIntent,
		max_results: int = 20,
	) -> tuple[list[InspirationCandidate], list[str]]:
		_ = intent
		degraded: list[str] = []
		if self._tracker.over_budget(self.provider_id, self._policy):
			return [], ['dribbble_rate_budget_exhausted']

		queries = [q.text for q in community_plan.executable_queries if q.execute]
		if not queries:
			queries = [plan.seed_query or community_plan.seed_query]
		limit = 1 if is_fast_mode() else 3
		queries = [q for q in queries if q.strip()][:limit]

		seen: set[str] = set()
		candidates: list[InspirationCandidate] = []

		for query in queries:
			if self._tracker.over_budget(self.provider_id, self._policy):
				degraded.append('dribbble_rate_budget_exhausted')
				break

			batch, batch_degraded = await self._discover_query(query, max_results=max_results - len(candidates))
			degraded.extend(batch_degraded)

			for hit in batch:
				shot_id = hit.get('shot_id', '')
				if not shot_id or shot_id in seen:
					continue
				seen.add(shot_id)
				preview = hit.get('preview_url', '')
				preview_kind = hit.get('preview_kind', 'unknown')

				if not is_fast_mode() and (
					not preview or preview_kind in {'teaser', 'placeholder', 'anonymous'}
				):
					preview, _, og_deg = await self._resolve_preview(shot_id, hit.get('url', ''))
					degraded.extend(og_deg)
				elif is_fast_mode() and not preview and len(candidates) < 2:
					preview, _, og_deg = await self._resolve_preview(shot_id, hit.get('url', ''))
					degraded.extend(og_deg)

				score = _query_match_score(query, hit.get('title', ''))
				candidates.append(
					InspirationCandidate(
						candidate_id=f'dribbble:{shot_id}',
						title=hit.get('title', f'Shot {shot_id}'),
						source=self.provider_id,
						provider_id=self.provider_id,
						external_id=shot_id,
						url=hit.get('url', DRIBBBLE_NAVIGATION.detail_url(shot_id)),
						preview_ref=preview,
						metadata={
							'search_query': query,
							'search_slug': query_to_slug(query),
							'preview_kind': preview_kind,
							'fetch_tier': hit.get('fetch_tier', 'unknown'),
						},
						discovery_score=score,
					)
				)
				if len(candidates) >= max_results:
					break
			if len(candidates) >= max_results:
				break

		if not self._session_cookie:
			degraded.append(
				'dribbble_auth_hint:set DRIBBBLE_SESSION_COOKIE for logged-in grid previews'
			)

		candidates.sort(key=lambda c: c.discovery_score, reverse=True)
		return candidates[:max_results], degraded

	async def capture_design(
		self,
		candidate: InspirationCandidate,
		*,
		intent: InspirationIntent,
		allow_browser_screenshot: bool = False,
	) -> InspirationCaptureResult:
		_ = intent
		import os

		degraded: list[str] = []
		screenshot_refs: list[str] = []
		env_allow = os.environ.get('INSPIRATION_ALLOW_BROWSER_SCREENSHOT', '').strip().lower() in {
			'1',
			'true',
			'yes',
		}
		use_browser_ss = allow_browser_screenshot or env_allow

		if candidate.preview_ref:
			screenshot_refs.append(candidate.preview_ref)
			degraded.append('capture_tier:discovery_preview')

		if not screenshot_refs and candidate.url:
			preview, _, og_deg = await asyncio.to_thread(enrich_preview_from_detail, candidate.url)
			degraded.extend(og_deg)
			if preview:
				screenshot_refs.append(preview)
				degraded.append('capture_tier:og_image')

		# Image-first: skip browser screenshot unless explicitly allowed.
		if not screenshot_refs and candidate.url and use_browser_ss and not is_fast_mode():
			img, ss_deg = await self._browser_screenshot(candidate.url)
			degraded.extend(ss_deg)
			if img:
				screenshot_refs.append(img)
				degraded.append('capture_tier:browser_screenshot')
		elif not screenshot_refs and candidate.url and not use_browser_ss:
			degraded.append('capture_browser_screenshot_skipped:image_first')

		return InspirationCaptureResult(
			candidate_id=candidate.candidate_id,
			provider_id=self.provider_id,
			screenshot_refs=screenshot_refs,
			raw_payload={'detail_url': candidate.url, 'external_id': candidate.external_id},
			degraded=degraded if screenshot_refs else degraded + ['dribbble_capture_no_preview'],
		)

	async def health(self) -> dict[str, Any]:
		return {
			'provider_id': self.provider_id,
			'status': 'ok',
			'fetch_tiers': ['http_probe', 'perception_browser', 'og_image'],
			'headless': False,
			'perception_runtime': True,
			'has_session_cookie': bool(self._session_cookie),
			'fast_mode': is_fast_mode(),
			'note': 'HTTP returns 202 WAF stub — browser required for search',
		}

	async def _discover_query(self, query: str, *, max_results: int) -> tuple[list[dict[str, str]], list[str]]:
		degraded: list[str] = []
		slug = query_to_slug(query)
		url = DRIBBBLE_NAVIGATION.search_url(slug)

		# Tier 1: HTTP probe (fast when it works — usually WAF 202 on Dribbble)
		self._tracker.wait_if_needed(self.provider_id, self._policy)
		html = ''
		status: int | None = None
		try:
			html, status = await self._load_search_page(url)
			parsed = parse_search_html(html)
			if parsed and not _http_is_waf_stub(html, status):
				hits = [
					{
						'shot_id': h.shot_id,
						'title': h.title,
						'url': h.url,
						'preview_url': h.preview_url,
						'fetch_tier': 'http',
						'preview_kind': 'teaser' if h.preview_url else 'anonymous',
					}
					for h in parsed
				]
				return hits[:max_results], degraded
			if _http_is_waf_stub(html, status):
				degraded.append(f'dribbble_http_waf:{status or "stub"}')
		except Exception as exc:
			degraded.append(f'dribbble_http_failed:{exc}')

		# Tier 2: Browser — required for Dribbble search (WAF blocks plain HTTP)
		if self._fetch_html is not None:
			degraded.append(f'dribbble_parse_empty:{slug}')
			return [], degraded

		self._tracker.wait_if_needed(self.provider_id, self._policy)
		try:
			async with InspirationBrowserSession(
				provider_id='dribbble',
				policy=self._policy,
				headless=self._headless,
				session_cookie=self._session_cookie,
			) as session:
				hits, browser_deg = await session.extract_dribbble_hits(url)
				degraded.extend(browser_deg)
				if hits:
					for h in hits:
						h['fetch_tier'] = 'browser_session' if self._session_cookie else 'browser'
						h['preview_kind'] = 'session' if h.get('preview_url') and self._session_cookie else (
							'teaser' if h.get('preview_url') else 'anonymous'
						)
					degraded.append('dribbble_perception_browser_required')
					return hits[:max_results], degraded
		except Exception as exc:
			degraded.append(f'dribbble_browser_failed:{exc}')

		degraded.append(f'dribbble_parse_empty:{slug}')
		return [], degraded

	async def _resolve_preview(self, shot_id: str, url: str) -> tuple[str, str, list[str]]:
		detail_url = url or DRIBBBLE_NAVIGATION.detail_url(shot_id)
		return await asyncio.to_thread(enrich_preview_from_detail, detail_url)

	async def _load_search_page(self, url: str) -> tuple[str, int | None]:
		if self._fetch_html is not None:
			result = self._fetch_html(url)
			if asyncio.iscoroutine(result):
				html = await result
			else:
				html = result
			return html, 200
		html, status, err = await asyncio.to_thread(http_get, url, timeout=12.0)
		if err:
			raise RuntimeError(err)
		block = detect_block_signal(html, status_code=status)
		if block and block not in {'http_202', 'waf_stub_page'}:
			raise RuntimeError(block)
		return html, status

	async def _browser_screenshot(self, url: str) -> tuple[str, list[str]]:
		try:
			async with InspirationBrowserSession(
				provider_id='dribbble',
				policy=self._policy,
				headless=self._headless,
				session_cookie=self._session_cookie,
			) as session:
				self._tracker.wait_if_needed(self.provider_id, self._policy)
				return await session.screenshot_url(url)
		except Exception as exc:
			return '', [f'browser_screenshot_failed:{exc}']


def _query_match_score(query: str, title: str) -> float:
	q_tokens = {t for t in query.lower().split() if len(t) > 2}
	if not q_tokens:
		return 0.45
	title_l = title.lower()
	hits = sum(1 for t in q_tokens if t in title_l)
	return min(0.95, 0.35 + 0.15 * hits)
