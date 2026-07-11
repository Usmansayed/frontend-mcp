"""Resource provider registry — commercial-only by default."""
from __future__ import annotations

from navigation.resource_intelligence.graph.seed import SEED_PROVIDERS
from navigation.resource_intelligence.models import ResourceProviderMeta


def is_commercial_provider(meta: ResourceProviderMeta) -> bool:
	"""True when provider allows commercial use (automation bans do not exclude)."""
	return bool(meta.license.commercial_use)


class ResourceProviderRegistry:
	def __init__(self) -> None:
		self._providers: dict[str, ResourceProviderMeta] = dict(SEED_PROVIDERS)

	def get(self, provider_id: str) -> ResourceProviderMeta | None:
		return self._providers.get(provider_id)

	def list_providers(
		self,
		*,
		commercial_only: bool = True,
		include_non_commercial: bool = False,
	) -> list[dict[str, object]]:
		out: list[dict[str, object]] = []
		for meta in self._providers.values():
			if meta.excluded and not include_non_commercial:
				continue
			if commercial_only and not is_commercial_provider(meta):
				continue
			out.append(meta.to_dict())
		return out

	def list_excluded(self) -> list[dict[str, object]]:
		"""Providers excluded because commercial use is not allowed."""
		return [m.to_dict() for m in self._providers.values() if m.excluded or not m.license.commercial_use]
