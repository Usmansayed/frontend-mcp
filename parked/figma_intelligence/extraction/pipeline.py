"""Progressive extraction — providers used only after Selection Planner."""
from __future__ import annotations

from navigation.figma_intelligence.models import FigmaCandidate, FigmaExtractionResult, FigmaIntent
from navigation.figma_intelligence.providers.manager import FigmaProviderRegistry
from navigation.figma_intelligence.selection.models import SelectionBudget, SelectionPlan


async def extract_selection_plan(
	selection_plan: SelectionPlan,
	*,
	intent: FigmaIntent,
	providers: FigmaProviderRegistry,
	provider_preference: str = 'figma_console',
	budget: SelectionBudget | None = None,
) -> tuple[list[FigmaExtractionResult], list[str]]:
	"""Open selected candidates via execution provider (PAT required)."""
	budget = budget or selection_plan.budget
	degraded: list[str] = []
	results: list[FigmaExtractionResult] = []
	api_calls = 0

	for batch_number in selection_plan.batch_numbers:
		batch = [s for s in selection_plan.selected if s.batch_number == batch_number]
		for selected in batch:
			if api_calls >= budget.max_api_calls:
				degraded.append('selection_api_budget_exhausted')
				return results, degraded

			candidate = _resolve_provider_candidate(selected.ranked.candidate, provider_preference)
			provider = providers.get(candidate.provider_id)
			if provider is None:
				degraded.append(f'extract_missing_provider:{candidate.provider_id}')
				continue

			result = await provider.extract_design(candidate, intent=intent)
			results.append(result)
			degraded.extend(result.degraded)
			api_calls += 1

		if _batch_confidence_sufficient(results, budget.confidence_stop_threshold):
			degraded.append(f'selection_stop_batch_{batch_number}')
			break

	return results, degraded


def _resolve_provider_candidate(candidate: FigmaCandidate, preference: str) -> FigmaCandidate:
	if candidate.provider_id:
		return candidate
	return FigmaCandidate(
		candidate_id=candidate.candidate_id,
		title=candidate.title,
		source=candidate.source,
		provider_id=preference,
		file_key=candidate.file_key,
		node_id=candidate.node_id,
		url=candidate.url,
		tags=list(candidate.tags),
		preview_ref=candidate.preview_ref,
		metadata=dict(candidate.metadata),
		profile=candidate.profile,
		discovery_score=candidate.discovery_score,
	)


def _batch_confidence_sufficient(
	extractions: list[FigmaExtractionResult],
	threshold: float,
) -> bool:
	if not extractions:
		return False
	rich = sum(1 for e in extractions if e.tokens or e.components or e.variables)
	score = rich / len(extractions)
	return score >= threshold
