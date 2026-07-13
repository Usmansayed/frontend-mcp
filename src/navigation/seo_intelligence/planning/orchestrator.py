"""SEO audit orchestrator — evidence-first pipeline (ADR-027)."""
from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from navigation.seo_intelligence.ai_visibility import AiVisibilityAdapter
from navigation.seo_intelligence.knowledge.graph.store import SeoKnowledgeGraphStore
from navigation.seo_intelligence.models import SeoAuditRequest, SeoAuditResult, SeoEvidenceRef, SeoAuditMode
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

ProgressCallback = Callable[..., None]
CancelCheck = Callable[[], bool]
EvidenceCallback = Callable[[dict[str, Any]], None]


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

	async def _collect_providers_parallel(
		self,
		request: SeoAuditRequest,
		provider_ids: list[str],
		connections: dict[str, str],
		degraded: list[str],
	) -> list[tuple[str, list[SeoEvidenceRef], list[str]]]:
		async def _collect_one(pid: str) -> tuple[str, list[SeoEvidenceRef], list[str]]:
			provider = self._providers.get(pid)
			if provider is None:
				return pid, [], [f'provider_not_implemented:{pid}']
			if connections.get(pid) == 'error':
				return pid, [], [f'provider_error:{pid}']
			if connections.get(pid) == 'not_configured':
				return pid, [], [f'provider_skipped_not_configured:{pid}']
			try:
				evidence, collect_deg = await provider.collect(request)
				return pid, evidence, collect_deg
			except Exception as exc:
				return pid, [], [f'provider_collect_error:{pid}:{exc}']

		if not provider_ids:
			return []

		results = await asyncio.gather(*[_collect_one(pid) for pid in provider_ids], return_exceptions=True)
		out: list[tuple[str, list[SeoEvidenceRef], list[str]]] = []
		for i, result in enumerate(results):
			pid = provider_ids[i]
			if isinstance(result, BaseException):
				degraded.append(f'provider_collect_exception:{pid}:{result}')
				out.append((pid, [], []))
			else:
				out.append(result)
		return out

	async def development_audit(self, request: SeoAuditRequest) -> SeoAuditResult:
		"""Instant Development SEO — browser scan evidence only, no companions or crawl."""
		return await self.audit(
			request,
			progress_callback=None,
			is_cancelled=None,
			on_evidence=None,
			skip_companions=True,
			force_mode=SeoAuditMode.DEVELOPMENT,
		)

	async def audit(
		self,
		request: SeoAuditRequest,
		*,
		progress_callback: ProgressCallback | None = None,
		is_cancelled: CancelCheck | None = None,
		on_evidence: EvidenceCallback | None = None,
		skip_companions: bool = False,
		force_mode: SeoAuditMode | None = None,
	) -> SeoAuditResult:
		def _progress(phase: str, pct: int, message: str, **extra: Any) -> None:
			if progress_callback is not None:
				progress_callback(phase, pct, message, **extra)

		def _cancelled() -> bool:
			return bool(is_cancelled and is_cancelled())

		def _emit_evidence(item: SeoEvidenceRef) -> None:
			if on_evidence is not None:
				on_evidence(item.to_dict())

		degraded: list[str] = []
		mode = force_mode or resolve_effective_mode(request)
		audit_id = new_audit_id()
		previous_audit_id = self._graph.latest_audit_id()
		self._graph.set_website(request.website_url, property_url=request.property_url)

		_progress("bootstrapping", 5, "companions", current_provider="companions")
		if _cancelled():
			raise asyncio.CancelledError("audit_cancelled")

		if (
			not skip_companions
			and mode == SeoAuditMode.PROFESSIONAL
			and auto_start_enabled()
			and os.environ.get('SEO_SKIP_COMPANION_BOOTSTRAP', '').strip().lower() not in {
				'1',
				'true',
				'yes',
			}
		):
			_, companion_notes = await ensure_companions_ready()
			degraded.extend(companion_notes)

		connections = await self._probe_connections(request)
		capability_routes, provider_ids = self._planner.build_plan(request, connections)

		if request.providers:
			provider_ids = [
				pid for pid in request.providers
				if self._registry.get(pid) and provider_allowed(pid, mode)
			]

		pending = list(provider_ids)
		_progress(
			"collecting",
			10,
			"provider_collection",
			current_provider=pending[0] if pending else "",
			pending_providers=pending,
			completed_providers=[],
		)

		all_evidence: list[SeoEvidenceRef] = []
		queried: list[str] = []

		if _cancelled():
			raise asyncio.CancelledError("audit_cancelled")

		collect_results = await self._collect_providers_parallel(
			request,
			provider_ids,
			connections,
			degraded,
		)
		for pid, evidence, collect_deg in collect_results:
			degraded.extend(collect_deg)
			if evidence:
				queried.append(pid)
			for item in evidence:
				self._graph.upsert_evidence(item, base_url=request.website_url)
				_emit_evidence(item)
			all_evidence.extend(evidence)
			if pid in pending:
				pending.remove(pid)
			done = [p for p in provider_ids if p in queried]
			pct = 10 + int(60 * len(done) / max(1, len(provider_ids)))
			_progress(
				"collecting",
				min(pct, 70),
				f"collected:{pid}",
				current_provider=pid,
				completed_providers=done,
				pending_providers=[p for p in provider_ids if p not in done],
			)

		if _cancelled():
			raise asyncio.CancelledError("audit_cancelled")

		_progress("analyzing", 75, "ai_visibility", current_provider="ai-visibility")
		if request.include_ai_visibility and all_evidence:
			ai_evidence, ai_deg = AiVisibilityAdapter().derive(
				all_evidence,
				base_url=request.website_url,
			)
			degraded.extend(ai_deg)
			for item in ai_evidence:
				self._graph.upsert_evidence(item, base_url=request.website_url)
				_emit_evidence(item)
			all_evidence.extend(ai_evidence)
			if ai_evidence and 'ai-visibility' not in queried:
				queried.append('ai-visibility')

		_progress("analyzing", 85, "recommendations", current_provider="recommendations")
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

		_progress("analyzing", 100, "completed", current_provider="")

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
