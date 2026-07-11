"""HTTP MCP client for self-hosted OpenSEO (every-app/open-seo)."""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def resolve_mcp_url() -> str:
	"""Resolve OpenSEO MCP endpoint from env."""
	explicit = os.environ.get('OPENSEO_MCP_URL', '').strip().rstrip('/')
	if explicit:
		return explicit
	base = os.environ.get('OPENSEO_BASE_URL', '').strip().rstrip('/')
	if not base:
		return ''
	if base.endswith('/mcp'):
		return base
	return f'{base}/mcp'


def resolve_project_id() -> str:
	return os.environ.get('OPENSEO_PROJECT_ID', '').strip()


class OpenSeoMcpClient:
	"""Call OpenSEO MCP tools over Streamable HTTP."""

	def __init__(
		self,
		*,
		mcp_url: str | None = None,
		project_id: str | None = None,
		timeout: float = 30.0,
	) -> None:
		self._mcp_url = (mcp_url or resolve_mcp_url()).rstrip('/')
		self._project_id = project_id if project_id is not None else resolve_project_id()
		self._timeout = timeout

	def configured(self) -> bool:
		return bool(self._mcp_url)

	def project_configured(self) -> bool:
		return bool(self._project_id)

	@asynccontextmanager
	async def session(self) -> AsyncIterator[ClientSession]:
		if not self._mcp_url:
			raise RuntimeError('openseo_mcp_url_not_configured')
		async with streamablehttp_client(self._mcp_url, timeout=self._timeout) as (read_stream, write_stream, _):
			async with ClientSession(read_stream, write_stream) as client:
				await client.initialize()
				yield client

	async def list_tools(self) -> tuple[list[str], list[str]]:
		degraded: list[str] = []
		if not self.configured():
			return [], ['openseo_mcp_not_configured']
		try:
			async with self.session() as client:
				result = await client.list_tools()
		except Exception as exc:
			return [], [f'openseo_mcp_error:{type(exc).__name__}']
		names = [tool.name for tool in result.tools]
		if not names:
			degraded.append('openseo_mcp_no_tools')
		return names, degraded

	async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> tuple[Any, list[str]]:
		degraded: list[str] = []
		if not self.configured():
			return None, ['openseo_mcp_not_configured']
		if not self.project_configured():
			return None, ['openseo_project_id_missing:set_OPENSEO_PROJECT_ID']
		args = dict(arguments or {})
		if 'projectId' not in args:
			args['projectId'] = self._project_id
		try:
			async with self.session() as client:
				result = await client.call_tool(tool_name, args)
		except Exception as exc:
			return None, [f'openseo_mcp_error:{type(exc).__name__}']

		payload = _parse_tool_result(result)
		if payload is None:
			degraded.append(f'openseo_empty_result:{tool_name}')
		return payload, degraded

	async def health(self) -> dict[str, Any]:
		tools, degraded = await self.list_tools()
		free_tools = {'get_search_console_performance', 'inspect_urls'}
		has_free = bool(free_tools & set(tools))
		if tools and not degraded:
			status = 'ok' if has_free else 'degraded'
			if not has_free:
				degraded.append('openseo_free_tools_unavailable')
		elif self.configured() and not tools:
			status = 'degraded'
		else:
			status = 'degraded'
		return {
			'provider_id': 'openseo',
			'status': status,
			'mcp_url': self._mcp_url,
			'project_id_set': self.project_configured(),
			'tools': tools,
			'degraded': degraded,
		}


def _parse_tool_result(result: Any) -> Any:
	structured = getattr(result, 'structuredContent', None)
	if isinstance(structured, dict) and structured:
		return structured
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
