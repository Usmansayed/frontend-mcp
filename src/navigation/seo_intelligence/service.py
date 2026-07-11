"""SEO Intelligence service facade."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from navigation.seo_intelligence.knowledge.graph.store import SeoKnowledgeGraphStore
from navigation.seo_intelligence.models import SeoAuditRequest, SeoAuditResult
from navigation.seo_intelligence.planning.orchestrator import SeoAuditOrchestrator
from navigation.seo_intelligence.registry import SeoProviderRegistry
from navigation.seo_intelligence.verification.loop import evaluate_verification

if TYPE_CHECKING:
	from navigation.core.scan_registry import ScanRegistry


class SeoIntelligenceService:
	"""Orchestration layer for free-first SEO evidence and recommendations."""

	def __init__(
		self,
		*,
		registry: SeoProviderRegistry | None = None,
		orchestrator: SeoAuditOrchestrator | None = None,
		graph: SeoKnowledgeGraphStore | None = None,
		scan_registry: ScanRegistry | None = None,
	) -> None:
		self._registry = registry or SeoProviderRegistry()
		self._graph = graph or SeoKnowledgeGraphStore()
		self._orchestrator = orchestrator or SeoAuditOrchestrator(
			registry=self._registry,
			graph=self._graph,
			scan_registry=scan_registry,
		)

	def list_providers(self) -> list[dict[str, object]]:
		return self._registry.list_providers()

	def list_capabilities(self) -> list[dict[str, object]]:
		return self._registry.list_capabilities()

	def graph_summary(self) -> dict[str, object]:
		return self._graph.summary()

	async def audit(self, request: SeoAuditRequest) -> SeoAuditResult:
		return await self._orchestrator.audit(request)

	async def verify(
		self,
		request: SeoAuditRequest,
		*,
		baseline: SeoAuditResult | None = None,
		recommendation_ids: list[str] | None = None,
	) -> dict[str, Any]:
		"""Re-run audit and evaluate recommendation verification status."""
		current = await self.audit(request)
		if baseline is None:
			baseline = self._baseline_from_graph()
		if baseline is None:
			return {
				'ok': False,
				'error': 'baseline_audit_missing:run_perception_seo_audit_first',
				'current': current.to_dict(),
			}
		result = evaluate_verification(
			baseline=baseline,
			current=current,
			recommendation_ids=recommendation_ids or [],
		)
		for item in result.get('items') or []:
			if not isinstance(item, dict):
				continue
			rec_id = str(item.get('recommendation_id') or '')
			status = str(item.get('status') or '')
			notes = str(item.get('notes') or '')
			if rec_id and status:
				self._graph.record_verification(rec_id, status, notes=notes)
		self._graph.save()
		return {
			'ok': True,
			'verification': result,
			'current_audit': current.to_dict(),
		}

	def _baseline_from_graph(self) -> SeoAuditResult | None:
		data = self._graph.load()
		evidence_raw = data.get('evidence') or {}
		recs_raw = data.get('recommendations') or {}
		if not evidence_raw and not recs_raw:
			return None
		from navigation.seo_intelligence.models import (
			SeoEvidenceKind,
			SeoEvidenceRef,
			SeoRecommendation,
		)

		evidence = []
		for item in evidence_raw.values():
			if not isinstance(item, dict):
				continue
			evidence.append(
				SeoEvidenceRef(
					evidence_id=str(item['evidence_id']),
					provider_id=str(item['provider_id']),
					kind=SeoEvidenceKind(str(item['kind'])),
					title=str(item.get('title') or ''),
					summary=str(item.get('summary') or ''),
					url=str(item.get('url') or ''),
					page_url=str(item.get('page_url') or ''),
					metric_value=item.get('metric_value'),
					metric_unit=str(item.get('metric_unit') or ''),
					severity=str(item.get('severity') or 'info'),
					source_ref=str(item.get('source_ref') or ''),
					metadata=dict(item.get('metadata') or {}),
				)
			)
		recommendations = []
		for item in recs_raw.values():
			if not isinstance(item, dict):
				continue
			recommendations.append(
				SeoRecommendation(
					recommendation_id=str(item['recommendation_id']),
					title=str(item.get('title') or ''),
					summary=str(item.get('summary') or ''),
					priority=str(item.get('priority') or 'medium'),
					category=str(item.get('category') or ''),
					evidence_ids=list(item.get('evidence_ids') or []),
					fix_guidance=str(item.get('fix_guidance') or ''),
					verification_steps=list(item.get('verification_steps') or []),
					confidence=float(item.get('confidence') or 0.0),
					metadata=dict(item.get('metadata') or {}),
				)
			)
		website = data.get('website') or {}
		request = SeoAuditRequest(
			website_url=str(website.get('url') or ''),
			property_url=str(website.get('property_url') or ''),
		)
		return SeoAuditResult(
			request=request,
			evidence=evidence,
			recommendations=recommendations,
		)

	def status(self) -> dict[str, Any]:
		from navigation.seo_intelligence.auth.google import google_oauth_status
		from navigation.seo_intelligence.providers.librecrawl.client import base_url as librecrawl_url
		from navigation.seo_intelligence.providers.manager import SeoProviderManager
		from navigation.seo_intelligence.providers.openseo.client import resolve_mcp_url
		from navigation.frontend_quality_intelligence.audits.runner import lighthouse_available

		live = SeoProviderManager().list_live_provider_ids()
		return {
			'module': 'seo_intelligence',
			'phase': 'production_v1',
			'philosophy': 'free_first_orchestration_not_ahrefs',
			'providers_catalog': len(self.list_providers()),
			'capabilities_catalog': len(self.list_capabilities()),
			'providers_live': live,
			'integrations': {
				'google_oauth': google_oauth_status(),
				'librecrawl_configured': bool(librecrawl_url()),
				'lighthouse_available': lighthouse_available(),
				'openseo_configured': bool(resolve_mcp_url()),
			},
			'openseo': {
				'optional': True,
				'hard_dependency': False,
				'app_cost': 'free_self_hostable',
				'data_cost': 'dataforseo_pay_as_you_go',
			},
			'graph': self._graph.summary(),
			'do_not_build': [
				'keyword_databases',
				'backlink_crawlers',
				'internet_scale_crawlers',
				'serp_databases',
			],
		}
