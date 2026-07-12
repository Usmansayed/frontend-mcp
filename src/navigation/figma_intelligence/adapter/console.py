"""Figma Console MCP adapter — clean internal API hiding MCP tool names."""
from __future__ import annotations

import re
from typing import Any

from navigation.figma_intelligence.providers.figma_console.client import FigmaConsoleMcpClient


_FILE_KEY_RE = re.compile(r'figma\.com/(?:file|design)/([a-zA-Z0-9]+)')


def parse_file_key(value: str) -> str:
	raw = value.strip()
	if not raw:
		return ''
	match = _FILE_KEY_RE.search(raw)
	if match:
		return match.group(1)
	if re.fullmatch(r'[a-zA-Z0-9]{10,}', raw):
		return raw
	return ''


class FigmaConsoleAdapter:
	"""Adapter over southleft/figma-console-mcp — rest of MCP never imports tool names."""

	def __init__(self, *, client: FigmaConsoleMcpClient | None = None) -> None:
		self._client = client or FigmaConsoleMcpClient()
		self._degraded: list[str] = []

	def consume_degraded(self) -> list[str]:
		out = list(self._degraded)
		self._degraded = []
		return out

	async def connect(self) -> dict[str, Any]:
		payload, degraded = await self._client.call_tool('figma_get_status', {})
		self._degraded.extend(degraded)
		return payload if isinstance(payload, dict) else {}

	async def list_files(self, *, known_files: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
		files = list(known_files or [])
		status = await self.connect()
		current = _current_file_from_status(status)
		if current and not any(f.get('file_key') == current.get('file_key') for f in files):
			files.insert(0, current)
		return files

	async def get_current_file(self, *, file_key: str = '', file_url: str = '') -> dict[str, Any] | None:
		key = file_key or parse_file_key(file_url)
		if not key and file_url:
			await self.navigate(file_url=file_url)
			status = await self.connect()
			key = parse_file_key(str(status.get('fileKey') or status.get('file_key') or ''))
		if not key:
			status = await self.connect()
			key = str(status.get('fileKey') or status.get('file_key') or '').strip()
		if not key:
			self._degraded.append('figma_no_active_file')
			return None
		payload, degraded = await self._client.call_tool('figma_get_file_data', {'fileKey': key})
		self._degraded.extend(degraded)
		if isinstance(payload, dict):
			payload.setdefault('file_key', key)
		return payload if isinstance(payload, dict) else None

	async def navigate(self, *, file_url: str = '', file_key: str = '') -> dict[str, Any] | None:
		target = file_url.strip() or file_key.strip()
		if not target:
			self._degraded.append('figma_navigate_target_required')
			return None
		args: dict[str, Any] = {}
		if file_url.strip():
			args['url'] = file_url.strip()
		else:
			args['fileKey'] = file_key.strip()
		payload, degraded = await self._client.call_tool('figma_navigate', args)
		self._degraded.extend(degraded)
		return payload if isinstance(payload, dict) else None

	async def get_pages(self, *, file_key: str) -> list[dict[str, Any]]:
		file_data = await self.get_current_file(file_key=file_key)
		if not file_data:
			return []
		return _as_node_list(file_data.get('pages') or file_data.get('document', {}).get('children'))

	async def get_frames(self, *, file_key: str, page_id: str = '') -> list[dict[str, Any]]:
		pages = await self.get_pages(file_key=file_key)
		frames: list[dict[str, Any]] = []
		for page in pages:
			pid = str(page.get('id') or page.get('page_id') or '')
			if page_id and pid != page_id:
				continue
			for child in _as_node_list(page.get('children') or page.get('frames')):
				if _is_frame_like(child):
					frames.append(child)
		return frames

	async def get_components(self, *, file_key: str) -> list[dict[str, Any]]:
		payload, degraded = await self._client.call_tool(
			'figma_get_library_components',
			{'fileKey': file_key},
		)
		self._degraded.extend(degraded)
		if payload is None:
			kit, more = await self._client.call_tool('figma_get_design_system_kit', {'fileKey': file_key})
			self._degraded.extend(more)
			if isinstance(kit, dict):
				return _as_node_list(kit.get('components') or kit.get('componentSets'))
			return []
		return _extract_component_list(payload)

	async def get_styles(self, *, file_key: str) -> list[dict[str, Any]]:
		payload, degraded = await self._client.call_tool('figma_get_styles', {'fileKey': file_key})
		self._degraded.extend(degraded)
		if isinstance(payload, dict):
			return _as_node_list(payload.get('styles') or payload.get('meta', {}).get('styles') or payload)
		return _as_node_list(payload)

	async def get_variables(self, *, file_key: str) -> list[dict[str, Any]]:
		payload, degraded = await self._client.call_tool('figma_get_variables', {'fileKey': file_key})
		self._degraded.extend(degraded)
		if isinstance(payload, dict):
			return _as_node_list(
				payload.get('variables')
				or payload.get('variableCollections')
				or payload.get('collections')
			)
		return _as_node_list(payload)

	async def get_tokens(self, *, file_key: str) -> list[dict[str, Any]]:
		payload, degraded = await self._client.call_tool('figma_get_token_values', {'fileKey': file_key})
		self._degraded.extend(degraded)
		if payload is not None:
			return _extract_token_list(payload)
		vars_payload = await self.get_variables(file_key=file_key)
		return [{'name': v.get('name', ''), 'value': v, 'source': 'variables'} for v in vars_payload]

	async def get_selection(self) -> dict[str, Any]:
		status = await self.connect()
		selection = status.get('selection') or status.get('selectedNodes') or []
		if isinstance(selection, dict):
			return selection
		if isinstance(selection, list):
			return {'node_ids': [str(n.get('id') if isinstance(n, dict) else n) for n in selection]}
		node_ids = status.get('selectionNodeIds') or status.get('selection_node_ids') or []
		return {'node_ids': [str(n) for n in node_ids if n]}


def _current_file_from_status(status: dict[str, Any]) -> dict[str, str]:
	key = str(status.get('fileKey') or status.get('file_key') or '').strip()
	name = str(status.get('fileName') or status.get('file_name') or status.get('name') or '').strip()
	url = str(status.get('fileUrl') or status.get('file_url') or status.get('url') or '').strip()
	if not key and not url:
		return {}
	return {'file_key': key, 'file_name': name, 'file_url': url}


def _as_node_list(value: Any) -> list[dict[str, Any]]:
	if isinstance(value, list):
		return [item for item in value if isinstance(item, dict)]
	if isinstance(value, dict):
		return [{'id': k, **v} if isinstance(v, dict) else {'id': k, 'value': v} for k, v in value.items()]
	return []


def _is_frame_like(node: dict[str, Any]) -> bool:
	kind = str(node.get('type') or node.get('kind') or '').upper()
	return kind in {'FRAME', 'COMPONENT', 'COMPONENT_SET', 'SECTION', 'GROUP'} or bool(
		node.get('width') and node.get('height')
	)


def _extract_component_list(payload: Any) -> list[dict[str, Any]]:
	if isinstance(payload, list):
		return [item for item in payload if isinstance(item, dict)]
	if isinstance(payload, dict):
		for key in ('components', 'componentSets', 'items', 'libraryComponents'):
			items = payload.get(key)
			if items:
				return _as_node_list(items)
	return []


def _extract_token_list(payload: Any) -> list[dict[str, Any]]:
	if isinstance(payload, list):
		return [item for item in payload if isinstance(item, dict)]
	if isinstance(payload, dict):
		for key in ('tokens', 'values', 'tokenValues', 'items'):
			items = payload.get(key)
			if items:
				return _as_node_list(items)
		return _as_node_list(payload)
	return []
