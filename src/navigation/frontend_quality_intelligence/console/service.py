"""Per-session console capture lifecycle."""
from __future__ import annotations

from typing import Any

from .buffer import ConsoleRingBuffer
from .collector import ConsoleCollector
from .models import ConsoleFilter, ConsoleReport


class SessionConsoleService:
	"""Owns ring buffer + collector for one browser session."""

	def __init__(self, *, max_entries: int = 500) -> None:
		self._buffer = ConsoleRingBuffer(max_entries=max_entries)
		self._collector = ConsoleCollector(self._buffer)
		self._attached = False

	@property
	def session_total(self) -> int:
		return self._buffer.session_total

	async def attach(self, session: Any) -> None:
		if self._attached:
			return
		await self._collector.start(session)
		self._attached = True

	def detach(self) -> None:
		if not self._attached:
			return
		self._collector.stop()
		self._attached = False

	def mark_window(self) -> int:
		"""Absolute index at observe window start (next entry index)."""
		return self._buffer.session_total

	def clear(self) -> int:
		return self._buffer.clear()

	def report(
		self,
		*,
		window_start_index: int | None = None,
		filter: ConsoleFilter | None = None,
	) -> ConsoleReport:
		start = window_start_index if window_start_index is not None else 0
		return self._buffer.report(window_start_index=start, filter=filter)

	def window_report(self, window_start_index: int, *, limit: int = 100) -> ConsoleReport:
		return self.report(
			window_start_index=window_start_index,
			filter=ConsoleFilter(limit=limit),
		)
