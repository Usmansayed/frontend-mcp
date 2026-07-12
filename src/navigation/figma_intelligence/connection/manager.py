"""Figma connection manager — PAT connect, validate, reuse."""
from __future__ import annotations

import os
from typing import Any

from navigation.figma_intelligence.connection.token_store import (
	clear_pat,
	get_pat,
	has_stored_pat,
	save_pat,
)
from navigation.figma_intelligence.providers.figma_console.client import FigmaConsoleMcpClient


class FigmaConnectionManager:
	def __init__(self, *, client: FigmaConsoleMcpClient | None = None) -> None:
		self._client = client or FigmaConsoleMcpClient()

	def is_configured(self) -> bool:
		return has_stored_pat() or self._client.available()

	async def connect(self, pat: str, *, account_hint: str = '') -> dict[str, Any]:
		clean = pat.strip()
		if not clean:
			raise ValueError('figma_pat_required')

		prev_env = os.environ.get('FIGMA_ACCESS_TOKEN')
		os.environ['FIGMA_ACCESS_TOKEN'] = clean
		try:
			health = await self._client.health()
		finally:
			if prev_env is None:
				os.environ.pop('FIGMA_ACCESS_TOKEN', None)
			else:
				os.environ['FIGMA_ACCESS_TOKEN'] = prev_env

		if health.get('status') != 'ok':
			degraded = health.get('degraded') or []
			raise RuntimeError(degraded[0] if degraded else 'figma_pat_validation_failed')

		save_pat(clean, account_hint=account_hint)
		os.environ['FIGMA_ACCESS_TOKEN'] = clean
		return {
			'connected': True,
			'validated': True,
			'mcp': 'southleft/figma-console-mcp',
			'account_hint': account_hint,
		}

	def disconnect(self) -> dict[str, Any]:
		clear_pat()
		os.environ.pop('FIGMA_ACCESS_TOKEN', None)
		os.environ.pop('FIGMA_PAT', None)
		return {'connected': False}

	def status(self) -> dict[str, Any]:
		return {
			'connected': has_stored_pat(),
			'has_pat': has_stored_pat(),
			'mcp': 'southleft/figma-console-mcp',
			'token_source': 'stored' if has_stored_pat() else ('env' if get_pat() else 'none'),
		}

	def client(self) -> FigmaConsoleMcpClient:
		return self._client
