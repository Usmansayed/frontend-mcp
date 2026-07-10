"""Open Design integration adapter — only direct external integration.

Supports OD daemon HTTP API (when OD_DAEMON_URL is set) or degraded plan-only mode.
Replaceable via DesignSenseProvider protocol.
"""
from __future__ import annotations

import os
from typing import Any

from ...models import ProviderContribution, ReviewFinding, ReviewRequest
from .client import OpenDesignClient


class OpenDesignProvider:
	name = 'open_design'
	kind = 'integration'
	lane = 'subjective'

	def __init__(self, client: OpenDesignClient | None = None) -> None:
		self._client = client or OpenDesignClient()

	async def contribute(self, request: ReviewRequest) -> ProviderContribution:
		degraded: list[str] = []
		findings: list[ReviewFinding] = []
		notes: list[str] = []

		if not self._client.is_configured():
			return ProviderContribution(
				provider=self.name,
				notes=['Open Design not configured — set OD_DAEMON_URL or run local od daemon'],
				degraded=['open_design_not_configured'],
			)

		project = request.open_design_project
		if not project:
			active = await self._client.get_active_context()
			if active.get('active'):
				project = str(active.get('project') or '')
			else:
				degraded.append('open_design_no_active_project')
				notes.append(str(active.get('hint') or 'Specify open_design_project'))

		if project:
			meta = await self._client.get_project(project)
			notes.append(f'open_design_project:{meta.get("name", project)}')
			if request.user_task:
				search = await self._client.search_files(project, request.user_task)
				for hit in (search.get('results') or [])[:5]:
					findings.append(
						ReviewFinding(
							id=f'od_search_{len(findings)}',
							category='reference',
							severity='advisory',
							message=f'Open Design artifact match: {hit.get("path", "?")}',
							recommendation='Compare implementation against Open Design reference artifact',
							source=self.name,
							metadata=dict(hit) if isinstance(hit, dict) else {},
						)
					)

		if degraded and not findings:
			degraded.append('open_design_heuristic_only')

		return ProviderContribution(
			provider=self.name,
			findings=findings,
			notes=notes,
			degraded=list(dict.fromkeys(degraded)),
		)
