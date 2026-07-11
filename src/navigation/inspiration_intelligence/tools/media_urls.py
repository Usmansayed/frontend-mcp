"""Medium-quality URL rewriting for inspiration previews."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

MEDIUM_MAX_WIDTH = int(__import__('os').environ.get('INSPIRATION_BLOB_MAX_WIDTH', '960'))
MEDIUM_JPEG_QUALITY = int(__import__('os').environ.get('INSPIRATION_BLOB_JPEG_QUALITY', '76'))


def normalize_image_url(url: str) -> str:
	"""Normalize preview/srcset URLs without breaking cdn-cgi comma params."""
	url = url.strip()
	if not url:
		return ''
	if url.startswith('file://'):
		return Path(unquote(urlparse(url).path)).as_posix()
	# srcset list: "https://a.jpg 420w, https://b.jpg 840w"
	if re.search(r',\s*https?://', url):
		return url.split(',')[0].strip().split()[0]
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
		out = re.sub(r'width=\d+', 'width=640', url)
		return out.replace('quality=75', 'quality=70')

	if 'behance.net' in url and '/project_modules/1400/' in url:
		return url.replace('/project_modules/1400/', '/project_modules/800/')

	if 'behance.net' in url and '/project_modules/fs/' in url:
		return url.replace('/project_modules/fs/', '/project_modules/800/')

	if 'awwwards.com' in url and 'thumb_440_330' in url:
		return url.replace('thumb_440_330', 'thumb_440_330')  # resize on save via Pillow

	if pid == 'land-book' and 'og-image' in url:
		return ''

	return url


def agent_view_url(*, page_url: str, preview_url: str = '', screenshot_path: str = '') -> str:
	"""Best URL for an agent to open — prefer live page, then image, then local screenshot."""
	page_url = page_url.strip()
	preview_url = normalize_image_url(preview_url)
	screenshot_path = screenshot_path.strip()
	if page_url.startswith('http'):
		return page_url
	if is_http_url(preview_url):
		return preview_url
	if screenshot_path and Path(screenshot_path).is_file():
		return Path(screenshot_path).resolve().as_uri()
	return page_url or preview_url


def image_extension(url: str) -> str:
	lower = url.lower()
	if '.jpg' in lower or '.jpeg' in lower:
		return '.jpg'
	if '.webp' in lower:
		return '.webp'
	return '.png'
