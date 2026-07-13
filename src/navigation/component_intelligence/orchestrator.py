"""Full Component Intelligence pipeline orchestrator."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from .contracts import IntelligenceContracts
from .integration.pipeline import IntegrationPipeline
from .integration_models import (
	CandidateGuidance,
	CodebaseGuidance,
	ConsistencyGuidance,
	DesignSenseGuidance,
	FrameworkGuidance,
	IntegrationRequest,
	IntegrationResult,
	IntegrationStatus,
)
from .models import ComponentCandidate, ComponentSearchResponse
from .parser import parse_query
from .planner import build_search_plan
from .providers import ProviderManager
from .search import SearchExecutor
from .selection import select_foundation
from .validation import RepairLoop
from .guidance.synthesis import SynthesisResult


class ComponentOrchestrator:
	"""Search → select foundation → integrate → validate → repair."""

	def __init__(
		self,
		*,
		provider_manager: ProviderManager | None = None,
		search_executor: SearchExecutor | None = None,
		integration_engine: IntegrationPipeline | None = None,
		repair_loop: RepairLoop | None = None,
		contracts: IntelligenceContracts | None = None,
	) -> None:
		providers = provider_manager or ProviderManager()
		self._contracts = contracts or IntelligenceContracts.default()
		self._search = search_executor or SearchExecutor(provider_manager=providers)
		self._integration = integration_engine or IntegrationPipeline(
			provider_manager=providers,
			contracts=self._contracts,
		)
		self._repair = repair_loop or RepairLoop(contracts=self._contracts)

	async def build_integration_plan(self, request: IntegrationRequest) -> IntegrationResult:
		"""Fast partial plan — selection + install steps, no install/validate/repair."""
		degraded: list[str] = ['integration_plan_only']
		repo_root = Path(request.repo_root) if request.repo_root else Path.cwd()
		plan_override = request.search_plan
		search: ComponentSearchResponse | None = None
		selection = None

		if request.candidate_id:
			candidate = _candidate_stub(request.candidate_id)
			from .integration_models import FoundationSelection

			guidance = CandidateGuidance(
				candidate_id=candidate.id,
				framework=FrameworkGuidance(compatible=True),
				codebase=CodebaseGuidance(),
				design_sense=DesignSenseGuidance(),
				consistency=ConsistencyGuidance(),
				synthesis=SynthesisResult(eligible=True, summary='explicit candidate'),
			)
			selection = FoundationSelection(
				chosen=candidate,
				guidance=guidance,
				rationale='explicit_candidate_id',
			)
		elif request.query:
			parsed = parse_query(request.query)
			plan = build_search_plan(parsed)
			if plan_override:
				from .models import SearchPlan

				plan = SearchPlan.from_dict(plan_override, fallback_parsed=parsed)
			search = await self._search.execute(plan)
			degraded.extend(search.degraded)
			if not search.candidates:
				return IntegrationResult(
					status=IntegrationStatus.FAILED,
					request=request,
					search=search,
					degraded=degraded + ['search_empty'],
				)
			selection = await select_foundation(
				search.candidates,
				repo_root=repo_root,
				parsed_query=parsed,
				max_candidates=min(request.max_candidates_for_guidance, 3),
				contracts=self._contracts,
			)
		else:
			return IntegrationResult(
				status=IntegrationStatus.FAILED,
				request=request,
				degraded=['query_or_candidate_id_required'],
			)

		from .integration.documentation_reader import read_documentation
		from .integration.installation_planner import build_installation_plan
		from .integration_models import IntegrationArtifacts

		try:
			documentation = await asyncio.wait_for(
				read_documentation(
					selection.chosen,
					repo_root=repo_root,
					selection=selection,
					contracts=self._contracts,
				),
				timeout=1.5,
			)
		except (asyncio.TimeoutError, Exception):
			from .integration_models import DocumentationBundle

			documentation = DocumentationBundle.from_candidate(selection.chosen)
			degraded.append('documentation_fast_fallback')

		installation_plan = build_installation_plan(documentation, selection, repo_root=repo_root)
		degraded.extend(installation_plan.degraded)

		artifacts = IntegrationArtifacts(
			documentation=documentation,
			installation_plan=installation_plan,
			degraded=list(dict.fromkeys(degraded)),
		)

		return IntegrationResult(
			status=IntegrationStatus.DEGRADED,
			request=request,
			search=search,
			selection=selection,
			integration=artifacts,
			degraded=list(dict.fromkeys(degraded)),
		)

	async def integrate(
		self,
		request: IntegrationRequest,
		*,
		search_plan: dict[str, Any] | None = None,
	) -> IntegrationResult:
		if request.plan_only and not request.execute_install:
			return await self.build_integration_plan(request)
		degraded: list[str] = []
		repo_root = Path(request.repo_root) if request.repo_root else Path.cwd()
		plan_override = search_plan or request.search_plan

		search: ComponentSearchResponse | None = None
		selection = None

		if request.candidate_id:
			candidate = _candidate_stub(request.candidate_id)
			from .guidance.collectors import collect_guidance
			from .integration_models import FoundationSelection

			parsed = parse_query(request.query) if request.query else None
			guidance = await collect_guidance(
				candidate,
				repo_root=repo_root,
				parsed_query=parsed,
				contracts=self._contracts,
			)
			selection = FoundationSelection(
				chosen=candidate,
				guidance=guidance,
				rationale='explicit_candidate_id',
			)
		elif request.query:
			parsed = parse_query(request.query)
			plan = build_search_plan(parsed)
			if plan_override:
				from .models import SearchPlan

				plan = SearchPlan.from_dict(plan_override, fallback_parsed=parsed)
			search = await self._search.execute(plan)
			degraded.extend(search.degraded)
			if not search.candidates:
				return IntegrationResult(
					status=IntegrationStatus.FAILED,
					request=request,
					search=search,
					degraded=degraded + ['search_empty'],
				)
			selection = await select_foundation(
				search.candidates,
				repo_root=repo_root,
				parsed_query=parsed,
				max_candidates=request.max_candidates_for_guidance,
				contracts=self._contracts,
			)
		else:
			return IntegrationResult(
				status=IntegrationStatus.FAILED,
				request=request,
				degraded=['query_or_candidate_id_required'],
			)

		integration = await self._integration.run(
			selection,
			repo_root=repo_root,
			execute_install=request.execute_install,
		)
		degraded.extend(integration.degraded)

		artifacts, validation, repair_attempts = await self._repair.run(selection, integration, request)
		degraded.extend(validation.degraded)

		status = IntegrationStatus.DEGRADED
		if validation.passed:
			status = IntegrationStatus.COMPLETED
		elif integration.compatibility and integration.compatibility.blockers:
			status = IntegrationStatus.FAILED

		return IntegrationResult(
			status=status,
			request=request,
			search=search,
			selection=selection,
			integration=artifacts,
			validation=validation,
			repair_attempts=repair_attempts,
			degraded=list(dict.fromkeys(degraded)),
		)

	async def select_foundation_only(
		self,
		query: str,
		*,
		repo_root: Path,
		search_plan: dict[str, Any] | None = None,
		max_candidates: int = 12,
	):
		parsed = parse_query(query)
		plan = build_search_plan(parsed)
		if search_plan:
			from .models import SearchPlan

			plan = SearchPlan.from_dict(search_plan, fallback_parsed=parsed)
		search = await self._search.execute(plan)
		if not search.candidates:
			raise ValueError('search_empty')
		selection = await select_foundation(
			search.candidates,
			repo_root=repo_root,
			parsed_query=parsed,
			max_candidates=max_candidates,
			contracts=self._contracts,
		)
		return selection, search


def _candidate_stub(candidate_id: str) -> ComponentCandidate:
	parts = candidate_id.split(':')
	name = parts[-1] if parts else candidate_id
	provider = parts[0] if len(parts) > 1 else 'unknown'
	return ComponentCandidate(
		id=candidate_id,
		provider=provider,
		provider_group=provider,
		name=name,
		title=name,
		category='component',
		description='',
		framework='react',
	)
