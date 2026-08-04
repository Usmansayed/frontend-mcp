"""Sticky inspiration source affinity — remember winners per intent for ~30m.

Boosts specialist galleries / scout categories that recently delivered usable refs.
Persists to disk so MCP restarts keep sticky winners.
"""
from __future__ import annotations

import time
from threading import Lock
from typing import Any

from navigation.inspiration_intelligence.cache_store import load_json_dict, save_json_dict

_LOCK = Lock()
_WINS: dict[str, dict[str, Any]] = {}
_TTL_S = 30 * 60
_MAX_KEYS = 48
_LOADED = False


def _disk():
	from navigation.inspiration_intelligence.cache_store import cache_path

	return cache_path('inspiration_affinity.json')


def affinity_key(*, scope: str, intent_class: str = '', query: str = '') -> str:
	"""Stable bucket for sticky boosts."""
	scope_l = (scope or 'page').strip().lower()
	intent = (intent_class or '').strip().lower()
	if intent and intent != 'default':
		return f'{scope_l}:{intent}'
	toks = [t for t in (query or '').lower().split() if len(t) > 3][:2]
	tail = '_'.join(toks) if toks else 'general'
	return f'{scope_l}:{tail}'


def _ensure_loaded() -> None:
	global _LOADED
	if _LOADED:
		return
	raw = load_json_dict(_disk())
	entries = raw.get('wins') if isinstance(raw.get('wins'), dict) else {}
	now = time.time()
	for k, v in entries.items():
		if isinstance(v, dict) and now - float(v.get('updated_at') or 0) <= _TTL_S:
			_WINS[str(k)] = v
	_LOADED = True


def _persist() -> None:
	save_json_dict(_disk(), {'wins': dict(_WINS)})


def record_winners(key: str, provider_ids: list[str], *, weight: float = 1.0) -> None:
	if not key or not provider_ids:
		return
	with _LOCK:
		_ensure_loaded()
		_purge_unlocked()
		row = _WINS.setdefault(key, {'scores': {}, 'updated_at': time.time()})
		scores: dict[str, float] = dict(row.get('scores') or {})
		for pid in provider_ids:
			pid = str(pid or '').strip()
			if not pid or pid.startswith('_'):
				continue
			scores[pid] = float(scores.get(pid) or 0) + float(weight)
		row['scores'] = scores
		row['updated_at'] = time.time()
		_WINS[key] = row
		if len(_WINS) > _MAX_KEYS:
			oldest = min(_WINS.items(), key=lambda kv: float(kv[1].get('updated_at') or 0))
			_WINS.pop(oldest[0], None)
		_persist()


def prefer_providers(key: str, *, limit: int = 6) -> list[str]:
	with _LOCK:
		_ensure_loaded()
		_purge_unlocked()
		row = _WINS.get(key)
		if not row:
			return []
		scores = dict(row.get('scores') or {})
	ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
	return [pid for pid, _ in ranked[: max(1, limit)]]


def prefer_categories_from_providers(provider_ids: list[str]) -> list[str]:
	"""Map sticky providers → multi-scout prefer_categories hints."""
	mapping = {
		'navbar_gallery': 'navigation',
		'footer_design': 'landing',
		'hero_gallery': 'landing',
		'saasframe': 'landing',
		'saaslandingpage': 'landing',
		'saasinterface': 'dashboard',
		'daisyui': 'component_showcase',
		'aceternity_buttons': 'component_showcase',
		'shadcnblocks': 'component_showcase',
		'ibelick_buttons': 'component_showcase',
		'flowbite_button_docs': 'component_showcase',
		'flowbite_modal_docs': 'component_showcase',
		'flowbite_navbar_docs': 'navigation',
		'flowbite_sidebar_docs': 'dashboard',
		'onepagelove': 'landing',
		'httpster': 'landing',
		'web_search': 'landing',
	}
	out: list[str] = []
	seen: set[str] = set()
	for pid in provider_ids:
		cat = mapping.get(pid)
		if cat and cat not in seen:
			seen.add(cat)
			out.append(cat)
	return out


def clear_affinity() -> None:
	global _LOADED
	with _LOCK:
		_WINS.clear()
		_LOADED = True
		_persist()


def _purge_unlocked() -> None:
	now = time.time()
	dead = [k for k, v in _WINS.items() if now - float(v.get('updated_at') or 0) > _TTL_S]
	for k in dead:
		_WINS.pop(k, None)
