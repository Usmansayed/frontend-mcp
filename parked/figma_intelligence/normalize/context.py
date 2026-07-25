"""Normalize Figma Console payloads into internal context models."""
from __future__ import annotations

from typing import Any

from navigation.figma_intelligence.context_models import (
	FigmaComponentRef,
	FigmaDesignContext,
	FigmaFileRef,
	FigmaFrameRef,
	FigmaPageRef,
	FigmaSelectionRef,
	FigmaStyleRef,
	FigmaTokenRef,
	FigmaVariableRef,
	FigmaVariantRef,
)


def normalize_design_context(
	*,
	connected: bool,
	session: dict[str, Any],
	file_payload: dict[str, Any] | None,
	components: list[dict[str, Any]],
	variables: list[dict[str, Any]],
	styles: list[dict[str, Any]],
	tokens: list[dict[str, Any]],
	selection: dict[str, Any],
	known_files: list[dict[str, str]],
	cache_meta: dict[str, Any] | None = None,
	degraded: list[str] | None = None,
) -> FigmaDesignContext:
	file_ref = _normalize_file(session, file_payload, known_files)
	pages = file_ref.pages if file_ref else []
	active_page_id = str(session.get('active_page_id') or '')
	active_frame_id = str(session.get('active_frame_id') or '')

	if not active_page_id and pages:
		active_page_id = pages[0].page_id

	return FigmaDesignContext(
		connected=connected,
		file=file_ref,
		active_page_id=active_page_id,
		active_frame_id=active_frame_id,
		selection=_normalize_selection(selection, session),
		components=[_normalize_component(c) for c in components],
		variables=[_normalize_variable(v) for v in variables],
		styles=[_normalize_style(s) for s in styles],
		tokens=[_normalize_token(t) for t in tokens],
		session=dict(session),
		cache=dict(cache_meta or {}),
		degraded=list(degraded or []),
	)


def _normalize_file(
	session: dict[str, Any],
	payload: dict[str, Any] | None,
	known_files: list[dict[str, str]],
) -> FigmaFileRef | None:
	file_key = str(session.get('file_key') or '').strip()
	file_name = str(session.get('file_name') or '').strip()
	file_url = str(session.get('file_url') or '').strip()

	if payload:
		file_key = str(payload.get('file_key') or payload.get('fileKey') or file_key).strip()
		file_name = str(payload.get('name') or payload.get('fileName') or file_name).strip()
		file_url = str(payload.get('url') or payload.get('fileUrl') or file_url).strip()

	if not file_key:
		for entry in known_files:
			if entry.get('file_key'):
				file_key = str(entry['file_key'])
				file_name = file_name or str(entry.get('file_name') or '')
				file_url = file_url or str(entry.get('file_url') or '')
				break

	if not file_key:
		return None

	pages = _normalize_pages(payload)
	return FigmaFileRef(
		file_key=file_key,
		name=file_name,
		url=file_url,
		last_modified=str((payload or {}).get('lastModified') or (payload or {}).get('last_modified') or ''),
		pages=pages,
		metadata={'source': 'figma_console'},
	)


def _normalize_pages(payload: dict[str, Any] | None) -> list[FigmaPageRef]:
	if not payload:
		return []
	raw_pages = payload.get('pages')
	if raw_pages is None:
		doc = payload.get('document')
		if isinstance(doc, dict):
			raw_pages = doc.get('children')
	if not isinstance(raw_pages, list):
		return []

	pages: list[FigmaPageRef] = []
	for page in raw_pages:
		if not isinstance(page, dict):
			continue
		page_id = str(page.get('id') or page.get('page_id') or '')
		name = str(page.get('name') or page.get('title') or page_id)
		frames = [
			_normalize_frame(child, page_id=page_id)
			for child in (page.get('children') or page.get('frames') or [])
			if isinstance(child, dict)
		]
		pages.append(FigmaPageRef(page_id=page_id, name=name, frames=frames))
	return pages


def _normalize_frame(node: dict[str, Any], *, page_id: str) -> FigmaFrameRef:
	return FigmaFrameRef(
		frame_id=str(node.get('id') or node.get('frame_id') or ''),
		name=str(node.get('name') or ''),
		page_id=page_id,
		width=_num(node.get('width')),
		height=_num(node.get('height')),
		metadata={'type': str(node.get('type') or '')},
	)


def _normalize_component(raw: dict[str, Any]) -> FigmaComponentRef:
	variants = [
		FigmaVariantRef(
			variant_id=str(v.get('id') or ''),
			name=str(v.get('name') or ''),
			properties={str(k): str(val) for k, val in (v.get('properties') or {}).items()},
		)
		for v in (raw.get('variants') or [])
		if isinstance(v, dict)
	]
	return FigmaComponentRef(
		component_id=str(raw.get('id') or raw.get('key') or raw.get('component_id') or ''),
		name=str(raw.get('name') or ''),
		key=str(raw.get('key') or ''),
		description=str(raw.get('description') or ''),
		variants=variants,
		metadata=dict(raw),
	)


def _normalize_variable(raw: dict[str, Any]) -> FigmaVariableRef:
	return FigmaVariableRef(
		variable_id=str(raw.get('id') or raw.get('variable_id') or ''),
		name=str(raw.get('name') or ''),
		type=str(raw.get('resolvedType') or raw.get('type') or ''),
		values_by_mode=dict(raw.get('valuesByMode') or raw.get('values_by_mode') or {}),
		metadata=dict(raw),
	)


def _normalize_style(raw: dict[str, Any]) -> FigmaStyleRef:
	return FigmaStyleRef(
		style_id=str(raw.get('id') or raw.get('style_id') or raw.get('key') or ''),
		name=str(raw.get('name') or ''),
		kind=str(raw.get('styleType') or raw.get('kind') or raw.get('type') or ''),
		metadata=dict(raw),
	)


def _normalize_token(raw: dict[str, Any]) -> FigmaTokenRef:
	name = str(raw.get('name') or raw.get('token') or '')
	value = raw.get('value')
	if isinstance(value, dict):
		value_str = str(value.get('value') or value)
	else:
		value_str = str(value or '')
	return FigmaTokenRef(
		token_id=str(raw.get('id') or raw.get('token_id') or name),
		name=name,
		value=value_str,
		collection=str(raw.get('collection') or raw.get('collectionName') or ''),
		mode=str(raw.get('mode') or ''),
		metadata=dict(raw),
	)


def _normalize_selection(selection: dict[str, Any], session: dict[str, Any]) -> FigmaSelectionRef:
	node_ids = [str(n) for n in (selection.get('node_ids') or selection.get('nodeIds') or []) if n]
	if not node_ids:
		node_ids = [str(n) for n in (session.get('selection_node_ids') or []) if n]
	nodes = [n for n in (selection.get('nodes') or []) if isinstance(n, dict)]
	return FigmaSelectionRef(
		node_ids=node_ids,
		nodes=nodes,
		page_id=str(selection.get('page_id') or session.get('active_page_id') or ''),
		frame_id=str(selection.get('frame_id') or session.get('active_frame_id') or ''),
	)


def _num(value: Any) -> float | None:
	try:
		return float(value) if value is not None else None
	except (TypeError, ValueError):
		return None
