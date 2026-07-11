"""Preview URL helpers for resource assets."""
from __future__ import annotations

import os
import re

MEDIUM_MAX_WIDTH = int(os.environ.get('RESOURCE_BLOB_MAX_WIDTH', os.environ.get('INSPIRATION_BLOB_MAX_WIDTH', '960')))
MEDIUM_JPEG_QUALITY = int(os.environ.get('RESOURCE_BLOB_JPEG_QUALITY', os.environ.get('INSPIRATION_BLOB_JPEG_QUALITY', '76')))


def is_http_url(value: str) -> bool:
	return value.startswith('http://') or value.startswith('https://')


def is_local_image_ref(value: str) -> bool:
	if not value:
		return False
	if value.startswith('file://'):
		return True
	return value.endswith(('.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif'))


def normalize_asset_url(url: str) -> str:
	url = (url or '').strip()
	if not url:
		return ''
	return url


def to_medium_preview_url(url: str, *, provider_id: str = '', format_hint: str = '') -> str:
	url = normalize_asset_url(url)
	if not is_http_url(url):
		return url
	if provider_id == 'iconify' or 'api.iconify.design' in url:
		if 'height=' in url:
			return url
		sep = '&' if '?' in url else '?'
		return f'{url}{sep}height=256'
	if provider_id == 'dicebear' or 'api.dicebear.com' in url:
		if '/svg' in url:
			url = url.replace('/svg', '/png')
		sep = '&' if '?' in url else '?'
		return f'{url}{sep}size=256'
	if format_hint == 'svg' and url.endswith('.svg'):
		return url
	return url


def agent_view_url(*, access_url: str, preview_url: str) -> str:
	return normalize_asset_url(access_url) or normalize_asset_url(preview_url)
