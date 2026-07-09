"""HAR 1.2 export from network entries."""
from __future__ import annotations

import time
from typing import Any

from .models import NetworkEntry


def entries_to_har(entries: list[NetworkEntry], *, page_url: str = '') -> dict[str, Any]:
	started = min((e.started_at for e in entries), default=time.time())
	creator = {'name': 'frontend-perception-engine', 'version': '0.5.0'}
	har_entries: list[dict[str, Any]] = []
	for entry in entries:
		har_entries.append(_entry_to_har(entry, page_started=started))
	return {
		'log': {
			'version': '1.2',
			'creator': creator,
			'pages': [{'startedDateTime': _iso(started), 'id': 'page_1', 'title': page_url or 'page', 'pageTimings': {}}],
			'entries': har_entries,
		}
	}


def _iso(ts: float) -> str:
	return time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(ts))


def _entry_to_har(entry: NetworkEntry, *, page_started: float) -> dict[str, Any]:
	req_headers = [{'name': k, 'value': v} for k, v in entry.request_headers.items()]
	resp_headers = [{'name': k, 'value': v} for k, v in entry.response_headers.items()]
	duration = entry.duration_ms if entry.duration_ms is not None else 0.0
	status = entry.status if entry.status is not None else 0
	request: dict[str, Any] = {
		'method': entry.method,
		'url': entry.url,
		'httpVersion': 'HTTP/1.1',
		'headers': req_headers,
		'queryString': [],
		'cookies': [],
		'headersSize': -1,
		'bodySize': len(entry.request_body or ''),
	}
	if entry.request_body:
		request['postData'] = {
			'mimeType': entry.request_headers.get('Content-Type', 'application/octet-stream'),
			'text': entry.request_body,
		}
	return {
		'startedDateTime': _iso(entry.started_at or page_started),
		'time': duration,
		'request': request,
		'response': {
			'status': status,
			'statusText': entry.status_text,
			'httpVersion': 'HTTP/1.1',
			'headers': resp_headers,
			'cookies': [],
			'content': {
				'size': len(entry.response_body or ''),
				'mimeType': entry.mime_type or 'application/octet-stream',
				'text': entry.response_body or '',
			},
			'redirectURL': entry.redirect_urls[-1] if entry.redirect_urls else '',
			'headersSize': -1,
			'bodySize': len(entry.response_body or ''),
		},
		'cache': {},
		'timings': {
			'blocked': -1,
			'dns': -1,
			'connect': -1,
			'ssl': -1,
			'send': 0,
			'wait': duration,
			'receive': 0,
		},
		'pageref': 'page_1',
	}
