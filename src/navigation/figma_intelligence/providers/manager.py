"""Provider manager — swappable execution backends."""
from __future__ import annotations

from navigation.figma_intelligence.providers.figma_console.provider import FigmaConsoleProvider
from navigation.figma_intelligence.providers.future.provider import FutureFigmaProvider
from navigation.figma_intelligence.providers.official_figma.provider import OfficialFigmaProvider
from navigation.figma_intelligence.providers.protocol import FigmaProvider

_DEFAULT_ORDER = ('figma_console', 'official_figma', 'future')


class FigmaProviderRegistry:
	def __init__(self) -> None:
		self._providers: dict[str, FigmaProvider] = {
			FigmaConsoleProvider.provider_id: FigmaConsoleProvider(),
			OfficialFigmaProvider.provider_id: OfficialFigmaProvider(),
			FutureFigmaProvider.provider_id: FutureFigmaProvider(),
		}

	def get(self, provider_id: str) -> FigmaProvider | None:
		return self._providers.get(provider_id)

	def list_providers(self) -> list[dict[str, object]]:
		return [
			{
				'provider_id': p.provider_id,
				'display_name': p.display_name,
				'capabilities': sorted(p.capabilities),
			}
			for p in self._providers.values()
		]

	def resolve_chain(self, preference: str | None = None) -> list[FigmaProvider]:
		if preference and preference in self._providers:
			rest = [pid for pid in _DEFAULT_ORDER if pid != preference]
			return [self._providers[preference]] + [self._providers[pid] for pid in rest]
		return [self._providers[pid] for pid in _DEFAULT_ORDER if pid in self._providers]
