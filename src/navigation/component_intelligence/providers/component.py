"""Component provider protocol — search orchestration stays provider-agnostic."""
from __future__ import annotations

from typing import Protocol

from ..models import ComponentCandidate, ComponentDetail, SearchContext


class ComponentProviderError(Exception):
	"""Raised when a component provider fails."""


class ComponentProvider(Protocol):
	name: str
	group: str
	enabled: bool

	async def search(self, context: SearchContext) -> list[ComponentCandidate]:
		"""Return normalized candidates for one search pass."""

	async def get_component(self, component_id: str) -> ComponentDetail:
		"""Fetch full component metadata by normalized id."""

	async def install(self, component_id: str) -> dict[str, object]:
		"""Install component into project (later phases)."""
