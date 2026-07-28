"""Process-wide Scrapling FetcherSession (opt-in HTTP backend).

Official Scrapling docs: ``Fetcher.get`` opens a *temporary* session per call —
~10× slower than a reused ``FetcherSession``. Our first spike used cold
``Fetcher.get``, which unfairly penalized Scrapling vs our httpx keep-alive pool.

This module mirrors ``http_pool.py``: one shared session for scout fan-out.
"""
from __future__ import annotations

import threading
from typing import Any

_LOCK = threading.Lock()
_SESSION: Any = None
_SESSION_CM: Any = None
_FAILED = False


def shared_scrapling_session(
	*,
	timeout: float = 10.0,
	retries: int = 1,
	impersonate: str = 'chrome',
):
	"""Lazy process-wide FetcherSession (entered once; connection reuse).

	retries default 1 (not Scrapling's 3) so inspiration scout fan-out fails
	fast like our httpx path — fair latency + less stampede on soft 403s.
	"""
	global _SESSION, _SESSION_CM, _FAILED
	if _FAILED:
		return None
	with _LOCK:
		if _SESSION is not None:
			return _SESSION
		try:
			from scrapling.fetchers import FetcherSession

			_SESSION_CM = FetcherSession(
				impersonate=impersonate,
				stealthy_headers=True,
				timeout=timeout,
				retries=max(1, int(retries)),
				retry_delay=0,
				follow_redirects='safe',
			)
			_SESSION = _SESSION_CM.__enter__()
			return _SESSION
		except Exception:
			_FAILED = True
			_SESSION = None
			_SESSION_CM = None
			return None


def close_shared_scrapling_session() -> None:
	"""Best-effort shutdown (tests / process exit)."""
	global _SESSION, _SESSION_CM, _FAILED
	with _LOCK:
		if _SESSION_CM is not None:
			try:
				_SESSION_CM.__exit__(None, None, None)
			except Exception:
				pass
		_SESSION = None
		_SESSION_CM = None
		_FAILED = False


def session_get(
	url: str,
	*,
	headers: dict[str, str] | None = None,
	timeout: float = 8.0,
	max_bytes: int | None = None,
) -> tuple[str, int | None, str | None] | None:
	"""GET via shared Scrapling session. Returns None if unavailable."""
	session = shared_scrapling_session(timeout=max(timeout, 1.0))
	if session is None:
		return None
	try:
		kwargs: dict[str, Any] = {'timeout': timeout}
		if headers:
			kwargs['headers'] = headers
		page = session.get(url, **kwargs)
		status = getattr(page, 'status', None) or getattr(page, 'status_code', None)
		body = _response_text(page)
		if max_bytes is not None and max_bytes > 0 and len(body) > max_bytes:
			body = body[:max_bytes]
		st = int(status) if status is not None else 200
		if st >= 400 and not body:
			return body, st, f'http_{st}'
		return body, st, None
	except Exception as exc:  # noqa: BLE001
		msg = str(exc)
		if 'CERTIFICATE' in msg.upper() or 'SSL' in msg.upper():
			return '', None, f'SSL:{msg}'
		return '', None, msg


def session_get_bytes(
	url: str,
	*,
	headers: dict[str, str] | None = None,
	timeout: float = 10.0,
) -> tuple[bytes | None, str | None] | None:
	"""GET raw bytes via shared Scrapling session."""
	session = shared_scrapling_session(timeout=max(timeout, 1.0))
	if session is None:
		return None
	try:
		kwargs: dict[str, Any] = {'timeout': timeout}
		if headers:
			kwargs['headers'] = headers
		page = session.get(url, **kwargs)
		raw = getattr(page, 'body', None)
		if isinstance(raw, (bytes, bytearray)):
			return bytes(raw), None
		text = _response_text(page)
		return text.encode('utf-8', errors='replace'), None
	except Exception as exc:  # noqa: BLE001
		return None, str(exc)


def _response_text(page: Any) -> str:
	for attr in ('html', 'body', 'text', 'content'):
		val = getattr(page, attr, None)
		if val is None:
			continue
		if isinstance(val, (bytes, bytearray)):
			return bytes(val).decode('utf-8', errors='replace')
		s = str(val)
		if s:
			return s
	return ''
