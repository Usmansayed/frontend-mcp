"""HTTP client for Open Design daemon — read-only project access."""
from __future__ import annotations

import os
from typing import Any

try:
	import httpx
except ImportError:
	httpx = None  # type: ignore[assignment]


class OpenDesignClient:
	"""Thin client for OD daemon endpoints (list_projects, get_project, search_files, etc.)."""

	def __init__(self, *, base_url: str | None = None, timeout: float = 15.0) -> None:
		self._base_url = (base_url or os.environ.get('OD_DAEMON_URL') or '').rstrip('/')
		self._timeout = timeout

	def is_configured(self) -> bool:
		return bool(self._base_url) and httpx is not None

	async def _get(self, path: str) -> dict[str, Any]:
		if not self.is_configured():
			return {}
		assert httpx is not None
		url = f'{self._base_url}{path}'
		async with httpx.AsyncClient(timeout=self._timeout) as client:
			resp = await client.get(url)
			resp.raise_for_status()
			data = resp.json()
			return data if isinstance(data, dict) else {}

	async def list_projects(self) -> dict[str, Any]:
		return await self._get('/api/projects')

	async def get_project(self, project: str) -> dict[str, Any]:
		return await self._get(f'/api/projects/{project}')

	async def get_active_context(self) -> dict[str, Any]:
		return await self._get('/api/active-context')

	async def search_files(self, project: str, query: str) -> dict[str, Any]:
		if not self.is_configured():
			return {}
		assert httpx is not None
		url = f'{self._base_url}/api/projects/{project}/search'
		async with httpx.AsyncClient(timeout=self._timeout) as client:
			resp = await client.get(url, params={'q': query})
			resp.raise_for_status()
			data = resp.json()
			return data if isinstance(data, dict) else {}

	async def get_artifact(self, project: str) -> dict[str, Any]:
		return await self._get(f'/api/projects/{project}/artifact')
