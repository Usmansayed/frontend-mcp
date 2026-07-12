"""Design context cache — avoid redundant Figma Console MCP calls."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class FigmaDesignCacheEntry:
	session_key: str
	context: dict[str, Any]
	fetched_at: float = field(default_factory=time.time)
	ttl_seconds: float = 120.0

	def is_valid(self, session_key: str) -> bool:
		if session_key != self.session_key:
			return False
		return (time.time() - self.fetched_at) < self.ttl_seconds


class FigmaDesignCache:
	def __init__(self, *, ttl_seconds: float = 120.0) -> None:
		self._ttl = ttl_seconds
		self._entry: FigmaDesignCacheEntry | None = None

	@staticmethod
	def session_key(session: dict[str, Any]) -> str:
		parts = [
			str(session.get('file_key') or ''),
			str(session.get('active_page_id') or ''),
			str(session.get('active_frame_id') or ''),
			','.join(session.get('selection_node_ids') or []),
		]
		return '|'.join(parts)

	def get(self, session: dict[str, Any]) -> dict[str, Any] | None:
		key = self.session_key(session)
		if self._entry and self._entry.is_valid(key):
			return self._entry.context
		return None

	def put(self, session: dict[str, Any], context: dict[str, Any]) -> None:
		self._entry = FigmaDesignCacheEntry(
			session_key=self.session_key(session),
			context=dict(context),
			ttl_seconds=self._ttl,
		)

	def invalidate(self) -> None:
		self._entry = None

	def meta(self, session: dict[str, Any]) -> dict[str, Any]:
		key = self.session_key(session)
		if self._entry and self._entry.is_valid(key):
			return {
				'hit': True,
				'age_seconds': round(time.time() - self._entry.fetched_at, 2),
				'ttl_seconds': self._ttl,
			}
		return {'hit': False, 'ttl_seconds': self._ttl}
