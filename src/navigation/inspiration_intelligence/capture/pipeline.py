"""Progressive capture — providers used only after Selection Planner."""
from __future__ import annotations

from navigation.inspiration_intelligence.models import (
	InspirationCandidate,
	InspirationCaptureResult,
	InspirationIntent,
)
from navigation.inspiration_intelligence.providers.manager import InspirationProviderRegistry
from navigation.inspiration_intelligence.selection.models import SelectionBudget, SelectionPlan


async def capture_selection_plan(
	selection_plan: SelectionPlan,
	*,
	intent: InspirationIntent,
	providers: InspirationProviderRegistry,
	provider_preference: str = 'dribbble',
	budget: SelectionBudget | None = None,
) -> tuple[list[InspirationCaptureResult], list[str]]:
	"""Capture selected candidates via execution provider."""
	budget = budget or selection_plan.budget
	degraded: list[str] = []
	results: list[InspirationCaptureResult] = []
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
				degraded.append(f'capture_missing_provider:{candidate.provider_id}')
				continue

			result = await provider.capture_design(candidate, intent=intent)
			results.append(result)
			degraded.extend(result.degraded)
			api_calls += 1

		if _batch_confidence_sufficient(results, budget.confidence_stop_threshold):
			degraded.append(f'selection_stop_batch_{batch_number}')
			break

	return results, degraded


def _resolve_provider_candidate(
	candidate: InspirationCandidate,
	preference: str,
) -> InspirationCandidate:
	if candidate.provider_id:
		return candidate
	return InspirationCandidate(
		candidate_id=candidate.candidate_id,
		title=candidate.title,
		source=preference,
		provider_id=preference,
		external_id=candidate.external_id,
		url=candidate.url,
		tags=list(candidate.tags),
		preview_ref=candidate.preview_ref,
		metadata=dict(candidate.metadata),
		profile=candidate.profile,
		discovery_score=candidate.discovery_score,
	)


def _batch_confidence_sufficient(
	captures: list[InspirationCaptureResult],
	threshold: float,
) -> bool:
	if not captures:
		return False
	rich = sum(1 for c in captures if c.screenshot_refs)
	score = rich / len(captures)
	return score >= threshold
