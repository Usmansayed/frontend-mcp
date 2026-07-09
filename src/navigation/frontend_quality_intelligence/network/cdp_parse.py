"""CDP Network event parsing helpers."""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

from navigation.frontend_quality_intelligence.console.cdp_parse import cdp_get

_GRAPHQL_OP_RE = re.compile(r'(?:query|mutation|subscription)\s+(\w+)', re.IGNORECASE)


def headers_to_dict(headers: Any) -> dict[str, str]:
	if headers is None:
		return {}
	if isinstance(headers, dict):
		return {str(k): str(v) for k, v in headers.items()}
	return {}


def normalize_url(url: str) -> str:
	parsed = urlparse(url)
	return f'{parsed.scheme}://{parsed.netloc}{parsed.path}'


def api_group(url: str) -> str | None:
	path = urlparse(url).path
	if '/api/' not in path:
		return None
	segment = path.split('/api/', 1)[-1].split('/')[0]
	return segment or 'api'


def extract_graphql_operation(
	method: str,
	url: str,
	request_body: str | None,
	content_type: str,
) -> str | None:
	if method.upper() != 'POST' or not request_body:
		return None
	looks_graphql = 'graphql' in url.lower() or 'application/json' in content_type.lower()
	if not looks_graphql and '/api/' not in url:
		return None
	try:
		data = json.loads(request_body)
	except json.JSONDecodeError:
		return None
	if not isinstance(data, dict):
		return None
	if data.get('operationName'):
		return str(data['operationName'])
	query = str(data.get('query') or '')
	match = _GRAPHQL_OP_RE.search(query)
	if match:
		return match.group(1)
	return None


def timing_duration_ms(timing: Any) -> float | None:
	if not timing or not isinstance(timing, dict):
		return None
	# CDP Network timing: requestTime is seconds since epoch; use relative phases when present
	start = timing.get('requestTime')
	if start is None:
		return None
	# Prefer end-to-start from phases in milliseconds when available
	def _phase(name: str) -> float | None:
		val = timing.get(name)
		return float(val) if val is not None and val >= 0 else None

	receive_end = _phase('receiveHeadersEnd')
	send_start = _phase('sendStart')
	if receive_end is not None and send_start is not None:
		return max(0.0, (receive_end - send_start) * 1000.0)
	return None


def truncate_body(text: str, max_bytes: int) -> tuple[str, bool]:
	raw = text.encode('utf-8', errors='replace')
	if len(raw) <= max_bytes:
		return text, False
	return raw[:max_bytes].decode('utf-8', errors='replace'), True
