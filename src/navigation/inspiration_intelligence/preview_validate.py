"""Cheap HEAD/GET validation for inspiration preview URLs.

Skips known-good CDN hosts (daisyUI). Used so soft-stop does not count 404s.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request

from navigation.inspiration_intelligence.browser.fetch import _shared_opener, browser_headers, _DEFAULT_UA

# Trust these without network — measured stable direct CDNs
_TRUSTED_HOST_FRAGMENTS = (
	'img.daisyui.com',
	'cdn.prod.website-files.com',
	'framerusercontent.com',
	'assets.aceternity.com',
	'cdn.shadcnblocks.com',
)


def is_trusted_preview(url: str) -> bool:
	host = (urlparse(url).netloc or '').lower()
	return any(t in host for t in _TRUSTED_HOST_FRAGMENTS)


def _head_ok(url: str, *, timeout_s: float = 2.0) -> tuple[bool, str]:
	"""Return (ok, reason). Accept 200/206/301/302 with image-ish content-type when present."""
	if not url.startswith('http'):
		return False, 'not_http'
	if is_trusted_preview(url):
		return True, 'trusted_cdn'
	req = Request(url, headers=browser_headers(_DEFAULT_UA))
	req.get_method = lambda: 'HEAD'  # type: ignore[method-assign]
	opener = _shared_opener()
	try:
		with opener.open(req, timeout=timeout_s) as resp:
			status = getattr(resp, 'status', None) or 200
			ctype = (resp.headers.get('Content-Type') or '').lower()
			if status in {200, 206} and (not ctype or 'image' in ctype or 'octet' in ctype or 'webp' in ctype):
				return True, f'head_{status}'
			if status in {301, 302, 303, 307, 308}:
				return True, f'head_redirect_{status}'
			# Some CDNs reject HEAD — try tiny GET
			if status in {403, 405, 501}:
				return _get_probe(url, timeout_s=timeout_s)
			return False, f'head_{status}:{ctype[:40]}'
	except Exception:
		return _get_probe(url, timeout_s=timeout_s)


def _get_probe(url: str, *, timeout_s: float) -> tuple[bool, str]:
	req = Request(url, headers={**browser_headers(_DEFAULT_UA), 'Range': 'bytes=0-64'})
	opener = _shared_opener()
	try:
		with opener.open(req, timeout=timeout_s) as resp:
			status = getattr(resp, 'status', None) or 200
			ctype = (resp.headers.get('Content-Type') or '').lower()
			body = resp.read(64)
			if status in {200, 206} and body:
				if not ctype or 'image' in ctype or 'octet' in ctype or 'webp' in ctype:
					return True, f'get_{status}'
			return False, f'get_{status}:{ctype[:40]}'
	except Exception as exc:  # noqa: BLE001
		return False, f'probe_fail:{exc}'[:80]


async def validate_preview_urls(
	urls: list[str],
	*,
	concurrency: int = 8,
	timeout_s: float = 2.0,
) -> dict[str, bool]:
	"""Concurrent validate. Returns url → ok."""
	out: dict[str, bool] = {}
	uniq = []
	seen: set[str] = set()
	for u in urls:
		u = (u or '').strip()
		if not u or u in seen:
			continue
		seen.add(u)
		uniq.append(u)
	if not uniq:
		return out

	sem = asyncio.Semaphore(max(1, concurrency))

	async def _one(u: str) -> None:
		async with sem:
			ok, _reason = await asyncio.to_thread(_head_ok, u, timeout_s=timeout_s)
			out[u] = ok

	await asyncio.gather(*[_one(u) for u in uniq])
	return out


async def filter_valid_previews(
	hits: list[Any],
	*,
	preview_attr: str = 'preview_url',
	concurrency: int = 8,
	timeout_s: float = 2.0,
) -> tuple[list[Any], list[str]]:
	"""Keep hits with trusted or HEAD-ok previews. Returns (kept, degraded)."""
	t0 = time.perf_counter()
	urls: list[str] = []
	for h in hits:
		if isinstance(h, dict):
			u = str(h.get(preview_attr) or '')
		else:
			u = str(getattr(h, preview_attr, '') or '')
		if u.startswith('http') and not is_trusted_preview(u):
			urls.append(u)
	validity = await validate_preview_urls(urls, concurrency=concurrency, timeout_s=timeout_s)
	kept: list[Any] = []
	dropped = 0
	for h in hits:
		if isinstance(h, dict):
			u = str(h.get(preview_attr) or '')
		else:
			u = str(getattr(h, preview_attr, '') or '')
		if u.startswith('file:'):
			kept.append(h)
			continue
		if not u.startswith('http'):
			dropped += 1
			continue
		if is_trusted_preview(u) or validity.get(u, False):
			kept.append(h)
		else:
			dropped += 1
	degraded: list[str] = []
	if dropped:
		degraded.append(f'preview_validate_dropped:{dropped}')
	ms = (time.perf_counter() - t0) * 1000.0
	degraded.append(f'preview_validate_ms:{round(ms, 1)}')
	return kept, degraded
