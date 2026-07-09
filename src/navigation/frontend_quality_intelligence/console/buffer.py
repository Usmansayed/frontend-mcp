"""Ring buffer for console log entries."""
from __future__ import annotations

from collections import Counter

from .cdp_parse import normalize_level
from .models import ConsoleFilter, ConsoleLogEntry, ConsoleReport


class ConsoleRingBuffer:
	"""Append-only ring buffer; oldest entries drop when max_entries exceeded."""

	def __init__(self, *, max_entries: int = 500) -> None:
		self.max_entries = max_entries
		self._entries: list[ConsoleLogEntry] = []
		self._dropped: int = 0

	@property
	def session_total(self) -> int:
		return len(self._entries) + self._dropped

	def add(self, entry: ConsoleLogEntry) -> int:
		"""Append entry; return index of entry in buffer."""
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

	def entries_since(self, start_index: int) -> list[ConsoleLogEntry]:
		"""Return entries with absolute session index >= start_index."""
		out: list[ConsoleLogEntry] = []
		for i, entry in enumerate(self._entries):
			if self._dropped + i >= start_index:
				out.append(entry)
		return out

	def report(
		self,
		*,
		window_start_index: int = 0,
		filter: ConsoleFilter | None = None,
	) -> ConsoleReport:
		filter = filter or ConsoleFilter()
		level_set = filter.normalized_levels()
		contains = (filter.contains or '').strip().lower()
		limit = max(1, int(filter.limit))

		start = max(0, filter.since_index if filter.since_index is not None else window_start_index)
		candidates = self.entries_since(start)

		filtered: list[ConsoleLogEntry] = []
		for entry in candidates:
			if level_set is not None and entry.level not in level_set:
				continue
			if contains and contains not in entry.text.lower():
				continue
			filtered.append(entry)

		window_entries = filtered[:limit]
		by_level = Counter(e.level for e in window_entries)

		blocking: list[str] = []
		for entry in window_entries:
			if entry.level == 'error':
				blocking.append(f'Console error: {entry.text}')
			elif entry.level == 'exception':
				blocking.append(f'Uncaught exception: {entry.text}')

		return ConsoleReport(
			total=len(window_entries),
			session_total=self.session_total,
			by_level=dict(by_level),
			entries=[e.to_dict() for e in window_entries],
			blocking=blocking,
			window_start_index=window_start_index,
		)
