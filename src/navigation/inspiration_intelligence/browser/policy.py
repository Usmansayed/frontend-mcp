"""Anti-bot policy — rate limits, delays, and block detection for inspiration sites."""
from __future__ import annotations

import os
import random
import re
import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class ProviderFetchPolicy:
	"""Per-provider fetch constraints — tune via env or defaults."""

	provider_id: str
	min_delay_s: float = 2.0
	max_delay_s: float = 5.0
	hydration_wait_s: float = 8.0
	headless_default: bool = False
	max_requests_per_run: int = 8
	prefer_api: bool = True
	prefer_browser_with_session: bool = True

	@property
	def jitter_delay_s(self) -> float:
		return random.uniform(self.min_delay_s, self.max_delay_s)


_BLOCK_PATTERNS = re.compile(
	r'403\s+error|access\s+denied|cf-browser-verification|'
	r'captcha|challenge-platform|please\s+verify|blocked',
	re.IGNORECASE,
)


def detect_block_signal(html: str, *, status_code: int | None = None) -> str | None:
	if status_code in {403, 429, 503, 202}:
		return f'http_{status_code}'
	if not html.strip():
		return 'empty_response'
	if _BLOCK_PATTERNS.search(html[:8000]):
		return 'bot_challenge_detected'
	if (
		len(html) < 3000
		and '/shots/' not in html
		and 'og:image' not in html.lower()
		and 'cdn.dribbble.com' not in html.lower()
	):
		return 'waf_stub_page'
	return None


def env_bool(name: str, default: bool) -> bool:
	raw = os.environ.get(name, '').strip().lower()
	if not raw:
		return default
	return raw in {'1', 'true', 'yes', 'on'}


def is_fast_mode() -> bool:
	"""Single-search UX — one query, HTTP-first, target <20s. Default on."""
	raw = os.environ.get('INSPIRATION_FAST', '1').strip().lower()
	return raw not in {'0', 'false', 'no'}


def fast_hydration_wait(base: ProviderFetchPolicy) -> float:
	"""Shorter wait for search pages in fast mode."""
	if is_fast_mode():
		return min(base.hydration_wait_s, 5.0)
	return base.hydration_wait_s


def load_global_policy() -> dict[str, object]:
	return {
		'headless': env_bool('INSPIRATION_HEADLESS', False),
	'rate_limit_ms': int(os.environ.get('INSPIRATION_RATE_LIMIT_MS', '800')),
		'dribbble_session_cookie': os.environ.get('DRIBBBLE_SESSION_COOKIE', '').strip()
		or os.environ.get('dribbble_session_cookie', '').strip(),
	}


def _env_float(name: str, default: float) -> float:
	raw = os.environ.get(name, '').strip()
	return float(raw) if raw else default


_DEFAULT_POLICIES: dict[str, ProviderFetchPolicy] = {
	'dribbble': ProviderFetchPolicy(
		provider_id='dribbble',
		min_delay_s=0.5,
		max_delay_s=1.5,
		hydration_wait_s=9.0,
		headless_default=False,
		max_requests_per_run=3,
	),
	'behance': ProviderFetchPolicy(
		provider_id='behance',
		min_delay_s=0.5,
		max_delay_s=1.5,
		hydration_wait_s=6.0,
		headless_default=False,
		max_requests_per_run=3,
	),
	'awwwards': ProviderFetchPolicy(
		provider_id='awwwards',
		min_delay_s=2.0,
		max_delay_s=4.0,
		hydration_wait_s=5.0,
		headless_default=False,
		max_requests_per_run=3,
	),
	'siteinspire': ProviderFetchPolicy(
		provider_id='siteinspire',
		min_delay_s=1.5,
		max_delay_s=3.5,
		hydration_wait_s=4.0,
		headless_default=False,
		max_requests_per_run=3,
	),
	'godly': ProviderFetchPolicy(
		provider_id='godly',
		min_delay_s=2.0,
		max_delay_s=4.0,
		hydration_wait_s=5.0,
		headless_default=False,
		max_requests_per_run=3,
	),
	'land-book': ProviderFetchPolicy(
		provider_id='land-book',
		min_delay_s=2.0,
		max_delay_s=4.0,
		hydration_wait_s=5.0,
		headless_default=False,
		max_requests_per_run=3,
	),
	'onepagelove': ProviderFetchPolicy(
		provider_id='onepagelove',
		min_delay_s=0.5,
		max_delay_s=1.5,
		hydration_wait_s=4.0,
		headless_default=False,
		max_requests_per_run=4,
	),
}


def production_policy(provider_id: str) -> ProviderFetchPolicy:
	"""Production pacing — ~1 request per minute, max 3 searches per provider per run."""
	if is_fast_mode():
		min_s = _env_float('INSPIRATION_MIN_DELAY_S', 0.8)
	else:
		min_s = _env_float('INSPIRATION_MIN_DELAY_S', 60.0)
	max_s = _env_float('INSPIRATION_MAX_DELAY_S', min_s * 1.25)
	max_req = int(_env_float('INSPIRATION_MAX_REQUESTS_PER_RUN', 3))
	base = _DEFAULT_POLICIES.get(provider_id, ProviderFetchPolicy(provider_id=provider_id))
	return ProviderFetchPolicy(
		provider_id=provider_id,
		min_delay_s=min_s,
		max_delay_s=max_s,
		hydration_wait_s=base.hydration_wait_s,
		headless_default=base.headless_default,
		max_requests_per_run=max_req,
	)


@dataclass
class RateLimitTracker:
	"""In-memory per-provider cooldown — avoids hammering sites in one pipeline run."""

	_last_request: dict[str, float] = field(default_factory=dict)
	_request_counts: dict[str, int] = field(default_factory=dict)

	def wait_if_needed(self, provider_id: str, policy: ProviderFetchPolicy) -> float:
		if os.environ.get('INSPIRATION_FORCE', '').strip().lower() in {'1', 'true', 'yes'}:
			self._request_counts[provider_id] = self._request_counts.get(provider_id, 0) + 1
			return 0.0
		now = time.monotonic()
		last = self._last_request.get(provider_id, 0.0)
		elapsed = now - last
		delay = policy.jitter_delay_s
		if elapsed < delay:
			time.sleep(delay - elapsed)
		self._last_request[provider_id] = time.monotonic()
		self._request_counts[provider_id] = self._request_counts.get(provider_id, 0) + 1
		return delay

	def over_budget(self, provider_id: str, policy: ProviderFetchPolicy) -> bool:
		return self._request_counts.get(provider_id, 0) >= policy.max_requests_per_run

	def policy_for(self, provider_id: str) -> ProviderFetchPolicy:
		return _DEFAULT_POLICIES.get(provider_id, ProviderFetchPolicy(provider_id=provider_id))
