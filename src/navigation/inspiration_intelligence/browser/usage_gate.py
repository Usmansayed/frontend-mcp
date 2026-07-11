"""Usage gate — inspiration fetches only when needed, never mass-requested."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_COOLDOWN_S = 30  # 30s between full inspiration runs (single search stays fast)
_CACHE_PATH = Path(os.environ.get('INSPIRATION_USAGE_CACHE', '.cache/inspiration_usage.json'))


@dataclass(slots=True)
class UsageGateResult:
	allowed: bool
	reason: str = ''
	seconds_until_ready: float = 0.0


class InspirationUsageGate:
	"""Persisted cooldown — agents should call inspiration only when building UI.

	Env:
	  INSPIRATION_MIN_COOLDOWN_S — seconds between pipeline runs (default 120)
	  INSPIRATION_FORCE=1 — bypass gate (probes/tests only)
	"""

	def __init__(self, *, cache_path: Path | None = None, cooldown_s: float | None = None) -> None:
		self._cache_path = cache_path or _CACHE_PATH
		self._cooldown_s = cooldown_s if cooldown_s is not None else float(
			os.environ.get('INSPIRATION_MIN_COOLDOWN_S', _DEFAULT_COOLDOWN_S)
		)

	def check(self, *, purpose: str = 'discover') -> UsageGateResult:
		if os.environ.get('INSPIRATION_FORCE', '').strip() in {'1', 'true', 'yes'}:
			return UsageGateResult(allowed=True, reason='force_bypass')

		state = self._read()
		last = float(state.get('last_run_at', 0))
		elapsed = time.time() - last
		if last > 0 and elapsed < self._cooldown_s:
			remaining = self._cooldown_s - elapsed
			return UsageGateResult(
				allowed=False,
				reason=f'cooldown_active:{purpose}',
				seconds_until_ready=remaining,
			)
		return UsageGateResult(allowed=True)

	def record_run(self, *, purpose: str = 'discover', provider_ids: list[str] | None = None) -> None:
		state = self._read()
		state['last_run_at'] = time.time()
		state['last_purpose'] = purpose
		state['last_providers'] = provider_ids or []
		self._write(state)

	def wait_until_ready(self) -> UsageGateResult:
		result = self.check()
		if result.allowed:
			return result
		if result.seconds_until_ready > 0:
			time.sleep(result.seconds_until_ready)
		return UsageGateResult(allowed=True, reason='cooldown_elapsed')

	def _read(self) -> dict[str, object]:
		if not self._cache_path.exists():
			return {}
		try:
			return json.loads(self._cache_path.read_text(encoding='utf-8'))
		except (json.JSONDecodeError, OSError):
			return {}

	def _write(self, state: dict[str, object]) -> None:
		self._cache_path.parent.mkdir(parents=True, exist_ok=True)
		self._cache_path.write_text(json.dumps(state, indent=2), encoding='utf-8')
