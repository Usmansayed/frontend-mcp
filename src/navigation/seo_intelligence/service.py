"""SEO Intelligence service facade."""
from __future__ import annotations

from typing import Any

from navigation.seo_intelligence.knowledge.graph.store import SeoKnowledgeGraphStore
from navigation.seo_intelligence.models import SeoAuditRequest, SeoAuditResult
from navigation.seo_intelligence.planning.orchestrator import SeoAuditOrchestrator
from navigation.seo_intelligence.registry import SeoProviderRegistry


class SeoIntelligenceService:
	"""Orchestration layer for free-first SEO evidence and recommendations."""

	def __init__(
		self,
		*,
		registry: SeoProviderRegistry | None = None,
		orchestrator: SeoAuditOrchestrator | None = None,
		graph: SeoKnowledgeGraphStore | None = None,
	) -> None:
		self._registry = registry or SeoProviderRegistry()
		self._graph = graph or SeoKnowledgeGraphStore()
		self._orchestrator = orchestrator or SeoAuditOrchestrator(registry=self._registry, graph=self._graph)

	def list_providers(self) -> list[dict[str, object]]:
		return self._registry.list_providers()

	def graph_summary(self) -> dict[str, object]:
		return self._graph.summary()

	async def audit(self, request: SeoAuditRequest) -> SeoAuditResult:
		return await self._orchestrator.audit(request)

	def status(self) -> dict[str, Any]:
		from navigation.seo_intelligence.providers.manager import SeoProviderManager

		live = SeoProviderManager().list_live_provider_ids()
		return {
			'module': 'seo_intelligence',
			'phase': 'architecture_v1',
			'philosophy': 'free_first_orchestration_not_ahrefs',
			'providers_catalog': len(self.list_providers()),
			'providers_live_stubs': live,
			'graph': self._graph.summary(),
			'do_not_build': [
				'keyword_databases',
				'backlink_crawlers',
				'internet_scale_crawlers',
				'serp_databases',
			],
		}
