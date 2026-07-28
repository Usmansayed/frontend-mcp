"""Live famous-site screenshot channel — exclusive browser queue.

Captures viewport screenshots of curated product URLs for Inspiration collect.
Uses Inspiration's own Chromium (not the host Perception session_id) to avoid
session fights; concurrency is serial by default (anti-bot / machine load).
"""
from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse

from navigation.inspiration_intelligence.browser.host_cooldown import (
	is_cooled,
	mark_from_degraded,
)
from navigation.inspiration_intelligence.browser.policy import ProviderFetchPolicy
from navigation.inspiration_intelligence.famous_sites import (
	famous_site_hit_sketch,
	select_famous_sites,
)

CaptureFn = Callable[[dict[str, str]], Awaitable[tuple[str, str, list[str]]]]

_CAPTURE_LOCK = asyncio.Lock()
_MIN_CAPTURE_BUDGET_S = 6.0


@dataclass
class LiveSiteCaptureResult:
	hits: list[dict[str, Any]] = field(default_factory=list)
	degraded: list[str] = field(default_factory=list)
	timing: list[dict[str, Any]] = field(default_factory=list)
	sites_attempted: int = 0


def should_run_live_sites(
	*,
	mode: str,
	channels: list[str],
	max_famous_sites: int,
	gallery_ref_count: int,
	min_refs: int,
	include_live_sites: bool | None,
) -> bool:
	if include_live_sites is False:
		return False
	if max_famous_sites <= 0 or 'live_site' not in channels:
		return False
	if include_live_sites is True:
		return True
	mode_l = (mode or 'fast').lower()
	if mode_l in {'broad', 'deep'}:
		return True
	return gallery_ref_count < min_refs


def _origin(url: str) -> str:
	parsed = urlparse(url)
	if not parsed.scheme or not parsed.netloc:
		return ''
	return f'{parsed.scheme}://{parsed.netloc}'


def _headed_retry_enabled() -> bool:
	raw = (os.environ.get('INSPIRATION_HEADED_RETRY') or '1').strip().lower()
	return raw not in {'0', 'false', 'no', 'off'}


async def _force_close_session(session: Any) -> None:
	"""Best-effort close + Chromium reset — hard-bounded so cleanup cannot hang forever."""
	try:
		await asyncio.wait_for(session.close(), timeout=2.5)
	except Exception:
		pass
	runtime = getattr(session, '_runtime', None)
	if runtime is not None:
		try:
			await asyncio.wait_for(runtime.force_kill(), timeout=3.0)
		except Exception:
			pass


async def _capture_once(
	site: dict[str, str],
	*,
	headless: bool,
	timeout_s: float,
	focus_scope: str | None,
) -> tuple[str, str, list[str]]:
	from navigation.inspiration_intelligence.browser.session import InspirationBrowserSession

	url = str(site.get('url') or '')
	origin = _origin(url)
	title = str(site.get('title') or '')
	policy = ProviderFetchPolicy(
		provider_id='famous_site',
		min_delay_s=0.5,
		max_delay_s=1.0,
		hydration_wait_s=3.5 if not headless else 2.5,
		headless_default=headless,
		max_requests_per_run=4,
	)
	session = InspirationBrowserSession(
		provider_id='famous_site',
		policy=policy,
		headless=headless,
		base_url=origin,
	)

	async def _run() -> tuple[str, str, list[str]]:
		nonlocal title
		await session.start()
		path, ss_deg = await session.screenshot_url(
			url,
			wait_s=1.0 if headless else 1.5,
			ready_timeout=8.0 if headless else 10.0,
			focus_scope=focus_scope,
			focus_query=str(site.get('focus_query') or site.get('title') or ''),
		)
		degraded_local = list(ss_deg)
		try:
			runtime = session._runtime  # noqa: SLF001
			if runtime is not None:
				page_title = await runtime.execute_script('document.title')
				if isinstance(page_title, str) and page_title.strip():
					title = page_title.strip()
		except Exception:
			pass
		return path or '', title, degraded_local

	async def _drain(task: asyncio.Task) -> None:
		try:
			await task
		except (asyncio.CancelledError, Exception):
			pass

	task = asyncio.create_task(_run())
	try:
		path, title, deg = await asyncio.wait_for(task, timeout=max(3.0, float(timeout_s)))
		await session.close()
		return path, title, deg
	except asyncio.TimeoutError:
		task.cancel()
		await _drain(task)
		await _force_close_session(session)
		return '', title, [f'live_site_capture_timeout:{timeout_s}s', 'browser_force_closed']
	except asyncio.CancelledError:
		task.cancel()
		await _drain(task)
		await _force_close_session(session)
		raise
	except Exception as exc:  # noqa: BLE001
		task.cancel()
		await _drain(task)
		await _force_close_session(session)
		return '', title, [f'live_site_capture_failed:{exc}', 'browser_force_closed']


async def _default_capture(
	site: dict[str, str],
	*,
	timeout_s: float = 10.0,
	deadline_mono: float | None = None,
	headed_retry: bool | None = None,
) -> tuple[str, str, list[str]]:
	url = str(site.get('url') or '')
	origin = _origin(url)
	if not url or not origin:
		return '', '', ['live_site_invalid_url']

	# Kill-switch — keep HTTP/pattern path dominant when Chromium is unhealthy
	if (os.environ.get('INSPIRATION_SKIP_LIVE_BROWSER') or '').strip().lower() in {
		'1',
		'true',
		'yes',
		'on',
	}:
		return '', str(site.get('title') or ''), ['live_browser_skipped_by_env']

	env_to = (os.environ.get('INSPIRATION_LIVE_CAPTURE_TIMEOUT_S') or '').strip()
	if env_to:
		try:
			timeout_s = min(float(timeout_s), max(3.0, float(env_to)))
		except ValueError:
			pass

	title = str(site.get('title') or '')
	focus_scope = str(site.get('focus_scope') or site.get('scope') or '').strip() or None
	degraded: list[str] = []

	if is_cooled(url):
		return '', title, ['host_cooldown_skip']

	if deadline_mono is not None:
		remaining = deadline_mono - time.monotonic()
		if remaining < _MIN_CAPTURE_BUDGET_S:
			return '', title, [f'live_site_deadline_skip:{remaining:.1f}s']
		timeout_s = min(float(timeout_s), max(3.0, remaining - 0.5))

	do_headed = _headed_retry_enabled() if headed_retry is None else bool(headed_retry)

	async with _CAPTURE_LOCK:
		if is_cooled(url):
			return '', title, ['host_cooldown_skip']
		if deadline_mono is not None and (deadline_mono - time.monotonic()) < _MIN_CAPTURE_BUDGET_S:
			return '', title, ['live_site_deadline_skip_locked']

		path, title, deg = await _capture_once(
			site,
			headless=True,
			timeout_s=timeout_s,
			focus_scope=focus_scope,
		)
		degraded.extend(deg)
		mark_from_degraded(url, deg)

		blocked = any(
			x in ' '.join(deg).lower()
			for x in ('bot_challenge', 'waf_stub', 'screenshot_skipped_blocked', 'perception_block:')
		)
		if (
			not path
			and blocked
			and do_headed
			and (deadline_mono is None or (deadline_mono - time.monotonic()) >= _MIN_CAPTURE_BUDGET_S + 2)
		):
			from navigation.inspiration_intelligence.browser import host_cooldown as hc

			h = hc.host_of(url)
			with hc._LOCK:  # noqa: SLF001
				hc._COOLDOWN.pop(h, None)  # noqa: SLF001

			path2, title2, deg2 = await _capture_once(
				site,
				headless=False,
				timeout_s=min(12.0, float(timeout_s) + 2.0),
				focus_scope=focus_scope,
			)
			degraded.extend(['headed_retry_after_block'] + list(deg2))
			mark_from_degraded(url, deg2)
			if path2:
				return path2, title2 or title, degraded
			return '', title2 or title, degraded

		return path, title, degraded


async def capture_famous_sites(
	categories: list[str],
	*,
	max_sites: int = 2,
	browser_concurrency: int = 1,
	capture_fn: CaptureFn | None = None,
	capture_timeout_s: float = 10.0,
	focus_scope: str | None = None,
	deadline_mono: float | None = None,
) -> LiveSiteCaptureResult:
	sites = select_famous_sites(categories, max_sites=max_sites)
	result = LiveSiteCaptureResult()
	if not sites:
		result.degraded.append('live_site_corpus_empty')
		return result

	filtered: list[dict[str, str]] = []
	for site in sites:
		if focus_scope:
			site.setdefault('focus_scope', focus_scope)
		url = str(site.get('url') or '')
		if is_cooled(url):
			result.degraded.append(f"host_cooldown_skip:{site.get('id')}")
			continue
		filtered.append(site)
	sites = filtered
	if not sites:
		result.degraded.append('live_site_all_cooled')
		return result

	async def _default_with_timeout(site: dict[str, str]) -> tuple[str, str, list[str]]:
		return await _default_capture(
			site,
			timeout_s=capture_timeout_s,
			deadline_mono=deadline_mono,
		)

	fn = capture_fn or _default_with_timeout
	for site in sites:
		if deadline_mono is not None and (deadline_mono - time.monotonic()) < _MIN_CAPTURE_BUDGET_S:
			result.degraded.append('live_site_wave_deadline_stop')
			break
		t0 = time.perf_counter()
		try:
			path, title, deg = await asyncio.wait_for(
				fn(site),
				timeout=max(3.0, float(capture_timeout_s) + 1.0),
			)
		except asyncio.TimeoutError:
			path, title, deg = '', str(site.get('title') or ''), [
				f'live_site_capture_timeout:{capture_timeout_s}s'
			]
		elapsed = (time.perf_counter() - t0) * 1000.0
		result.sites_attempted += 1
		result.degraded.extend(deg)
		result.timing.append(
			{
				'provider_id': 'famous_site',
				'site_id': site.get('id'),
				'elapsed_ms': round(elapsed, 1),
				'ok': bool(path),
				'tier': 'live_site',
			}
		)
		if not path:
			result.degraded.append(f"live_site_no_screenshot:{site.get('id')}")
			continue
		hit = famous_site_hit_sketch(site, page_title=title)
		hit['screenshot_path'] = path
		from pathlib import Path

		p = Path(path)
		if p.is_file():
			hit['preview_url'] = p.resolve().as_uri()
		result.hits.append(hit)

	return result
