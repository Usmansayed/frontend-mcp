"""LibreCrawl HTTP API client."""
from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx


def base_url() -> str:
	raw = os.environ.get('LIBRECRAWL_BASE_URL', '').strip().rstrip('/')
	if not raw:
		return ''
	if raw.endswith('/api'):
		return raw
	return f'{raw}/api'


def session_cookie() -> str:
	return os.environ.get('LIBRECRAWL_SESSION_COOKIE', '').strip()


def crawl_timeout_s() -> int:
	try:
		return max(10, int(os.environ.get('LIBRECRAWL_CRAWL_TIMEOUT_S', '90')))
	except ValueError:
		return 90


class LibreCrawlClient:
	def __init__(self, *, base: str | None = None, session: str | None = None) -> None:
		self._base = (base or base_url()).rstrip('/')
		self._session = session if session is not None else session_cookie()

	def configured(self) -> bool:
		return bool(self._base)

	def _headers(self) -> dict[str, str]:
		headers = {'Content-Type': 'application/json'}
		if self._session:
			headers['Cookie'] = f'session={self._session}'
		return headers

	async def _request(self, method: str, path: str, **kwargs: Any) -> tuple[dict[str, Any] | None, list[str]]:
		if not self.configured():
			return None, ['librecrawl_not_configured']
		url = f'{self._base}{path}'
		try:
			async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
				resp = await client.request(method, url, headers=self._headers(), **kwargs)
			if resp.status_code == 401:
				return None, ['librecrawl_unauthorized:set_LIBRECRAWL_SESSION_COOKIE_or_guest_login']
			resp.raise_for_status()
			data = resp.json()
			return data if isinstance(data, dict) else {'data': data}, []
		except Exception as exc:
			return None, [f'librecrawl_http_error:{type(exc).__name__}']

	async def guest_login(self) -> tuple[str | None, list[str]]:
		payload, degraded = await self._request('POST', '/guest-login', json={})
		if payload is None:
			return None, degraded
		if payload.get('success'):
			# Session cookie must be set by caller from response cookies when available.
			return self._session or 'guest', degraded
		return None, degraded + ['librecrawl_guest_login_failed']

	async def start_crawl(self, url: str) -> tuple[dict[str, Any] | None, list[str]]:
		return await self._request('POST', '/start_crawl', json={'url': url})

	async def crawl_status(self) -> tuple[dict[str, Any] | None, list[str]]:
		return await self._request('GET', '/crawl_status')

	async def wait_for_crawl(self, *, timeout_s: int | None = None) -> tuple[dict[str, Any] | None, list[str]]:
		limit = timeout_s if timeout_s is not None else crawl_timeout_s()
		degraded: list[str] = []
		elapsed = 0.0
		interval = 2.0
		last: dict[str, Any] | None = None
		while elapsed < limit:
			payload, poll_deg = await self.crawl_status()
			degraded.extend(poll_deg)
			if payload is None:
				return None, degraded
			last = payload
			status = str(payload.get('status') or '').lower()
			if status in {'completed', 'stopped', 'failed'}:
				return payload, degraded
			if status in {'idle', 'not_running', ''} and (payload.get('urls') or payload.get('issues')):
				return payload, degraded
			await asyncio.sleep(interval)
			elapsed += interval
		degraded.append(f'librecrawl_crawl_timeout:{int(limit)}s')
		return last, degraded

	async def crawl_site(self, url: str) -> tuple[dict[str, Any] | None, list[str]]:
		degraded: list[str] = []
		status_payload, status_deg = await self.crawl_status()
		degraded.extend(status_deg)
		running = status_payload and str(status_payload.get('status', '')).lower() in {'running', 'paused'}
		if not running:
			start_payload, start_deg = await self.start_crawl(url)
			degraded.extend(start_deg)
			if start_payload is None:
				return None, degraded
		return await self.wait_for_crawl()
