"""Shared HTTP connection pool for inspiration fetch paths.

Uses httpx keep-alive when available; urllib remains the hard fallback so
collect never depends on httpx import success at runtime.
"""
from __future__ import annotations

import threading
from typing import Any

_LOCK = threading.Lock()
_CLIENT: Any = None
_HTTPX_FAILED = False

_DEFAULT_UA = (
	'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
	'(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
)

_BROWSER_HEADERS = {
	'User-Agent': _DEFAULT_UA,
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
	'Accept-Language': 'en-US,en;q=0.9',
	'Cache-Control': 'no-cache',
	'Pragma': 'no-cache',
}


def shared_httpx_client():
	"""Lazy process-wide httpx.Client (connection reuse under scout fan-out)."""
	global _CLIENT, _HTTPX_FAILED
	if _HTTPX_FAILED:
		return None
	with _LOCK:
		if _CLIENT is not None:
			return _CLIENT
		try:
			import httpx

			verify: Any = True
			try:
				import ssl

				import certifi

				verify = ssl.create_default_context(cafile=certifi.where())
			except Exception:
				pass
			_CLIENT = httpx.Client(
				timeout=httpx.Timeout(10.0, connect=5.0),
				limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
				headers=dict(_BROWSER_HEADERS),
				follow_redirects=True,
				verify=verify,
			)
			return _CLIENT
		except Exception:
			_HTTPX_FAILED = True
			_CLIENT = None
			return None


def close_shared_httpx_client() -> None:
	"""Best-effort shutdown (tests / process exit)."""
	global _CLIENT
	with _LOCK:
		if _CLIENT is not None:
			try:
				_CLIENT.close()
			except Exception:
				pass
			_CLIENT = None


def pool_get(
	url: str,
	*,
	headers: dict[str, str] | None = None,
	timeout: float = 8.0,
	max_bytes: int | None = None,
) -> tuple[str, int | None, str | None] | None:
	"""GET via shared pool. Returns None if pool unavailable (caller falls back)."""
	client = shared_httpx_client()
	if client is None:
		return None
	try:
		resp = client.get(url, headers=headers or None, timeout=timeout)
		raw = resp.content
		if max_bytes is not None and max_bytes > 0:
			raw = raw[:max_bytes]
		body = raw.decode('utf-8', errors='replace')
		return body, int(resp.status_code), None
	except Exception as exc:  # noqa: BLE001
		msg = str(exc)
		if 'CERTIFICATE' in msg.upper() or 'SSL' in msg.upper():
			return '', None, f'SSL:{msg}'
		return '', None, msg


def pool_get_bytes(
	url: str,
	*,
	headers: dict[str, str] | None = None,
	timeout: float = 10.0,
) -> tuple[bytes | None, str | None] | None:
	"""GET bytes via shared pool. Returns None if pool unavailable."""
	client = shared_httpx_client()
	if client is None:
		return None
	try:
		resp = client.get(url, headers=headers or None, timeout=timeout)
		return resp.content, None
	except Exception as exc:  # noqa: BLE001
		return None, str(exc)


def pool_post_json(
	url: str,
	*,
	payload: dict[str, Any],
	headers: dict[str, str] | None = None,
	timeout: float = 8.0,
) -> tuple[dict[str, Any] | None, int | None, str | None] | None:
	"""POST JSON via shared pool. Returns None if pool unavailable."""
	client = shared_httpx_client()
	if client is None:
		return None
	try:
		resp = client.post(url, json=payload, headers=headers or None, timeout=timeout)
		data = resp.json() if resp.content else {}
		if not isinstance(data, dict):
			data = {}
		return data, int(resp.status_code), None
	except Exception as exc:  # noqa: BLE001
		return None, None, str(exc)
