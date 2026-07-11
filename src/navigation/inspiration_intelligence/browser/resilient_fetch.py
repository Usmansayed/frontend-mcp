"""Resilient page fetch — HTTP probe, perception browser fallback, bounded retries."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from navigation.inspiration_intelligence.browser.fetch import http_get
from navigation.inspiration_intelligence.browser.policy import (
	ProviderFetchPolicy,
	RateLimitTracker,
	detect_block_signal,
	fast_hydration_wait,
	is_fast_mode,
	load_global_policy,
)
from navigation.inspiration_intelligence.browser.session import InspirationBrowserSession


ParseFn = Callable[[str, str], list[dict[str, str]]]
UrlBuilder = Callable[[str], list[str]]


@dataclass(slots=True)
class FetchAttemptResult:
	ok: bool
	html: str = ''
	hits: list[dict[str, str]] = field(default_factory=list)
	fetch_tier: str = 'none'
	url: str = ''
	degraded: list[str] = field(default_factory=list)
	error: str | None = None


@dataclass(slots=True)
class ResilientFetchConfig:
	provider_id: str
	parse_html: ParseFn
	build_urls: UrlBuilder
	link_selector: str = ''
	id_regex: str = ''
	extract_script: str = ''
	browser_required: bool = False
	prefer_browser: bool = False
	max_url_attempts: int = 2
	max_browser_retries: int = 2
	ready_timeout: float = 20.0
	hydration_s: float | None = None
	session_cookie: str = ''
	cookie_domain: str = ''


def _needs_browser(html: str, status: int | None, hits: list[dict[str, str]], *, browser_required: bool) -> bool:
	if browser_required:
		return True
	if hits:
		return False
	block = detect_block_signal(html, status_code=status)
	if block:
		return True
	if not html.strip():
		return True
	# SPA shells — short HTML without result anchors
	if len(html) < 12000 and not hits:
		return True
	return False


def _build_extract_script(link_selector: str, id_regex: str, *, max_hits: int = 40) -> str:
	import json

	return f"""
(() => {{
  const hits = [];
  const seen = new Set();
  const idRe = new RegExp({json.dumps(id_regex)});
  for (const a of document.querySelectorAll({json.dumps(link_selector)})) {{
    const href = a.href || '';
    const m = href.match(idRe);
    if (!m) continue;
    const externalId = m[1];
    if (seen.has(externalId)) continue;
    seen.add(externalId);
    const title = a.getAttribute('aria-label')?.replace(/^View\\s+/i, '')
      || a.querySelector('img')?.alt
      || a.textContent?.trim()
      || externalId;
    const img = a.querySelector('img');
    hits.push({{
      external_id: externalId,
      title: title.trim().slice(0, 140),
      url: href.split('?')[0],
      preview_url: img?.src || img?.getAttribute('data-src') || '',
    }});
    if (hits.length >= {max_hits}) break;
  }}
  return {{ hits, url: location.href }};
}})()
"""


class ResilientPageFetcher:
	"""Production fetcher — never gives up on first empty/block without browser retries."""

	def __init__(self, config: ResilientFetchConfig) -> None:
		self._config = config
		self._tracker = RateLimitTracker()
		self._policy = self._tracker.policy_for(config.provider_id)
		cfg = load_global_policy()
		self._headless = bool(cfg.get('headless', False))

	async def fetch_hits(self, query: str, *, max_hits: int = 20) -> FetchAttemptResult:
		degraded: list[str] = []
		cfg = self._config
		urls = cfg.build_urls(query)
		if not urls:
			return FetchAttemptResult(ok=False, degraded=['resilient_no_urls'], error='no_urls')

		limit = 1 if is_fast_mode() and not cfg.prefer_browser else cfg.max_url_attempts
		if cfg.browser_required or cfg.prefer_browser:
			attempt_urls = urls[: cfg.max_url_attempts]
			for url in attempt_urls:
				result = await self._fetch_browser_only(url, max_hits=max_hits, attempt=0)
				degraded.extend(result.degraded)
				if result.ok and result.hits:
					result.degraded = degraded
					return result
			# Land-book: return category browse URL so agents can open the gallery in perception
			if cfg.provider_id == 'land-book' and attempt_urls:
				browse = attempt_urls[0]
				return FetchAttemptResult(
					ok=True,
					hits=[{
						'external_id': 'browse',
						'title': 'Land-book gallery browse',
						'url': browse,
						'preview_url': '',
					}],
					fetch_tier='perception_browse_fallback',
					url=browse,
					degraded=degraded + ['landbook_browse_fallback'],
				)
			return FetchAttemptResult(
				ok=False,
				degraded=degraded + ['resilient_all_attempts_failed'],
				error='all_attempts_failed',
			)

		for url in urls[:limit]:
			result = await self._fetch_one_url(url, max_hits=max_hits)
			degraded.extend(result.degraded)
			if result.ok and result.hits:
				result.degraded = degraded
				return result

		# Retry remaining URLs with browser-only if fast mode only tried one HTTP path
		if is_fast_mode() and len(urls) > 1:
			for url in urls[1:2]:
				result = await self._fetch_browser_only(url, max_hits=max_hits, attempt=1)
				degraded.extend(result.degraded)
				if result.ok and result.hits:
					result.degraded = degraded
					return result

		return FetchAttemptResult(
			ok=False,
			degraded=degraded + ['resilient_all_attempts_failed'],
			error='all_attempts_failed',
		)

	async def _fetch_one_url(self, url: str, *, max_hits: int) -> FetchAttemptResult:
		degraded: list[str] = []
		cfg = self._config

		if not cfg.browser_required:
			self._tracker.wait_if_needed(cfg.provider_id, self._policy)
			html, status, err = await asyncio.to_thread(http_get, url, timeout=15.0)
			if err:
				degraded.append(f'http_error:{err}')
			else:
				hits = cfg.parse_html(html, url)
				if hits:
					return FetchAttemptResult(
						ok=True,
						html=html,
						hits=hits[:max_hits],
						fetch_tier='http',
						url=url,
						degraded=degraded,
					)
				block = detect_block_signal(html, status_code=status)
				if block:
					degraded.append(f'http_block:{block}')

				if not _needs_browser(html, status, hits, browser_required=False):
					degraded.append('http_parse_empty')
					return FetchAttemptResult(ok=False, url=url, html=html, degraded=degraded, error='parse_empty')

		return await self._fetch_browser_only(url, max_hits=max_hits, attempt=0, prior_degraded=degraded)

	async def _fetch_browser_only(
		self,
		url: str,
		*,
		max_hits: int,
		attempt: int,
		prior_degraded: list[str] | None = None,
	) -> FetchAttemptResult:
		degraded = list(prior_degraded or [])
		cfg = self._config
		retries = 1 if is_fast_mode() else cfg.max_browser_retries

		for retry in range(retries):
			self._tracker.wait_if_needed(cfg.provider_id, self._policy)
			try:
				async with InspirationBrowserSession(
					provider_id=cfg.provider_id,
					policy=self._policy,
					headless=self._headless,
					session_cookie=cfg.session_cookie,
					cookie_domain=cfg.cookie_domain,
				) as session:
					hits: list[dict[str, str]] = []
					html = ''

					if cfg.extract_script:
						hits = await session.extract_with_script(
							url,
							extract_script=cfg.extract_script,
							ready_timeout=cfg.ready_timeout,
							hydration_s=cfg.hydration_s,
						)
						if hits:
							degraded.append('perception_script_extract')
					elif cfg.link_selector and cfg.id_regex:
						hits = await session.extract_gallery_hits(
							url,
							link_selector=cfg.link_selector,
							id_regex=cfg.id_regex,
						)
						if hits:
							degraded.append('perception_js_extract')
					else:
						html, browse_deg = await session.fetch_html(url)
						degraded.extend(browse_deg)
						hits = cfg.parse_html(html, url) if html else []

					if hits:
						tier = 'perception_browser'
						if retry > 0 or attempt > 0:
							tier = 'perception_browser_retry'
						return FetchAttemptResult(
							ok=True,
							html=html,
							hits=hits[:max_hits],
							fetch_tier=tier,
							url=url,
							degraded=degraded,
						)

					if retry < retries - 1:
						degraded.append(f'perception_retry:{retry + 1}')
						await asyncio.sleep(fast_hydration_wait(self._policy))
			except Exception as exc:
				degraded.append(f'perception_browser_failed:{exc}')

		return FetchAttemptResult(ok=False, url=url, degraded=degraded, error='browser_failed')
