"""Coordination layer — cache vs refresh vs MCP query."""
from __future__ import annotations

from typing import Any

from navigation.figma_intelligence.adapter.console import FigmaConsoleAdapter, parse_file_key
from navigation.figma_intelligence.cache.store import FigmaDesignCache
from navigation.figma_intelligence.connection.manager import FigmaConnectionManager
from navigation.figma_intelligence.context_models import FigmaDesignContext
from navigation.figma_intelligence.normalize.context import normalize_design_context
from navigation.figma_intelligence.session.manager import FigmaSessionManager


class FigmaCoordinationLayer:
	def __init__(
		self,
		*,
		connection: FigmaConnectionManager | None = None,
		session: FigmaSessionManager | None = None,
		adapter: FigmaConsoleAdapter | None = None,
		cache: FigmaDesignCache | None = None,
	) -> None:
		self._connection = connection or FigmaConnectionManager()
		self._session = session or FigmaSessionManager()
		self._adapter = adapter or FigmaConsoleAdapter(client=self._connection.client())
		self._cache = cache or FigmaDesignCache()

	async def get_design_context(self, *, refresh: bool = False) -> FigmaDesignContext:
		state = self._session.load()
		session_dict = state.to_dict()
		degraded: list[str] = []

		if not refresh:
			cached = self._cache.get(session_dict)
			if cached:
				cached = dict(cached)
				cached['cache'] = {**self._cache.meta(session_dict), 'hit': True}
				cached['connected'] = self._connection.status().get('connected', False)
				return _context_from_dict(cached)

		if not self._connection.is_configured():
			degraded.append('figma_not_connected')
			return normalize_design_context(
				connected=False,
				session=session_dict,
				file_payload=None,
				components=[],
				variables=[],
				styles=[],
				tokens=[],
				selection={},
				known_files=state.known_files,
				cache_meta=self._cache.meta(session_dict),
				degraded=degraded,
			)

		file_key = state.file_key or parse_file_key(state.file_url)
		if state.file_url and not file_key:
			await self._adapter.navigate(file_url=state.file_url)
			degraded.extend(self._adapter.consume_degraded())
			status = await self._adapter.connect()
			file_key = parse_file_key(str(status.get('fileKey') or status.get('file_key') or state.file_url))

		if not file_key:
			status = await self._adapter.connect()
			degraded.extend(self._adapter.consume_degraded())
			file_key = str(status.get('fileKey') or status.get('file_key') or '').strip()
			if file_key:
				self._session.set_active_file(file_key=file_key, file_name=str(status.get('fileName') or ''))
				state = self._session.load()
				session_dict = state.to_dict()

		file_payload = None
		components: list[dict[str, Any]] = []
		variables: list[dict[str, Any]] = []
		styles: list[dict[str, Any]] = []
		tokens: list[dict[str, Any]] = []

		if file_key:
			file_payload = await self._adapter.get_current_file(file_key=file_key, file_url=state.file_url)
			degraded.extend(self._adapter.consume_degraded())
			components = await self._adapter.get_components(file_key=file_key)
			degraded.extend(self._adapter.consume_degraded())
			variables = await self._adapter.get_variables(file_key=file_key)
			degraded.extend(self._adapter.consume_degraded())
			styles = await self._adapter.get_styles(file_key=file_key)
			degraded.extend(self._adapter.consume_degraded())
			tokens = await self._adapter.get_tokens(file_key=file_key)
			degraded.extend(self._adapter.consume_degraded())

		selection = await self._adapter.get_selection()
		degraded.extend(self._adapter.consume_degraded())

		context = normalize_design_context(
			connected=True,
			session=session_dict,
			file_payload=file_payload,
			components=components,
			variables=variables,
			styles=styles,
			tokens=tokens,
			selection=selection,
			known_files=state.known_files,
			cache_meta=self._cache.meta(session_dict),
			degraded=degraded,
		)
		self._cache.put(session_dict, context.to_dict())
		return context

	async def list_files(self) -> list[dict[str, str]]:
		state = self._session.load()
		return await self._adapter.list_files(known_files=state.known_files)

	def invalidate_cache(self) -> None:
		self._cache.invalidate()


def _context_from_dict(data: dict[str, Any]) -> FigmaDesignContext:
	from navigation.figma_intelligence.context_models import (
		FigmaComponentRef,
		FigmaFileRef,
		FigmaFrameRef,
		FigmaPageRef,
		FigmaSelectionRef,
		FigmaStyleRef,
		FigmaTokenRef,
		FigmaVariableRef,
		FigmaVariantRef,
	)

	file = None
	raw_file = data.get('file')
	if isinstance(raw_file, dict):
		pages = [
			FigmaPageRef(
				page_id=str(p.get('page_id') or ''),
				name=str(p.get('name') or ''),
				frames=[
					FigmaFrameRef(
						frame_id=str(f.get('frame_id') or ''),
						name=str(f.get('name') or ''),
						page_id=str(f.get('page_id') or ''),
						width=f.get('width'),
						height=f.get('height'),
						metadata=dict(f.get('metadata') or {}),
					)
					for f in (p.get('frames') or [])
					if isinstance(f, dict)
				],
			)
			for p in (raw_file.get('pages') or [])
			if isinstance(p, dict)
		]
		file = FigmaFileRef(
			file_key=str(raw_file.get('file_key') or ''),
			name=str(raw_file.get('name') or ''),
			url=str(raw_file.get('url') or ''),
			last_modified=str(raw_file.get('last_modified') or ''),
			pages=pages,
			metadata=dict(raw_file.get('metadata') or {}),
		)

	sel = data.get('selection') or {}
	selection = FigmaSelectionRef(
		node_ids=[str(n) for n in (sel.get('node_ids') or [])],
		nodes=[n for n in (sel.get('nodes') or []) if isinstance(n, dict)],
		page_id=str(sel.get('page_id') or ''),
		frame_id=str(sel.get('frame_id') or ''),
	)

	return FigmaDesignContext(
		connected=bool(data.get('connected')),
		file=file,
		active_page_id=str(data.get('active_page_id') or ''),
		active_frame_id=str(data.get('active_frame_id') or ''),
		selection=selection,
		components=[
			FigmaComponentRef(
				component_id=str(c.get('component_id') or ''),
				name=str(c.get('name') or ''),
				key=str(c.get('key') or ''),
				description=str(c.get('description') or ''),
				variants=[
					FigmaVariantRef(
						variant_id=str(v.get('variant_id') or ''),
						name=str(v.get('name') or ''),
						properties={str(k): str(val) for k, val in (v.get('properties') or {}).items()},
					)
					for v in (c.get('variants') or [])
					if isinstance(v, dict)
				],
				metadata=dict(c.get('metadata') or {}),
			)
			for c in (data.get('components') or [])
			if isinstance(c, dict)
		],
		variables=[
			FigmaVariableRef(
				variable_id=str(v.get('variable_id') or ''),
				name=str(v.get('name') or ''),
				type=str(v.get('type') or ''),
				values_by_mode=dict(v.get('values_by_mode') or {}),
				metadata=dict(v.get('metadata') or {}),
			)
			for v in (data.get('variables') or [])
			if isinstance(v, dict)
		],
		styles=[
			FigmaStyleRef(
				style_id=str(s.get('style_id') or ''),
				name=str(s.get('name') or ''),
				kind=str(s.get('kind') or ''),
				metadata=dict(s.get('metadata') or {}),
			)
			for s in (data.get('styles') or [])
			if isinstance(s, dict)
		],
		tokens=[
			FigmaTokenRef(
				token_id=str(t.get('token_id') or ''),
				name=str(t.get('name') or ''),
				value=str(t.get('value') or ''),
				collection=str(t.get('collection') or ''),
				mode=str(t.get('mode') or ''),
				metadata=dict(t.get('metadata') or {}),
			)
			for t in (data.get('tokens') or [])
			if isinstance(t, dict)
		],
		assets=list(data.get('assets') or []),
		session=dict(data.get('session') or {}),
		cache=dict(data.get('cache') or {}),
		degraded=list(data.get('degraded') or []),
	)
