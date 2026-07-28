"""Per-provider circuit breaker — skip recently failing galleries briefly."""
from __future__ import annotations

import time
from threading import Lock
from typing import Any

_LOCK = Lock()
_STATE: dict[str, dict[str, Any]] = {}
_FAIL_THRESHOLD = 2
_OPEN_S = 90.0  # skip provider for 90s after repeated failures


def record_success(provider_id: str) -> None:
	with _LOCK:
		_STATE.pop(provider_id, None)


def record_failure(provider_id: str) -> None:
	with _LOCK:
		row = _STATE.setdefault(provider_id, {'fails': 0, 'opened_at': 0.0})
		row['fails'] = int(row.get('fails') or 0) + 1
		if row['fails'] >= _FAIL_THRESHOLD:
			row['opened_at'] = time.time()


def is_open(provider_id: str) -> bool:
	"""True when provider should be skipped (circuit open)."""
	with _LOCK:
		row = _STATE.get(provider_id)
		if not row:
			return False
		opened = float(row.get('opened_at') or 0)
		if opened <= 0:
			return False
		if time.time() - opened > _OPEN_S:
			_STATE.pop(provider_id, None)
			return False
		return int(row.get('fails') or 0) >= _FAIL_THRESHOLD


def filter_open_circuits(provider_ids: list[str]) -> tuple[list[str], list[str]]:
	"""Return (eligible, skipped)."""
	eligible: list[str] = []
	skipped: list[str] = []
	for pid in provider_ids:
		if is_open(pid):
			skipped.append(pid)
		else:
			eligible.append(pid)
	return eligible, skipped


def clear_circuits() -> None:
	with _LOCK:
		_STATE.clear()
