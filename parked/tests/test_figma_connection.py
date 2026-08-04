"""Figma Intelligence connection layer tests."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.figma_intelligence.adapter.console import FigmaConsoleAdapter, parse_file_key
from navigation.figma_intelligence.cache.store import FigmaDesignCache
from navigation.figma_intelligence.connection.manager import FigmaConnectionManager
from navigation.figma_intelligence.connection.token_store import clear_pat
from navigation.figma_intelligence.coordination.coordinator import FigmaCoordinationLayer
from navigation.figma_intelligence.normalize.context import normalize_design_context
from navigation.figma_intelligence.providers.figma_console.client import FigmaConsoleMcpClient
from navigation.figma_intelligence.service import FigmaIntelligenceService
from navigation.figma_intelligence.session.manager import FigmaSessionManager


class _FakeClient(FigmaConsoleMcpClient):
	def __init__(self) -> None:
		super().__init__(command='echo', args=['ok'])

	async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> tuple[Any, list[str]]:
		_ = arguments
		if tool_name == 'figma_get_status':
			return {
				'fileKey': 'AbCdEfGhIj',
				'fileName': 'Design System',
				'selection': {'node_ids': ['1:2']},
			}, []
		if tool_name == 'figma_get_file_data':
			return {
				'file_key': 'AbCdEfGhIj',
				'name': 'Design System',
				'pages': [
					{
						'id': '0:1',
						'name': 'Cover',
						'children': [
							{'id': '1:2', 'name': 'Hero', 'type': 'FRAME', 'width': 1440, 'height': 900},
						],
					},
				],
			}, []
		if tool_name == 'figma_get_library_components':
			return {'components': [{'id': 'c1', 'name': 'Button'}]}, []
		if tool_name == 'figma_get_variables':
			return {'variables': [{'id': 'v1', 'name': 'primary', 'resolvedType': 'COLOR'}]}, []
		if tool_name == 'figma_get_styles':
			return {'styles': [{'id': 's1', 'name': 'Heading', 'styleType': 'TEXT'}]}, []
		if tool_name == 'figma_get_token_values':
			return {'tokens': [{'name': 'color.primary', 'value': '#0055FF'}]}, []
		return {}, [f'unhandled:{tool_name}']

	async def health(self) -> dict[str, Any]:
		return {'provider_id': 'figma_console', 'status': 'ok', 'mcp': 'test', 'degraded': [], 'payload': {}}


def test_parse_file_key() -> None:
	assert parse_file_key('https://www.figma.com/design/AbCdEfGhIj/My-File') == 'AbCdEfGhIj'
	assert parse_file_key('AbCdEfGhIjKlMn') == 'AbCdEfGhIjKlMn'
	assert parse_file_key('') == ''


def test_normalize_design_context() -> None:
	ctx = normalize_design_context(
		connected=True,
		session={'file_key': 'AbCdEfGhIj', 'active_page_id': '0:1'},
		file_payload={'file_key': 'AbCdEfGhIj', 'name': 'DS', 'pages': [{'id': '0:1', 'name': 'Cover'}]},
		components=[{'id': 'c1', 'name': 'Button'}],
		variables=[],
		styles=[],
		tokens=[],
		selection={'node_ids': ['1:2']},
		known_files=[],
	)
	assert ctx.connected
	assert ctx.file is not None
	assert ctx.file.file_key == 'AbCdEfGhIj'
	assert ctx.components[0].name == 'Button'
	assert ctx.selection.node_ids == ['1:2']


def test_design_cache_hit() -> None:
	cache = FigmaDesignCache(ttl_seconds=60)
	session = {'file_key': 'x', 'active_page_id': '', 'active_frame_id': '', 'selection_node_ids': []}
	cache.put(session, {'connected': True, 'file': None, 'components': []})
	assert cache.get(session) is not None
	cache.invalidate()
	assert cache.get(session) is None


def test_service_connect_and_context(tmp_path: Path, monkeypatch: Any) -> None:
	token_file = tmp_path / 'figma_tokens.json'
	session_file = tmp_path / 'figma_session.json'
	monkeypatch.setenv('FIGMA_TOKEN_PATH', str(token_file))
	monkeypatch.setenv('FIGMA_SESSION_PATH', str(session_file))

	client = _FakeClient()
	connection = FigmaConnectionManager(client=client)
	session_mgr = FigmaSessionManager(path=session_file)
	service = FigmaIntelligenceService(
		connection=connection,
		session=session_mgr,
		coordinator=FigmaCoordinationLayer(
			connection=connection,
			session=session_mgr,
			adapter=FigmaConsoleAdapter(client=client),
		),
	)

	async def _run() -> None:
		clear_pat()
		result = await service.connect('test-pat-token')
		assert result['connected']
		service.set_active_file(file_url='https://www.figma.com/design/AbCdEfGhIj/DS')
		ctx = await service.get_context()
		assert ctx.file is not None
		assert ctx.file.file_key == 'AbCdEfGhIj'
		assert ctx.components
		assert ctx.tokens
		cached = await service.get_context()
		assert cached.cache.get('hit')

	asyncio.run(_run())
	clear_pat()
