"""Console capture models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .cdp_parse import normalize_level


@dataclass(slots=True)
class ConsoleLogEntry:
	level: str
	text: str
	timestamp: float
	url: str = ''
	line: int | None = None
	column: int | None = None
	stack: str = ''
	source: str = 'cdp_console'

	def to_dict(self) -> dict[str, Any]:
		return {
			'level': self.level,
			'text': self.text,
			'timestamp': self.timestamp,
			'url': self.url,
			'line': self.line,
			'column': self.column,
			'stack': self.stack,
			'source': self.source,
		}


@dataclass(slots=True)
class ConsoleFilter:
	levels: list[str] | None = None
	contains: str | None = None
	since_index: int | None = None
	limit: int = 100

	def normalized_levels(self) -> set[str] | None:
		if not self.levels:
			return None
		return {normalize_level(l) for l in self.levels}


@dataclass(slots=True)
class ConsoleReport:
	total: int
	session_total: int
	by_level: dict[str, int] = field(default_factory=dict)
	entries: list[dict[str, Any]] = field(default_factory=list)
	blocking: list[str] = field(default_factory=list)
	window_start_index: int = 0

	def to_dict(self) -> dict[str, Any]:
		return {
			'total': self.total,
			'session_total': self.session_total,
			'by_level': dict(self.by_level),
			'entries': list(self.entries),
			'blocking': list(self.blocking),
			'window_start_index': self.window_start_index,
		}
