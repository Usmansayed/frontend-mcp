"""Process cooldown for WAF / bot-challenge hosts.

Avoids burning Chromium budget on hosts that already blocked us.
Persists to disk so MCP restarts keep cooled hosts.
Does not affect the fast HTTP/pattern path.
"""
from __future__ import annotations

import time
from threading import Lock
from urllib.parse import urlparse

from navigation.inspiration_intelligence.cache_store import load_json_dict, save_json_dict

_LOCK = Lock()
_COOLDOWN: dict[str, dict[str, float | str]] = {}
_TTL_S = 20 * 60
_MAX = 128
_LOADED = False

_BLOCK_MARKERS = (
	'bot_challenge',
	'waf_stub',
	'http_403',
	'http_429',
	'http_503',
	'screenshot_skipped_blocked',
	'perception_block:',
)


def _disk():
	from navigation.inspiration_intelligence.cache_store import cache_path

	return cache_path('inspiration_host_cooldown.json')


def host_of(url: str) -> str:
	try:
		return (urlparse(url).netloc or '').lower().removeprefix('www.')
	except Exception:
		return ''


def _ensure_loaded() -> None:
	global _LOADED
	if _LOADED:
		return
	raw = load_json_dict(_disk())
	entries = raw.get('hosts') if isinstance(raw.get('hosts'), dict) else {}
	now = time.time()
	for k, v in entries.items():
		if isinstance(v, dict) and now - float(v.get('at') or 0) <= _TTL_S:
			_COOLDOWN[str(k)] = v
	_LOADED = True


def _persist() -> None:
	save_json_dict(_disk(), {'hosts': dict(_COOLDOWN)})


def is_cooled(url_or_host: str) -> bool:
	h = host_of(url_or_host) if '://' in (url_or_host or '') else (url_or_host or '').lower()
	h = h.removeprefix('www.')
	if not h:
		return False
	with _LOCK:
		_ensure_loaded()
		_purge()
		return h in _COOLDOWN


def mark_blocked(url_or_host: str, *, reason: str = 'blocked') -> None:
	h = host_of(url_or_host) if '://' in (url_or_host or '') else (url_or_host or '').lower()
	h = h.removeprefix('www.')
	if not h:
		return
	with _LOCK:
		_ensure_loaded()
		_purge()
		if len(_COOLDOWN) >= _MAX and h not in _COOLDOWN:
			oldest = min(_COOLDOWN.items(), key=lambda kv: float(kv[1].get('at') or 0))
			_COOLDOWN.pop(oldest[0], None)
		_COOLDOWN[h] = {'at': time.time(), 'reason': reason[:120]}
		_persist()


def mark_from_degraded(url_or_host: str, degraded: list[str]) -> bool:
	blob = ' '.join(degraded or []).lower()
	if not any(m in blob for m in _BLOCK_MARKERS):
		return False
	reason = next((d for d in degraded if any(m in d.lower() for m in _BLOCK_MARKERS)), 'blocked')
	mark_blocked(url_or_host, reason=str(reason))
	return True


def clear_host_cooldown() -> None:
	global _LOADED
	with _LOCK:
		_COOLDOWN.clear()
		_LOADED = True
		_persist()


def _purge() -> None:
	now = time.time()
	dead = [k for k, v in _COOLDOWN.items() if now - float(v.get('at') or 0) > _TTL_S]
	for k in dead:
		_COOLDOWN.pop(k, None)
