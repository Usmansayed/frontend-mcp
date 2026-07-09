"""Ring buffer and report assembly for network entries."""
from __future__ import annotations

from collections import Counter

from .cdp_parse import api_group, extract_graphql_operation, normalize_url
from .models import NetworkEntry, NetworkFilter, NetworkReport


class NetworkRingBuffer:
	def __init__(self, *, max_entries: int = 300) -> None:
		self.max_entries = max_entries
		self._entries: list[NetworkEntry] = []
		self._dropped: int = 0

	@property
	def session_total(self) -> int:
		return len(self._entries) + self._dropped

	def add(self, entry: NetworkEntry) -> int:
		if len(self._entries) >= self.max_entries:
			self._entries.pop(0)
			self._dropped += 1
		self._entries.append(entry)
		return self._dropped + len(self._entries) - 1

	def clear(self) -> int:
		cleared = len(self._entries)
		self._entries.clear()
		self._dropped = 0
		return cleared

	def entries_since(self, start_index: int) -> list[NetworkEntry]:
		out: list[NetworkEntry] = []
		for i, entry in enumerate(self._entries):
			if self._dropped + i >= start_index:
				out.append(entry)
		return out

	def all_entries(self) -> list[NetworkEntry]:
		return list(self._entries)

	def build_report(
		self,
		candidates: list[NetworkEntry],
		*,
		window_start_index: int = 0,
		filter: NetworkFilter | None = None,
		slow_threshold_ms: float = 1000.0,
		duplicate_window_ms: float = 2000.0,
	) -> NetworkReport:
		filter = filter or NetworkFilter()
		contains = (filter.contains or '').strip().lower()
		limit = max(1, int(filter.limit))

		filtered: list[NetworkEntry] = []
		for entry in candidates:
			if filter.failed_only and not entry.failed and (entry.status is None or entry.status < 400):
				continue
			if filter.api_group and entry.api_group != filter.api_group:
				continue
			if filter.status_min is not None and (entry.status is None or entry.status < filter.status_min):
				continue
			if filter.status_max is not None and (entry.status is None or entry.status > filter.status_max):
				continue
			if contains and contains not in entry.url.lower():
				continue
			filtered.append(entry)

		failures_all = [
			e for e in filtered if e.failed or (e.status is not None and e.status >= 400)
		]
		slow_all = [
			e
			for e in filtered
			if e.duration_ms is not None and e.duration_ms >= slow_threshold_ms
		]
		duplicates = _find_duplicates(filtered, duplicate_window_ms)

		display_sorted = sorted(
			filtered,
			key=lambda e: (
				0 if (e.failed or (e.status is not None and e.status >= 400)) else 1,
				0 if e.api_group else 1,
				-(e.duration_ms or 0),
				e.started_at,
			),
		)
		window_entries = display_sorted[:limit]

		blocking: list[str] = []
		for entry in failures_all:
			if entry.failed:
				blocking.append(f'Network failed: {entry.url} ({entry.error_text or "failed"})')
			elif entry.status is not None:
				blocking.append(f'HTTP {entry.status}: {entry.method} {entry.url}')

		by_api: Counter[str] = Counter()
		for entry in filtered:
			if entry.api_group:
				by_api[entry.api_group] += 1

		include_bodies = filter.include_bodies
		return NetworkReport(
			total=len(window_entries),
			session_total=self.session_total,
			failed_count=len(failures_all),
			slow_count=len(slow_all),
			duplicate_count=len(duplicates),
			by_api_group=dict(by_api),
			entries=[e.to_dict(include_bodies=include_bodies) for e in window_entries],
			slow_requests=[e.to_dict(include_bodies=False) for e in slow_all[:20]],
			duplicates=duplicates,
			failures=[e.to_dict(include_bodies=False) for e in failures_all[:20]],
			blocking=blocking,
			window_start_index=window_start_index,
			slow_threshold_ms=slow_threshold_ms,
		)


def _find_duplicates(entries: list[NetworkEntry], window_ms: float) -> list[dict[str, Any]]:
	seen: list[tuple[float, str, str]] = []
	dups: list[dict[str, Any]] = []
	for entry in sorted(entries, key=lambda e: e.started_at):
		key = (entry.method.upper(), normalize_url(entry.url))
		for prev_at, prev_method, prev_url in seen:
			if prev_method == key[0] and prev_url == key[1]:
				if (entry.started_at - prev_at) * 1000.0 <= window_ms:
					dups.append(
						{
							'method': entry.method,
							'url': entry.url,
							'count': 2,
							'window_ms': window_ms,
						}
					)
					break
		seen.append((entry.started_at, key[0], key[1]))
	return dups


def finalize_entry_metadata(entry: NetworkEntry) -> None:
	if entry.api_group is None:
		entry.api_group = api_group(entry.url)
	content_type = entry.request_headers.get('Content-Type') or entry.request_headers.get('content-type') or ''
	entry.graphql_operation = extract_graphql_operation(
		entry.method,
		entry.url,
		entry.request_body,
		content_type,
	)
