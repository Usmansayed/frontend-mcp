"""CDP console event collector — fans in via DevInsightsHub."""
from __future__ import annotations

import time
from typing import Any

from navigation.core.cdp_hub import CDP_CONSOLE, CDP_EXCEPTION, CDP_LOG, DevInsightsHub

from .buffer import ConsoleRingBuffer
from .cdp_parse import (
	cdp_get,
	exception_message,
	format_console_message,
	format_stack_trace,
	normalize_level,
)
from .models import ConsoleLogEntry


class ConsoleCollector:
	"""Capture all console levels + exceptions into a ring buffer."""

	def __init__(self, buffer: ConsoleRingBuffer) -> None:
		self._buffer = buffer
		self._hub: DevInsightsHub | None = None
		self._started = False

	async def start(self, session: Any) -> None:
		if self._started:
			return
		self._hub = await DevInsightsHub.for_session(session)
		await self._hub.ensure_domains()
		self._hub.attach(self)
		self._started = True

	def stop(self) -> None:
		if self._started and self._hub is not None:
			self._hub.detach(self)
		self._started = False
		self._hub = None

	def _handle_cdp(self, method: str, params: Any, session_id: str | None = None) -> None:
		if method == CDP_CONSOLE:
			self._on_console(params)
		elif method == CDP_EXCEPTION:
			self._on_exception(params)
		elif method == CDP_LOG:
			self._on_log(params)

	def _now(self) -> float:
		return time.time()

	def _add(self, entry: ConsoleLogEntry) -> None:
		self._buffer.add(entry)

	def _on_console(self, params: Any) -> None:
		level = normalize_level(str(cdp_get(params, 'type') or 'log'))
		text = format_console_message(params)
		if not text and level not in {'error', 'warn'}:
			return
		stack = format_stack_trace(cdp_get(params, 'stackTrace'))
		ts = cdp_get(params, 'timestamp')
		timestamp = float(ts) / 1000.0 if ts is not None else self._now()
		self._add(
			ConsoleLogEntry(
				level=level,
				text=text or f'({level})',
				timestamp=timestamp,
				stack=stack,
				source='cdp_console',
			)
		)

	def _on_log(self, params: Any) -> None:
		entry_obj = cdp_get(params, 'entry') or {}
		level = normalize_level(str(cdp_get(entry_obj, 'level') or 'log'))
		text = str(cdp_get(entry_obj, 'text') or '').strip()
		if not text:
			return
		url = str(cdp_get(entry_obj, 'url') or '')
		line = cdp_get(entry_obj, 'lineNumber')
		ts = cdp_get(entry_obj, 'timestamp')
		timestamp = float(ts) if ts is not None else self._now()
		self._add(
			ConsoleLogEntry(
				level=level,
				text=text,
				timestamp=timestamp,
				url=url,
				line=int(line) if line is not None else None,
				source='cdp_log',
			)
		)

	def _on_exception(self, params: Any) -> None:
		details = cdp_get(params, 'exceptionDetails') or {}
		text = exception_message(details)
		url = str(cdp_get(details, 'url') or '')
		line = cdp_get(details, 'lineNumber')
		col = cdp_get(details, 'columnNumber')
		stack = format_stack_trace(cdp_get(details, 'stackTrace'))
		self._add(
			ConsoleLogEntry(
				level='exception',
				text=text,
				timestamp=self._now(),
				url=url,
				line=int(line) if line is not None else None,
				column=int(col) if col is not None else None,
				stack=stack,
				source='cdp_exception',
			)
		)
