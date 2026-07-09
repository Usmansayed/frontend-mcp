"""Network capture models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class NetworkEntry:
	request_id: str
	url: str
	method: str
	status: int | None = None
	status_text: str = ''
	mime_type: str = ''
	started_at: float = 0.0
	ended_at: float | None = None
	duration_ms: float | None = None
	request_headers: dict[str, str] = field(default_factory=dict)
	response_headers: dict[str, str] = field(default_factory=dict)
	request_body: str | None = None
	response_body: str | None = None
	request_body_truncated: bool = False
	response_body_truncated: bool = False
	failed: bool = False
	canceled: bool = False
	error_text: str = ''
	redirect_urls: list[str] = field(default_factory=list)
	graphql_operation: str | None = None
	api_group: str | None = None
	resource_type: str = ''

	def to_dict(self, *, include_bodies: bool = True) -> dict[str, Any]:
		out: dict[str, Any] = {
			'request_id': self.request_id,
			'url': self.url,
			'method': self.method,
			'status': self.status,
			'status_text': self.status_text,
			'mime_type': self.mime_type,
			'started_at': self.started_at,
			'ended_at': self.ended_at,
			'duration_ms': self.duration_ms,
			'request_headers': dict(self.request_headers),
			'response_headers': dict(self.response_headers),
			'failed': self.failed,
			'canceled': self.canceled,
			'error_text': self.error_text,
			'redirect_urls': list(self.redirect_urls),
			'graphql_operation': self.graphql_operation,
			'api_group': self.api_group,
			'resource_type': self.resource_type,
		}
		if include_bodies:
			out['request_body'] = self.request_body
			out['response_body'] = self.response_body
			out['request_body_truncated'] = self.request_body_truncated
			out['response_body_truncated'] = self.response_body_truncated
		return out


@dataclass(slots=True)
class NetworkFilter:
	status_min: int | None = None
	status_max: int | None = None
	failed_only: bool = False
	api_group: str | None = None
	contains: str | None = None
	since_index: int | None = None
	limit: int = 50
	include_bodies: bool = False


@dataclass(slots=True)
class NetworkReport:
	total: int
	session_total: int
	failed_count: int
	slow_count: int
	duplicate_count: int
	by_api_group: dict[str, int] = field(default_factory=dict)
	entries: list[dict[str, Any]] = field(default_factory=list)
	slow_requests: list[dict[str, Any]] = field(default_factory=list)
	duplicates: list[dict[str, Any]] = field(default_factory=list)
	failures: list[dict[str, Any]] = field(default_factory=list)
	blocking: list[str] = field(default_factory=list)
	har_path: str | None = None
	window_start_index: int = 0
	slow_threshold_ms: float = 1000.0

	def to_dict(self) -> dict[str, Any]:
		return {
			'total': self.total,
			'session_total': self.session_total,
			'failed_count': self.failed_count,
			'slow_count': self.slow_count,
			'duplicate_count': self.duplicate_count,
			'by_api_group': dict(self.by_api_group),
			'entries': list(self.entries),
			'slow_requests': list(self.slow_requests),
			'duplicates': list(self.duplicates),
			'failures': list(self.failures),
			'blocking': list(self.blocking),
			'har_path': self.har_path,
			'window_start_index': self.window_start_index,
			'slow_threshold_ms': self.slow_threshold_ms,
		}
