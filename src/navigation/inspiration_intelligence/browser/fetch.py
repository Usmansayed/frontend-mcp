"""Smart HTTP fetch with browser-like headers and block detection."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from navigation.inspiration_intelligence.browser.policy import detect_block_signal

_DEFAULT_UA = (
	'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
	'(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
)

_BROWSER_HEADERS = {
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
	'Accept-Language': 'en-US,en;q=0.9',
	'Cache-Control': 'no-cache',
	'Pragma': 'no-cache',
}


def browser_headers(user_agent: str) -> dict[str, str]:
	return {'User-Agent': user_agent, **_BROWSER_HEADERS}

_OG_IMAGE = re.compile(
	r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
	re.IGNORECASE,
)
_OG_IMAGE_ALT = re.compile(
	r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
	re.IGNORECASE,
)
_OG_TITLE = re.compile(
	r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
	re.IGNORECASE,
)
_JSON_LD = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)


def _ssl_context():
	"""Prefer certifi CA bundle when available (avoids stale system roots)."""
	import ssl

	try:
		import certifi

		return ssl.create_default_context(cafile=certifi.where())
	except Exception:
		return ssl.create_default_context()


def http_get(
	url: str,
	*,
	headers: dict[str, str] | None = None,
	timeout: float = 8.0,
	max_bytes: int | None = None,
) -> tuple[str, int | None, str | None]:
	"""Fetch HTML. Default timeout 8s — fail fast for MCP inspiration collect.

	max_bytes: when set, only read that many bytes (scout speed — enough for thumbs/meta).
	Prefers shared httpx keep-alive pool; falls back to urllib opener.

	HTTP backends (``INSPIRATION_HTTP_BACKEND``):
	- default — httpx/urllib; on WAF allowlist + 403/block, one cheap Scrapling
	  TLS retry (FetcherSession) — not Stealthy
	- ``scrapling`` — Scrapling session only
	- ``scrapling_fallback`` — same as default auto-retry, but on any host
	Stealthy browser fallback is separate: ``stealthy_fallback.py`` (slow, allowlisted).
	"""
	import os

	backend = (os.environ.get('INSPIRATION_HTTP_BACKEND') or '').strip().lower()
	if backend == 'scrapling':
		body, status, err = _http_get_scrapling(url, headers=headers, timeout=timeout, max_bytes=max_bytes)
		if body or not err:
			return body, status, err
		# Fall through to httpx/urllib on total failure

	body, status, err = _http_get_default(url, headers=headers, timeout=timeout, max_bytes=max_bytes)
	want_tls = backend == 'scrapling_fallback' or _should_auto_scrapling_http(url, status, err, body)
	if want_tls and _should_scrapling_retry(status, err, body):
		b2, st2, e2 = _http_get_scrapling(url, headers=headers, timeout=timeout, max_bytes=max_bytes)
		# Prefer Scrapling if it unlocks HTML; else keep original
		if b2 and (st2 is None or st2 < 400):
			return b2, st2, e2
	return body, status, err


def _should_auto_scrapling_http(
	url: str,
	status: int | None,
	err: str | None,
	body: str,
) -> bool:
	"""Cheap TLS impersonation only on known hard hosts (LAPA-class)."""
	try:
		from navigation.inspiration_intelligence.browser.scrapling_route import is_important_waf_host

		return is_important_waf_host(url)
	except Exception:
		return False


def _should_scrapling_retry(status: int | None, err: str | None, body: str) -> bool:
	if status in (403, 429, 503, 202):
		return True
	if not body:
		return bool(err) and status is None  # transport failure — optional retry
	sig = detect_block_signal(body[:8000], status_code=status)
	return sig in {'bot_challenge_detected', 'waf_stub_page'} or (
		isinstance(sig, str) and sig.startswith('http_')
	)


def _http_get_default(
	url: str,
	*,
	headers: dict[str, str] | None = None,
	timeout: float = 8.0,
	max_bytes: int | None = None,
) -> tuple[str, int | None, str | None]:
	hdr = browser_headers(_DEFAULT_UA)
	if headers:
		hdr.update(headers)
	try:
		from navigation.inspiration_intelligence.browser.http_pool import pool_get

		pooled = pool_get(url, headers=hdr, timeout=timeout, max_bytes=max_bytes)
		if pooled is not None:
			body, status, err = pooled
			# Empty body with error → try urllib once; success/partial HTML → return
			if body or not err:
				return body, status, err
	except Exception:
		pass
	req = urllib.request.Request(url, headers=hdr)
	opener = _shared_opener()
	try:
		with opener.open(req, timeout=timeout) as resp:
			if max_bytes is not None and max_bytes > 0:
				body = resp.read(max_bytes).decode('utf-8', errors='replace')
			else:
				body = resp.read().decode('utf-8', errors='replace')
			return body, getattr(resp, 'status', None) or 200, None
	except urllib.error.HTTPError as exc:
		raw = exc.read(max_bytes) if (max_bytes and exc.fp) else (exc.read() if exc.fp else b'')
		body = raw.decode('utf-8', errors='replace') if isinstance(raw, (bytes, bytearray)) else ''
		return body, exc.code, str(exc)
	except Exception as exc:
		msg = str(exc)
		# Tag SSL failures so providers can degrade cleanly and cascade.
		if 'CERTIFICATE' in msg.upper() or 'SSL' in msg.upper():
			return '', None, f'SSL:{msg}'
		return '', None, msg


def _http_get_scrapling(
	url: str,
	*,
	headers: dict[str, str] | None = None,
	timeout: float = 8.0,
	max_bytes: int | None = None,
) -> tuple[str, int | None, str | None]:
	"""Scrapling FetcherSession backend (process-wide pool; research / env opt-in)."""
	try:
		from navigation.inspiration_intelligence.browser.scrapling_pool import session_get

		pooled = session_get(url, headers=headers, timeout=timeout, max_bytes=max_bytes)
		if pooled is not None:
			return pooled
	except Exception as exc:  # noqa: BLE001
		return '', None, f'scrapling_pool:{exc}'
	return '', None, 'scrapling_unavailable'

_OPENER: urllib.request.OpenerDirector | None = None


def _shared_opener() -> urllib.request.OpenerDirector:
	"""Lazy shared opener with HTTPS handler — cheaper under concurrent scout fan-out."""
	global _OPENER
	if _OPENER is None:
		_OPENER = urllib.request.build_opener(
			urllib.request.HTTPSHandler(context=_ssl_context()),
			urllib.request.HTTPHandler(),
		)
	return _OPENER


def http_get_bytes(url: str, *, headers: dict[str, str] | None = None, timeout: float = 10.0) -> tuple[bytes | None, str | None]:
	"""Fetch raw bytes (blobs). Default timeout 10s."""
	hdr = browser_headers(_DEFAULT_UA)
	if headers:
		hdr.update(headers)
	try:
		from navigation.inspiration_intelligence.browser.http_pool import pool_get_bytes

		pooled = pool_get_bytes(url, headers=hdr, timeout=timeout)
		if pooled is not None:
			data, err = pooled
			if data is not None or not err:
				return data, err
	except Exception:
		pass
	req = urllib.request.Request(url, headers=hdr)
	try:
		with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
			return resp.read(), None
	except Exception as exc:
		return None, str(exc)


def extract_og_image(html: str) -> str:
	for pattern in (_OG_IMAGE, _OG_IMAGE_ALT):
		match = pattern.search(html)
		if match:
			return match.group(1).strip()
	for block in _JSON_LD.findall(html):
		try:
			data = json.loads(block)
			if isinstance(data, dict):
				img = data.get('image') or data.get('thumbnailUrl')
				if isinstance(img, str):
					return img
				if isinstance(img, list) and img:
					return str(img[0])
		except json.JSONDecodeError:
			continue
	return ''


def extract_og_title(html: str) -> str:
	match = _OG_TITLE.search(html)
	return match.group(1).strip() if match else ''


def enrich_preview_from_detail(url: str) -> tuple[str, str, list[str]]:
	"""Fetch shot/page detail and extract og:image — often available without login."""
	degraded: list[str] = []
	html, status, err = http_get(url)
	if err:
		degraded.append(f'og_fetch_failed:{err}')
		return '', '', degraded
	block = detect_block_signal(html, status_code=status)
	if block:
		degraded.append(f'og_block:{block}')
		return '', '', degraded
	preview = extract_og_image(html)
	title = extract_og_title(html)
	if not preview:
		degraded.append('og_image_missing')
	return preview, title, degraded
