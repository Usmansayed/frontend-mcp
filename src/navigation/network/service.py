"""Per-session network capture lifecycle."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .buffer import NetworkRingBuffer
from .collector import NetworkCollector
from .har import entries_to_har
from .models import NetworkFilter, NetworkReport


class SessionNetworkService:
	def __init__(
		self,
		*,
		max_entries: int = 300,
		slow_threshold_ms: float = 1000.0,
	) -> None:
		self._buffer = NetworkRingBuffer(max_entries=max_entries)
		self._collector = NetworkCollector(self._buffer)
		self._slow_threshold_ms = slow_threshold_ms
		self._attached = False

	@property
	def session_total(self) -> int:
		return self._buffer.session_total

	async def attach(self, session: Any) -> None:
		if self._attached:
			return
		await self._collector.start(session)
		self._attached = True

	def detach(self) -> None:
		if not self._attached:
			return
		self._collector.stop()
		self._attached = False

	def mark_window(self) -> int:
		return self._buffer.session_total

	def clear(self) -> int:
		return self._buffer.clear()

	async def report(
		self,
		session: Any,
		*,
		window_start_index: int | None = None,
		filter: NetworkFilter | None = None,
		page_url: str = '',
		har_dir: Path | None = None,
		har_name: str = 'network',
		fetch_bodies: bool = False,
		settle_timeout: float = 5.0,
	) -> NetworkReport:
		await self._collector.await_pending(settle_timeout)
		start = window_start_index if window_start_index is not None else 0
		candidates = self._buffer.entries_since(start)
		if fetch_bodies:
			await self._collector.enrich_bodies(candidates)
		report = self._buffer.build_report(
			candidates,
			window_start_index=start,
			filter=filter,
			slow_threshold_ms=self._slow_threshold_ms,
		)
		if har_dir is not None and candidates:
			har_dir.mkdir(parents=True, exist_ok=True)
			har_path = har_dir / f'{har_name}.har'
			har_path.write_text(
				json.dumps(entries_to_har(candidates, page_url=page_url), indent=2),
				encoding='utf-8',
			)
			report.har_path = str(har_path)
		return report

	async def window_report(
		self,
		session: Any,
		window_start_index: int,
		*,
		page_url: str = '',
		har_dir: Path | None = None,
		har_name: str = 'network',
		limit: int = 50,
		fetch_bodies: bool = True,
	) -> NetworkReport:
		return await self.report(
			session,
			window_start_index=window_start_index,
			filter=NetworkFilter(limit=limit, include_bodies=fetch_bodies),
			page_url=page_url,
			har_dir=har_dir,
			har_name=har_name,
			fetch_bodies=fetch_bodies,
		)
