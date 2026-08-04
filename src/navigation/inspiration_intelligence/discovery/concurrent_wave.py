"""Concurrent HTTP provider discovery wave with early cancel."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from navigation.inspiration_intelligence.concurrent import (
	BROWSER_HEAVY_PROVIDERS,
	DEFAULT_HTTP_CONCURRENCY,
	split_provider_tiers,
)
from navigation.inspiration_intelligence.models import (
	CommunitySearchPlan,
	InspirationCandidate,
	InspirationIntent,
	InspirationSearchPlan,
)
from navigation.inspiration_intelligence.providers.manager import InspirationProviderRegistry

# Hard cap so a hung HTTP gallery cannot stall the whole MCP tool call.
DEFAULT_PROVIDER_TIMEOUT_S = 8.0


def _peel_leading_browser(provider_ids: list[str]) -> tuple[list[str], list[str]]:
	"""Providers listed before the first HTTP id run first (honors preference pin)."""
	lead: list[str] = []
	rest = list(provider_ids)
	while rest and rest[0] in BROWSER_HEAVY_PROVIDERS:
		lead.append(rest.pop(0))
	return lead, rest


async def discover_providers_concurrent(
	registry: InspirationProviderRegistry,
	provider_ids: list[str],
	*,
	search_plan: InspirationSearchPlan,
	community_plan: CommunitySearchPlan,
	intent: InspirationIntent,
	max_results: int,
	http_concurrency: int = DEFAULT_HTTP_CONCURRENCY,
	should_stop: Any | None = None,
	provider_timeout_s: float = DEFAULT_PROVIDER_TIMEOUT_S,
) -> tuple[
	dict[str, tuple[list[InspirationCandidate], list[str]]],
	list[dict[str, Any]],
	list[str],
]:
	"""Honor preference-first, then fan out HTTP; browser-heavy otherwise serial.

	Order:
	  1. Leading browser-heavy providers (e.g. dribbble when preferred) — serial
	  2. HTTP/CDN providers — concurrent with early cancel
	  3. Remaining browser-heavy — serial exclusive queue

	Returns:
	  results_by_provider: provider_id → (candidates, degraded)
	  timing_traces: per-provider elapsed_ms
	  providers_searched: ordered list of providers that ran
	"""
	lead_browser, rest = _peel_leading_browser(provider_ids)
	http_ids, trail_browser = split_provider_tiers(rest)
	results: dict[str, tuple[list[InspirationCandidate], list[str]]] = {}
	traces: list[dict[str, Any]] = []
	searched: list[str] = []

	async def _one(pid: str) -> tuple[str, float, list[InspirationCandidate], list[str], str | None]:
		provider = registry.get(pid)
		if provider is None:
			return pid, 0.0, [], [f'discovery_missing_provider:{pid}'], 'missing'
		t0 = time.perf_counter()
		try:
			batch, deg = await asyncio.wait_for(
				provider.discover_candidates(
					search_plan,
					community_plan=community_plan,
					intent=intent,
					max_results=max_results,
				),
				timeout=max(1.0, provider_timeout_s),
			)
			err = None
		except asyncio.TimeoutError:
			batch, deg, err = [], [f'discovery_timeout:{provider_timeout_s}s'], 'timeout'
		except Exception as exc:  # noqa: BLE001 — surface in traces
			batch, deg, err = [], [f'discovery_error:{exc}'], str(exc)
		elapsed = (time.perf_counter() - t0) * 1000.0
		return pid, elapsed, batch, deg, err

	async def _run_serial(pids: list[str], *, tier: str) -> None:
		for pid in pids:
			if should_stop is not None and should_stop(results):
				break
			_pid, elapsed, batch, deg, err = await _one(pid)
			results[_pid] = (batch, deg)
			searched.append(_pid)
			traces.append(
				{
					'provider_id': _pid,
					'elapsed_ms': round(elapsed, 1),
					'ok': err is None,
					'count': len(batch),
					'error': err,
					'tier': tier,
				}
			)

	# --- 1. Preference / leading browser-heavy first ---
	await _run_serial(lead_browser, tier='browser_lead')
	if should_stop is not None and should_stop(results):
		return results, traces, searched

	# --- 2. HTTP wave with early cancel ---
	if http_ids:
		tasks: dict[asyncio.Task, str] = {}
		sem = asyncio.Semaphore(max(1, http_concurrency))

		async def _bounded(pid: str):
			async with sem:
				return await _one(pid)

		for pid in http_ids:
			tasks[asyncio.create_task(_bounded(pid))] = pid

		pending: set[asyncio.Task] = set(tasks)
		while pending:
			if should_stop is not None and should_stop(results):
				for t in pending:
					t.cancel()
				await asyncio.gather(*pending, return_exceptions=True)
				traces.append(
					{
						'provider_id': '_http_wave',
						'elapsed_ms': 0,
						'ok': True,
						'stopped_early': True,
						'cancelled': len(pending),
					}
				)
				break

			done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
			for task in done:
				pid = tasks[task]
				if task.cancelled():
					traces.append({'provider_id': pid, 'elapsed_ms': 0, 'ok': False, 'cancelled': True})
					continue
				exc = task.exception()
				if exc is not None:
					results[pid] = ([], [f'discovery_error:{exc}'])
					traces.append({'provider_id': pid, 'elapsed_ms': 0, 'ok': False, 'error': str(exc)})
					searched.append(pid)
					continue
				_pid, elapsed, batch, deg, err = task.result()
				results[_pid] = (batch, deg)
				searched.append(_pid)
				traces.append(
					{
						'provider_id': _pid,
						'elapsed_ms': round(elapsed, 1),
						'ok': err is None,
						'count': len(batch),
						'error': err,
						'tier': 'http',
					}
				)
				if should_stop is not None and should_stop(results):
					for t in pending:
						t.cancel()
					await asyncio.gather(*pending, return_exceptions=True)
					traces.append(
						{
							'provider_id': '_http_wave',
							'elapsed_ms': 0,
							'ok': True,
							'stopped_early': True,
							'cancelled': len(pending),
						}
					)
					pending = set()
					break

	# --- 3. Trailing browser exclusive queue ---
	if should_stop is not None and should_stop(results):
		return results, traces, searched

	await _run_serial(trail_browser, tier='browser')
	return results, traces, searched
