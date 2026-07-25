"""Community Discovery Adapter — public search without PAT."""
from __future__ import annotations

from navigation.figma_intelligence.discovery.community_adapter.backends.catalog import CatalogBackend
from navigation.figma_intelligence.discovery.community_adapter.backends.http import HttpCommunityBackend
from navigation.figma_intelligence.discovery.community_adapter.models import CommunityDiscoveryHit
from navigation.figma_intelligence.models import CommunitySearchPlan, PlannedCommunityQuery


class CommunityDiscoveryService:
	"""Runs Community Intelligence queries against public discovery backends.

	Never invokes Figma Console MCP or FIGMA_ACCESS_TOKEN.
	"""

	def __init__(
		self,
		*,
		catalog: CatalogBackend | None = None,
		http: HttpCommunityBackend | None = None,
	) -> None:
		self._catalog = catalog or CatalogBackend()
		self._http = http or HttpCommunityBackend()

	async def discover(
		self,
		plan: CommunitySearchPlan,
		*,
		max_results: int,
	) -> tuple[list[CommunityDiscoveryHit], list[str]]:
		queries = plan.executable_queries or plan.planned_queries[:12]
		if not queries:
			return [], ['community_plan_empty']

		degraded: list[str] = []
		merged: dict[str, CommunityDiscoveryHit] = {}

		# HTTP first when configured (future Community endpoint).
		if self._http.enabled():
			for query in queries:
				hits, deg = await self._http.search(query, max_results=max_results)
				degraded.extend(deg)
				_merge_hits(merged, hits)
				if len(merged) >= max_results:
					break

		# Catalog fallback — always available, no PAT.
		if len(merged) < max_results:
			for query in queries:
				hits, deg = await self._catalog.search(query, max_results=max_results)
				degraded.extend(deg)
				_merge_hits(merged, hits)
				if len(merged) >= max_results:
					break

		if not merged:
			degraded.append('community_discovery_empty')

		ranked = sorted(merged.values(), key=lambda h: h.discovery_score, reverse=True)
		return ranked[:max_results], list(dict.fromkeys(degraded))

	def list_backends(self) -> list[dict[str, object]]:
		return [
			{'backend_id': self._catalog.backend_id, 'enabled': True},
			{'backend_id': self._http.backend_id, 'enabled': self._http.enabled()},
		]


def _merge_hits(store: dict[str, CommunityDiscoveryHit], hits: list[CommunityDiscoveryHit]) -> None:
	for hit in hits:
		existing = store.get(hit.hit_id)
		if existing is None or hit.discovery_score > existing.discovery_score:
			store[hit.hit_id] = hit
