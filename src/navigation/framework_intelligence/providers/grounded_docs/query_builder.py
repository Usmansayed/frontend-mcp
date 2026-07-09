"""Build version-aware search queries from project metadata."""
from __future__ import annotations

from ...models import ProjectMetadata


def build_search_query(metadata: ProjectMetadata, topic: str) -> str:
	"""Enrich topic with factual project metadata (no framework how-to knowledge)."""
	parts = [topic.strip()]
	if metadata.language:
		parts.append(f'Language: {metadata.language}')
	if metadata.build_tool:
		parts.append(f'Build tool: {metadata.build_tool}')
	if metadata.router_mode:
		parts.append(f'Router: {metadata.router_mode}')
	if metadata.rendering_mode:
		parts.append(f'Rendering: {metadata.rendering_mode}')
	if metadata.is_monorepo:
		parts.append('Monorepo: yes')
	if metadata.config_files:
		parts.append('Config: ' + ', '.join(metadata.config_files[:6]))
	return '. '.join(p for p in parts if p)
