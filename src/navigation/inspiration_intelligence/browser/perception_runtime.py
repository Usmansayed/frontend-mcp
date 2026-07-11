"""Perception MCP browser runtime — SessionStore + navigate/execute (inspiration mode)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from navigation.visual_browser_intelligence.browser.session_store import SessionStore
from navigation.visual_browser_intelligence.observe.preflight import preflight_check
from navigation.visual_browser_intelligence.verify.verification import evaluate_js, read_current_url


class PerceptionBrowseResult:
	"""Lightweight navigate result — avoids full scan_page/design-sense pipeline."""

	def __init__(
		self,
		*,
		ok: bool,
		url: str,
		screenshot_path: str | None = None,
		degraded: list[str] | None = None,
		error: str | None = None,
	) -> None:
		self.ok = ok
		self.url = url
		self.screenshot_path = screenshot_path
		self.degraded = degraded or []
		self.error = error


class PerceptionBrowserRuntime:
	"""Headed perception browser — same SessionStore as perception_session_start."""

	def __init__(self, *, artifacts_root: Path | None = None) -> None:
		root = artifacts_root or Path.cwd() / 'artifacts' / 'inspiration_browser'
		self._store = SessionStore(artifacts_root=root)
		self._session_id: str | None = None
		self._rec: Any = None

	@property
	def session_id(self) -> str | None:
		return self._session_id

	@property
	def browser(self) -> Any:
		return self._rec.browser if self._rec else None

	async def start(self, *, base_url: str, headless: bool = False) -> str:
		self._rec = await self._store.start(
			base_url=base_url,
			headless=headless,
			viewport_width=1440,
			viewport_height=900,
		)
		self._session_id = self._rec.session_id
		return self._session_id

	async def close(self) -> None:
		if self._session_id:
			await self._store.end(self._session_id)
		self._session_id = None
		self._rec = None

	async def navigate_and_observe(
		self,
		url: str,
		*,
		name: str = 'inspiration-scan',
		screenshot: bool = True,
		ready_timeout: float = 15.0,
	) -> PerceptionBrowseResult:
		if self._rec is None:
			return PerceptionBrowseResult(ok=False, url=url, error='perception_session_not_started')

		browser = self._rec.browser
		degraded: list[str] = []

		preflight = await preflight_check(browser, url, ready_timeout=ready_timeout)
		degraded.extend(preflight.degraded or [])
		if not preflight.ok:
			return PerceptionBrowseResult(
				ok=False,
				url=url,
				error=preflight.error or 'preflight_failed',
				degraded=degraded,
			)

		current_url = preflight.url or await read_current_url(browser)

		screenshot_path: str | None = None
		if screenshot:
			screenshot_path = await self._capture_screenshot(name=name)
			if not screenshot_path:
				degraded.append('perception_screenshot_missing')

		return PerceptionBrowseResult(
			ok=True,
			url=current_url or url,
			screenshot_path=screenshot_path,
			degraded=degraded,
		)

	async def execute_script(self, script: str) -> Any:
		if self._rec is None:
			raise RuntimeError('perception_session_not_started')
		return await evaluate_js(self._rec.browser, script)

	async def inject_cookies(self, cookie_header: str, *, domain: str) -> None:
		browser = self.browser
		if not browser or not cookie_header.strip():
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
						'domain': domain,
						'path': '/',
						'secure': True,
						'httpOnly': False,
					},
					session_id=cdp.session_id,
				)
		except Exception:
			pass

	async def _capture_screenshot(self, *, name: str) -> str | None:
		if self._rec is None:
			return None
		images_dir = self._rec.artifacts_dir / 'images'
		images_dir.mkdir(parents=True, exist_ok=True)
		path = images_dir / f'{name}.png'
		try:
			cdp = await self._rec.browser.get_or_create_cdp_session(target_id=None, focus=True)
			result = await cdp.cdp_client.send.Page.captureScreenshot(
				params={'format': 'png', 'fromSurface': True},
				session_id=cdp.session_id,
			)
			data = result.get('data', '') if isinstance(result, dict) else ''
			if not data:
				return None
			import base64

			path.write_bytes(base64.b64decode(data))
			return str(path)
		except Exception:
			return None
