"""Extract content_id and REST file_key from Figma URLs and API payloads."""
from __future__ import annotations

import re
from typing import Any

FIGMA_FILE_KEY_RE = re.compile(r'^[A-Za-z0-9]{10,128}$')
COMMUNITY_CONTENT_ID_RE = re.compile(
	r'figma\.com/community/file/(\d+)',
	re.IGNORECASE,
)
DESIGN_FILE_KEY_RE = re.compile(
	r'figma\.com/(?:design|file)/([A-Za-z0-9]{10,128})',
	re.IGNORECASE,
)
PROTO_FILE_KEY_RE = re.compile(
	r'figma\.com/proto/([A-Za-z0-9]{10,128})',
	re.IGNORECASE,
)


def content_id_from_url(url: str) -> str:
	match = COMMUNITY_CONTENT_ID_RE.search(url or '')
	return match.group(1) if match else ''


def file_key_from_url(url: str) -> str:
	for pattern in (DESIGN_FILE_KEY_RE, PROTO_FILE_KEY_RE):
		match = pattern.search(url or '')
		if match:
			key = match.group(1)
			if FIGMA_FILE_KEY_RE.match(key):
				return key
	return ''


def resolve_content_id(*, url: str = '', metadata: dict[str, Any] | None = None) -> str:
	meta = metadata or {}
	for key in ('content_id', 'community_file_id', 'hub_file_id'):
		val = str(meta.get(key, '')).strip()
		if val.isdigit():
			return val
	return content_id_from_url(url)


def resolve_file_key_from_payload(payload: dict[str, Any]) -> tuple[str, str]:
	"""Return (file_key, draft_url) from hub_files duplicate or similar JSON."""
	if not payload:
		return '', ''

	for url_key in ('draft_url', 'redirect_url', 'url', 'editor_url', 'file_url'):
		url_val = _deep_get(payload, url_key)
		if isinstance(url_val, str):
			key = file_key_from_url(url_val)
			if key:
				return key, url_val

	for key_path in (
		('meta', 'key'),
		('meta', 'file_key'),
		('meta', 'fileKey'),
		('meta', 'duplicate', 'key'),
		('meta', 'duplicate', 'file_key'),
		('meta', 'file', 'key'),
		('meta', 'file', 'file_key'),
		('key',),
		('file_key',),
		('fileKey',),
	):
		val = _deep_get(payload, *key_path)
		if isinstance(val, str) and FIGMA_FILE_KEY_RE.match(val):
			draft = _deep_get(payload, 'meta', 'url') or _deep_get(payload, 'meta', 'redirect_url')
			return val, str(draft) if isinstance(draft, str) else f'https://www.figma.com/design/{val}'

	# Walk entire tree for design URLs
	found_url = _find_design_url(payload)
	if found_url:
		return file_key_from_url(found_url), found_url

	return '', ''


def _deep_get(obj: Any, *keys: str) -> Any:
	cur = obj
	for key in keys:
		if not isinstance(cur, dict):
			return None
		cur = cur.get(key)
	return cur


def _find_design_url(obj: Any) -> str:
	if isinstance(obj, str) and 'figma.com/design/' in obj:
		return obj
	if isinstance(obj, dict):
		for val in obj.values():
			found = _find_design_url(val)
			if found:
				return found
	elif isinstance(obj, list):
		for item in obj:
			found = _find_design_url(item)
			if found:
				return found
	return ''
