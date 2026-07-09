"""Lightweight in-memory cache for framework documentation lookups."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CacheEntry:
	value: dict[str, Any]
	created_at: float
	version_key: str


class FrameworkDocsCache:
	def __init__(self, *, ttl_s: int = 3600, max_entries: int = 128) -> None:
		self._ttl_s = ttl_s
		self._max_entries = max_entries
		self._entries: dict[str, CacheEntry] = {}
		self._version_keys: dict[str, str] = {}

	def _topic_hash(self, topic: str) -> str:
		return hashlib.sha256(topic.strip().lower().encode('utf-8')).hexdigest()[:16]

	def make_key(self, *, framework: str, framework_version: str, topic: str) -> str:
		return f'{framework}:{framework_version}:{self._topic_hash(topic)}'

	def get(self, key: str, *, version_key: str) -> dict[str, Any] | None:
		stored_version = self._version_keys.get(key)
		if stored_version and stored_version != version_key:
			self.delete(key)
			return None
		entry = self._entries.get(key)
		if entry is None:
			return None
		if time.time() - entry.created_at > self._ttl_s:
			self.delete(key)
			return None
		if entry.version_key != version_key:
			self.delete(key)
			return None
		return dict(entry.value)

	def set(self, key: str, *, version_key: str, value: dict[str, Any]) -> None:
		if len(self._entries) >= self._max_entries:
			oldest = min(self._entries.items(), key=lambda item: item[1].created_at)[0]
			self.delete(oldest)
		self._entries[key] = CacheEntry(value=value, created_at=time.time(), version_key=version_key)
		self._version_keys[key] = version_key

	def delete(self, key: str) -> None:
		self._entries.pop(key, None)
		self._version_keys.pop(key, None)

	def invalidate_framework(self, *, framework: str, framework_version: str) -> int:
		prefix = f'{framework}:{framework_version}:'
		keys = [k for k in self._entries if k.startswith(prefix)]
		for key in keys:
			self.delete(key)
		return len(keys)
