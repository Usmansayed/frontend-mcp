"""Scrapling recovery router — use ours first; Scrapling when important fetches fail.

Ladder (inspiration collect):
  1. Our httpx/urllib (``http_get`` default)
  2. Cheap Scrapling TLS (FetcherSession) — auto inside ``http_get`` on WAF allowlist
  3. Our Perception Chromium (when not fast-skipped)
  4. Scrapling Stealthy — important WAF hosts only, budgeted, after ours failed

``important`` = host on the WAF allowlist (Dribbble, Land-book, LAPA, Behance, Awwwards).
Friendly CDNs never escalate to Stealthy.
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

from navigation.inspiration_intelligence.browser.policy import detect_block_signal, is_fast_mode

# Tough galleries where bake-offs showed Scrapling recovery value.
IMPORTANT_WAF_HOST_SUFFIXES: tuple[str, ...] = (
	'dribbble.com',
	'land-book.com',
	'lapa.ninja',
	'behance.net',
	'awwwards.com',
)


def is_important_waf_host(url: str) -> bool:
	host = (urlparse(url).hostname or '').lower()
	if not host:
		return False
	return any(host == s or host.endswith('.' + s) for s in IMPORTANT_WAF_HOST_SUFFIXES)


# Back-compat alias used by http_get / older call sites
def waf_host_allowlisted(url: str) -> bool:
	return is_important_waf_host(url)


def scrapling_recovery_enabled() -> bool:
	"""Master switch for TLS + Stealthy recovery. Default ON."""
	raw = (os.environ.get('INSPIRATION_SCRAPLING_RECOVERY') or '1').strip().lower()
	if raw in {'0', 'false', 'no', 'off'}:
		return False
	# Legacy alias
	raw2 = (os.environ.get('INSPIRATION_STEALTHY_FALLBACK') or '1').strip().lower()
	return raw2 not in {'0', 'false', 'no', 'off'}


def http_looks_blocked(status: int | None, body: str, err: str | None = None) -> bool:
	if status in (403, 429, 503, 202):
		return True
	if err and not body:
		return True
	if not (body or '').strip():
		return True
	sig = detect_block_signal(body[:8000], status_code=status)
	return bool(sig)


def scrapling_tls_available() -> bool:
	try:
		import scrapling.fetchers  # noqa: F401

		return True
	except Exception:
		return False


def scrapling_stealthy_available() -> bool:
	try:
		from scrapling.fetchers import AsyncStealthySession  # noqa: F401

		return True
	except Exception:
		return False


def should_try_stealthy(
	url: str,
	*,
	blocked: bool,
	fast_mode: bool | None = None,
	chromium_failed_or_skipped: bool = True,
) -> bool:
	"""Stealthy only for important hosts after our path failed/skipped."""
	from navigation.inspiration_intelligence.browser import stealthy_fallback as sf

	if not blocked:
		return False
	if not chromium_failed_or_skipped:
		return False
	if not scrapling_recovery_enabled():
		return False
	if not is_important_waf_host(url):
		return False
	if fast_mode is None:
		fast_mode = is_fast_mode()
	# Important hosts may use Stealthy even in fast mode (recovery). Opt out:
	# INSPIRATION_STEALTHY_SKIP_IN_FAST=1
	if fast_mode:
		skip = (os.environ.get('INSPIRATION_STEALTHY_SKIP_IN_FAST') or '').strip().lower()
		if skip in {'1', 'true', 'yes', 'on'}:
			return False
		# Legacy: INSPIRATION_STEALTHY_IN_FAST=0 used to mean "never in fast".
		# New default: allow important recovery. Only honor explicit skip above.
	if sf.stealthy_budget_remaining() <= 0:
		return False
	if not scrapling_stealthy_available():
		return False
	return True


async def fetch_html_important_recovery(
	url: str,
	*,
	max_bytes: int = 200_000,
	already_blocked: bool = True,
) -> tuple[str, int | None, str | None, list[str], str]:
	"""Run Stealthy recovery for an important blocked URL.

	Returns (html, status, err, notes, tier). tier is ``scrapling_stealthy`` or ``none``.
	"""
	from navigation.inspiration_intelligence.browser.stealthy_fallback import fetch_html_stealthy

	notes: list[str] = ['scrapling_route:important_recovery']
	if not should_try_stealthy(
		url,
		blocked=already_blocked,
		fast_mode=is_fast_mode(),
		chromium_failed_or_skipped=True,
	):
		notes.append('stealthy_not_eligible')
		return '', None, 'stealthy_not_eligible', notes, 'none'

	html, status, err, sn = await fetch_html_stealthy(url, max_bytes=max_bytes)
	notes.extend(sn)
	if err or not html:
		return html or '', status, err or 'empty', notes, 'none'
	if http_looks_blocked(status, html, err):
		notes.append('stealthy_still_blocked')
		return html, status, err or 'still_blocked', notes, 'none'
	return html, status, None, notes, 'scrapling_stealthy'


def recovery_status() -> dict[str, Any]:
	"""Diagnostics for health / agent summary."""
	from navigation.inspiration_intelligence.browser import stealthy_fallback as sf

	return {
		'recovery_enabled': scrapling_recovery_enabled(),
		'tls_available': scrapling_tls_available(),
		'stealthy_available': scrapling_stealthy_available(),
		'stealthy_budget_remaining': sf.stealthy_budget_remaining(),
		'important_hosts': list(IMPORTANT_WAF_HOST_SUFFIXES),
		'fast_mode': is_fast_mode(),
		'stealthy_skip_in_fast': (os.environ.get('INSPIRATION_STEALTHY_SKIP_IN_FAST') or '').strip().lower()
		in {'1', 'true', 'yes', 'on'},
	}
