"""Medium-quality URL rewriting for inspiration previews."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

MEDIUM_MAX_WIDTH = int(__import__('os').environ.get('INSPIRATION_BLOB_MAX_WIDTH', '960'))
MEDIUM_JPEG_QUALITY = int(__import__('os').environ.get('INSPIRATION_BLOB_JPEG_QUALITY', '76'))


def normalize_image_url(url: str) -> str:
	"""Normalize preview/srcset URLs without breaking cdn-cgi comma params.

	Srcset lists look like: ``https://a.jpg 420w, https://b.jpg 840w``.
	Cloudflare image URLs contain commas *inside* the path
	(``.../cdn-cgi/image/width=840,height=560/...``) — those must stay intact.
	"""
	url = url.strip()
	if not url:
		return ''
	if url.startswith('file://'):
		return Path(unquote(urlparse(url).path)).as_posix()
	# True srcset: comma followed by another absolute URL
	parts = re.split(r',\s*(?=https?://)', url)
	if len(parts) > 1:
		# Prefer the last (usually largest) candidate; take the URL token only.
		candidate = parts[-1].strip().split()[0]
		return candidate
	return url


def is_http_url(url: str) -> bool:
	return url.startswith('http://') or url.startswith('https://')


def is_local_image_ref(url: str) -> bool:
	if not url:
		return False
	if url.startswith('file://'):
		return Path(unquote(urlparse(url).path)).is_file()
	p = Path(url)
	return p.is_file() or (len(url) > 2 and url[1] == ':' and p.is_file())


def to_medium_inspiration_url(url: str, *, provider_id: str = '') -> str:
	"""Rewrite CDN preview URLs to a smaller tier when the host supports it."""
	url = normalize_image_url(url)
	if not url or not is_http_url(url):
		return url

	pid = provider_id.lower()

	if 'onepagelove.com' in url:
		return re.sub(r'width=\d+', 'width=480', url).replace('quality=85', 'quality=75')

	if 'siteinspire.com' in url:
		# Cloudflare Images: force JPEG so Pillow can open without AVIF support.
		out = re.sub(r'width=\d+', 'width=640', url)
		out = re.sub(r'quality=\d+', 'quality=70', out)
		if 'format=' in out:
			out = re.sub(r'format=[a-z0-9]+', 'format=jpeg', out, flags=re.I)
		else:
			out = out.replace('/cdn-cgi/image/', '/cdn-cgi/image/format=jpeg,')
		return out

	# Behance /project_modules/800/ is dead (404). Prefer max_1200 or leave 1400.
	if 'behance.net' in url and '/project_modules/1400/' in url:
		return url.replace('/project_modules/1400/', '/project_modules/max_1200/')
	if 'behance.net' in url and '/project_modules/fs/' in url:
		return url.replace('/project_modules/fs/', '/project_modules/max_1200/')
	if 'behance.net' in url and '/project_modules/800/' in url:
		return url.replace('/project_modules/800/', '/project_modules/max_1200/')

	# Lapa CDN: prefer 1x thumbs for faster blob materialization.
	if 'cdn.lapa.ninja' in url and '/2x/' in url:
		return url.replace('/2x/', '/1x/')

	# Dribbble template placeholders → concrete mid size
	if 'cdn.dribbble.com' in url and '{width}' in url:
		return url.replace('{width}', '800').replace('{height}', '600')

	if pid == 'land-book' and 'og-image' in url:
		return ''

	return url


def agent_view_url(*, page_url: str, preview_url: str = '', screenshot_path: str = '') -> str:
	"""Best URL for an agent — prefer CDN/preview image for vision, then page, then local file."""
	page_url = page_url.strip()
	preview_url = normalize_image_url(preview_url)
	screenshot_path = screenshot_path.strip()
	# Image-first: host vision models reason better from original gallery images.
	if is_http_url(preview_url):
		return preview_url
	if screenshot_path and Path(screenshot_path).is_file():
		return Path(screenshot_path).resolve().as_uri()
	if page_url.startswith('http'):
		return page_url
	return page_url or preview_url


def image_extension(url: str) -> str:
	lower = url.lower()
	if '.jpg' in lower or '.jpeg' in lower:
		return '.jpg'
	if '.webp' in lower:
		return '.webp'
	return '.png'
