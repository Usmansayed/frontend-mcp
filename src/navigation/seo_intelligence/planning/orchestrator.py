"""SEO audit orchestrator — capability-aware planning → collection → graph → analysis."""
from __future__ import annotations

from typing import TYPE_CHECKING

from navigation.seo_intelligence.analysis.cross_analyzer import run_cross_analysis
from navigation.seo_intelligence.knowledge.graph.store import SeoKnowledgeGraphStore
from navigation.seo_intelligence.models import SeoAuditRequest, SeoAuditResult
from navigation.seo_intelligence.planning.planner import SeoAuditPlanner
from navigation.seo_intelligence.providers.manager import SeoProviderManager
from navigation.seo_intelligence.recommendations.engine import build_recommendations
from navigation.seo_intelligence.registry import SeoProviderRegistry
from navigation.seo_intelligence.verification.loop import build_verification_plan

if TYPE_CHECKING:
	from navigation.core.scan_registry import ScanRegistry


class SeoAuditOrchestrator:
	def __init__(
		self,
		*,
		registry: SeoProviderRegistry | None = None,
		providers: SeoProviderManager | None = None,
		graph: SeoKnowledgeGraphStore | None = None,
		scan_registry: ScanRegistry | None = None,
	) -> None:
		self._registry = registry or SeoProviderRegistry()
		self._providers = providers or SeoProviderManager(scan_registry=scan_registry)
		self._planner = SeoAuditPlanner(self._registry)
		self._graph = graph or SeoKnowledgeGraphStore()

	async def _probe_connections(self, request: SeoAuditRequest) -> dict[str, str]:
		connections: dict[str, str] = {}
		for pid in self._providers.list_live_provider_ids():
			provider = self._providers.get(pid)
			if provider is None:
				continue
			status, _ = await provider.connection_status(request)
			connections[pid] = status
		return connections

	async def audit(self, request: SeoAuditRequest) -> SeoAuditResult:
		degraded: list[str] = []
		self._graph.set_website(request.website_url, property_url=request.property_url)

		connections = await self._probe_connections(request)
		capability_routes, provider_ids = self._planner.build_plan(request, connections)

		if request.providers:
			provider_ids = [pid for pid in request.providers if self._registry.get(pid)]

		all_evidence = []
		queried: list[str] = []

		for pid in provider_ids:
			provider = self._providers.get(pid)
			if provider is None:
				degraded.append(f'provider_not_implemented:{pid}')
				continue
			if connections.get(pid) == 'error':
				degraded.append(f'provider_error:{pid}')
				continue
			if connections.get(pid) == 'not_configured':
				degraded.append(f'provider_skipped_not_configured:{pid}')
				continue

			if pid == 'openseo':
				openseo_caps = [r.capability_id for r in capability_routes if r.chosen_provider == 'openseo']
				evidence, collect_deg = await provider.collect(request, capabilities=openseo_caps)
			else:
				evidence, collect_deg = await provider.collect(request)

			degraded.extend(collect_deg)
			queried.append(pid)
			for item in evidence:
				self._graph.upsert_evidence(item)
			all_evidence.extend(evidence)

		cross_analysis: list[dict] = []
		recommendations = []
		verification: dict = {}

		if request.include_cross_analysis and all_evidence:
			cross_analysis = run_cross_analysis(all_evidence)

		if request.include_recommendations:
			recommendations = build_recommendations(all_evidence, cross_analysis)
			for rec in recommendations:
				self._graph.upsert_recommendation(rec)
			verification = build_verification_plan(recommendations)

		if not all_evidence:
			degraded.append('no_evidence_collected:configure_providers_or_credentials')

		self._graph.save()

		return SeoAuditResult(
			request=request,
			evidence=all_evidence,
			recommendations=recommendations,
			providers_queried=queried,
			capability_routes=capability_routes,
			connections=connections,
			cross_analysis=cross_analysis,
			verification=verification,
			degraded=sorted(set(degraded)),
			graph_summary=self._graph.summary(),
		)
