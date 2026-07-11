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


def http_get(url: str, *, headers: dict[str, str] | None = None, timeout: float = 30.0) -> tuple[str, int | None, str | None]:
	hdr = browser_headers(_DEFAULT_UA)
	if headers:
		hdr.update(headers)
	req = urllib.request.Request(url, headers=hdr)
	try:
		with urllib.request.urlopen(req, timeout=timeout) as resp:
			body = resp.read().decode('utf-8', errors='replace')
			return body, resp.status, None
	except urllib.error.HTTPError as exc:
		body = exc.read().decode('utf-8', errors='replace') if exc.fp else ''
		return body, exc.code, str(exc)
	except Exception as exc:
		return '', None, str(exc)


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
