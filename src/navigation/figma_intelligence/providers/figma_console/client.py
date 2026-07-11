"""Thin MCP stdio client for southleft/figma-console-mcp."""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class FigmaConsoleMcpClient:
	"""Spawn figma-console-mcp via npx and call tools."""

	def __init__(
		self,
		*,
		command: str | None = None,
		args: list[str] | None = None,
		env: dict[str, str] | None = None,
	) -> None:
		self._command = command or os.environ.get('FIGMA_CONSOLE_MCP_COMMAND', 'npx')
		default_args = os.environ.get('FIGMA_CONSOLE_MCP_ARGS', '-y figma-console-mcp@latest').split()
		self._args = args or default_args
		self._env = env

	def _figma_token(self) -> str:
		return (
			os.environ.get('FIGMA_ACCESS_TOKEN', '').strip()
			or os.environ.get('figma_pat', '').strip()
			or os.environ.get('FIGMA_PAT', '').strip()
		)

	def available(self) -> bool:
		if self._figma_token():
			return True
		# Local bridge mode may work without token when Desktop Bridge is connected.
		return os.environ.get('FIGMA_CONSOLE_MCP_ENABLED', '1').strip() not in {'0', 'false', 'no'}

	@asynccontextmanager
	async def session(self) -> AsyncIterator[ClientSession]:
		env = dict(os.environ)
		token = self._figma_token()
		if token:
			env['FIGMA_ACCESS_TOKEN'] = token
		if self._env:
			env.update(self._env)
		params = StdioServerParameters(command=self._command, args=self._args, env=env)
		async with stdio_client(params) as (read_stream, write_stream):
			async with ClientSession(read_stream, write_stream) as client:
				await client.initialize()
				yield client

	async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> tuple[Any, list[str]]:
		degraded: list[str] = []
		if not self.available():
			return None, ['figma_console_mcp_unavailable']
		try:
			async with self.session() as client:
				result = await client.call_tool(tool_name, arguments or {})
		except Exception as exc:
			return None, [f'figma_console_mcp_error:{type(exc).__name__}']

		payload = _parse_tool_result(result)
		if payload is None:
			degraded.append(f'figma_console_empty_result:{tool_name}')
		return payload, degraded

	async def health(self) -> dict[str, Any]:
		payload, degraded = await self.call_tool('figma_get_status', {})
		status = 'ok' if payload and not degraded else 'degraded'
		return {
			'provider_id': 'figma_console',
			'status': status,
			'mcp': 'southleft/figma-console-mcp',
			'degraded': degraded,
			'payload': payload,
		}


def _parse_tool_result(result: Any) -> Any:
	content = getattr(result, 'content', None)
	if not content:
		return None
	for block in content:
		text = getattr(block, 'text', None)
		if not isinstance(text, str) or not text.strip():
			continue
		try:
			return json.loads(text)
		except json.JSONDecodeError:
			return {'text': text}
	return None
