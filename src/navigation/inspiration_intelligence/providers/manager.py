"""Provider manager — priority inspiration backends with early-stop discovery."""
from __future__ import annotations

from navigation.inspiration_intelligence.planning.search_planner import DEFAULT_PROVIDER_PRIORITY
from navigation.inspiration_intelligence.providers.dribbble.provider import DribbbleProvider
from navigation.inspiration_intelligence.providers.protocol import InspirationProvider
from navigation.inspiration_intelligence.providers.site_factory import (
	build_awwwards_provider,
	build_behance_provider,
	build_godly_provider,
	build_landbook_provider,
	build_onepagelove_provider,
	build_siteinspire_provider,
)

HIGH_CONFIDENCE_SCORE = 0.55
PRODUCTION_MIN_CANDIDATES = 1

# Rescue order when full cascade returns empty — most reliable sources first
RESCUE_PROVIDER_ORDER: list[str] = ['onepagelove', 'behance', 'dribbble']


def min_high_confidence_hits() -> int:
	from navigation.inspiration_intelligence.browser.policy import is_fast_mode

	return 2 if is_fast_mode() else 3


class InspirationProviderRegistry:
	def __init__(self) -> None:
		self._providers: dict[str, InspirationProvider] = {
			'dribbble': DribbbleProvider(),
			'behance': build_behance_provider(),
			'onepagelove': build_onepagelove_provider(),
			'awwwards': build_awwwards_provider(),
			'siteinspire': build_siteinspire_provider(),
			'godly': build_godly_provider(),
			'land-book': build_landbook_provider(),
		}

	def get(self, provider_id: str) -> InspirationProvider | None:
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

	def resolve_chain(self, preference: str | None = None) -> list[InspirationProvider]:
		order = list(DEFAULT_PROVIDER_PRIORITY)
		if preference and preference in self._providers:
			order = [preference] + [pid for pid in order if pid != preference]
		return [self._providers[pid] for pid in order if pid in self._providers]
