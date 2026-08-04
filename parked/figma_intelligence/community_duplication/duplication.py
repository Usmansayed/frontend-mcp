"""Community file duplication — session API + browser fallback."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from navigation.figma_intelligence.community_duplication.file_key_resolver import (
	resolve_file_key_from_payload,
)
from navigation.figma_intelligence.community_duplication.models import DuplicationResult

HUB_DUPLICATE_URL = 'https://www.figma.com/api/hub_files/{content_id}/duplicate'
RESOURCES_DUPLICATE_URL = 'https://www.figma.com/api/resources/hub_files/{content_id}/duplicate'


async def duplicate_via_session_api(
	content_id: str,
	*,
	session_cookie: str,
	referer: str = '',
) -> tuple[DuplicationResult, dict[str, Any] | None]:
	"""POST hub_files duplicate using authenticated browser session cookies."""
	degraded: list[str] = []
	if not session_cookie.strip():
		return DuplicationResult(content_id=content_id, degraded=['session_cookie_missing']), None

	payload, err = _post_duplicate(HUB_DUPLICATE_URL.format(content_id=content_id), session_cookie, referer)
	if payload is None:
		payload, err2 = _post_duplicate(
			RESOURCES_DUPLICATE_URL.format(content_id=content_id),
			session_cookie,
			referer,
		)
		err = err or err2

	if payload is None:
		degraded.append(f'session_api_duplicate_failed:{err or "unknown"}')
		return DuplicationResult(content_id=content_id, degraded=degraded), None

	file_key, draft_url = resolve_file_key_from_payload(payload)
	if not file_key:
		degraded.append('session_api_duplicate_no_file_key_in_response')
		return (
			DuplicationResult(
				content_id=content_id,
				method='api_hub_files_duplicate',
				degraded=degraded,
			),
			payload,
		)

	return (
		DuplicationResult(
			content_id=content_id,
			file_key=file_key,
			draft_url=draft_url,
			method='api_hub_files_duplicate',
			degraded=degraded,
		),
		payload,
	)


def _post_duplicate(url: str, cookie: str, referer: str) -> tuple[dict[str, Any] | None, str | None]:
	headers = {
		'User-Agent': (
			'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
			'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
		),
		'Accept': 'application/json',
		'Content-Type': 'application/json',
		'Cookie': cookie.strip(),
		'x-csrf-bypass': 'yes',
	}
	if referer:
		headers['Referer'] = referer
	req = urllib.request.Request(url, data=b'{}', headers=headers, method='POST')
	try:
		with urllib.request.urlopen(req, timeout=60) as resp:
			raw = resp.read().decode('utf-8')
			return json.loads(raw), None
	except urllib.error.HTTPError as exc:
		body = exc.read().decode('utf-8', 'replace')[:300]
		return None, f'HTTP{exc.code}:{body}'
	except Exception as exc:
		return None, f'{type(exc).__name__}:{exc}'
