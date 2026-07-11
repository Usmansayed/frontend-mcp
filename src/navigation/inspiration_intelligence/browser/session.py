"""Perception MCP browser session for inspiration providers — headed by default."""
from __future__ import annotations

import asyncio
from typing import Any

from navigation.inspiration_intelligence.browser.extract_scripts import PREPARE_PAGE_SCRIPT
from navigation.inspiration_intelligence.browser.perception_runtime import PerceptionBrowserRuntime
from navigation.inspiration_intelligence.browser.policy import ProviderFetchPolicy, detect_block_signal, fast_hydration_wait

_BROWSER_HEADERS = {
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
	'Accept-Language': 'en-US,en;q=0.9',
	'Cache-Control': 'no-cache',
	'Pragma': 'no-cache',
	'Sec-Fetch-Dest': 'document',
	'Sec-Fetch-Mode': 'navigate',
	'Sec-Fetch-Site': 'none',
	'Sec-Fetch-User': '?1',
	'Upgrade-Insecure-Requests': '1',
}

EXTRACT_SEARCH_HITS_SCRIPT = """
(() => {
  const hits = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href*="/shots/"]')) {
    const m = a.href.match(/\\/shots\\/(\\d+)/);
    if (!m || seen.has(m[1])) continue;
    seen.add(m[1]);
    const slug = (a.href.split('/shots/')[1] || '').split('?')[0];
    const titleFromSlug = slug.replace(/^\\d+-?/, '').replace(/-/g, ' ').trim();
    const title = a.getAttribute('aria-label')?.replace(/^View\\s+/i, '')
      || a.querySelector('img')?.alt
      || (titleFromSlug || `Shot ${m[1]}`);
    const img = a.querySelector('img[src*="cdn.dribbble.com"]');
    hits.push({
      shot_id: m[1],
      title: title.trim(),
      url: a.href.split('?')[0],
      preview_url: img?.src || img?.getAttribute('data-src') || '',
    });
    if (hits.length >= 40) break;
  }
  return { hits, title: document.title, url: location.href };
})()
"""


class InspirationBrowserSession:
	"""Headed perception browser — SessionStore + preflight navigate (same stack as perception MCP)."""

	def __init__(
		self,
		*,
		provider_id: str,
		policy: ProviderFetchPolicy,
		headless: bool | None = None,
		session_cookie: str = '',
		cookie_domain: str = '',
	) -> None:
		self._provider_id = provider_id
		self._policy = policy
		# Inspiration always uses headed perception browser unless explicitly overridden.
		self._headless = False if headless is None else headless
		self._session_cookie = session_cookie.strip()
		self._cookie_domain = cookie_domain or f'.{provider_id}.com'
		self._runtime: PerceptionBrowserRuntime | None = None
		self._last_screenshot_path: str | None = None

	async def __aenter__(self) -> InspirationBrowserSession:
		await self.start()
		return self

	async def __aexit__(self, *args: object) -> None:
		await self.close()

	async def start(self) -> None:
		base = f'https://{self._provider_id}.com'
		if self._provider_id == 'land-book':
			base = 'https://land-book.com'
		elif self._provider_id == 'onepagelove':
			base = 'https://onepagelove.com'
		elif self._provider_id == 'godly':
			base = 'https://recent.design'
		self._runtime = PerceptionBrowserRuntime()
		await self._runtime.start(base_url=base, headless=self._headless)
		if self._session_cookie:
			domain = '.dribbble.com' if self._provider_id == 'dribbble' else self._cookie_domain
			await self._runtime.inject_cookies(self._session_cookie, domain=domain)

	async def close(self) -> None:
		if self._runtime:
			await self._runtime.close()
		self._runtime = None

	async def fetch_html(self, url: str) -> tuple[str, list[str]]:
		degraded: list[str] = []
		runtime = self._runtime
		if runtime is None:
			return '', ['perception_session_not_started']

		result = await runtime.navigate_and_observe(url, name=f'{self._provider_id}-html')
		if not result.ok:
			degraded.append(f'perception_scan_failed:{result.error}')
			return '', degraded

		await asyncio.sleep(fast_hydration_wait(self._policy))
		html = await runtime.execute_script('document.documentElement.outerHTML') or ''
		if not isinstance(html, str):
			html = str(html)

		block = detect_block_signal(html)
		if block:
			degraded.append(f'perception_block:{block}')
		if result.screenshot_path:
			self._last_screenshot_path = result.screenshot_path

		degraded.extend(result.degraded)
		return html, degraded

	async def extract_with_script(
		self,
		url: str,
		*,
		extract_script: str,
		prepare: bool = True,
		ready_timeout: float = 20.0,
		hydration_s: float | None = None,
	) -> list[dict[str, str]]:
		"""Headed perception extract — prepare page (cookies/scroll) then run provider script."""
		runtime = self._runtime
		if runtime is None:
			return []

		result = await runtime.navigate_and_observe(
			url,
			name=f'{self._provider_id}-extract',
			screenshot=False,
			ready_timeout=ready_timeout,
		)
		if not result.ok:
			return []

		wait_s = hydration_s if hydration_s is not None else fast_hydration_wait(self._policy)
		await asyncio.sleep(wait_s)
		if prepare:
			await runtime.execute_script(PREPARE_PAGE_SCRIPT)
			await asyncio.sleep(min(wait_s, 3.0))
			# Provider script may be async (land-book load-more)
			extracted = await runtime.execute_script(extract_script)
		else:
			extracted = await runtime.execute_script(extract_script)
		if not isinstance(extracted, dict):
			return []

		hits = extracted.get('hits') or []
		normalized: list[dict[str, str]] = []
		for hit in hits:
			if not isinstance(hit, dict):
				continue
			normalized.append(
				{
					'external_id': str(hit.get('external_id', '')),
					'title': str(hit.get('title', '')),
					'url': str(hit.get('url', '')),
					'preview_url': str(hit.get('preview_url', '')),
				}
			)
		return normalized

	async def extract_gallery_hits(
		self,
		url: str,
		*,
		link_selector: str,
		id_regex: str,
	) -> list[dict[str, str]]:
		"""Generic gallery extraction via perception browser JS."""
		import json

		degraded: list[str] = []
		runtime = self._runtime
		if runtime is None:
			return []

		result = await runtime.navigate_and_observe(url, name=f'{self._provider_id}-gallery')
		degraded.extend(result.degraded)
		if not result.ok:
			return []

		await asyncio.sleep(fast_hydration_wait(self._policy))
		script = f"""
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
    if (hits.length >= 40) break;
  }}
  return {{ hits, url: location.href }};
}})()
"""
		extracted = await runtime.execute_script(script)
		if not isinstance(extracted, dict):
			return []
		hits = extracted.get('hits') or []
		normalized: list[dict[str, str]] = []
		for hit in hits:
			if not isinstance(hit, dict):
				continue
			normalized.append(
				{
					'external_id': str(hit.get('external_id', '')),
					'title': str(hit.get('title', '')),
					'url': str(hit.get('url', '')),
					'preview_url': str(hit.get('preview_url', '')),
				}
			)
		return normalized

	async def extract_dribbble_hits(self, url: str) -> tuple[list[dict[str, str]], list[str]]:
		degraded: list[str] = []
		runtime = self._runtime
		if runtime is None:
			return [], ['perception_session_not_started']

		result = await runtime.navigate_and_observe(url, name='dribbble-search')
		degraded.extend(result.degraded)
		if not result.ok:
			degraded.append(f'perception_scan_failed:{result.error}')
			return [], degraded

		await asyncio.sleep(fast_hydration_wait(self._policy))
		extracted = await runtime.execute_script(EXTRACT_SEARCH_HITS_SCRIPT)
		if not isinstance(extracted, dict):
			return [], ['perception_extract_failed']

		if result.screenshot_path:
			self._last_screenshot_path = result.screenshot_path
			degraded.append('perception_screenshot_captured')

		hits = extracted.get('hits') or []
		if not hits:
			degraded.append('perception_no_hits')
		if not self._session_cookie:
			degraded.append('dribbble_anonymous_previews_may_be_limited')

		normalized: list[dict[str, str]] = []
		for hit in hits:
			if not isinstance(hit, dict):
				continue
			normalized.append(
				{
					'shot_id': str(hit.get('shot_id', '')),
					'title': str(hit.get('title', '')),
					'url': str(hit.get('url', '')),
					'preview_url': str(hit.get('preview_url', '')),
				}
			)
		return normalized, degraded

	async def screenshot_url(self, url: str, *, wait_s: float | None = None) -> tuple[str, list[str]]:
		degraded: list[str] = []
		runtime = self._runtime
		if runtime is None:
			return '', ['perception_session_not_started']

		result = await runtime.navigate_and_observe(url, name=f'{self._provider_id}-capture')
		degraded.extend(result.degraded)
		if not result.ok:
			return '', degraded + [f'perception_scan_failed:{result.error}']

		if wait_s:
			await asyncio.sleep(wait_s)

		path = result.screenshot_path
		if path:
			return path, degraded + ['capture_tier:perception_screenshot']
		return '', degraded + ['perception_screenshot_missing']
