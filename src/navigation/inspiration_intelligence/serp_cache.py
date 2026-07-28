"""Short-TTL cache for open-web SERP results (Serper/Brave/DDG)."""
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


def _disk() -> Path:
	from pathlib import Path

	from navigation.inspiration_intelligence.cache_store import cache_path

	return cache_path('inspiration_serp.json')


def serp_fingerprint(query: str, *, limit: int = 8) -> str:
	norm = re.sub(r'\s+', ' ', (query or '').strip().lower())
	raw = f'serp|{norm}|{limit}'
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


def get_serp(fp: str) -> dict[str, Any] | None:
	with _LOCK:
		_ensure_loaded()
		_purge()
		row = _CACHE.get(fp)
		if row is None:
			return None
		return dict(row.get('payload') or {})


def put_serp(fp: str, payload: dict[str, Any]) -> None:
	if not payload:
		return
	with _LOCK:
		_ensure_loaded()
		_purge()
		if len(_CACHE) >= _MAX_ENTRIES:
			oldest = min(_CACHE.items(), key=lambda kv: float(kv[1].get('created_at') or 0))
			_CACHE.pop(oldest[0], None)
		_CACHE[fp] = {'payload': dict(payload), 'created_at': time.time()}
		_persist()


def clear_serp_cache() -> None:
	global _LOADED
	with _LOCK:
		_CACHE.clear()
		_LOADED = True
		_persist()


def _purge() -> None:
	now = time.time()
	dead = [k for k, v in _CACHE.items() if now - float(v.get('created_at') or 0) > _TTL_S]
	for k in dead:
		_CACHE.pop(k, None)
