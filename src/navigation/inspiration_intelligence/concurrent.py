"""Concurrent inspiration fetch pools — HTTP parallel, browser exclusive.

Research spike (inspiration-layer enlargement): fan out HTTP/CDN gallery
providers with asyncio.gather; keep headed/WAF providers on a serial exclusive path.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar('T')

# Browser / WAF / SPA galleries — never fan out together (anti-bot + shared Chromium).
BROWSER_HEAVY_PROVIDERS: frozenset[str] = frozenset(
	{
		'dribbble',
		'awwwards',
		'godly',
		'land-book',
	}
)

DEFAULT_HTTP_CONCURRENCY = 5


def split_provider_tiers(provider_ids: list[str]) -> tuple[list[str], list[str]]:
	"""Split into (http_concurrent, browser_serial) preserving caller order."""
	http: list[str] = []
	browser: list[str] = []
	for pid in provider_ids:
		if pid in BROWSER_HEAVY_PROVIDERS:
			browser.append(pid)
		else:
			# HTTP/CDN galleries + unknown providers — concurrent-safe.
			http.append(pid)
	return http, browser


async def gather_limited(
	coros: list[Awaitable[T]],
	*,
	limit: int = DEFAULT_HTTP_CONCURRENCY,
) -> list[T | BaseException]:
	"""Run awaitables with a concurrency cap; return results in input order."""
	if not coros:
		return []
	sem = asyncio.Semaphore(max(1, limit))

	async def _wrap(coro: Awaitable[T]) -> T:
		async with sem:
			return await coro

	return list(await asyncio.gather(*[_wrap(c) for c in coros], return_exceptions=True))


async def timed_call(
	label: str,
	coro: Awaitable[T],
) -> tuple[str, float, T | BaseException]:
	"""Return (label, elapsed_ms, result_or_exc)."""
	t0 = time.perf_counter()
	try:
		result: T | BaseException = await coro
	except BaseException as exc:  # noqa: BLE001 — spike telemetry needs all failures
		result = exc
	elapsed_ms = (time.perf_counter() - t0) * 1000.0
	return label, elapsed_ms, result


def merge_timing_traces(
	traces: list[dict[str, Any]],
	*,
	label: str,
	elapsed_ms: float,
	ok: bool,
	extra: dict[str, Any] | None = None,
) -> None:
	row: dict[str, Any] = {
		'provider_id': label,
		'elapsed_ms': round(elapsed_ms, 1),
		'ok': ok,
	}
	if extra:
		row.update(extra)
	traces.append(row)
