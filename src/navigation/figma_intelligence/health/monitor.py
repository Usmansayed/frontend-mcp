"""Figma Intelligence health monitor."""
from __future__ import annotations

from typing import Any

from navigation.figma_intelligence.adapter.console import FigmaConsoleAdapter
from navigation.figma_intelligence.connection.manager import FigmaConnectionManager


class FigmaHealthMonitor:
	def __init__(
		self,
		*,
		connection: FigmaConnectionManager | None = None,
		adapter: FigmaConsoleAdapter | None = None,
	) -> None:
		self._connection = connection or FigmaConnectionManager()
		self._adapter = adapter or FigmaConsoleAdapter(client=self._connection.client())

	async def check(self) -> dict[str, Any]:
		conn = self._connection.status()
		if not conn.get('connected') and not self._connection.is_configured():
			return {
				'status': 'disconnected',
				'connected': False,
				'mcp': 'southleft/figma-console-mcp',
				'degraded': ['figma_not_connected'],
			}

		health = await self._connection.client().health()
		adapter_degraded = self._adapter.consume_degraded()
		status = 'ok' if health.get('status') == 'ok' else 'degraded'
		return {
			'status': status,
			'connected': bool(conn.get('connected')),
			'mcp': 'southleft/figma-console-mcp',
			'token_source': conn.get('token_source'),
			'console': health,
			'degraded': list(health.get('degraded') or []) + adapter_degraded,
		}
