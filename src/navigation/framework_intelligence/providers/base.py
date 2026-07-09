"""Provider interface — MCP never depends on Context7 directly."""
from __future__ import annotations

from typing import Protocol

from ..models import ProjectMetadata, ResolvedLibrary


class KnowledgeProvider(Protocol):
	name: str

	async def resolve_library(self, metadata: ProjectMetadata, *, topic: str) -> ResolvedLibrary | None:
		"""Map detected project metadata to a documentation library."""

	async def fetch_documentation(
		self,
		*,
		library_id: str,
		topic: str,
		metadata: ProjectMetadata,
	) -> str:
		"""Fetch documentation content for a topic."""
