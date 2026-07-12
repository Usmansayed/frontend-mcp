"""LibreCrawl companion service — health probes + native process orchestration."""

from __future__ import annotations



import asyncio

import os

import time

from dataclasses import dataclass, field

from typing import Any, Awaitable, Callable



from navigation.seo_intelligence.config.defaults import bundled_librecrawl_base_url

from navigation.seo_intelligence.providers.librecrawl.client import LibreCrawlClient

from navigation.seo_intelligence.setup.companion_processes import (

	ensure_monitor_started,

	start_companion_process,

)



_DEFAULT_WAIT_S = 180.0

_DEFAULT_POLL_S = 2.0





@dataclass

class CompanionStatus:

	service_id: str

	url: str

	healthy: bool

	running: bool = False

	notes: list[str] = field(default_factory=list)

	diagnostic: str = ''



	def to_dict(self) -> dict[str, Any]:

		return {

			'service_id': self.service_id,

			'url': self.url,

			'healthy': self.healthy,

			'running': self.running,

			'notes': list(self.notes),

			'diagnostic': self.diagnostic,

		}





def auto_start_enabled() -> bool:

	raw = os.environ.get('SEO_COMPANIONS_AUTO_START', 'true').strip().lower()

	return raw not in {'0', 'false', 'no', 'off'}





async def probe_librecrawl() -> CompanionStatus:

	base = bundled_librecrawl_base_url()

	if not base:

		return CompanionStatus('librecrawl', '', False, diagnostic='librecrawl_url_not_configured')



	client = LibreCrawlClient()

	payload, degraded = await client.crawl_status()

	if payload is not None:

		return CompanionStatus('librecrawl', base, True, running=True, notes=degraded)

	return CompanionStatus(

		'librecrawl',

		base,

		False,

		notes=degraded,

		diagnostic=degraded[0] if degraded else 'librecrawl_unreachable',

	)





async def _wait_until_healthy(

	service_id: str,

	probe: Callable[[], Awaitable[CompanionStatus]],

	*,

	timeout_s: float | None = None,

) -> CompanionStatus:

	limit = timeout_s if timeout_s is not None else _wait_timeout_s()

	deadline = time.monotonic() + limit

	last = await probe()

	while time.monotonic() < deadline:

		if last.healthy:

			last.running = True

			return last

		await asyncio.sleep(_poll_interval_s())

		last = await probe()

	last.diagnostic = last.diagnostic or f'{service_id}_health_timeout:{int(limit)}s'

	last.notes.append(f'companions_health_timeout:{service_id}')

	return last





def _wait_timeout_s() -> float:

	raw = os.environ.get('SEO_COMPANIONS_START_TIMEOUT_S', '').strip()

	try:

		return max(30.0, float(raw)) if raw else _DEFAULT_WAIT_S

	except ValueError:

		return _DEFAULT_WAIT_S





def _poll_interval_s() -> float:

	raw = os.environ.get('SEO_COMPANIONS_POLL_INTERVAL_S', '').strip()

	try:

		return max(0.5, float(raw)) if raw else _DEFAULT_POLL_S

	except ValueError:

		return _DEFAULT_POLL_S





async def ensure_companion(service_id: str) -> CompanionStatus:

	"""Probe → native start if needed → wait until healthy."""

	if service_id != 'librecrawl':

		return CompanionStatus(service_id, '', False, diagnostic=f'unknown_companion:{service_id}')



	status = await probe_librecrawl()

	if status.healthy:

		status.running = True

		return status



	if not auto_start_enabled():

		status.diagnostic = status.diagnostic or f'{service_id}_not_running:auto_start_disabled'

		return status



	started, start_notes = await asyncio.to_thread(start_companion_process, service_id)

	status.notes.extend(start_notes)

	if not started:

		status.diagnostic = start_notes[0] if start_notes else f'{service_id}_start_failed'

		return status



	final = await _wait_until_healthy(service_id, probe_librecrawl)

	final.notes = [*status.notes, *final.notes]

	return final





async def ensure_companions_ready() -> tuple[dict[str, CompanionStatus], list[str]]:

	"""Ensure LibreCrawl is healthy before an SEO audit."""

	ensure_monitor_started()

	all_notes: list[str] = []

	statuses: dict[str, CompanionStatus] = {}



	status = await ensure_companion('librecrawl')

	statuses['librecrawl'] = status

	all_notes.extend(status.notes)

	if not status.healthy:

		diag = status.diagnostic or 'librecrawl_unavailable'

		all_notes.append(f'companion_unhealthy:librecrawl:{diag}')



	return statuses, all_notes





def companion_summary(statuses: dict[str, CompanionStatus]) -> dict[str, Any]:

	return {sid: st.to_dict() for sid, st in statuses.items()}


