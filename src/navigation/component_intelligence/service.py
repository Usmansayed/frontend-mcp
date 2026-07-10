"""Component Intelligence service — search, selection, integration, probes."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import IntelligenceContracts
from .integration_models import FoundationSelection, IntegrationRequest, IntegrationResult
from .models import ComponentSearchResponse, SearchPlan
from .orchestrator import ComponentOrchestrator
from .parser import parse_query
from .planner import build_search_plan
from .probes.form_probe import probe_validation_form
from .providers import ProviderManager
from .search import SearchExecutor


class ComponentIntelligenceService:
	"""Facade for component search, foundation selection, integration, and probes."""

	def __init__(
		self,
		*,
		provider_manager: ProviderManager | None = None,
		contracts: IntelligenceContracts | None = None,
	) -> None:
		self._providers = provider_manager or ProviderManager()
		self._contracts = contracts or IntelligenceContracts.default()
		self._executor = SearchExecutor(provider_manager=self._providers)
		self._orchestrator = ComponentOrchestrator(
			provider_manager=self._providers,
			contracts=self._contracts,
		)

	async def search_components(
		self,
		query: str,
		*,
		search_plan: dict[str, Any] | None = None,
	) -> ComponentSearchResponse:
		parsed = parse_query(query)
		if not parsed.raw.strip() and not parsed.keywords:
			return ComponentSearchResponse(
				query=parsed,
				candidates=[],
				degraded=['query_missing'],
			)
		plan = self.build_search_plan(query, search_plan=search_plan)
		return await self._executor.execute(plan)

	async def select_foundation(
		self,
		query: str,
		*,
		repo_root: str | Path,
		search_plan: dict[str, Any] | None = None,
		max_candidates: int = 12,
	) -> tuple[FoundationSelection, ComponentSearchResponse]:
		return await self._orchestrator.select_foundation_only(
			query,
			repo_root=Path(repo_root),
			search_plan=search_plan,
			max_candidates=max_candidates,
		)

	async def integrate_component(self, request: IntegrationRequest) -> IntegrationResult:
		return await self._orchestrator.integrate(request)

	def build_search_plan(
		self,
		query: str,
		*,
		search_plan: dict[str, Any] | None = None,
	) -> SearchPlan:
		parsed = parse_query(query)
		if search_plan:
			plan = SearchPlan.from_dict(search_plan, fallback_parsed=parsed)
			if plan.planned_queries:
				return plan
		return build_search_plan(parsed)

	def list_search_providers(self) -> list[dict[str, object]]:
		return self._providers.list_providers()

	probe_validation_form = staticmethod(probe_validation_form)
