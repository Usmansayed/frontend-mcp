"""Lightweight cache for framework documentation lookups (memory + optional disk)."""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class CacheEntry:
	value: dict[str, Any]
	created_at: float
	version_key: str


class FrameworkDocsCache:
	def __init__(
		self,
		*,
		ttl_s: int = 3600,
		max_entries: int = 128,
		disk_dir: Path | None = None,
	) -> None:
		self._ttl_s = ttl_s
		self._max_entries = max_entries
		self._entries: dict[str, CacheEntry] = {}
		self._version_keys: dict[str, str] = {}
		self._disk_dir = disk_dir
		if self._disk_dir is None:
			raw = os.environ.get('FRAMEWORK_DOCS_CACHE_PATH', '').strip()
			if raw:
				self._disk_dir = Path(raw)

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
		if entry is not None:
			if time.time() - entry.created_at > self._ttl_s:
				self.delete(key)
				return None
			if entry.version_key != version_key:
				self.delete(key)
				return None
			return dict(entry.value)

		disk_entry = self._read_disk(key, version_key=version_key)
		if disk_entry is not None:
			self._entries[key] = disk_entry
			self._version_keys[key] = version_key
			return dict(disk_entry.value)
		return None

	def set(self, key: str, *, version_key: str, value: dict[str, Any]) -> None:
		if len(self._entries) >= self._max_entries:
			oldest = min(self._entries.items(), key=lambda item: item[1].created_at)[0]
			self.delete(oldest)
		entry = CacheEntry(value=value, created_at=time.time(), version_key=version_key)
		self._entries[key] = entry
		self._version_keys[key] = version_key
		self._write_disk(key, entry)

	def delete(self, key: str) -> None:
		self._entries.pop(key, None)
		self._version_keys.pop(key, None)
		if self._disk_dir is not None:
			path = self._disk_path(key)
			if path.is_file():
				path.unlink(missing_ok=True)

	def invalidate_framework(self, *, framework: str, framework_version: str) -> int:
		prefix = f'{framework}:{framework_version}:'
		keys = [k for k in list(self._entries) if k.startswith(prefix)]
		for key in keys:
			self.delete(key)
		if self._disk_dir is not None and self._disk_dir.is_dir():
			for path in self._disk_dir.glob('*.json'):
				if path.stem.startswith(self._safe_filename(prefix)):
					path.unlink(missing_ok=True)
		return len(keys)

	def _disk_path(self, key: str) -> Path:
		assert self._disk_dir is not None
		self._disk_dir.mkdir(parents=True, exist_ok=True)
		return self._disk_dir / f'{self._safe_filename(key)}.json'

	@staticmethod
	def _safe_filename(key: str) -> str:
		return hashlib.sha256(key.encode('utf-8')).hexdigest()

	def _read_disk(self, key: str, *, version_key: str) -> CacheEntry | None:
		if self._disk_dir is None:
			return None
		path = self._disk_path(key)
		if not path.is_file():
			return None
		try:
			payload = json.loads(path.read_text(encoding='utf-8'))
		except (OSError, json.JSONDecodeError):
			path.unlink(missing_ok=True)
			return None
		if not isinstance(payload, dict):
			return None
		created_at = float(payload.get('created_at') or 0)
		stored_version = str(payload.get('version_key') or '')
		value = payload.get('value')
		if not isinstance(value, dict) or stored_version != version_key:
			path.unlink(missing_ok=True)
			return None
		if time.time() - created_at > self._ttl_s:
			path.unlink(missing_ok=True)
			return None
		return CacheEntry(value=value, created_at=created_at, version_key=stored_version)

	def _write_disk(self, key: str, entry: CacheEntry) -> None:
		if self._disk_dir is None:
			return
		path = self._disk_path(key)
		payload = {
			'created_at': entry.created_at,
			'version_key': entry.version_key,
			'value': entry.value,
		}
		path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
