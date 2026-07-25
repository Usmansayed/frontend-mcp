"""SEO provider registry — free-first catalog (research phase)."""
from __future__ import annotations

from navigation.seo_intelligence.knowledge.graph.seed import SEED_PROVIDERS
from navigation.seo_intelligence.models import SeoProviderMeta
from navigation.seo_intelligence.planning.capabilities import CAPABILITY_CATALOG


class SeoProviderRegistry:
	def __init__(self) -> None:
		self._providers: dict[str, SeoProviderMeta] = dict(SEED_PROVIDERS)

	def get(self, provider_id: str) -> SeoProviderMeta | None:
		return self._providers.get(provider_id)

	def list_providers(self) -> list[dict[str, object]]:
		return [meta.to_dict() for meta in sorted(self._providers.values(), key=lambda m: (m.priority_tier, m.provider_id))]

	def list_capabilities(self) -> list[dict[str, object]]:
		return [spec.to_dict() for spec in CAPABILITY_CATALOG.values()]

	def list_by_priority(self) -> list[str]:
		return [m.provider_id for m in sorted(self._providers.values(), key=lambda m: (m.priority_tier, m.provider_id))]
