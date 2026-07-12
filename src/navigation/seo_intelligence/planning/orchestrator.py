"""SEO audit orchestrator — evidence-first pipeline (ADR-027)."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from navigation.seo_intelligence.ai_visibility import AiVisibilityAdapter
from navigation.seo_intelligence.knowledge.graph.store import SeoKnowledgeGraphStore
from navigation.seo_intelligence.models import SeoAuditRequest, SeoAuditResult
from navigation.seo_intelligence.planning.modes import provider_allowed, resolve_effective_mode
from navigation.seo_intelligence.planning.planner import SeoAuditPlanner
from navigation.seo_intelligence.providers.manager import SeoProviderManager
from navigation.seo_intelligence.reasoning.context_v2 import new_audit_id
from navigation.seo_intelligence.recommendations.pipeline import run_recommendation_pipeline
from navigation.seo_intelligence.registry import SeoProviderRegistry
from navigation.seo_intelligence.setup.companion_services import auto_start_enabled, ensure_companions_ready
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
		mode = resolve_effective_mode(request)
		audit_id = new_audit_id()
		previous_audit_id = self._graph.latest_audit_id()
		self._graph.set_website(request.website_url, property_url=request.property_url)

		if auto_start_enabled() and os.environ.get('SEO_SKIP_COMPANION_BOOTSTRAP', '').strip().lower() not in {
			'1',
			'true',
			'yes',
		}:
			_, companion_notes = await ensure_companions_ready()
			degraded.extend(companion_notes)

		connections = await self._probe_connections(request)
		capability_routes, provider_ids = self._planner.build_plan(request, connections)

		if request.providers:
			provider_ids = [
				pid for pid in request.providers
				if self._registry.get(pid) and provider_allowed(pid, mode)
			]

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

			evidence, collect_deg = await provider.collect(request)
			degraded.extend(collect_deg)
			queried.append(pid)
			for item in evidence:
				self._graph.upsert_evidence(item, base_url=request.website_url)
			all_evidence.extend(evidence)

		if request.include_ai_visibility and all_evidence:
			ai_evidence, ai_deg = AiVisibilityAdapter().derive(
				all_evidence,
				base_url=request.website_url,
			)
			degraded.extend(ai_deg)
			for item in ai_evidence:
				self._graph.upsert_evidence(item, base_url=request.website_url)
			all_evidence.extend(ai_evidence)
			if ai_evidence and 'ai-visibility' not in queried:
				queried.append('ai-visibility')

		graph_data = self._graph.load()
		verification_history = graph_data.get('verification') or {}

		recommendations: list = []
		cross_analysis: list[dict] = []
		reasoning_context_v2: dict = {}
		verification: dict = {}

		if all_evidence and (request.include_recommendations or request.include_cross_analysis):
			snapshot_diff = None
			if previous_audit_id:
				snapshot_diff = self._graph.build_snapshot_diff(audit_id, previous_audit_id)

			recommendations, cross_analysis, reasoning_context_v2 = run_recommendation_pipeline(
				all_evidence,
				audit_id=audit_id,
				mode=mode,
				website_url=request.website_url,
				repo_root=request.repo_root,
				scan_id=request.scan_id,
				providers=connections,
				graph_summary=self._graph.summary(),
				verification_history=verification_history,
				snapshot_diff=snapshot_diff,
				previous_audit_id=previous_audit_id,
				include_recommendations=request.include_recommendations,
				ai_reasoning=request.ai_reasoning,
				include_ai_visibility=request.include_ai_visibility,
			)
			for rec in recommendations:
				self._graph.upsert_recommendation(rec)
			if request.include_recommendations:
				verification = build_verification_plan(recommendations)
			ai_meta = reasoning_context_v2.get('ai_reasoning') or {}
			if ai_meta.get('degraded'):
				degraded.extend(list(ai_meta.get('degraded') or []))

		if not all_evidence:
			degraded.append('no_evidence_collected:configure_providers_or_credentials')

		self._graph.save_audit_snapshot(
			audit_id,
			evidence=all_evidence,
			recommendations=recommendations,
			reasoning_context_v2=reasoning_context_v2,
			mode=mode.value,
			providers_queried=queried,
		)
		self._graph.save()

		return SeoAuditResult(
			request=request,
			audit_id=audit_id,
			mode=mode.value,
			evidence=all_evidence,
			recommendations=recommendations,
			providers_queried=queried,
			capability_routes=capability_routes,
			connections=connections,
			cross_analysis=cross_analysis,
			reasoning_context=reasoning_context_v2,
			verification=verification,
			degraded=sorted(set(degraded)),
			graph_summary=self._graph.summary(),
		)
