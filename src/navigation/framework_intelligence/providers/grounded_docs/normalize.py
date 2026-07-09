"""Normalize Grounded Docs CLI responses to internal documentation format."""
from __future__ import annotations

import json
from typing import Any

from ...models import DocumentationResult, ProjectMetadata
from .registry import GroundedDocsLibrarySpec


def normalize_search_response(
	raw: Any,
	*,
	provider: str,
	spec: GroundedDocsLibrarySpec,
	metadata: ProjectMetadata,
	topic: str,
) -> DocumentationResult:
	content, citations, snippets = _extract_content(raw)
	library_id = _library_id(spec, metadata)
	title = spec.display_name
	summary = (
		f'{title} {metadata.framework_version or ""} docs for "{topic}" '
		f'via {provider} ({library_id}); {len(content.split())} words'
	).strip()
	return DocumentationResult(
		provider=provider,
		library_id=library_id,
		title=title,
		content=content,
		summary=summary,
		citations=citations,
		snippets=snippets,
	)

def _library_id(spec: GroundedDocsLibrarySpec, metadata: ProjectMetadata) -> str:
	if metadata.framework_version:
		return f'{spec.library}@{metadata.framework_version}'
	return spec.library


def _extract_content(raw: Any) -> tuple[str, list[str], list[dict[str, Any]]]:
	if isinstance(raw, str):
		return raw, [], []

	if isinstance(raw, dict):
		for key in ('content', 'text', 'answer', 'markdown'):
			val = raw.get(key)
			if isinstance(val, str) and val.strip():
				return val, _citations_from_dict(raw), _snippets_from_dict(raw)

		results = raw.get('results') or raw.get('snippets') or raw.get('matches') or raw.get('documents')
		if isinstance(results, list):
			return _join_results(results)

	if isinstance(raw, list):
		return _join_results(raw)

	return json.dumps(raw, indent=2, default=str), [], []


def _join_results(results: list[Any]) -> tuple[str, list[str], list[dict[str, Any]]]:
	parts: list[str] = []
	citations: list[str] = []
	snippets: list[dict[str, Any]] = []
	for item in results[:12]:
		if isinstance(item, str):
			parts.append(item)
			continue
		if not isinstance(item, dict):
			continue
		snippets.append(item)
		body = item.get('content') or item.get('text') or item.get('snippet') or item.get('body')
		if body:
			parts.append(str(body))
		url = item.get('url') or item.get('source') or item.get('path')
		if url:
			citations.append(str(url))
	return '\n\n'.join(parts), citations, snippets


def _citations_from_dict(raw: dict[str, Any]) -> list[str]:
	out: list[str] = []
	for key in ('url', 'source', 'library'):
		val = raw.get(key)
		if val:
			out.append(str(val))
	return out


def _snippets_from_dict(raw: dict[str, Any]) -> list[dict[str, Any]]:
	results = raw.get('results') or raw.get('snippets')
	return list(results) if isinstance(results, list) else []
