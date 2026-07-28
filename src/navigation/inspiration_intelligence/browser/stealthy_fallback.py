"""Scrapling Stealthy fetch primitive + budget (see scrapling_route for policy)."""
from __future__ import annotations

import os
import threading
from typing import Any

_LOCK = threading.Lock()
_USED = 0


def stealthy_fallback_enabled() -> bool:
	from navigation.inspiration_intelligence.browser.scrapling_route import scrapling_recovery_enabled

	return scrapling_recovery_enabled()


def stealthy_in_fast_mode() -> bool:
	"""Legacy: explicit opt-in. Prefer important-host recovery (default on)."""
	raw = (os.environ.get('INSPIRATION_STEALTHY_IN_FAST') or '0').strip().lower()
	return raw in {'1', 'true', 'yes', 'on'}


def stealthy_budget() -> int:
	try:
		return max(0, int(os.environ.get('INSPIRATION_STEALTHY_BUDGET') or '2'))
	except ValueError:
		return 2


def stealthy_timeout_ms() -> int:
	try:
		return max(8_000, int(os.environ.get('INSPIRATION_STEALTHY_TIMEOUT_MS') or '28000'))
	except ValueError:
		return 28_000


def stealthy_budget_remaining() -> int:
	with _LOCK:
		return max(0, stealthy_budget() - _USED)


def reset_stealthy_budget_for_tests() -> None:
	global _USED
	with _LOCK:
		_USED = 0


def waf_host_allowlisted(url: str) -> bool:
	from navigation.inspiration_intelligence.browser.scrapling_route import is_important_waf_host

	return is_important_waf_host(url)


def should_try_stealthy(url: str, *, blocked: bool, fast_mode: bool) -> bool:
	from navigation.inspiration_intelligence.browser.scrapling_route import should_try_stealthy as _route

	return _route(url, blocked=blocked, fast_mode=fast_mode, chromium_failed_or_skipped=True)


def _consume_budget() -> bool:
	global _USED
	with _LOCK:
		if _USED >= stealthy_budget():
			return False
		_USED += 1
		return True


def _response_text(page: Any) -> str:
	for attr in ('html_content', 'html', 'body', 'text', 'content'):
		val = getattr(page, attr, None)
		if val is None:
			continue
		if isinstance(val, (bytes, bytearray)):
			return bytes(val).decode('utf-8', errors='replace')
		s = str(val)
		if s:
			return s
	return ''


async def fetch_html_stealthy(
	url: str,
	*,
	timeout_ms: int | None = None,
	max_bytes: int = 200_000,
	solve_cloudflare: bool = True,
) -> tuple[str, int | None, str | None, list[str]]:
	"""One-shot AsyncStealthySession fetch. Consumes budget on attempt start.

	Returns (html, status, error, notes). Never raises.
	"""
	notes: list[str] = ['stealthy_fallback']
	if not _consume_budget():
		return '', None, 'stealthy_budget_exhausted', notes + ['budget_exhausted']

	try:
		from scrapling.fetchers import AsyncStealthySession
	except Exception as exc:  # noqa: BLE001
		return '', None, f'stealthy_import:{exc}', notes + ['scrapling_not_installed']

	ms = timeout_ms if timeout_ms is not None else stealthy_timeout_ms()
	try:
		async with AsyncStealthySession(
			headless=True,
			timeout=ms,
			network_idle=True,
			solve_cloudflare=solve_cloudflare,
			retries=1,
			retry_delay=0,
		) as session:
			page = await session.fetch(url)
			status = getattr(page, 'status', None) or getattr(page, 'status_code', None)
			body = _response_text(page)
			if max_bytes > 0 and len(body) > max_bytes:
				body = body[:max_bytes]
			st = int(status) if status is not None else 200
			notes.append(f'stealthy_status:{st}')
			if st >= 400 and not body:
				return body, st, f'http_{st}', notes
			return body, st, None, notes
	except Exception as exc:  # noqa: BLE001
		return '', None, f'stealthy:{type(exc).__name__}:{exc}', notes
