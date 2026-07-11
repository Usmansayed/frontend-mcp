"""SEO audit orchestrator — planning → collection → graph → cross-analysis → recommendations."""
from __future__ import annotations

from navigation.seo_intelligence.analysis.cross_analyzer import run_cross_analysis
from navigation.seo_intelligence.knowledge.graph.store import SeoKnowledgeGraphStore
from navigation.seo_intelligence.models import SeoAuditRequest, SeoAuditResult
from navigation.seo_intelligence.planning.planner import SeoAuditPlanner
from navigation.seo_intelligence.providers.manager import SeoProviderManager
from navigation.seo_intelligence.recommendations.engine import build_recommendations
from navigation.seo_intelligence.registry import SeoProviderRegistry
from navigation.seo_intelligence.verification.loop import build_verification_plan


class SeoAuditOrchestrator:
	def __init__(
		self,
		*,
		registry: SeoProviderRegistry | None = None,
		providers: SeoProviderManager | None = None,
		graph: SeoKnowledgeGraphStore | None = None,
	) -> None:
		self._registry = registry or SeoProviderRegistry()
		self._providers = providers or SeoProviderManager()
		self._planner = SeoAuditPlanner(self._registry)
		self._graph = graph or SeoKnowledgeGraphStore()

	async def audit(self, request: SeoAuditRequest) -> SeoAuditResult:
		degraded: list[str] = []
		provider_ids = self._planner.resolve_provider_ids(request)
		self._graph.set_website(request.website_url, property_url=request.property_url)

		all_evidence = []
		connections: dict[str, str] = {}
		queried: list[str] = []

		for pid in provider_ids:
			provider = self._providers.get(pid)
			if provider is None:
				degraded.append(f'provider_not_implemented:{pid}')
				continue
			status, status_deg = await provider.connection_status(request)
			connections[pid] = status
			degraded.extend(status_deg)
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
			degraded.append('no_evidence_collected:providers_in_research_phase')

		self._graph.save()

		return SeoAuditResult(
			request=request,
			evidence=all_evidence,
			recommendations=recommendations,
			providers_queried=queried,
			connections=connections,
			cross_analysis=cross_analysis,
			verification=verification,
			degraded=sorted(set(degraded)),
			graph_summary=self._graph.summary(),
		)
