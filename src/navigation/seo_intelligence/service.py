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

	def graph_query(self, query_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
		from navigation.seo_intelligence.knowledge.graph.api import SeoGraphAPI

		return SeoGraphAPI(self._graph).query(query_id, params)

	def list_graph_queries(self) -> list[dict[str, Any]]:
		from navigation.seo_intelligence.knowledge.graph.api import SeoGraphAPI

		return SeoGraphAPI(self._graph).list_queries()

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
		latest = self._graph.latest_audit_id()
		if latest:
			snapshot = self._graph.get_audit_snapshot(latest)
			if snapshot:
				return self._audit_result_from_snapshot(snapshot)

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
					root_cause=str(item.get('root_cause') or ''),
					business_impact=str(item.get('business_impact') or ''),
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
			audit_id=latest or '',
			evidence=evidence,
			recommendations=recommendations,
			reasoning_context=(data.get('audits') or {}).get(latest, {}).get('reasoning_context_v2') or {},
		)

	def _audit_result_from_snapshot(self, snapshot: dict[str, object]) -> SeoAuditResult:
		from navigation.seo_intelligence.models import (
			SeoEvidenceKind,
			SeoEvidenceRef,
			SeoRecommendation,
		)

		evidence = []
		for item in (snapshot.get('evidence') or {}).values():
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
		for item in (snapshot.get('recommendations') or {}).values():
			if not isinstance(item, dict):
				continue
			recommendations.append(
				SeoRecommendation(
					recommendation_id=str(item['recommendation_id']),
					title=str(item.get('title') or ''),
					summary=str(item.get('summary') or ''),
					root_cause=str(item.get('root_cause') or ''),
					business_impact=str(item.get('business_impact') or ''),
					priority=str(item.get('priority') or 'medium'),
					category=str(item.get('category') or ''),
					evidence_ids=list(item.get('evidence_ids') or []),
					fix_guidance=str(item.get('fix_guidance') or ''),
					verification_steps=list(item.get('verification_steps') or []),
					confidence=float(item.get('confidence') or 0.0),
					metadata=dict(item.get('metadata') or {}),
				)
			)
		website = self._graph.load().get('website') or {}
		request = SeoAuditRequest(
			website_url=str(website.get('url') or ''),
			property_url=str(website.get('property_url') or ''),
		)
		return SeoAuditResult(
			request=request,
			audit_id=str(snapshot.get('audit_id') or ''),
			mode=str(snapshot.get('mode') or 'development'),
			evidence=evidence,
			recommendations=recommendations,
			reasoning_context=dict(snapshot.get('reasoning_context_v2') or {}),
		)

	def status(self) -> dict[str, Any]:
		from navigation.seo_intelligence.auth.bing import bing_auth_status
		from navigation.seo_intelligence.auth.google import google_oauth_status
		from navigation.seo_intelligence.config.defaults import (
			bundled_librecrawl_base_url,
			oauth_callback_port,
		)
		from navigation.seo_intelligence.providers.librecrawl.client import base_url as librecrawl_url
		from navigation.seo_intelligence.providers.manager import SeoProviderManager
		from navigation.frontend_quality_intelligence.audits.runner import lighthouse_available

		from navigation.seo_intelligence.reasoning.llm_client import ai_reasoning_enabled

		live = SeoProviderManager().list_live_provider_ids()
		from navigation.seo_intelligence.ai_visibility.analyzers.registry import registered_analyzer_ids

		return {
			'module': 'seo_intelligence',
			'phase': 'agent_ready_v4',
			'philosophy': 'evidence_first_seo_intelligence',
			'ai_visibility': {
				'phase': 'ai_readiness_v1',
				'analyzers': len(registered_analyzer_ids()),
				'sources': 'src/navigation/seo_intelligence/ai_visibility/docs/ANALYZER_SOURCES.md',
			},
			'default_mode': 'development',
			'modes': {
				'development': {
					'display_name': 'Development SEO',
					'auth_required': False,
					'providers': ['browser', 'lighthouse', 'librecrawl'],
					'use_while': 'Building a website — validate metadata, CWV, crawl, rendering continuously',
				},
				'professional': {
					'display_name': 'Professional SEO Optimization',
					'auth_required': True,
					'providers': ['search-console', 'analytics-ga4', 'librecrawl', 'lighthouse', 'browser'],
					'use_when': 'User asks to optimize SEO, connect Search Console, or analyze with Google data',
				},
			},
			'architecture': [
				'evidence_collection',
				'evidence_correlation',
				'ai_reasoning_context',
				'recommendation_engine',
				'browser_verification',
			],
			'evidence_providers': [
				'search-console',
				'analytics-ga4',
				'librecrawl',
				'lighthouse',
				'browser',
			],
			'providers_catalog': len(self.list_providers()),
			'capabilities_catalog': len(self.list_capabilities()),
			'providers_live': live,
			'integrations': {
				'google_oauth': google_oauth_status(),
				'bing_oauth': bing_auth_status(),
				'librecrawl_configured': bool(librecrawl_url()),
				'librecrawl_default_url': bundled_librecrawl_base_url(),
				'lighthouse_available': lighthouse_available(),
				'ai_reasoning_available': ai_reasoning_enabled(None),
			},
			'companions': {
				'core_services': ['librecrawl'],
				'auto_start': True,
				'runtime': 'native_process',
				'librecrawl_url': bundled_librecrawl_base_url(),
				'note': 'LibreCrawl starts as a native background process before each audit',
			},
			'onboarding': {
				'steps': ['website_url'],
				'auth_on_demand': True,
				'auth_flow': 'local_browser_oauth',
				'callback_port': oauth_callback_port(),
				'auto_discovers': [
					'search_console',
					'ga4',
					'bing_site',
					'librecrawl',
					'lighthouse',
					'browser',
				],
				'advanced_overrides_only_on_failure': True,
			},
			'graph': self._graph.summary(),
			'do_not_build': [
				'keyword_databases',
				'backlink_crawlers',
				'internet_scale_crawlers',
				'serp_databases',
				'third_party_seo_apps',
			],
		}
