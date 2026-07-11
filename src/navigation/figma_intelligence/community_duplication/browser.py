"""Browser automation for Community → Drafts duplication (browser_use + CDP network)."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from navigation.figma_intelligence.community_duplication.file_key_resolver import (
	file_key_from_url,
	resolve_file_key_from_payload,
)
from navigation.figma_intelligence.community_duplication.models import DuplicationResult
from navigation.frontend_quality_intelligence.network.service import SessionNetworkService
from navigation.visual_browser_intelligence.observe.preflight import wait_for_page_ready
from navigation.visual_browser_intelligence.verify.verification import (
	evaluate_js,
	read_current_url,
)

DUPLICATE_CLICK_SCRIPT = """
(async () => {
  for (let i = 0; i < 40; i++) {
    const btn = document.querySelector('[data-testid="community-duplicate-button"]')
      || [...document.querySelectorAll('button,a')].find(el => /open in figma/i.test(el.innerText || ''));
    if (btn) {
      btn.click();
      return { ok: true };
    }
    await new Promise(r => setTimeout(r, 500));
  }
  return { ok: false, reason: 'button_not_found', title: document.title, url: location.href };
})()
"""

LOGIN_CHECK_SCRIPT = """
(() => {
  const url = location.href;
  if (url.includes('/login') || url.includes('/start')) return { login: true };
  const body = document.body?.innerText || '';
  if (body.includes('Log in to Figma') && !body.includes('Open in Figma')) return { login: true };
  return { login: false };
})()
"""


class CommunityDuplicationBrowser:
	"""Browser Intelligence-backed duplication using browser_use + network capture."""

	def __init__(
		self,
		*,
		headless: bool = False,
		session_cookie: str = '',
		timeout_s: float = 120.0,
	) -> None:
		self._headless = headless
		self._session_cookie = session_cookie.strip()
		self._timeout_s = timeout_s
		self._browser: Any = None
		self._network = SessionNetworkService()

	async def __aenter__(self) -> CommunityDuplicationBrowser:
		await self.start()
		return self

	async def __aexit__(self, *args: object) -> None:
		await self.close()

	async def start(self) -> None:
		from browser_use import BrowserProfile, BrowserSession

		self._browser = BrowserSession(
			browser_profile=BrowserProfile(
				headless=self._headless,
				viewport={'width': 1920, 'height': 1080},
			)
		)
		await self._browser.start()
		await self._network.attach(self._browser)
		if self._session_cookie:
			await self._inject_cookies(self._session_cookie)

	async def close(self) -> None:
		try:
			self._network.detach()
		except Exception:
			pass
		if self._browser:
			try:
				await self._browser.kill()
			except Exception:
				pass
		self._browser = None

	async def duplicate_community_file(
		self,
		*,
		content_id: str,
		community_url: str,
	) -> tuple[DuplicationResult, list[str]]:
		degraded: list[str] = []
		url = community_url or f'https://www.figma.com/community/file/{content_id}'
		browser = self._browser
		assert browser is not None

		await browser.navigate_to(url)
		await wait_for_page_ready(browser, timeout=25.0)
		await asyncio.sleep(10)

		page_probe = await evaluate_js(
			browser,
			"({ title: document.title, body: (document.body?.innerText||'').slice(0,200), url: location.href })",
		)
		if isinstance(page_probe, dict) and '403 ERROR' in str(page_probe.get('body', '')):
			degraded.append('browser_cloudfront_blocked')
			return (
				DuplicationResult(content_id=content_id, method='browser_open_in_figma', degraded=degraded),
				degraded,
			)

		login_state = await evaluate_js(browser, LOGIN_CHECK_SCRIPT)
		if isinstance(login_state, dict) and login_state.get('login'):
			degraded.append('browser_login_required')
			return (
				DuplicationResult(content_id=content_id, method='browser_open_in_figma', degraded=degraded),
				degraded,
			)

		window_start = self._network.mark_window()
		click_result = await evaluate_js(browser, DUPLICATE_CLICK_SCRIPT)
		if not (isinstance(click_result, dict) and click_result.get('ok')):
			reason = click_result.get('reason') if isinstance(click_result, dict) else 'unknown'
			degraded.append(f'browser_duplicate_button_not_found:{reason}')
			return (
				DuplicationResult(content_id=content_id, method='browser_open_in_figma', degraded=degraded),
				degraded,
			)

		file_key = await self._wait_for_design_url(browser, timeout_s=self._timeout_s)
		if not file_key:
			file_key, draft_url = await self._file_key_from_network(
				content_id,
				window_start=window_start,
			)
		else:
			draft_url = await read_current_url(browser)

		if not file_key:
			degraded.append('browser_duplicate_no_file_key')
			return (
				DuplicationResult(content_id=content_id, method='browser_open_in_figma', degraded=degraded),
				degraded,
			)

		return (
			DuplicationResult(
				content_id=content_id,
				file_key=file_key,
				draft_url=draft_url or f'https://www.figma.com/design/{file_key}',
				method='browser_open_in_figma',
				degraded=degraded,
			),
			degraded,
		)

	async def _wait_for_design_url(self, browser: Any, *, timeout_s: float) -> str:
		deadline = time.monotonic() + timeout_s
		while time.monotonic() < deadline:
			url = await read_current_url(browser)
			key = file_key_from_url(url)
			if key:
				return key
			await asyncio.sleep(0.35)
		return ''

	async def _file_key_from_network(self, content_id: str, *, window_start: int) -> tuple[str, str]:
		report = await self._network.report(
			self._browser,
			window_start_index=window_start,
			fetch_bodies=True,
		)
		for entry in reversed(report.entries):
			url = entry.url or ''
			if f'/hub_files/{content_id}/duplicate' not in url and not url.rstrip('/').endswith(
				f'{content_id}/duplicate'
			):
				continue
			if entry.response_body:
				try:
					payload = json.loads(entry.response_body)
					return resolve_file_key_from_payload(payload)
				except json.JSONDecodeError:
					continue
			key = file_key_from_url(url)
			if key:
				return key, url
		return '', ''

	async def _inject_cookies(self, cookie_header: str) -> None:
		"""Best-effort cookie injection via CDP."""
		browser = self._browser
		if not browser:
			return
		try:
			cdp = await browser.get_or_create_cdp_session(target_id=None, focus=True)
			for part in cookie_header.split(';'):
				part = part.strip()
				if not part or '=' not in part:
					continue
				name, value = part.split('=', 1)
				await cdp.cdp_client.send.Network.setCookie(
					params={
						'name': name.strip(),
						'value': value.strip(),
						'domain': '.figma.com',
						'path': '/',
					},
					session_id=cdp.session_id,
				)
		except Exception:
			pass
