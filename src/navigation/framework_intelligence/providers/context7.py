"""Context7 documentation provider."""
from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ..models import ProjectMetadata, ResolvedLibrary

_API_BASE = 'https://context7.com/api/v2'


class Context7Error(Exception):
	pass


class Context7Provider:
	name = 'context7'

	def __init__(self, *, api_key: str | None = None, timeout_s: int = 30) -> None:
		self._api_key = api_key or os.environ.get('CONTEXT7_API_KEY', '').strip() or None
		self._timeout_s = timeout_s

	def _headers(self) -> dict[str, str]:
		headers = {'Accept': 'application/json', 'User-Agent': 'frontend-perception-mcp/0.9'}
		if self._api_key:
			headers['Authorization'] = f'Bearer {self._api_key}'
		return headers

	def _request_json(self, path: str, params: dict[str, str]) -> Any:
		query = urllib.parse.urlencode(params)
		url = f'{_API_BASE}{path}?{query}'
		req = urllib.request.Request(url, headers=self._headers(), method='GET')
		try:
			with urllib.request.urlopen(req, timeout=self._timeout_s) as resp:
				raw = resp.read().decode('utf-8')
		except urllib.error.HTTPError as exc:
			body = exc.read().decode('utf-8', errors='replace')
			raise Context7Error(f'Context7 HTTP {exc.code}: {body[:300]}') from exc
		except Exception as exc:
			raise Context7Error(str(exc)) from exc
		try:
			return json.loads(raw)
		except json.JSONDecodeError as exc:
			raise Context7Error('Context7 returned non-JSON response') from exc

	def _build_search_query(self, metadata: ProjectMetadata, topic: str) -> str:
		parts = [topic.strip()]
		if metadata.framework:
			parts.append(f'Framework: {metadata.framework}')
		if metadata.framework_version:
			parts.append(f'Version: {metadata.framework_version}')
		if metadata.language:
			parts.append(f'Language: {metadata.language}')
		if metadata.build_tool:
			parts.append(f'Build tool: {metadata.build_tool}')
		if metadata.router_mode:
			parts.append(f'Router: {metadata.router_mode}')
		if metadata.rendering_mode:
			parts.append(f'Rendering: {metadata.rendering_mode}')
		if metadata.config_files:
			parts.append('Configs: ' + ', '.join(metadata.config_files[:6]))
		return '. '.join(parts)

	def _pick_library(self, libraries: list[dict[str, Any]], metadata: ProjectMetadata) -> dict[str, Any] | None:
		if not libraries:
			return None
		target = (metadata.context7_library_name or metadata.framework or '').lower()
		for item in libraries:
			title = str(item.get('title') or item.get('name') or '').lower()
			lib_id = str(item.get('id') or '').lower()
			if target and (target in title or target.replace('.', '') in lib_id):
				return item
		return libraries[0]

	def _versioned_library_id(self, library_id: str, metadata: ProjectMetadata) -> str:
		if not metadata.framework_version or '/' not in library_id:
			return library_id
		if library_id.count('/') >= 3:
			return library_id
		return f'{library_id}/v{metadata.framework_version}'

	async def resolve_library(self, metadata: ProjectMetadata, *, topic: str) -> ResolvedLibrary | None:
		if not metadata.context7_library_name and not metadata.framework:
			return None
		library_name = metadata.context7_library_name or metadata.framework or ''
		query = self._build_search_query(metadata, topic)
		data = await asyncio.to_thread(
			self._request_json,
			'/libs/search',
			{'libraryName': library_name, 'query': query},
		)
		libraries = data if isinstance(data, list) else data.get('results') or data.get('libraries') or []
		if not isinstance(libraries, list) or not libraries:
			return None
		best = self._pick_library(libraries, metadata)
		if best is None:
			return None
		lib_id = str(best.get('id') or '')
		if not lib_id:
			return None
		versions_raw = best.get('versions') or []
		versions = [str(v) for v in versions_raw] if isinstance(versions_raw, list) else []
		return ResolvedLibrary(
			provider=self.name,
			library_id=self._versioned_library_id(lib_id, metadata),
			title=str(best.get('title') or best.get('name') or library_name),
			description=str(best.get('description') or ''),
			versions=versions,
		)

	async def fetch_documentation(
		self,
		*,
		library_id: str,
		topic: str,
		metadata: ProjectMetadata,
	) -> str:
		query = self._build_search_query(metadata, topic)
		data = await asyncio.to_thread(
			self._request_json,
			'/context',
			{'libraryId': library_id, 'query': query},
		)
		if isinstance(data, str):
			return data
		if isinstance(data, dict):
			for key in ('content', 'context', 'text', 'answer'):
				val = data.get(key)
				if isinstance(val, str) and val.strip():
					return val
			snippets = data.get('snippets') or data.get('results')
			if isinstance(snippets, list):
				parts: list[str] = []
				for item in snippets[:8]:
					if isinstance(item, str):
						parts.append(item)
					elif isinstance(item, dict):
						body = item.get('content') or item.get('text') or item.get('snippet')
						if body:
							parts.append(str(body))
				if parts:
					return '\n\n'.join(parts)
		return json.dumps(data, indent=2, default=str)
