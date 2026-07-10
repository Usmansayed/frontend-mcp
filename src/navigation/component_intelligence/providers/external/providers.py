"""External component library providers (Group B) — placeholders for Phase 1."""
from __future__ import annotations

from dataclasses import dataclass

from ...models import ComponentCandidate, ComponentDetail, SearchContext
from ..component import ComponentProviderError


@dataclass(slots=True)
class PlaceholderExternalProvider:
	"""Adapter stub for non-shadcn ecosystems."""

	name: str
	library: str
	framework: str = 'react'
	enabled: bool = False
	group: str = 'external'

	async def search(self, context: SearchContext) -> list[ComponentCandidate]:
		return []

	async def get_component(self, component_id: str) -> ComponentDetail:
		raise ComponentProviderError(f'not_implemented:{self.name}')

	async def install(self, component_id: str) -> dict[str, object]:
		raise ComponentProviderError(f'not_implemented:{self.name}')


EXTERNAL_LIBRARIES: tuple[tuple[str, str], ...] = (
	('mui', 'MUI'),
	('chakra_ui', 'Chakra UI'),
	('mantine', 'Mantine'),
	('flowbite', 'Flowbite'),
	('heroui', 'HeroUI'),
	('park_ui', 'Park UI'),
	('tremor', 'Tremor'),
	('melt_ui', 'Melt UI'),
	('web_awesome', 'Web Awesome'),
	('react_aria', 'React Aria'),
)


def build_external_providers() -> list[PlaceholderExternalProvider]:
	return [
		PlaceholderExternalProvider(name=slug, library=label, enabled=False)
		for slug, label in EXTERNAL_LIBRARIES
	]
