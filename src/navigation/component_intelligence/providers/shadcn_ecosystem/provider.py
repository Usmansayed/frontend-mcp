"""Shadcn registry ecosystem — unified Group A provider."""
from __future__ import annotations

import asyncio
from typing import Any

from ...models import ComponentCandidate, ComponentDetail, SearchContext
from ...planner.provider_vocabulary import registry_search_terms
from ...parser.query_parser import build_search_text
from ..component import ComponentProviderError
from ..normalize import normalize_shadcn_item
from .catalog import RegistryEntry, fetch_registries_index, fetch_registry_catalog, select_registries_for_plan
from .scoring import score_item

PROVIDER_NAME = 'shadcn_ecosystem'
MAX_RESULTS = 100
CATALOG_CONCURRENCY = 12
MIN_SCORE = 0.12


class ShadcnEcosystemProvider:
	name = PROVIDER_NAME
	group = 'shadcn_ecosystem'
	enabled = True

	def __init__(
		self,
		*,
		max_registries: int = 25,
		max_results: int = MAX_RESULTS,
	) -> None:
		self._max_registries = max_registries
		self._max_results = max_results
		self._catalog_cache: dict[str, list[dict[str, Any]]] = {}

	async def search(self, context: SearchContext) -> list[ComponentCandidate]:
		try:
			index = await asyncio.to_thread(fetch_registries_index)
		except Exception as exc:
			raise ComponentProviderError(f'registries_index_unavailable:{exc}') from exc

		search_text = build_search_text(context.parsed)
		registries = select_registries_for_plan(
			index,
			context.plan.suggested_registries,
			search_text,
			max_registries=self._max_registries,
		)
		if not registries:
			return []

		sem = asyncio.Semaphore(CATALOG_CONCURRENCY)

		async def _load(entry: RegistryEntry) -> tuple[RegistryEntry, list[dict[str, Any]]]:
			async with sem:
				cached = self._catalog_cache.get(entry.catalog_url)
				if cached is not None:
					return entry, cached
				items = await asyncio.to_thread(fetch_registry_catalog, entry.catalog_url)
				self._catalog_cache[entry.catalog_url] = items
				return entry, items

		pairs = await asyncio.gather(*[_load(entry) for entry in registries], return_exceptions=True)
		plan_terms = [q.text for q in context.queries]
		best_by_id: dict[str, ComponentCandidate] = {}

		for pair in pairs:
			if isinstance(pair, BaseException):
				continue
			entry, items = pair
			registry_terms = registry_search_terms(entry.namespace, plan_terms)
			registry_queries = [
				q for q in context.queries if q.text.lower() in {t.lower() for t in registry_terms}
			]
			if not registry_queries:
				registry_queries = context.queries[:4]

			for item in items:
				if not isinstance(item, dict):
					continue
				best_score = 0.0
				best_query = context.queries[0]
				for planned in registry_queries:
					score = score_item(item, context.parsed, planned_query=planned)
					if score > best_score:
						best_score = score
						best_query = planned
				if best_score < MIN_SCORE:
					continue
				candidate = normalize_shadcn_item(
					item,
					provider=self.name,
					provider_group=self.group,
					registry=entry.namespace,
					registry_homepage=entry.homepage,
					item_url_template=entry.item_url_template,
					relevance_score=best_score,
					matched_query=best_query.text,
					search_pass=context.pass_number,
					plan_confidence=best_query.confidence,
				)
				existing = best_by_id.get(candidate.id)
				if existing is None or candidate.relevance_score > existing.relevance_score:
					best_by_id[candidate.id] = candidate

		candidates = sorted(best_by_id.values(), key=lambda c: c.relevance_score, reverse=True)
		return candidates[: self._max_results]

	async def get_component(self, component_id: str) -> ComponentDetail:
		raise ComponentProviderError('not_implemented:get_component')

	async def install(self, component_id: str) -> dict[str, object]:
		raise ComponentProviderError('not_implemented:install')
