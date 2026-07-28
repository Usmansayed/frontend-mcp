"""Query-fingerprint result cache — make frequent MCP collect/discover cheap."""
from __future__ import annotations

import hashlib
import re
import time
from threading import Lock
from typing import Any

from navigation.inspiration_intelligence.cache_store import load_json_dict, save_json_dict

_LOCK = Lock()
_CACHE: dict[str, dict[str, Any]] = {}
_TTL_S = 15 * 60
_MAX_ENTRIES = 64
_LOADED = False


def _disk():
	from navigation.inspiration_intelligence.cache_store import cache_path

	return cache_path('inspiration_result.json')


def fingerprint(
	query: str,
	*,
	mode: str = 'fast',
	provider_ids: list[str] | None = None,
) -> str:
	norm = re.sub(r'\s+', ' ', (query or '').strip().lower())
	pids = ','.join(provider_ids or [])
	raw = f'{norm}|{mode}|{pids}'
	return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]


def _ensure_loaded() -> None:
	global _LOADED
	if _LOADED:
		return
	raw = load_json_dict(_disk())
	entries = raw.get('entries') if isinstance(raw.get('entries'), dict) else {}
	now = time.time()
	for k, v in entries.items():
		if not isinstance(v, dict):
			continue
		if now - float(v.get('created_at') or 0) > _TTL_S:
			continue
		_CACHE[str(k)] = v
	_LOADED = True


def _persist() -> None:
	save_json_dict(_disk(), {'entries': dict(_CACHE)})


def get_cached_hits(fp: str) -> list[dict[str, Any]] | None:
	with _LOCK:
		_ensure_loaded()
		_purge_unlocked()
		row = _CACHE.get(fp)
		if row is None:
			return None
		return list(row.get('hits') or [])


def put_cached_hits(fp: str, hits: list[dict[str, Any]]) -> None:
	if not hits:
		return
	with _LOCK:
		_ensure_loaded()
		_purge_unlocked()
		if len(_CACHE) >= _MAX_ENTRIES:
			oldest = min(_CACHE.items(), key=lambda kv: float(kv[1].get('created_at') or 0))
			_CACHE.pop(oldest[0], None)
		_CACHE[fp] = {
			'hits': list(hits)[:8],
			'created_at': time.time(),
		}
		_persist()


def clear_result_cache() -> None:
	global _LOADED
	with _LOCK:
		_CACHE.clear()
		_LOADED = True
		_persist()


def _purge_unlocked() -> None:
	now = time.time()
	dead = [k for k, v in _CACHE.items() if now - float(v.get('created_at') or 0) > _TTL_S]
	for k in dead:
		_CACHE.pop(k, None)
