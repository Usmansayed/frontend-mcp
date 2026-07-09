"""Documentation provider protocol — MCP stays provider-agnostic."""
from __future__ import annotations

from typing import Protocol

from ..models import DocumentationResult, ProjectMetadata


class DocumentationProviderError(Exception):
	"""Raised when an external documentation provider fails."""


class DocumentationProvider(Protocol):
	name: str

	async def fetch_documentation(
		self,
		metadata: ProjectMetadata,
		*,
		topic: str,
	) -> DocumentationResult:
		"""Resolve sources if needed, fetch docs for one topic, return normalized result."""
