"""Multi-pass parallel search executor."""
from __future__ import annotations

import time
import uuid
from typing import Any

from ..models import ComponentCandidate, ComponentSearchResponse, ParsedQuery, SearchContext, SearchPlan, SearchSession
from ..providers.manager import ProviderManager
from .merge import is_sufficient, merge_candidates

MAX_PASSES = 3


class SearchExecutor:
	def __init__(self, *, provider_manager: ProviderManager | None = None) -> None:
		self._providers = provider_manager or ProviderManager()

	async def execute(self, plan: SearchPlan) -> ComponentSearchResponse:
		session = SearchSession(
			session_id=uuid.uuid4().hex[:12],
			original_request=plan.parsed.raw,
			plan=plan,
		)
		started = time.perf_counter()
		candidates: list[ComponentCandidate] = []
		providers_queried: list[str] = []
		provider_errors: dict[str, str] = {}
		degraded: list[str] = []

		for pass_number in range(1, MAX_PASSES + 1):
			pass_queries = plan.queries_for_pass(pass_number)
			if not pass_queries:
				continue

			context = SearchContext(parsed=plan.parsed, plan=plan, pass_number=pass_number, queries=pass_queries)
			session.passes_executed.append(pass_number)
			session.queries_executed.extend(q.to_dict() for q in pass_queries)

			pass_started = time.perf_counter()
			outcomes = await self._providers.search_pass(context)
			session.latency_ms[f'pass_{pass_number}'] = round((time.perf_counter() - pass_started) * 1000, 2)

			pass_candidates: list[ComponentCandidate] = []
			for provider_name, outcome in outcomes.items():
				if provider_name not in providers_queried and not outcome.get('error'):
					providers_queried.append(provider_name)
				if outcome.get('error'):
					provider_errors[provider_name] = str(outcome['error'])
					degraded.append(f'{provider_name}_pass_{pass_number}_error')
					continue
				items = outcome.get('candidates') or []
				pass_candidates.extend(items)
				session.results_per_provider[provider_name] = session.results_per_provider.get(provider_name, 0) + len(
					items
				)
				if provider_name not in session.providers_searched:
					session.providers_searched.append(provider_name)

			candidates = merge_candidates(candidates, pass_candidates)
			if is_sufficient(candidates):
				break

		session.total_latency_ms = round((time.perf_counter() - started) * 1000, 2)
		return ComponentSearchResponse(
			query=plan.parsed,
			candidates=candidates,
			search_plan=plan,
			search_session=session,
			providers_queried=providers_queried,
			provider_errors=provider_errors,
			degraded=degraded,
		)

	async def plan_only(self, parsed: ParsedQuery, plan: SearchPlan) -> dict[str, Any]:
		return plan.to_dict()
