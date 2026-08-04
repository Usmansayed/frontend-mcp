"""Discover scout cache — let collect reuse URLs without re-running the cascade."""
from __future__ import annotations

import secrets
import time
from threading import Lock
from typing import Any

_LOCK = Lock()
_CACHE: dict[str, dict[str, Any]] = {}
_TTL_S = 30 * 60  # 30 minutes


def mint_discover_token(
	*,
	query: str,
	candidates: list[dict[str, Any]],
	provider_ids: list[str] | None = None,
) -> str:
	"""Store scout results; return opaque token for collect reuse."""
	token = f'disc_{secrets.token_hex(8)}'
	with _LOCK:
		_purge_expired_unlocked()
		_CACHE[token] = {
			'query': query,
			'candidates': list(candidates),
			'provider_ids': list(provider_ids or []),
			'created_at': time.time(),
		}
	return token


def peek_discover_token(token: str) -> dict[str, Any] | None:
	raw = (token or '').strip()
	if not raw:
		return None
	with _LOCK:
		_purge_expired_unlocked()
		row = _CACHE.get(raw)
		if row is None:
			return None
		return {
			'query': row.get('query') or '',
			'candidates': list(row.get('candidates') or []),
			'provider_ids': list(row.get('provider_ids') or []),
		}


def consume_discover_token(token: str) -> dict[str, Any] | None:
	"""Read and keep token (reuse allowed within TTL — collect may retry blobs)."""
	return peek_discover_token(token)


def _purge_expired_unlocked() -> None:
	now = time.time()
	dead = [k for k, v in _CACHE.items() if now - float(v.get('created_at') or 0) > _TTL_S]
	for k in dead:
		_CACHE.pop(k, None)


def clear_scout_cache() -> None:
	with _LOCK:
		_CACHE.clear()
